"""Generation Orchestrator — coordinates the L5 pipeline.

Executes the 8-step pipeline:
  1. Validate Permission Envelope (HMAC + expiry)
  2. Scan question for prompt injection
  3. Generate schema fragments
  4. Assemble prompt
  5. Call LLM
  6. Parse SQL from response
  7. Return result
"""

from __future__ import annotations

import re
import time

import structlog

from app.config import Settings
from app.models.api import (
    FilteredSchema, GenerationMetadata, GenerationRequest,
    GenerationResponse, PermissionEnvelope,
)
from app.models.enums import GenerationStatus
from app.services import (
    envelope_verifier,
    injection_scanner,
    llm_client,
    prompt_assembler,
    response_parser,
)

logger = structlog.get_logger(__name__)


def _extract_sql_tables(sql: str) -> set[str]:
    """Extract table names referenced in FROM/JOIN clauses (best-effort)."""
    tables: set[str] = set()
    for m in re.finditer(r"\b(?:from|join)\s+([a-zA-Z_\"`][\w\.\"`]*)", sql, flags=re.IGNORECASE):
        raw = m.group(1).strip().strip('"`')
        if raw:
            tables.add(raw.lower())
    return tables


def _allowed_table_tokens(schema: FilteredSchema) -> set[str]:
    """Build normalized allowed table identifiers from filtered schema."""
    allowed: set[str] = set()
    for t in schema.tables:
        tid = (t.table_id or "").lower()
        tname = (t.table_name or "").lower()
        if tid:
            allowed.add(tid)
            parts = [p for p in tid.split('.') if p]
            if parts:
                allowed.add(parts[-1])
            if len(parts) >= 2:
                allowed.add('.'.join(parts[-2:]))
        if tname:
            allowed.add(tname)
    return allowed


async def run(request: GenerationRequest, settings: Settings) -> GenerationResponse:
    """Execute the full L5 generation pipeline."""
    start_ts = time.monotonic()
    log = logger.bind(request_id=request.request_id)

    # ── Step 1: Validate Permission Envelope ───────────────────────────────
    # Skip HMAC check in dev/test if signing key is the dev default
    signing_key = settings.envelope_signing_key
    is_valid, reason = envelope_verifier.verify(request.permission_envelope, signing_key)
    if not is_valid and settings.app_env == "production":
        log.warning("Envelope validation failed", reason=reason)
        return GenerationResponse(
            request_id=request.request_id,
            status=GenerationStatus.INVALID_ENVELOPE,
            generation_metadata=GenerationMetadata(
                dialect=request.dialect.value,
            ),
        )

    # ── Step 2: Prompt injection scan ─────────────────────────────────────
    scan_result = injection_scanner.scan(
        request.user_question,
        injection_threshold=settings.injection_risk_threshold,
    )
    if scan_result.is_injection:
        log.warning("Prompt injection blocked", risk_score=scan_result.risk_score,
                    flags=scan_result.flags)
        return GenerationResponse(
            request_id=request.request_id,
            status=GenerationStatus.INJECTION_DETECTED,
            generation_metadata=GenerationMetadata(
                injection_risk_score=scan_result.risk_score,
                dialect=request.dialect.value,
            ),
        )

    sanitized_question = scan_result.sanitized_text

    # ── Steps 3–4: Schema fragments + Prompt assembly ─────────────────────
    assembled = prompt_assembler.assemble_prompt(
        sanitized_question=sanitized_question,
        envelope=request.permission_envelope,
        schema=request.filtered_schema,
        dialect=request.dialect,
        max_prompt_tokens=settings.max_prompt_tokens,
        response_reserve_tokens=settings.response_reserve_tokens,
        default_max_rows=settings.default_max_rows,
        database_metadata=request.database_metadata or None,
    )

    # ── Step 5: LLM call ──────────────────────────────────────────────────
    log.info(
        "llm_prompt_assembled",
        request_id=request.request_id,
        tables_included=assembled.tables_included,
        tables_truncated=assembled.tables_truncated,
        system_prompt=assembled.system_prompt,
        user_message=assembled.user_message,
    )
    try:
        llm_resp = await llm_client.generate(
            system_prompt=assembled.system_prompt,
            user_message=assembled.user_message,
            settings=settings,
        )
    except llm_client.LLMError as e:
        log.error("LLM generation failed", error=str(e))
        return GenerationResponse(
            request_id=request.request_id,
            status=GenerationStatus.GENERATION_FAILED,
            generation_metadata=GenerationMetadata(
                schema_tables_included=assembled.tables_included,
                schema_tables_truncated=assembled.tables_truncated,
                policy_rules_count=assembled.rules_count,
                injection_risk_score=scan_result.risk_score,
                dialect=request.dialect.value,
            ),
        )

    # ── Step 6: Parse response ─────────────────────────────────────────────
    parse_result = response_parser.parse(llm_resp.text)

    total_latency_ms = (time.monotonic() - start_ts) * 1000

    metadata = GenerationMetadata(
        model=llm_resp.model,
        attempt=llm_resp.attempt,
        prompt_tokens=llm_resp.prompt_tokens,
        completion_tokens=llm_resp.completion_tokens,
        generation_latency_ms=llm_resp.latency_ms,
        temperature=0.0,
        schema_tables_included=assembled.tables_included,
        schema_tables_truncated=assembled.tables_truncated,
        policy_rules_count=assembled.rules_count,
        injection_risk_score=scan_result.risk_score,
        dialect=request.dialect.value,
    )

    if parse_result.cannot_answer:
        return GenerationResponse(
            request_id=request.request_id,
            status=GenerationStatus.CANNOT_ANSWER,
            cannot_answer_reason=parse_result.cannot_answer_reason,
            generation_metadata=metadata,
            permission_envelope=request.permission_envelope,
        )

    if not parse_result.success:
        log.warning("SQL parsing failed", error=parse_result.parse_error)
        return GenerationResponse(
            request_id=request.request_id,
            status=GenerationStatus.GENERATION_FAILED,
            generation_metadata=metadata,
        )

    # Hard safety gate: generated SQL must only reference tables in filtered_schema.
    sql_tables = _extract_sql_tables(parse_result.sql or "")
    allowed = _allowed_table_tokens(request.filtered_schema)
    unknown = [t for t in sql_tables if t not in allowed]
    if unknown:
        log.warning("generated_sql_references_unknown_tables", unknown_tables=unknown)
        return GenerationResponse(
            request_id=request.request_id,
            status=GenerationStatus.CANNOT_ANSWER,
            cannot_answer_reason=(
                "Generated SQL referenced tables outside the authorized schema: "
                + ", ".join(sorted(unknown))
            ),
            generation_metadata=metadata,
            permission_envelope=request.permission_envelope,
        )

    # Infer target_database and actual dialect from the tables the LLM used.
    # This is more reliable than the pre-selected dialect because the LLM
    # chose which tables to reference based on the question context.
    inferred_db = ""
    inferred_dialect = request.dialect.value
    if request.database_metadata and sql_tables:
        # Build table_name → db_name map from schema
        tname_to_db: dict[str, str] = {}
        for t in request.filtered_schema.tables:
            parts = (t.table_id or "").split(".")
            short = (t.table_name or parts[-1] if parts else "").lower()
            db = parts[0].lower() if parts else ""
            if short and db:
                tname_to_db[short] = db
        # Find the most-referenced database in the generated SQL
        db_counts: dict[str, int] = {}
        for st in sql_tables:
            db = tname_to_db.get(st, "")
            if db:
                db_counts[db] = db_counts.get(db, 0) + 1
        if db_counts:
            inferred_db = max(db_counts, key=db_counts.get)  # type: ignore[arg-type]
            inferred_dialect = request.database_metadata.get(inferred_db, inferred_dialect)

    log.info("SQL generated successfully",
             dialect=inferred_dialect,
             target_database=inferred_db,
             latency_ms=f"{total_latency_ms:.1f}",
             model=llm_resp.model,
             tables_included=assembled.tables_included,
             generated_sql=parse_result.sql)

    return GenerationResponse(
        request_id=request.request_id,
        status=GenerationStatus.GENERATED,
        sql=parse_result.sql,
        dialect=inferred_dialect,
        target_database=inferred_db,
        generation_metadata=metadata,
        permission_envelope=request.permission_envelope,
    )
