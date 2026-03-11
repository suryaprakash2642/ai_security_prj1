"""Join Graph Construction — builds FK edges between allowed tables only.

Spec compliance (Intelligent-Retrieval-Layer-Specification §11.4):
  - Include FK: both source AND target tables passed RBAC → edge included
  - Exclude FK: either source OR target was DENIED → edge excluded entirely
  - Join restriction overlay: if PermissionEnvelope includes join_restrictions,
    the restricted edge is NOT placed in edges[]. Instead it goes into
    restricted_joins[] which carries domain-level info only (not table FQNs).
    The LLM is told via nl_policy_rules: 'Do NOT join these tables.'

Fix 4 from audit: restricted join edges are REMOVED from edges list entirely
and placed in restricted_joins with domain-level metadata. This prevents the
LLM from learning about the restricted path (spec §13.2 information leakage).
"""

from __future__ import annotations

import structlog

from app.clients.l2_client import L2Client
from app.cache.cache_service import CacheService
from app.models.l4_models import PermissionEnvelope
from app.models.retrieval import CandidateTable, FilteredTable, JoinEdge, JoinGraph

logger = structlog.get_logger(__name__)


class JoinGraphBuilder:
    """Constructs a filtered join graph from allowed tables only.

    Implements spec §11.4:
    - edges: FK relationships between two ALLOWED tables only, no restricted joins
    - restricted_joins: domain-level records of joins blocked by policy (no table FQNs)
    """

    def __init__(self, l2_client: L2Client, cache: CacheService) -> None:
        self._l2 = l2_client
        self._cache = cache

    async def build(
        self,
        allowed_tables: list[FilteredTable],
        candidates: list[CandidateTable],
        envelope: PermissionEnvelope,
    ) -> JoinGraph:
        """Build join graph with only allowed, unrestricted edges.

        Fix 4 (spec §11.4, §13.2):
        - Restricted edges are REMOVED from edges[] (not merely flagged)
        - They are recorded in restricted_joins[] with domain-level info only
        - LLM receives only clean edges[] + domain-level restriction hints via nl_rules
        """
        allowed_ids = {t.table_id for t in allowed_tables}
        edges: list[JoinEdge] = []
        restricted_joins: list[dict[str, str]] = []

        for table in allowed_tables:
            try:
                # Use cached FK data (spec §18 — local FK graph snapshot, 10min TTL)
                cached = self._cache.get_fk_local(table.table_id)
                if cached is not None:
                    fks = cached
                else:
                    fks = await self._l2.get_foreign_keys(table.table_id)
                    self._cache.set_fk_local(table.table_id, fks)

                for fk in fks:
                    target_fqn = fk.target_table_fqn or fk.target_table

                    # Spec §11.4: exclude FK if EITHER endpoint was denied
                    if target_fqn not in allowed_ids:
                        logger.debug(
                            "join_edge_excluded_target_denied",
                            source=table.table_id,
                            target=target_fqn,
                        )
                        continue

                    # Fix 4: check for join restriction BEFORE adding to edges
                    source_domain = self._get_domain(table.table_id, allowed_tables)
                    target_domain = self._get_domain(target_fqn, allowed_tables)
                    restriction = self._find_join_restriction(
                        source_domain, target_domain, envelope,
                    )

                    if restriction:
                        # Spec §11.4: restricted path goes to restricted_joins[] only.
                        # Use from_domain/to_domain keys per spec §12.1 RetrievalResult schema.
                        # Domain names (not table FQNs) to minimize leakage (§13.2).
                        restricted_joins.append({
                            "from_domain": restriction.source_domain or "unknown",
                            "to_domain": restriction.target_domain or "unknown",
                            "reason": restriction.policy_id or "policy_restriction",
                            "effect": "DENY",
                        })
                        logger.info(
                            "join_restricted_excluded",
                            source_domain=source_domain,
                            target_domain=target_domain,
                        )
                        # Edge is NOT added to edges[] — removed entirely (Fix 4)
                    else:
                        edges.append(JoinEdge(
                            source_table=table.table_id,
                            source_column=fk.source_column,
                            target_table=target_fqn,
                            target_column=fk.target_column,
                            constraint_name=fk.constraint_name,
                            is_restricted=False,
                        ))

            except Exception as exc:
                logger.debug(
                    "join_graph_fk_fetch_failed",
                    table=table.table_id,
                    error=str(exc),
                )

        return JoinGraph(edges=edges, restricted_joins=restricted_joins)

    def _find_join_restriction(
        self,
        source_domain: str,
        target_domain: str,
        envelope: PermissionEnvelope,
    ) -> "JoinRestriction | None":
        """Return the first matching JoinRestriction from the PermissionEnvelope.

        Uses the typed JoinRestriction model fields: source_domain / target_domain.
        Returns the JoinRestriction instance if found, None if no restriction applies.
        """
        from app.models.l4_models import JoinRestriction
        for restriction in envelope.join_restrictions:
            src = restriction.source_domain
            tgt = restriction.target_domain
            if (
                (src == source_domain and tgt == target_domain) or
                (src == target_domain and tgt == source_domain)
            ):
                return restriction
        return None

    @staticmethod
    def _get_domain(table_id: str, tables: list[FilteredTable]) -> str:
        """Get the domain for a table from the allowed set."""
        for t in tables:
            if t.table_id == table_id and t.domain_tags:
                return t.domain_tags[0]
        return ""
