"""Validation Orchestrator — L6 pipeline coordinator.

Executes the three gates (in parallel if configured), aggregates results,
and runs the Query Rewriter if all gates pass.

FAIL-SECURE: every error path returns BLOCKED.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import structlog

from app.config import Settings
from app.models.api import (
    GateResult, PermissionEnvelope, RewriteRecord,
    ValidationRequest, ValidationResponse, Violation,
)
from app.models.enums import GateStatus, ValidationDecision, ViolationSeverity
from app.services import (
    envelope_verifier,
    gate1_structural,
    gate2_classification,
    gate3_behavioral,
    query_rewriter,
)
from app.services.sql_parser import parse_sql

logger = structlog.get_logger(__name__)


def _make_blocked(request_id: str, violations: list[Violation],
                  gate_results: dict[str, GateResult],
                  latency_ms: float) -> ValidationResponse:
    return ValidationResponse(
        request_id=request_id,
        decision=ValidationDecision.BLOCKED,
        validated_sql=None,
        violations=violations,
        gate_results=gate_results,
        validation_latency_ms=latency_ms,
    )


async def run(request: ValidationRequest, settings: Settings) -> ValidationResponse:
    """Execute the full L6 validation pipeline. Always fail-secure."""
    start_ts = time.monotonic()
    log = logger.bind(request_id=request.request_id)

    # ── Step 1: Verify Permission Envelope ────────────────────────────────
    is_dev = settings.app_env != "production"
    is_valid, reason = envelope_verifier.verify(
        request.permission_envelope,
        settings.envelope_signing_key,
        skip_in_dev=is_dev,
    )
    if not is_valid:
        log.warning("Envelope verification failed", reason=reason)
        return ValidationResponse(
            request_id=request.request_id,
            decision=ValidationDecision.BLOCKED,
            violations=[Violation(
                gate=0,
                code="INVALID_ENVELOPE",  # type: ignore
                severity=ViolationSeverity.CRITICAL,
                detail=reason,
            )],
            validation_latency_ms=(time.monotonic() - start_ts) * 1000,
        )

    # ── Step 2: Parse SQL ─────────────────────────────────────────────────
    try:
        parsed = parse_sql(request.raw_sql, request.dialect)
    except Exception as e:
        log.error("SQL parsing raised exception", error=str(e))
        return _make_blocked(
            request.request_id,
            [Violation(gate=0, code="UNPARSEABLE_SQL", severity=ViolationSeverity.CRITICAL,  # type: ignore
                       detail=str(e))],
            {},
            (time.monotonic() - start_ts) * 1000,
        )

    if parsed.parse_error:
        log.warning("SQL parse error", error=parsed.parse_error)
        return _make_blocked(
            request.request_id,
            [Violation(gate=1, code="UNPARSEABLE_SQL", severity=ViolationSeverity.CRITICAL,  # type: ignore
                       detail=parsed.parse_error)],
            {},
            (time.monotonic() - start_ts) * 1000,
        )

    # ── Steps 3–5: Run all three gates ────────────────────────────────────
    if settings.enable_parallel_gates:
        g1_coro = asyncio.get_event_loop().run_in_executor(
            None, gate1_structural.run, parsed, request.permission_envelope,
            settings.max_subquery_depth
        )
        g2_coro = asyncio.get_event_loop().run_in_executor(
            None, gate2_classification.run, parsed, request.permission_envelope,
            request.security_context, None
        )
        g3_coro = asyncio.get_event_loop().run_in_executor(
            None, gate3_behavioral.run, parsed, request.raw_sql
        )
        gate1_result, gate2_result, gate3_result = await asyncio.gather(
            g1_coro, g2_coro, g3_coro,
        )
    else:
        gate1_result = gate1_structural.run(
            parsed, request.permission_envelope, settings.max_subquery_depth
        )
        gate2_result = gate2_classification.run(
            parsed, request.permission_envelope, request.security_context
        )
        gate3_result = gate3_behavioral.run(parsed, request.raw_sql)

    gate_results = {
        "gate1": gate1_result,
        "gate2": gate2_result,
        "gate3": gate3_result,
    }

    all_violations = (
        gate1_result.violations +
        gate2_result.violations +
        gate3_result.violations
    )

    # ── Step 6: Aggregate results ─────────────────────────────────────────
    all_passed = (
        gate1_result.status == GateStatus.PASS and
        gate2_result.status == GateStatus.PASS and
        gate3_result.status == GateStatus.PASS
    )

    if not all_passed:
        critical_violations = [v for v in all_violations
                                if v.severity == ViolationSeverity.CRITICAL]
        log.warning("SQL BLOCKED", violations=len(all_violations),
                    critical=len(critical_violations),
                    gate1=gate1_result.status,
                    gate2=gate2_result.status,
                    gate3=gate3_result.status)

        return _make_blocked(
            request.request_id,
            all_violations,
            gate_results,
            (time.monotonic() - start_ts) * 1000,
        )

    # ── Step 7: Query Rewriter ─────────────────────────────────────────────
    try:
        rewrite_result = query_rewriter.rewrite(
            sql=request.raw_sql,
            parsed=parsed,
            envelope=request.permission_envelope,
            dialect=request.dialect,
            gate2_violations=gate2_result.violations,
            gate1_violations=gate1_result.violations,
            default_max_rows=settings.default_max_rows,
        )
    except Exception as e:
        log.error("Query rewriter raised exception", error=str(e))
        return _make_blocked(
            request.request_id,
            [Violation(gate=0, code="REWRITER_ERROR", severity=ViolationSeverity.CRITICAL,  # type: ignore
                       detail=str(e))],
            gate_results,
            (time.monotonic() - start_ts) * 1000,
        )

    if not rewrite_result.success:
        log.error("Query rewriter failed", error=rewrite_result.error)
        return _make_blocked(
            request.request_id,
            all_violations + [Violation(
                gate=0,
                code="REWRITER_ERROR",  # type: ignore
                severity=ViolationSeverity.CRITICAL,
                detail=rewrite_result.error or "Rewriter failed",
            )],
            gate_results,
            (time.monotonic() - start_ts) * 1000,
        )

    final_sql = rewrite_result.sql
    latency_ms = (time.monotonic() - start_ts) * 1000

    log.info("SQL APPROVED",
             rewrites=len(rewrite_result.rewrites),
             latency_ms=f"{latency_ms:.1f}",
             dialect=request.dialect)

    return ValidationResponse(
        request_id=request.request_id,
        decision=ValidationDecision.APPROVED,
        validated_sql=final_sql,
        rewrites_applied=rewrite_result.rewrites,
        gate_results=gate_results,
        violations=all_violations,  # Include non-critical violations for audit
        validation_latency_ms=latency_ms,
    )
