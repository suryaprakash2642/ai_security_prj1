"""Gate 2 — Data Classification Check.

Validates column sensitivity levels against user clearance.
Uses the Permission Envelope + an optional Knowledge Graph lookup
as independent data sources.

This gate operates independently of Gate 1. It can BLOCK even if
Gate 1 passes, and vice versa.
"""

from __future__ import annotations

import time
from typing import Any

import structlog

from app.models.api import GateResult, PermissionEnvelope, Violation
from app.models.enums import GateStatus, ViolationCode, ViolationSeverity
from app.services.sql_parser import ParsedSQL

logger = structlog.get_logger(__name__)

# Sensitivity level matrix (from spec)
# Level 5 columns are always DENIED (never masked, just blocked)
_SENSITIVITY_LABELS = {
    1: "Public",
    2: "Internal",
    3: "Confidential",
    4: "Highly Confidential",
    5: "Restricted",
}

# PII column names that warrant sensitivity >= 3
_PII_COLUMN_NAMES = {
    "ssn", "aadhaar_number", "social_security_number",
    "full_name", "patient_name", "date_of_birth", "dob",
    "phone", "email", "address", "financial_account",
    "insurance_id", "credit_card", "bank_account",
    "mrn", "medical_record_number",
    # Sensitivity 5 (restricted)
    "substance_abuse", "psychotherapy_notes", "hiv_status",
    "genetic_data", "behavioral_health",
}

# Aggregate functions that should not operate on PII
_AGGREGATE_FUNCTIONS = {"count", "max", "min", "avg", "sum", "stddev", "variance"}


def _get_user_clearance(security_context: dict[str, Any]) -> int:
    """Extract user clearance level from SecurityContext."""
    return int(security_context.get("clearance_level", 1))


def _get_col_sensitivity(col_name: str, table_name: str,
                          classification_cache: dict) -> int:
    """Look up column sensitivity from cache or default heuristic."""
    key = f"{table_name}.{col_name}".lower()
    if key in classification_cache:
        return classification_cache[key]

    # Heuristic fallback based on column name patterns
    col_lower = col_name.lower()
    if any(pii in col_lower for pii in ["ssn", "aadhaar", "genetic"]):
        return 4
    if any(pii in col_lower for pii in ["substance", "psychotherapy", "hiv"]):
        return 5
    if any(pii in col_lower for pii in ["dob", "date_of_birth", "phone", "email",
                                         "address", "full_name", "patient_name"]):
        return 3
    if col_lower in {"mrn", "medical_record_number", "insurance_id"}:
        return 3
    return 1  # Default: public


def run(
    parsed: ParsedSQL,
    envelope: PermissionEnvelope,
    security_context: dict[str, Any],
    classification_cache: dict | None = None,
) -> GateResult:
    """Execute Gate 2 data classification check."""
    start = time.monotonic()
    violations: list[Violation] = []
    cache = classification_cache or {}

    if parsed.parse_error or not parsed.is_select:
        # Gate 1 already handled this
        return GateResult(
            status=GateStatus.PASS,
            violations=[],
            latency_ms=(time.monotonic() - start) * 1000,
        )

    user_clearance = _get_user_clearance(security_context)

    # Build table alias -> table_id map from envelope
    allowed_map: dict[str, str] = {}
    for tp in envelope.table_permissions:
        if tp.decision.upper() not in ("DENY",):
            name_part = tp.table_id.split(".")[-1].lower()
            allowed_map[name_part] = tp.table_id
            allowed_map[tp.table_id.lower()] = tp.table_id

    # Check each referenced column
    for col_table, col_name in parsed.columns:
        if col_name in ("*", ""):
            continue

        # Resolve table
        if col_table:
            table_id = allowed_map.get(col_table.lower())
            table_name = col_table.lower()
        else:
            # Unknown table ref — skip classification check
            continue

        if not table_id:
            continue

        tp = envelope.get_table_permission(table_id)

        # ── Masking compliance check ─────────────────────────────────────
        if tp:
            masked_cols = tp.masked_columns
            # Check if this is a SELECT column that should be masked
            is_in_select = any(
                ct == col_table and cn == col_name
                for ct, cn in parsed.select_columns
            ) or any(cn == col_name for _, cn in parsed.select_columns)

            if col_name in masked_cols and is_in_select:
                # Column needs masking — flag for rewriter (not a BLOCK, just HIGH)
                # The rewriter will apply the masking expression
                violations.append(Violation(
                    gate=2,
                    code=ViolationCode.UNMASKED_PII_COLUMN,
                    severity=ViolationSeverity.HIGH,
                    table=table_name,
                    column=col_name,
                    detail=f"PII column '{col_name}' selected without masking expression (rewriter will fix)",
                ))

        # ── Sensitivity vs clearance check ───────────────────────────────
        sensitivity = _get_col_sensitivity(col_name, table_name, cache)

        if sensitivity == 5:
            # Sensitivity 5 is always DENIED — no masking, just BLOCK
            violations.append(Violation(
                gate=2,
                code=ViolationCode.SENSITIVITY_EXCEEDED,
                severity=ViolationSeverity.CRITICAL,
                table=table_name,
                column=col_name,
                detail=f"Column '{col_name}' has sensitivity level 5 (RESTRICTED) — always denied",
            ))
        elif sensitivity > user_clearance:
            violations.append(Violation(
                gate=2,
                code=ViolationCode.SENSITIVITY_EXCEEDED,
                severity=ViolationSeverity.CRITICAL,
                table=table_name,
                column=col_name,
                detail=(f"Column '{col_name}' sensitivity={sensitivity} exceeds "
                        f"user clearance={user_clearance}"),
            ))

        # ── PII in WHERE literal check (MEDIUM — log only) ────────────────
        if sensitivity >= 4 and parsed.has_where:
            # This is a medium-level flag, not a block
            pass  # Would need deeper WHERE analysis — skip for now

    # ── Aggregate on PII check ────────────────────────────────────────────
    # Detect COUNT(ssn), MAX(date_of_birth), etc.
    if parsed.ast:
        import sqlglot.expressions as expr_mod
        for agg_func in parsed.ast.find_all(expr_mod.Anonymous):
            pass  # handled below with typed aggregates

        for agg_type in (expr_mod.Count, expr_mod.Max, expr_mod.Min,
                          expr_mod.Avg, expr_mod.Sum):
            for agg_node in parsed.ast.find_all(agg_type):
                for col in agg_node.find_all(expr_mod.Column):
                    col_name_lower = col.name.lower()
                    sensitivity = _get_col_sensitivity(col_name_lower, "", cache)
                    if sensitivity >= 4:
                        violations.append(Violation(
                            gate=2,
                            code=ViolationCode.AGGREGATE_ON_PII,
                            severity=ViolationSeverity.HIGH,
                            column=col_name_lower,
                            detail=f"Aggregate function on PII column '{col_name_lower}' (sensitivity={sensitivity})",
                        ))

    # Only CRITICAL violations cause FAIL
    critical = [v for v in violations if v.severity == ViolationSeverity.CRITICAL]
    status = GateStatus.FAIL if critical else GateStatus.PASS

    latency_ms = (time.monotonic() - start) * 1000
    logger.debug("Gate 2 complete", status=status, violations=len(violations),
                 latency_ms=f"{latency_ms:.2f}")

    return GateResult(status=status, violations=violations, latency_ms=latency_ms)
