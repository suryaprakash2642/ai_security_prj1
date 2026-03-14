"""Policy Collector.

Gathers all applicable policies for a set of candidate tables
given the user's initial roles.
"""

from __future__ import annotations

from app.models.domain_models import ColumnMetadata, PolicyNode, TableMetadata
from app.services.graph_client import GraphClient


class PolicyCollector:
    """Collects schema and policy metadata from Neo4j."""

    def __init__(self, graph_client: GraphClient):
        self._client = graph_client

    async def collect_metadata(self, table_ids: list[str], initial_roles: list[str]) -> dict[str, TableMetadata]:
        """Fetch all structure and policies for the given tables/roles.

        Returns a dictionary of TableMetadata objects containing the full
        state (domain, column lists, and all attached policies) needed by
        the conflict resolver.
        """
        if not table_ids or not initial_roles:
            return {}

        effective_roles = list(await self._client.get_effective_roles(initial_roles))
        
        # 1. Fetch table-level and domain-level policies
        # 2. Fetch column-level policies + column definitions
        # 3. Fetch all column definitions (to register columns without explicit policies)
        table_raw_policies = await self._client.get_table_policies(table_ids, effective_roles)
        column_raw_policies = await self._client.get_column_policies(table_ids, effective_roles)
        all_columns = await self._client.get_all_table_columns(table_ids)
        table_props = await self._client.get_table_properties(table_ids)

        # Assemble the structured objects
        tables: dict[str, TableMetadata] = {}

        # Parse table policies
        for record in table_raw_policies:
            tid = record["table_id"]
            if tid not in tables:
                tables[tid] = TableMetadata(table_id=tid, table_name=tid.split(".")[-1] if "." in tid else tid)

            pol_node = PolicyNode(**record["policy"])
            # In a real graph we'd distinguish GOVERNS_DOMAIN vs GOVERNS_TABLE
            # For resolution, table-level aggregates them.
            tables[tid].table_policies.append(pol_node)

        # Parse column policies & definitions
        for record in column_raw_policies:
            tid = record["table_id"]
            col_name = record["column_name"]
            col_id = record["column_id"] or f"{tid}.{col_name}"
            
            if tid not in tables:
                tables[tid] = TableMetadata(table_id=tid, table_name=tid.split(".")[-1] if "." in tid else tid)

            table_meta = tables[tid]
            if col_id not in table_meta.columns:
                table_meta.columns[col_id] = ColumnMetadata(
                    column_id=col_id,
                    column_name=col_name,
                    data_type="UNKNOWN"  # Populated fully in real schema discovery
                )
            
            if record.get("policy"):
                pol_node = PolicyNode(**record["policy"])
                table_meta.columns[col_id].policies.append(pol_node)

        # Register all columns from the schema even when no Policy node is attached.
        # Columns absent from column_raw_policies have no explicit policy → the
        # ConflictResolver's default-allow fallback will mark them VISIBLE.
        for record in all_columns:
            tid = record["table_id"]
            col_id = record["column_id"] or f"{tid}.{record['column_name']}"
            col_name = record["column_name"]
            if tid not in tables:
                tables[tid] = TableMetadata(table_id=tid, table_name=tid.split(".")[-1] if "." in tid else tid)
            if col_id not in tables[tid].columns:
                tables[tid].columns[col_id] = ColumnMetadata(
                    column_id=col_id,
                    column_name=col_name,
                    data_type="UNKNOWN"
                )

        # Ensure all requested tables exist in the dict (even if they have no policies,
        # so they can be explicitly DENIED by default)
        for tid in table_ids:
            if tid not in tables:
                tables[tid] = TableMetadata(table_id=tid, table_name=tid.split(".")[-1] if "." in tid else tid)

        # Populate table-level properties (sensitivity_level, domain) from Neo4j
        for tid, props in table_props.items():
            if tid in tables:
                tables[tid].sensitivity_level = props.get("sensitivity_level", 1)
                domain = props.get("domain", "")
                if domain and domain not in tables[tid].domain_tags:
                    tables[tid].domain_tags.append(domain)

        return tables
