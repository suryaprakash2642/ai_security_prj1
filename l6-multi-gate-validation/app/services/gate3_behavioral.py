"""Gate 3 — Behavioral Analysis.

Detects exploit patterns and malicious SQL constructs using both
AST-level analysis and regex pattern matching.

This gate operates INDEPENDENTLY of the Permission Envelope —
it analyzes SQL purely for dangerous behavioral patterns.
"""

from __future__ import annotations

import re
import time

import structlog
import sqlglot.expressions as exp

from app.models.api import GateResult, Violation
from app.models.enums import GateStatus, ViolationCode, ViolationSeverity
from app.services.sql_parser import ParsedSQL

logger = structlog.get_logger(__name__)


# ── Regex patterns (fallback / complement to AST) ─────────────────────────

_WRITE_OP_RE = re.compile(
    r"\b(INSERT\s+INTO|UPDATE\s+\w+\s+SET|DELETE\s+FROM|DROP\s+(TABLE|DATABASE|INDEX|VIEW)|"
    r"ALTER\s+(TABLE|DATABASE|USER)|CREATE\s+(TABLE|DATABASE|USER|INDEX|VIEW|FUNCTION)|"
    r"TRUNCATE\s+TABLE|MERGE\s+INTO)\b",
    re.IGNORECASE,
)

_SYSTEM_TABLE_RE = re.compile(
    r"\b(information_schema\.|sys\.|pg_catalog\.|pg_class|pg_tables|pg_columns|"
    r"SYSCOLUMNS|SYSOBJECTS|SYSCOMMENTS|ALL_TABLES|ALL_TAB_COLUMNS|DBA_TABLES|"
    r"USER_TABLES|SYSINDEXES|xp_cmdshell|openrowset|opendatasource)\b",
    re.IGNORECASE,
)

_DYNAMIC_SQL_RE = re.compile(
    r"\b(EXEC\s*\(|EXEC\s+[@\w]|sp_executesql|EXECUTE\s+IMMEDIATE|"
    r"PREPARE\s+\w+|EXECUTE\s+\w+|DO\s+\$\$|EVAL\s*\()",
    re.IGNORECASE,
)

_FILE_OP_RE = re.compile(
    r"\b(INTO\s+(OUTFILE|DUMPFILE)|COPY\s+.+\s+TO\s*'|BULK\s+INSERT|"
    r"OPENROWSET\s*\(|OPENDATASOURCE\s*\()\b",
    re.IGNORECASE,
)

_PRIVILEGE_RE = re.compile(
    r"\b(GRANT\s+|REVOKE\s+|SET\s+ROLE|ALTER\s+USER|CREATE\s+USER|"
    r"DROP\s+USER|ALTER\s+ROLE|CREATE\s+ROLE)\b",
    re.IGNORECASE,
)

_COMMENT_RE = re.compile(r"(--[^\n]*|/\*.*?\*/)", re.DOTALL)

_STACKED_QUERIES_RE = re.compile(r";\s*\w", re.DOTALL)


def run(parsed: ParsedSQL, raw_sql: str) -> GateResult:
    """Execute Gate 3 behavioral analysis."""
    start = time.monotonic()
    violations: list[Violation] = []

    sql_upper = raw_sql.upper()

    # ── AST-based checks ──────────────────────────────────────────────────

    # Write operations
    if parsed.has_write_ops or _WRITE_OP_RE.search(raw_sql):
        violations.append(Violation(
            gate=3,
            code=ViolationCode.WRITE_OPERATION,
            severity=ViolationSeverity.CRITICAL,
            detail="Write operation detected (INSERT/UPDATE/DELETE/DROP/ALTER/CREATE/TRUNCATE)",
        ))

    # UNION-based exfiltration
    if parsed.has_union:
        violations.append(Violation(
            gate=3,
            code=ViolationCode.UNION_EXFILTRATION,
            severity=ViolationSeverity.CRITICAL,
            detail="UNION SELECT detected — potential data exfiltration attempt",
        ))

    # Stacked queries (multiple statements)
    if parsed.statement_count > 1 or _STACKED_QUERIES_RE.search(raw_sql):
        violations.append(Violation(
            gate=3,
            code=ViolationCode.STACKED_QUERIES,
            severity=ViolationSeverity.CRITICAL,
            detail="Multiple SQL statements detected (stacked queries)",
        ))

    # ── Regex-based checks ────────────────────────────────────────────────

    # System table access
    if _SYSTEM_TABLE_RE.search(raw_sql):
        violations.append(Violation(
            gate=3,
            code=ViolationCode.SYSTEM_TABLE_ACCESS,
            severity=ViolationSeverity.CRITICAL,
            detail="System table access detected (information_schema/sys.*/pg_catalog/*)",
        ))

    # Dynamic SQL
    if _DYNAMIC_SQL_RE.search(raw_sql):
        violations.append(Violation(
            gate=3,
            code=ViolationCode.DYNAMIC_SQL,
            severity=ViolationSeverity.CRITICAL,
            detail="Dynamic SQL detected (EXEC/sp_executesql/EXECUTE IMMEDIATE)",
        ))

    # File operations
    if _FILE_OP_RE.search(raw_sql):
        violations.append(Violation(
            gate=3,
            code=ViolationCode.FILE_OPERATION,
            severity=ViolationSeverity.CRITICAL,
            detail="File operation detected (INTO OUTFILE/COPY TO/BULK INSERT)",
        ))

    # Privilege escalation
    if _PRIVILEGE_RE.search(raw_sql):
        violations.append(Violation(
            gate=3,
            code=ViolationCode.PRIVILEGE_ESCALATION,
            severity=ViolationSeverity.CRITICAL,
            detail="Privilege escalation operation detected (GRANT/REVOKE/SET ROLE)",
        ))

    # SQL comments (flag for stripping)
    if _COMMENT_RE.search(raw_sql):
        violations.append(Violation(
            gate=3,
            code=ViolationCode.COMMENT_INJECTION,
            severity=ViolationSeverity.MEDIUM,
            detail="SQL comments detected — stripping and re-validating",
        ))

    # ── AST-based: Cartesian products ─────────────────────────────────────
    if parsed.ast and len(parsed.tables) > 1:
        # Check for CROSS JOINs or implicit cross joins
        for join in parsed.ast.find_all(exp.Join):
            # JOIN with no ON or WHERE condition linking the tables
            if not join.args.get("on") and not join.args.get("using"):
                join_kind = str(join.args.get("kind", "")).upper()
                if join_kind in ("CROSS", "") and not parsed.has_where:
                    violations.append(Violation(
                        gate=3,
                        code=ViolationCode.CARTESIAN_PRODUCT,
                        severity=ViolationSeverity.HIGH,
                        detail="Potential cartesian product detected (JOIN without ON condition)",
                    ))
                    break

    # Excessive columns
    if len(parsed.select_columns) > 50:
        violations.append(Violation(
            gate=3,
            code=ViolationCode.EXCESSIVE_COLUMNS,
            severity=ViolationSeverity.MEDIUM,
            detail=f"Excessive columns in SELECT ({len(parsed.select_columns)} > 50)",
        ))

    # Determine pass/fail
    critical = [v for v in violations if v.severity == ViolationSeverity.CRITICAL]
    status = GateStatus.FAIL if critical else GateStatus.PASS

    latency_ms = (time.monotonic() - start) * 1000
    logger.debug("Gate 3 complete", status=status, violations=len(violations),
                 latency_ms=f"{latency_ms:.2f}")

    return GateResult(status=status, violations=violations, latency_ms=latency_ms)
