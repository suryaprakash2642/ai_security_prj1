"""Column-Level Scoping Engine.

For each allowed table, classifies each column into:
- VISIBLE: included in DDL fragment as-is
- MASKED: included with masking annotation
- HIDDEN: excluded entirely, counted but not named
- COMPUTED: replaced with computed expression

Produces FilteredTable with DDL fragment for LLM consumption.
Hidden column names are NEVER disclosed.
"""

from __future__ import annotations

import time
from typing import Any

import structlog

from app.cache.cache_service import CacheService
from app.clients.l2_client import L2Client
from app.models.enums import ColumnVisibility, TableDecision
from app.models.l2_models import L2ColumnInfo
from app.models.l4_models import ColumnDecision, PermissionEnvelope, TablePermission
from app.models.retrieval import CandidateTable, FilteredTable, ScopedColumn

logger = structlog.get_logger(__name__)


class ColumnScoper:
    """Scopes columns per policy decisions and builds DDL fragments."""

    def __init__(self, l2_client: L2Client, cache: CacheService) -> None:
        self._l2 = l2_client
        self._cache = cache

    async def scope_tables(
        self,
        candidates: list[CandidateTable],
        envelope: PermissionEnvelope,
    ) -> tuple[list[FilteredTable], float]:
        """Scope columns for all surviving candidates.

        Returns:
            (filtered_tables, scoping_latency_ms)
        """
        t0 = time.monotonic()
        filtered: list[FilteredTable] = []

        for candidate in candidates:
            perm = envelope.get_table_permission(candidate.table_id)
            if perm is None:
                continue

            try:
                ft = await self._scope_single_table(candidate, perm)
                filtered.append(ft)
            except Exception as exc:
                logger.warning(
                    "column_scoping_failed",
                    table=candidate.table_id,
                    error=str(exc),
                )

        elapsed_ms = (time.monotonic() - t0) * 1000
        return filtered, elapsed_ms

    async def _scope_single_table(
        self,
        candidate: CandidateTable,
        perm: TablePermission,
    ) -> FilteredTable:
        """Scope a single table's columns."""
        # Fetch column metadata from L2 (with cache)
        columns = await self._get_columns(candidate.table_id)

        # Build column decision map from L4
        decision_map: dict[str, ColumnDecision] = {}
        for cd in perm.columns:
            decision_map[cd.column_name.lower()] = cd

        visible: list[ScopedColumn] = []
        masked: list[ScopedColumn] = []
        hidden_count = 0

        for col in columns:
            col_decision = decision_map.get(col.name.lower())

            if col_decision:
                vis = col_decision.visibility
            else:
                # No explicit decision: visible if not PII, hidden otherwise
                vis = ColumnVisibility.HIDDEN if col.is_pii else ColumnVisibility.VISIBLE

            scoped = ScopedColumn(
                name=col.name,
                data_type=col.data_type,
                visibility=vis,
                is_pk=col.is_pk,
                description=col.description if vis != ColumnVisibility.HIDDEN else "",
            )

            if vis == ColumnVisibility.VISIBLE:
                visible.append(scoped)
            elif vis == ColumnVisibility.MASKED:
                scoped.masking_expression = (
                    col_decision.masking_expression if col_decision else f"MASKED({col.name})"
                )
                masked.append(scoped)
            elif vis == ColumnVisibility.COMPUTED:
                scoped.computed_expression = (
                    col_decision.computed_expression if col_decision else None
                )
                visible.append(scoped)  # Computed columns are visible with expression
            elif vis == ColumnVisibility.HIDDEN:
                hidden_count += 1
                # Column name NOT added to any visible list

        # Build DDL fragment
        ddl = self._build_ddl(
            candidate.table_name, candidate.table_id,
            visible, masked, perm,
        )

        return FilteredTable(
            table_id=candidate.table_id,
            table_name=candidate.table_name,
            description=candidate.description,
            relevance_score=candidate.final_score,
            domain_tags=[candidate.domain] if candidate.domain else [],
            visible_columns=visible,
            masked_columns=masked,
            hidden_column_count=hidden_count,
            row_filters=perm.row_filters,
            aggregation_only=perm.aggregation_only,
            max_rows=perm.max_rows,
            ddl_fragment=ddl,
        )

    async def _get_columns(self, table_id: str) -> list[L2ColumnInfo]:
        """Fetch columns with local cache."""
        cached = self._cache.get_columns_local(table_id)
        if cached is not None:
            return cached
        columns = await self._l2.get_table_columns(table_id)
        self._cache.set_columns_local(table_id, columns)
        return columns

    def _build_ddl(
        self,
        table_name: str,
        table_fqn: str,
        visible: list[ScopedColumn],
        masked: list[ScopedColumn],
        perm: TablePermission,
    ) -> str:
        """Build a DDL-style fragment optimized for LLM consumption."""
        lines: list[str] = []
        lines.append(f"-- Table: {table_fqn}")

        if perm.aggregation_only:
            lines.append("-- NOTE: AGGREGATION ONLY — no row-level SELECT allowed")

        if perm.max_rows:
            lines.append(f"-- NOTE: LIMIT {perm.max_rows} rows maximum")

        if perm.row_filters:
            for rf in perm.row_filters:
                lines.append(f"-- REQUIRED FILTER: {rf}")

        lines.append(f"CREATE TABLE {table_name} (")

        col_lines: list[str] = []
        for col in visible:
            parts = [f"  {col.name}"]
            parts.append(col.data_type or "TEXT")
            if col.is_pk:
                parts.append("PRIMARY KEY")
            if col.visibility == ColumnVisibility.COMPUTED and col.computed_expression:
                parts.append(f"-- COMPUTED: {col.computed_expression}")
            if col.description:
                parts.append(f"-- {col.description[:80]}")
            col_lines.append(" ".join(parts))

        for col in masked:
            expr = col.masking_expression or f"MASKED({col.name})"
            parts = [f"  {col.name}"]
            parts.append(col.data_type or "TEXT")
            parts.append(f"-- MASKED: use {expr}")
            col_lines.append(" ".join(parts))

        lines.append(",\n".join(col_lines))
        lines.append(");")

        return "\n".join(lines)
