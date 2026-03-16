"""SQL AST Parser wrapper using sqlglot.

Provides a unified interface for parsing, qualifying, and traversing
SQL ASTs across multiple dialects (PostgreSQL, T-SQL, Oracle).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import sqlglot
import sqlglot.expressions as exp
from sqlglot import errors as sg_errors

import structlog

logger = structlog.get_logger(__name__)

# Dialect mapping
_DIALECT_MAP = {
    "postgresql": "postgres",
    "tsql": "tsql",
    "oracle": "oracle",
    "postgres": "postgres",
}


@dataclass
class ParsedSQL:
    ast: exp.Expression | None
    tables: list[str] = field(default_factory=list)         # fully-qualified table names
    table_aliases: dict[str, str] = field(default_factory=dict)  # alias -> table_name
    columns: list[tuple[str | None, str]] = field(default_factory=list)  # (table, col)
    select_columns: list[tuple[str | None, str]] = field(default_factory=list)
    joins: list[tuple[str, str]] = field(default_factory=list)  # (left_table, right_table)
    has_where: bool = False
    where_conditions: list[str] = field(default_factory=list)
    has_group_by: bool = False
    has_union: bool = False
    has_limit: bool = False
    limit_value: int | None = None
    cte_names: list[str] = field(default_factory=list)
    subquery_depth: int = 0
    is_select: bool = True
    has_write_ops: bool = False
    statement_count: int = 1
    parse_error: str | None = None
    dialect: str = ""


def _count_subquery_depth(node: exp.Expression) -> int:
    """Count maximum subquery nesting depth using BFS (non-recursive)."""
    from collections import deque
    max_depth = 0
    # Queue of (node, current_depth)
    queue: deque = deque([(node, 0)])
    visited: set = set()
    while queue:
        current, depth = queue.popleft()
        node_id = id(current)
        if node_id in visited:
            continue
        visited.add(node_id)
        max_depth = max(max_depth, depth)
        for child in current.args.values():
            if child is None:
                continue
            items = child if isinstance(child, list) else [child]
            for item in items:
                if isinstance(item, exp.Expression) and id(item) not in visited:
                    new_depth = depth + 1 if isinstance(item, (exp.Subquery, exp.CTE)) else depth
                    queue.append((item, new_depth))
    return max_depth


def _extract_table_name(table_node: exp.Table) -> str:
    """Get canonical table name (schema.name or just name)."""
    parts = []
    if table_node.args.get("db"):
        parts.append(table_node.args["db"].name)
    parts.append(table_node.name)
    return ".".join(parts).lower()


def parse_sql(sql: str, dialect: str) -> ParsedSQL:
    """Parse SQL string into a structured ParsedSQL object."""
    sg_dialect = _DIALECT_MAP.get(dialect.lower(), "postgres")
    result = ParsedSQL(ast=None, dialect=dialect)

    # Check for multiple statements (stacked queries)
    try:
        statements = sqlglot.parse(sql, read=sg_dialect, error_level=sg_errors.ErrorLevel.RAISE)
    except Exception as e:
        result.parse_error = f"Parse error: {e}"
        return result

    if not statements:
        result.parse_error = "Empty SQL"
        return result

    result.statement_count = len(statements)
    ast = statements[0]
    result.ast = ast

    # Check for write operations (handle version differences in sqlglot)
    _truncate = getattr(exp, "TruncateTable", None) or getattr(exp, "Truncate", None)
    _command = getattr(exp, "Command", None)
    write_types = tuple(t for t in (
        exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Alter,
        exp.Create, _truncate, _command,
    ) if t is not None)
    if isinstance(ast, write_types):
        result.has_write_ops = True
        result.is_select = False
        return result

    # ── Extract tables ─────────────────────────────────────────────────
    for table_node in ast.find_all(exp.Table):
        tname = _extract_table_name(table_node)
        alias = table_node.alias
        if tname and tname not in result.tables:
            result.tables.append(tname)
        if alias and tname:
            result.table_aliases[alias.lower()] = tname

    # ── Extract CTEs ────────────────────────────────────────────────────
    for cte in ast.find_all(exp.CTE):
        if cte.alias:
            result.cte_names.append(cte.alias.lower())

    # ── Extract columns ─────────────────────────────────────────────────
    for col in ast.find_all(exp.Column):
        table_ref = col.table
        if table_ref:
            # Resolve alias
            resolved = result.table_aliases.get(table_ref.lower(), table_ref.lower())
        else:
            resolved = None
        col_name = col.name.lower() if col.name else "*"
        result.columns.append((resolved, col_name))

    # SELECT columns specifically
    select_node = ast.find(exp.Select)
    if select_node:
        for expr in select_node.expressions:
            if isinstance(expr, exp.Star):
                result.select_columns.append((None, "*"))
            elif isinstance(expr, exp.Column):
                table_ref = expr.table
                resolved = result.table_aliases.get(table_ref.lower(), table_ref.lower()) if table_ref else None
                result.select_columns.append((resolved, expr.name.lower()))
            elif isinstance(expr, (exp.Alias,)):
                inner = expr.this
                if isinstance(inner, exp.Column):
                    table_ref = inner.table
                    resolved = result.table_aliases.get(table_ref.lower(), table_ref.lower()) if table_ref else None
                    result.select_columns.append((resolved, inner.name.lower()))

    # ── Joins ────────────────────────────────────────────────────────────
    from_tables = [_extract_table_name(t) for t in ast.find_all(exp.Table)
                   if not isinstance(t.parent, (exp.Subquery,))]
    for join in ast.find_all(exp.Join):
        join_tbl_node = join.find(exp.Table)
        if join_tbl_node:
            join_tbl = _extract_table_name(join_tbl_node)
            for ft in from_tables:
                if ft != join_tbl:
                    result.joins.append((ft, join_tbl))

    # ── WHERE ────────────────────────────────────────────────────────────
    where_node = ast.find(exp.Where)
    if where_node:
        result.has_where = True
        result.where_conditions = [str(where_node.this)]

    # ── GROUP BY ─────────────────────────────────────────────────────────
    result.has_group_by = bool(ast.find(exp.Group))

    # ── UNION ────────────────────────────────────────────────────────────
    result.has_union = bool(ast.find(exp.Union))

    # ── LIMIT / TOP ──────────────────────────────────────────────────────
    limit_node = ast.find(exp.Limit)
    if limit_node and limit_node.expression:
        result.has_limit = True
        try:
            result.limit_value = int(limit_node.expression.name)
        except (ValueError, TypeError, AttributeError):
            result.has_limit = True

    # ── Subquery depth ────────────────────────────────────────────────────
    result.subquery_depth = _count_subquery_depth(ast)

    return result
