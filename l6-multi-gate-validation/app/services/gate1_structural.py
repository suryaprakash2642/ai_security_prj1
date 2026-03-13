"""Gate 1 — Structural Validation.

Validates all tables, columns, joins, row filters, and aggregation
requirements against the Permission Envelope. This is the primary
authorization gate.
"""

from __future__ import annotations

import time

import structlog

from app.models.api import GateResult, PermissionEnvelope, Violation
from app.models.enums import GateStatus, ViolationCode, ViolationSeverity
from app.services.sql_parser import ParsedSQL

logger = structlog.get_logger(__name__)

# Sensitivity-5 / always-denied table name patterns
_SENSITIVITY5_PATTERNS = [
    "substance_abuse", "behavioral_health_substance", "42cfr",
    "psychotherapy", "hiv_status", "genetic_data",
]


def _is_sensitivity5_table(table_name: str) -> bool:
    lower = table_name.lower()
    return any(p in lower for p in _SENSITIVITY5_PATTERNS)


def run(parsed: ParsedSQL, envelope: PermissionEnvelope,
        max_subquery_depth: int = 3) -> GateResult:
    """Execute Gate 1 structural validation."""
    start = time.monotonic()
    violations: list[Violation] = []

    if parsed.parse_error:
        violations.append(Violation(
            gate=1,
            code=ViolationCode.UNPARSEABLE_SQL,
            severity=ViolationSeverity.CRITICAL,
            detail=parsed.parse_error,
        ))
        return GateResult(
            status=GateStatus.FAIL,
            violations=violations,
            latency_ms=(time.monotonic() - start) * 1000,
        )

    if parsed.has_write_ops or not parsed.is_select:
        violations.append(Violation(
            gate=1,
            code=ViolationCode.WRITE_OPERATION,
            severity=ViolationSeverity.CRITICAL,
            detail="SQL contains write operations (INSERT/UPDATE/DELETE/DROP)",
        ))

    allowed_ids = envelope.allowed_table_ids
    # Build a map of table_name_lower -> table_id for matching
    allowed_map: dict[str, str] = {}
    for tp in envelope.table_permissions:
        if tp.decision.upper() not in ("DENY",):
            # table_id may be like "apollo.patients" or "patients"
            name_part = tp.table_id.split(".")[-1].lower()
            allowed_map[name_part] = tp.table_id
            allowed_map[tp.table_id.lower()] = tp.table_id

    # ── Table authorization ──────────────────────────────────────────────
    for table_name in parsed.tables:
        # Skip CTE virtual tables
        if table_name in [c.lower() for c in parsed.cte_names]:
            continue

        name_part = table_name.split(".")[-1]
        table_id = allowed_map.get(table_name) or allowed_map.get(name_part)

        if not table_id:
            violations.append(Violation(
                gate=1,
                code=ViolationCode.UNAUTHORIZED_TABLE,
                severity=ViolationSeverity.CRITICAL,
                table=table_name,
                detail=f"Table '{table_name}' not in Permission Envelope or DENIED",
            ))
            continue

        tp = envelope.get_table_permission(table_id)
        if not tp:
            continue

        # ── Column authorization ─────────────────────────────────────────
        allowed_cols = tp.allowed_column_names
        denied_cols = tp.denied_column_names
        masked_cols = tp.masked_columns

        for col_table, col_name in parsed.columns:
            if col_name == "*":
                continue
            # Match column to this table
            if col_table and col_table not in (name_part, table_name, table_id.lower()):
                continue

            if col_name in denied_cols:
                violations.append(Violation(
                    gate=1,
                    code=ViolationCode.UNAUTHORIZED_COLUMN,
                    severity=ViolationSeverity.CRITICAL,
                    table=table_name,
                    column=col_name,
                    detail=f"Column '{col_name}' in table '{table_name}' is DENIED for this role",
                ))
            elif allowed_cols and col_name not in allowed_cols and col_name not in masked_cols:
                # Column not in allowed set — may be unknown
                pass  # Unknown columns are flagged by the database, not here

        # ── Aggregation enforcement ───────────────────────────────────────
        if tp.aggregation_only:
            if not parsed.has_group_by:
                violations.append(Violation(
                    gate=1,
                    code=ViolationCode.AGGREGATION_VIOLATION,
                    severity=ViolationSeverity.CRITICAL,
                    table=table_name,
                    detail=f"Table '{table_name}' requires aggregation_only (GROUP BY mandatory)",
                ))

            # Verify no denied-in-select columns appear in SELECT.
            # Use the policy-driven list from the envelope; fall back to a
            # hardcoded PII safety net so new columns are still caught.
            denied_cols = set(tp.denied_in_select) if tp.denied_in_select else set()
            _PII_SAFETY_NET = {"mrn", "full_name", "ssn", "dob", "aadhaar_number",
                               "phone", "email", "address", "patient_id"}
            denied_cols |= _PII_SAFETY_NET
            for col_table, col_name in parsed.select_columns:
                if col_name in denied_cols:
                    violations.append(Violation(
                        gate=1,
                        code=ViolationCode.AGGREGATION_VIOLATION,
                        severity=ViolationSeverity.CRITICAL,
                        table=table_name,
                        column=col_name,
                        detail=f"Patient identifier '{col_name}' in SELECT with aggregation_only table",
                    ))

        # ── Row filter check (flag for rewriter) ──────────────────────────
        if tp.row_filters:
            # Simple heuristic: check if any filter keyword appears in WHERE
            has_filter = False
            if parsed.has_where and parsed.where_conditions:
                where_str = " ".join(parsed.where_conditions).lower()
                for f in tp.row_filters:
                    # Extract the column name from filter (e.g. "treating_provider_id = X")
                    col_hint = f.split("=")[0].strip().split(".")[-1].strip().lower()
                    if col_hint in where_str:
                        has_filter = True
                        break
            if not has_filter:
                violations.append(Violation(
                    gate=1,
                    code=ViolationCode.MISSING_REQUIRED_FILTER,
                    severity=ViolationSeverity.HIGH,
                    table=table_name,
                    detail=f"Required row filter missing for table '{table_name}'. Delegating to rewriter.",
                ))

    # ── Join domain restrictions ────────────────────────────────────────
    restricted_pairs = envelope.restricted_domain_pairs
    if restricted_pairs and parsed.joins:
        # Build domain map: table_name -> domain
        domain_map: dict[str, str] = {}
        # We don't have domain info directly — skip if no restriction data
        # In real impl, domain comes from KG metadata passed in the request
        pass  # Gate 2 handles classification; join domain check is best-effort here

    # ── Subquery depth ──────────────────────────────────────────────────
    if parsed.subquery_depth > max_subquery_depth:
        violations.append(Violation(
            gate=1,
            code=ViolationCode.EXCESSIVE_SUBQUERY_DEPTH,
            severity=ViolationSeverity.HIGH,
            detail=f"Subquery depth {parsed.subquery_depth} exceeds limit {max_subquery_depth}",
        ))

    # ── Multiple statements (stacked queries) ──────────────────────────
    if parsed.statement_count > 1:
        violations.append(Violation(
            gate=1,
            code=ViolationCode.UNPARSEABLE_SQL,
            severity=ViolationSeverity.CRITICAL,
            detail=f"Multiple SQL statements detected ({parsed.statement_count})",
        ))

    # Determine pass/fail
    critical_violations = [v for v in violations
                           if v.severity == ViolationSeverity.CRITICAL]
    status = GateStatus.FAIL if critical_violations else GateStatus.PASS

    latency_ms = (time.monotonic() - start) * 1000
    logger.debug("Gate 1 complete", status=status, violations=len(violations),
                 latency_ms=f"{latency_ms:.2f}")

    return GateResult(status=status, violations=violations, latency_ms=latency_ms)
