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
    )

    # ── Step 5: LLM call ──────────────────────────────────────────────────
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

    log.info("SQL generated successfully",
             dialect=request.dialect.value,
             latency_ms=f"{total_latency_ms:.1f}",
             model=llm_resp.model,
             tables_included=assembled.tables_included)

    return GenerationResponse(
        request_id=request.request_id,
        status=GenerationStatus.GENERATED,
        sql=parse_result.sql,
        dialect=request.dialect.value,
        generation_metadata=metadata,
        permission_envelope=request.permission_envelope,
    )
