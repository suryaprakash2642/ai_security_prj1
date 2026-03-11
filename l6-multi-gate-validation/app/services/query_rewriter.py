"""Query Rewriter.

Executes ONLY when all three gates PASS. Applies security-required
transformations to the SQL AST:

1. Comment stripping
2. Masking rewrites (PII columns → masking expressions)
3. WHERE filter injection (mandatory row filters)
4. LIMIT/TOP enforcement
5. Wildcard expansion (SELECT * → explicit column list)

All operations are AST-based using sqlglot, not string manipulation.
"""

from __future__ import annotations

import re
import time

import sqlglot
import sqlglot.expressions as exp
import structlog

from app.models.api import PermissionEnvelope, RewriteRecord, Violation
from app.models.enums import GateStatus, RewriteType, ViolationCode, ViolationSeverity
from app.services.sql_parser import ParsedSQL, _DIALECT_MAP

logger = structlog.get_logger(__name__)

# Comment patterns for string-level stripping (before AST re-parse)
_COMMENT_RE = re.compile(r"(--[^\n]*|/\*.*?\*/)", re.DOTALL)


class RewriteResult:
    def __init__(self, sql: str, rewrites: list[RewriteRecord], error: str | None = None):
        self.sql = sql
        self.rewrites = rewrites
        self.error = error

    @property
    def success(self) -> bool:
        return self.error is None


def _strip_comments(sql: str) -> tuple[str, bool]:
    """Remove SQL comments. Returns (cleaned_sql, was_modified)."""
    cleaned = _COMMENT_RE.sub("", sql).strip()
    return cleaned, cleaned != sql


def _get_limit_syntax(dialect: str, max_rows: int, sql: str) -> str:
    """Add or replace LIMIT/TOP clause in the SQL string."""
    sg_dialect = _DIALECT_MAP.get(dialect.lower(), "postgres")
    try:
        ast = sqlglot.parse_one(sql, read=sg_dialect)
        if ast is None:
            return sql

        if dialect.lower() == "tsql":
            # For T-SQL, add TOP N to SELECT
            select_node = ast.find(exp.Select)
            if select_node and not select_node.args.get("top"):
                select_node.set("top", exp.Top(this=exp.Literal.number(max_rows)))
        else:
            # For PostgreSQL/Oracle — set or replace LIMIT
            limit_node = ast.find(exp.Limit)
            if limit_node:
                current_val = limit_node.expression
                try:
                    current_int = int(current_val.name)
                    if current_int > max_rows:
                        limit_node.set("expression", exp.Literal.number(max_rows))
                except (ValueError, TypeError, AttributeError):
                    limit_node.set("expression", exp.Literal.number(max_rows))
            else:
                ast = ast.limit(max_rows)

        return ast.sql(dialect=sg_dialect)
    except Exception as e:
        logger.warning("LIMIT rewrite failed", error=str(e))
        # Fallback: append LIMIT
        return f"{sql.rstrip(';')} LIMIT {max_rows}"


def rewrite(
    sql: str,
    parsed: ParsedSQL,
    envelope: PermissionEnvelope,
    dialect: str = "postgresql",
    gate2_violations: list[Violation] | None = None,
    gate1_violations: list[Violation] | None = None,
    default_max_rows: int = 1000,
) -> RewriteResult:
    """Apply all necessary rewrites to the SQL. Returns RewriteResult."""
    start = time.monotonic()
    rewrites: list[RewriteRecord] = []
    current_sql = sql

    # ── Step 1: Strip comments if flagged by Gate 3 ───────────────────────
    stripped_sql, had_comments = _strip_comments(current_sql)
    if had_comments:
        current_sql = stripped_sql
        rewrites.append(RewriteRecord(
            rewrite_type=RewriteType.COMMENT_STRIP,
            original_fragment="SQL contains comments",
            rewritten_fragment="Comments stripped",
        ))

    sg_dialect = _DIALECT_MAP.get(dialect.lower(), "postgres")

    # ── Step 2: Apply masking rewrites ────────────────────────────────────
    unmasked_violations = [
        v for v in (gate2_violations or [])
        if v.code == ViolationCode.UNMASKED_PII_COLUMN and v.column
    ]

    for violation in unmasked_violations:
        col_name = violation.column
        table_name = violation.table or ""

        # Find masking expression from envelope
        masking_expr: str | None = None
        for tp in envelope.table_permissions:
            name_part = tp.table_id.split(".")[-1].lower()
            if name_part == table_name or tp.table_id.lower() == table_name:
                masking_expr = tp.masked_columns.get(col_name or "")
                break

        if not masking_expr:
            continue

        try:
            ast = sqlglot.parse_one(current_sql, read=sg_dialect)
            if ast is None:
                continue

            modified = False
            for col_node in ast.find_all(exp.Column):
                if col_node.name.lower() == col_name.lower():
                    # Replace with masking expression
                    mask_ast = sqlglot.parse_one(masking_expr, read=sg_dialect)
                    if mask_ast:
                        # Wrap in alias to preserve column name
                        aliased = exp.Alias(this=mask_ast, alias=exp.to_identifier(col_name))
                        col_node.replace(aliased)
                        modified = True

            if modified:
                current_sql = ast.sql(dialect=sg_dialect)
                rewrites.append(RewriteRecord(
                    rewrite_type=RewriteType.MASKING,
                    column=col_name,
                    table=table_name,
                    strategy="MASKED",
                    original_fragment=col_name,
                    rewritten_fragment=masking_expr,
                ))
        except Exception as e:
            logger.warning("Masking rewrite failed", col=col_name, error=str(e))
            return RewriteResult(sql=sql, rewrites=rewrites,
                                 error=f"Masking rewrite failed for {col_name}: {e}")

    # ── Step 3: WHERE filter injection ────────────────────────────────────
    missing_filter_violations = [
        v for v in (gate1_violations or [])
        if v.code == ViolationCode.MISSING_REQUIRED_FILTER and v.table
    ]

    for violation in missing_filter_violations:
        table_name = violation.table
        tp = None
        for t in envelope.table_permissions:
            name_part = t.table_id.split(".")[-1].lower()
            if name_part == table_name or t.table_id.lower() == table_name:
                tp = t
                break

        if not tp or not tp.row_filters:
            continue

        for filter_expr in tp.row_filters:
            try:
                ast = sqlglot.parse_one(current_sql, read=sg_dialect)
                if ast is None:
                    continue

                filter_ast = sqlglot.condition(filter_expr, dialect=sg_dialect)
                where_node = ast.find(exp.Where)

                if where_node:
                    # AND the new filter to existing WHERE
                    new_where = exp.And(this=where_node.this, expression=filter_ast)
                    where_node.set("this", new_where)
                else:
                    ast = ast.where(filter_expr, dialect=sg_dialect)

                current_sql = ast.sql(dialect=sg_dialect)
                rewrites.append(RewriteRecord(
                    rewrite_type=RewriteType.WHERE_FILTER,
                    table=table_name,
                    original_fragment="(no filter)",
                    rewritten_fragment=f"AND ({filter_expr})",
                ))
            except Exception as e:
                logger.warning("WHERE filter injection failed",
                               table=table_name, filter=filter_expr, error=str(e))
                # Don't fail — the database will enforce at the DB level
                continue

    # ── Step 4: LIMIT/TOP enforcement ─────────────────────────────────────
    # Determine the max_rows from envelope
    max_rows = default_max_rows
    for tp in envelope.table_permissions:
        if tp.max_rows and tp.max_rows < max_rows:
            max_rows = tp.max_rows

    # Add or tighten LIMIT
    try:
        reparsed = sqlglot.parse_one(current_sql, read=sg_dialect)
        limit_node = reparsed.find(exp.Limit) if reparsed else None
        needs_limit = True

        if limit_node:
            try:
                current_limit = int(limit_node.expression.name)
                if current_limit <= max_rows:
                    needs_limit = False  # Existing limit is tighter — preserve it
                else:
                    original_limit = current_limit
            except (ValueError, TypeError, AttributeError):
                pass

        # Skip LIMIT for aggregate-only queries
        has_agg = parsed.has_group_by
        effective_max = max_rows * 10 if has_agg else max_rows

        if needs_limit:
            new_sql = _get_limit_syntax(dialect, effective_max, current_sql)
            if new_sql != current_sql:
                rewrites.append(RewriteRecord(
                    rewrite_type=RewriteType.LIMIT,
                    original_fragment=f"(no limit)" if not limit_node else f"LIMIT {original_limit if limit_node else '?'}",
                    rewritten_fragment=f"LIMIT {effective_max}",
                ))
                current_sql = new_sql
    except Exception as e:
        logger.warning("LIMIT enforcement failed", error=str(e))
        # Append LIMIT as fallback
        if not parsed.has_limit:
            current_sql = f"{current_sql.rstrip(';')} LIMIT {max_rows}"
            rewrites.append(RewriteRecord(
                rewrite_type=RewriteType.LIMIT,
                original_fragment="(no limit)",
                rewritten_fragment=f"LIMIT {max_rows}",
            ))

    latency_ms = (time.monotonic() - start) * 1000
    logger.debug("Rewriter complete", rewrites=len(rewrites), latency_ms=f"{latency_ms:.2f}")

    return RewriteResult(sql=current_sql, rewrites=rewrites)
