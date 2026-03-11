"""Execution Orchestrator — L7 13-step pipeline coordinator.

Steps:
  1.  Receive and validate execution request
  2.  Verify Permission Envelope (independent of L6)
  3.  Check circuit breaker for target database
  4.  Route to correct database pool
  5.  Configure Resource Governor (timeout, row limit, memory cap, BTG)
  6.  Execute query (mock in dev, real DB in prod)
  7.  Enforce resource limits during streaming
  8.  Sanitize results (PII scan + runtime masking)
  9.  Format response (column metadata, typed values, row count)
  10. Optional NL summary
  11. Emit audit event to L8 (async, fire-and-forget)
  12. Return structured response

FAIL-SECURE: every error path returns no results.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Any

import structlog

from app.config import Settings
from app.models.api import (
    ColumnMetadata, ExecutionAuditEvent, ExecutionMetadata,
    ExecutionRequest, ExecutionResponse, PermissionEnvelope,
)
from app.models.enums import AuditFlag, ExecutionStatus
from app.services import audit_emitter, envelope_verifier, result_sanitizer
from app.services.circuit_breaker import get_registry
from app.services.mock_executor import execute_mock
from app.services.real_executor import execute_real
from app.services.resource_governor import ResourceGovernor, ResourceLimitExceeded

logger = structlog.get_logger(__name__)


def _determine_database(request: ExecutionRequest) -> str:
    """Route query to the correct database based on target_database field."""
    db = request.target_database.lower()
    if not db or db in ("mock", "dev", "test"):
        return "mock"
    return db


def _build_column_metadata(
    raw_cols: list[ColumnMetadata],
    envelope: PermissionEnvelope,
) -> list[ColumnMetadata]:
    """Annotate columns with masking flags from the Permission Envelope.

    Once a column is marked MASKED by any table permission, it stays
    masked — we never overwrite a MASKED entry with unmasked.
    """
    # col_name → (is_masked, masking_expr)
    masked_cols: dict[str, tuple[bool, str | None]] = {}
    for tp in envelope.table_permissions:
        for cd in tp.columns:
            key = cd.column_name.lower()
            is_masked = cd.visibility == "MASKED" or cd.masking_expression is not None
            existing_masked, existing_expr = masked_cols.get(key, (False, None))
            masked_cols[key] = (
                is_masked or existing_masked,
                cd.masking_expression or existing_expr,
            )

    enriched = []
    for col in raw_cols:
        key = col.name.lower()
        if key in masked_cols:
            is_masked, expr = masked_cols[key]
            enriched.append(ColumnMetadata(
                name=col.name,
                type=col.type,
                masked=is_masked,
                masking_strategy="PARTIAL" if is_masked else None,
            ))
        else:
            enriched.append(col)
    return enriched


async def run(
    request: ExecutionRequest,
    settings: Settings,
) -> ExecutionResponse:
    """Execute the full L7 pipeline. Always fail-secure."""
    start_ts = time.monotonic()
    log = logger.bind(request_id=request.request_id)
    audit_flags: list[AuditFlag] = []

    def _blocked(
        status: ExecutionStatus,
        detail: str,
        latency: float | None = None,
    ) -> ExecutionResponse:
        ms = (latency or (time.monotonic() - start_ts)) * 1000
        return ExecutionResponse(
            request_id=request.request_id,
            status=status,
            error_detail=detail,
        )

    # ── Step 1: Verify Permission Envelope ────────────────────────────────
    envelope_dict = request.permission_envelope.model_dump()
    is_valid, reason = envelope_verifier.verify(
        envelope_dict,
        settings.envelope_signing_key,
        skip_in_dev=settings.is_dev,
    )
    if not is_valid:
        log.warning("envelope_invalid", reason=reason)
        return _blocked(ExecutionStatus.INVALID_ENVELOPE, reason)

    # ── Step 2: Determine target database & check circuit breaker ─────────
    database = _determine_database(request)
    registry = get_registry(
        settings.circuit_breaker_error_threshold,
        settings.circuit_breaker_cooldown_seconds,
    )
    breaker = registry.get(database)
    if breaker.is_open():
        log.warning("circuit_breaker_open", database=database)
        return _blocked(
            ExecutionStatus.DATABASE_UNAVAILABLE,
            f"Database '{database}' is currently unavailable (circuit breaker open)",
        )

    # ── Step 3: BTG flag ──────────────────────────────────────────────────
    btg_active = request.execution_config.btg_active
    if btg_active:
        audit_flags.append(AuditFlag.EMERGENCY)
        log.info("btg_elevated_execution", database=database)

    # ── Step 4: Determine effective resource limits ───────────────────────
    envelope_max_rows = None
    for tp in request.permission_envelope.table_permissions:
        if tp.max_rows:
            if envelope_max_rows is None:
                envelope_max_rows = tp.max_rows
            else:
                envelope_max_rows = min(envelope_max_rows, tp.max_rows)

    max_rows = min(
        request.execution_config.max_rows,
        envelope_max_rows or settings.default_max_rows,
        settings.default_max_rows,
    )
    if btg_active:
        max_rows = min(max_rows * 5, settings.btg_max_rows)

    governor = ResourceGovernor(
        timeout_seconds=request.execution_config.timeout_seconds,
        max_rows=max_rows,
        max_memory_mb=settings.max_query_memory_mb,
        max_result_size_mb=settings.max_result_size_mb,
        btg_active=btg_active,
        btg_timeout_seconds=settings.btg_timeout_seconds,
        btg_max_rows=settings.btg_max_rows,
    )

    # ── Step 5: Execute query ─────────────────────────────────────────────
    columns: list[ColumnMetadata] = []
    rows: list[list[Any]] = []
    truncated = False
    db_latency_ms = 0.0

    try:
        governor.start()

        if settings.mock_execution or database == "mock":
            raw_cols, rows, truncated = await asyncio.wait_for(
                execute_mock(
                    request.validated_sql,
                    request.parameters,
                    max_rows=max_rows,
                    timeout_seconds=governor.timeout_seconds,
                    latency_ms=settings.mock_execution_latency_ms,
                ),
                timeout=governor.timeout_seconds + 5,
            )
            # Apply resource governor checks on returned rows
            for row in rows:
                try:
                    governor.check_row(len(row))
                except ResourceLimitExceeded as exc:
                    if exc.limit_type == "ROW_LIMIT_EXCEEDED":
                        truncated = True
                        rows = rows[:governor.row_count - 1]
                        audit_flags.append(AuditFlag.TRUNCATED)
                        break
                    raise
        else:
            # Real database execution — Aiven PostgreSQL / MySQL
            raw_cols, rows, truncated = await asyncio.wait_for(
                execute_real(
                    request.validated_sql,
                    request.parameters,
                    target_database=database,
                    max_rows=max_rows,
                    timeout_seconds=governor.timeout_seconds,
                    settings=settings,
                ),
                timeout=governor.timeout_seconds + 5,
            )

        columns = raw_cols
        db_latency_ms = governor.elapsed_seconds() * 1000
        breaker.record_success()

    except asyncio.TimeoutError:
        breaker.record_failure()
        log.warning("query_timeout",
                    timeout=governor.timeout_seconds,
                    database=database)
        return _blocked(
            ExecutionStatus.QUERY_TIMEOUT,
            f"Query exceeded {governor.timeout_seconds}s timeout",
        )
    except ResourceLimitExceeded as exc:
        breaker.record_failure()
        status_map = {
            "QUERY_TIMEOUT": ExecutionStatus.QUERY_TIMEOUT,
            "ROW_LIMIT_EXCEEDED": ExecutionStatus.ROW_LIMIT_EXCEEDED,
            "MEMORY_EXCEEDED": ExecutionStatus.MEMORY_EXCEEDED,
        }
        return _blocked(
            status_map.get(exc.limit_type, ExecutionStatus.DATABASE_ERROR),
            exc.detail,
        )
    except Exception as exc:
        breaker.record_failure()
        log.error("database_error", error=str(exc), database=database)
        return _blocked(ExecutionStatus.DATABASE_ERROR, "Database execution error")

    if truncated:
        audit_flags.append(AuditFlag.TRUNCATED)

    # ── Step 6: Enrich column metadata with masking flags ─────────────────
    columns = _build_column_metadata(columns, request.permission_envelope)

    # ── Step 7: Sanitize results (PII scan) ───────────────────────────────
    try:
        rows, san_result = result_sanitizer.sanitize(rows, columns)
        if san_result.pii_detected > 0:
            audit_flags.append(AuditFlag.SANITIZED)
            log.warning("sanitization_applied",
                        pii_events=san_result.pii_detected,
                        request_id=request.request_id)
    except Exception as exc:
        log.error("sanitization_error", error=str(exc))
        return _blocked(
            ExecutionStatus.SANITIZATION_ERROR,
            "Result sanitization failed — results withheld for safety",
        )

    # ── Step 8: Build response ────────────────────────────────────────────
    total_latency_ms = (time.monotonic() - start_ts) * 1000

    meta = ExecutionMetadata(
        database=database,
        execution_time_ms=round(db_latency_ms, 2),
        rows_fetched=len(rows),
        sanitization_events=san_result.pii_detected,
        memory_used_mb=round(governor.memory_mb, 2),
        truncated=truncated,
        audit_flags=audit_flags,
    )

    response = ExecutionResponse(
        request_id=request.request_id,
        status=ExecutionStatus.SUCCESS,
        columns=columns,
        rows=rows,
        row_count=len(rows),
        truncated=truncated,
        execution_metadata=meta,
    )

    # ── Step 9: Emit audit event to L8 (async, fire-and-forget) ──────────
    user_id = request.security_context.get("user_id", "unknown")
    session_id = request.security_context.get("session_id", "")
    audit_event = ExecutionAuditEvent(
        request_id=request.request_id,
        user_id=user_id,
        session_id=session_id,
        database=database,
        sql_executed=request.validated_sql[:500],  # Truncate for audit log
        dialect=request.dialect,
        rows_returned=len(rows),
        execution_time_ms=round(total_latency_ms, 2),
        resource_usage={
            "memory_mb": governor.memory_mb,
            "elapsed_s": governor.elapsed_seconds(),
        },
        sanitization_events=san_result.pii_detected,
        btg_active=btg_active,
        truncated=truncated,
        status=ExecutionStatus.SUCCESS.value,
        audit_flags=[f.value for f in audit_flags],
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    audit_emitter.emit_background(audit_event, settings.l8_audit_url)

    log.info("execution_complete",
             rows=len(rows),
             latency_ms=f"{total_latency_ms:.1f}",
             database=database,
             sanitization_events=san_result.pii_detected)

    return response
