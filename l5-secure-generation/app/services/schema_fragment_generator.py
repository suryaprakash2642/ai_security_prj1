"""Schema Fragment Generator.

Converts filtered schema tables + Permission Envelope decisions into
DDL strings optimized for LLM context window consumption.
"""

from __future__ import annotations

from app.models.api import FilteredTable, PermissionEnvelope, SQLDialect
from app.models.enums import SQLDialect as DialectEnum


def _build_column_ddl(col_name: str, data_type: str, description: str,
                      is_masked: bool, sql_rewrite: str | None) -> str:
    """Build a single column DDL line with annotations."""
    parts = [f"  {col_name:<30} {data_type}"]
    if description:
        parts.append(f"  -- {description}")
    if is_masked and sql_rewrite:
        parts.append(f"  -- MASKED: Use this expression: {sql_rewrite}")
    return "\n".join(parts) if len(parts) > 1 else parts[0]


def _format_fk_comment(table: FilteredTable) -> str:
    """Generate FK join annotations as SQL comments."""
    lines = []
    for fk in table.foreign_keys:
        lines.append(f"-- Join: {fk.from_table}.{fk.from_column} -> {fk.to_table}.{fk.to_column}")
    return "\n".join(lines)


def generate_fragment(table: FilteredTable, envelope: PermissionEnvelope,
                      dialect: SQLDialect = DialectEnum.POSTGRESQL,
                      database_metadata: dict[str, str] | None = None) -> str:
    """Generate a DDL fragment for one table as it should appear in the LLM prompt.

    Only permitted columns appear. Masked columns include rewrite expressions.
    Row filters and aggregation-only requirements are annotated.
    """
    tp = envelope.get_table_permission(table.table_id)
    allowed_col_names: set[str] = set()
    masked_col_map: dict[str, str] = {}  # col_name -> masking expression

    if tp:
        for cd in tp.columns:
            if cd.visibility not in ("HIDDEN",):
                allowed_col_names.add(cd.column_name)
            if cd.visibility == "MASKED" and cd.masking_expression:
                masked_col_map[cd.column_name] = cd.masking_expression
    else:
        # If no envelope decision (envelope-less call), include all columns
        allowed_col_names = {c.name for c in table.columns}

    # Extract database name from table_id FQN (e.g. "apollo_analytics.public.table")
    db_name = (table.table_id or "").split(".")[0] if table.table_id else ""

    # Header — include database name so LLM knows which DB this table is in
    header = f"-- Table: {table.name} | Domain: {table.domain}"
    if db_name and database_metadata:
        db_dialect = database_metadata.get(db_name.lower(), "")
        if db_dialect:
            header += f" | Database: {db_name} ({db_dialect})"
        else:
            header += f" | Database: {db_name}"
    elif db_name:
        header += f" | Database: {db_name}"
    lines = [header]
    if table.nl_description:
        lines.append(f"-- Description: {table.nl_description}")

    # Row filter annotations
    filters = tp.row_filters if tp else table.row_filters
    if filters:
        for f in filters:
            lines.append(f"-- REQUIRED: {f}")

    # Aggregation annotation
    agg_only = (tp.aggregation_only if tp else table.aggregation_only)
    if agg_only:
        lines.append("-- AGGREGATION ONLY: Must use GROUP BY with aggregate functions.")

    # CREATE TABLE
    lines.append(f"CREATE TABLE {table.name} (")
    col_lines = []
    for col in table.columns:
        if col.name not in allowed_col_names:
            continue
        is_masked = col.name in masked_col_map
        sql_rewrite = masked_col_map.get(col.name) or col.sql_rewrite
        col_ddl = f"  {col.name:<30} {col.data_type}"
        if col.nl_description:
            col_ddl += f"  -- {col.nl_description}"
        if is_masked and sql_rewrite:
            col_ddl += f"\n  -- MASKED: Use this expression: {sql_rewrite}"
        col_lines.append(col_ddl)
    lines.append(",\n".join(col_lines))
    lines.append(");")

    # FK comments
    fk_comment = _format_fk_comment(table)
    if fk_comment:
        lines.append(fk_comment)

    return "\n".join(lines)


def generate_all_fragments(tables: list[FilteredTable], envelope: PermissionEnvelope,
                           dialect: SQLDialect = DialectEnum.POSTGRESQL,
                           database_metadata: dict[str, str] | None = None) -> list[tuple[FilteredTable, str]]:
    """Return (table, ddl_string) pairs for all allowed tables, sorted by relevance desc."""
    allowed_ids = envelope.allowed_table_ids
    sorted_tables = sorted(
        [t for t in tables if t.table_id in allowed_ids],
        key=lambda t: t.relevance_score,
        reverse=True,
    )
    return [(t, generate_fragment(t, envelope, dialect, database_metadata=database_metadata))
            for t in sorted_tables]
