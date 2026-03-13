"""Multi-Strategy Retrieval Pipeline.

Three strategies run concurrently and results are fused:
1. Semantic Vector Search — cosine similarity over table/column embeddings
2. Keyword Exact Match — table name, column name, domain tag matching
3. FK Graph Walk — depth-1/2 expansion from seed tables via foreign keys

Strategy fusion deduplicates, applies multi-strategy bonus,
domain affinity boost, and produces ranked CandidateTable list.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import structlog

from app.cache.cache_service import CacheService
from app.clients.l2_client import L2Client
from app.clients.vector_search import VectorSearchClient
from app.config import Settings, load_ranking_weights
from app.models.enums import DomainHint, QueryIntent, RetrievalStrategy
from app.models.l2_models import L2ForeignKey, L2TableInfo, L2VectorSearchResult
from app.models.retrieval import CandidateTable, EnrichedQuery, IntentResult

logger = structlog.get_logger(__name__)


class RetrievalPipeline:
    """Executes multi-strategy retrieval and fuses results."""

    def __init__(
        self,
        settings: Settings,
        l2_client: L2Client,
        vector_client: VectorSearchClient,
        cache: CacheService,
    ) -> None:
        self._settings = settings
        self._l2 = l2_client
        self._vector = vector_client
        self._cache = cache
        self._weights = load_ranking_weights()

    async def retrieve_candidates(
        self,
        question: str,
        embedding: list[float],
        intent: IntentResult,
        max_tables: int = 10,
        clearance_level: int = 1,
        enriched: EnrichedQuery | None = None,
    ) -> tuple[list[CandidateTable], dict[str, float]]:
        """Run all three strategies concurrently and fuse results.

        Returns:
            (ranked_candidates, timing_ms)
        """
        retrieval_config = self._weights.get("retrieval", {})
        top_k = retrieval_config.get("semantic_top_k", 15)
        min_sim = retrieval_config.get("semantic_min_threshold", 0.35)

        # Extract database_names filter from enrichment
        database_names = enriched.database_hints if enriched and enriched.database_hints else None

        timing: dict[str, float] = {}

        # Run all three strategies concurrently
        t0 = time.monotonic()
        semantic_task = asyncio.create_task(
            self._semantic_search(embedding, top_k, min_sim, intent, clearance_level,
                                  database_names=database_names)
        )
        keyword_task = asyncio.create_task(
            self._keyword_search(question, intent)
        )

        semantic_results = await semantic_task
        timing["semantic_ms"] = (time.monotonic() - t0) * 1000

        t1 = time.monotonic()
        keyword_results = await keyword_task
        timing["keyword_ms"] = (time.monotonic() - t1) * 1000

        # FK walk seeds from top semantic + keyword hits
        seed_tables = _extract_seed_table_ids(semantic_results, keyword_results)

        t2 = time.monotonic()
        fk_results = await self._fk_graph_walk(seed_tables, intent)
        timing["fk_walk_ms"] = (time.monotonic() - t2) * 1000

        # Fuse results
        candidates = self._fuse_strategies(
            semantic_results, keyword_results, fk_results, intent
        )

        # Sort by final_score descending, limit
        candidates.sort(key=lambda c: c.final_score, reverse=True)
        return candidates[:max_tables * 2], timing  # Return 2x for RBAC headroom

    # ── Strategy 1: Semantic Vector Search ──────────────────

    async def _semantic_search(
        self,
        embedding: list[float],
        top_k: int,
        min_similarity: float,
        intent: IntentResult,
        clearance_level: int = 1,
        database_names: list[str] | None = None,
    ) -> list[CandidateTable]:
        """Query pgvector for semantically similar tables.

        Dual-layer cache design (spec §18):
        ─────────────────────────────────────────────────────────────────────
        Layer 1 — Embedding cache (in `embedding_engine.py`):
          - Key: SHA-256(preprocessed_question + model_version + dimensions)
          - Stores: raw embedding vector (float list)
          - Purpose: avoid expensive VoyageAI/OpenAI API call for the same
            question text from ANY user (embeddings are not user-specific).
          - TTL: set in CacheService (default 24h).

        Layer 2 — Semantic search result cache (this method):
          - Key: SHA-256(embedding[:16] bytes) + top_k + "cl{clearance_level}"
          - Stores: list[CandidateTable] JSON
          - Purpose: avoid repeated pgvector ANN scan for the same query.
          - clearance_level is MANDATORY in the key (spec §18): a high-clearance
            user's results must never be served to a lower-clearance user even
            if they embed the identical question text.
          - TTL: shorter than embedding cache (default 5min) — schema changes
            more frequently than embeddings.
        ─────────────────────────────────────────────────────────────────────
        """
        # Check semantic search cache — scoped to clearance level
        import hashlib
        embedding_sig = hashlib.sha256(
            b"|".join(str(v).encode() for v in embedding[:16])
        ).hexdigest()[:16]
        cache_key = f"sem:{embedding_sig}:{top_k}:cl{clearance_level}"
        cached = await self._cache.get_vector_results(cache_key)
        if cached:
            return [CandidateTable(**c) for c in cached]

        results = await self._vector.search_similar(
            embedding, top_k=top_k, min_similarity=min_similarity,
            entity_type="table",
            database_names=database_names,
        )

        # If database filtering returned too few results, retry without filter
        if database_names and len(results) < 2:
            logger.debug("semantic_search_broadening", filtered_count=len(results))
            results = await self._vector.search_similar(
                embedding, top_k=top_k, min_similarity=min_similarity,
                entity_type="table",
            )

        # Column-level semantic search for intent types where a column name
        # in the question is a strong signal (DATA_LOOKUP, DEFINITION,
        # AGGREGATION).  For aggregation, metric column names like
        # `avg_length_of_stay` will outscore abbreviations like `avg_los`,
        # pulling the correct parent table to the top.
        if intent.intent in (QueryIntent.DATA_LOOKUP, QueryIntent.DEFINITION,
                             QueryIntent.AGGREGATION):
            col_results = await self._vector.search_similar(
                embedding, top_k=5, min_similarity=min_similarity + 0.05,
                entity_type="column",
                database_names=database_names,
            )
            results.extend(col_results)

        candidates = _vector_to_candidates(results)

        # Cache results
        if candidates:
            await self._cache.set_vector_results(
                cache_key, [c.model_dump() for c in candidates]
            )

        return candidates

    # ── Strategy 2: Keyword Exact Match ─────────────────────

    async def _keyword_search(
        self, question: str, intent: IntentResult,
    ) -> list[CandidateTable]:
        """Search L2 by table/column names extracted from the question."""
        config = self._weights.get("retrieval", {})
        exact_table_boost = config.get("keyword_exact_table_boost", 0.95)
        exact_column_boost = config.get("keyword_exact_column_boost", 0.80)
        domain_boost = config.get("keyword_domain_boost", 0.60)
        max_domain_adds = config.get("keyword_domain_max_additions", 3)

        candidates: list[CandidateTable] = []

        # Search by question text
        try:
            tables = await self._l2.search_tables(question, limit=10)
            for t in tables:
                candidates.append(CandidateTable(
                    table_id=t.fqn,
                    table_name=t.name,
                    description=t.description,
                    domain=t.domain,
                    sensitivity_level=t.sensitivity_level,
                    hard_deny=t.hard_deny,
                    keyword_score=exact_table_boost,
                    contributing_strategies=[RetrievalStrategy.KEYWORD],
                ))
        except Exception as exc:
            logger.warning("keyword_search_l2_failed", error=str(exc))

        # Domain-based additions
        if intent.domain_hints:
            domain_added = 0
            for hint in intent.domain_hints:
                if domain_added >= max_domain_adds:
                    break
                try:
                    domain_tables = await self._l2.get_tables_by_domain(
                        hint.value, limit=5
                    )
                    for t in domain_tables:
                        if not any(c.table_id == t.fqn for c in candidates):
                            candidates.append(CandidateTable(
                                table_id=t.fqn,
                                table_name=t.name,
                                description=t.description,
                                domain=t.domain,
                                sensitivity_level=t.sensitivity_level,
                                hard_deny=t.hard_deny,
                                keyword_score=domain_boost,
                                contributing_strategies=[RetrievalStrategy.KEYWORD],
                            ))
                            domain_added += 1
                except Exception as exc:
                    logger.debug("domain_search_failed", domain=hint.value, error=str(exc))

        return candidates

    # ── Strategy 3: FK Graph Walk ───────────────────────────

    async def _fk_graph_walk(
        self,
        seed_table_ids: list[str],
        intent: IntentResult,
    ) -> list[CandidateTable]:
        """Expand seed tables via FK edges."""
        config = self._weights.get("retrieval", {})
        depth_1_boost = config.get("fk_depth_1_boost", 0.70)
        depth_2_boost = config.get("fk_depth_2_boost", 0.50)

        candidates: list[CandidateTable] = []
        visited: set[str] = set(seed_table_ids)
        max_depth = 2 if intent.intent == QueryIntent.JOIN_QUERY else 1

        for table_id in seed_table_ids[:5]:  # Cap seed tables for performance
            try:
                fks = await self._get_cached_fks(table_id)
                for fk in fks:
                    target = fk.target_table_fqn or fk.target_table
                    if target and target not in visited:
                        visited.add(target)
                        is_bridge = _is_bridge_table(fk.target_table or target)
                        candidates.append(CandidateTable(
                            table_id=target,
                            table_name=fk.target_table or target.split(".")[-1],
                            fk_score=depth_1_boost,
                            contributing_strategies=[RetrievalStrategy.FK_WALK],
                            fk_path=[table_id, target],
                            is_bridge_table=is_bridge,
                        ))

                        # Depth-2 walk for JOIN_QUERY
                        if max_depth >= 2:
                            try:
                                fks_2 = await self._get_cached_fks(target)
                                for fk2 in fks_2[:3]:
                                    t2 = fk2.target_table_fqn or fk2.target_table
                                    if t2 and t2 not in visited:
                                        visited.add(t2)
                                        candidates.append(CandidateTable(
                                            table_id=t2,
                                            table_name=fk2.target_table or t2.split(".")[-1],
                                            fk_score=depth_2_boost,
                                            contributing_strategies=[RetrievalStrategy.FK_WALK],
                                            fk_path=[table_id, target, t2],
                                            is_bridge_table=_is_bridge_table(
                                                fk2.target_table or t2.split(".")[-1]
                                            ),
                                        ))
                            except Exception:
                                pass
            except Exception as exc:
                logger.debug("fk_walk_failed", table=table_id, error=str(exc))

        return candidates

    async def _get_cached_fks(self, table_id: str) -> list[L2ForeignKey]:
        """Get FK edges with local cache."""
        cached = self._cache.get_fk_local(table_id)
        if cached is not None:
            return cached
        fks = await self._l2.get_foreign_keys(table_id)
        self._cache.set_fk_local(table_id, fks)
        return fks

    # ── Strategy Fusion ─────────────────────────────────────

    def _fuse_strategies(
        self,
        semantic: list[CandidateTable],
        keyword: list[CandidateTable],
        fk_walk: list[CandidateTable],
        intent: IntentResult,
    ) -> list[CandidateTable]:
        """Merge, deduplicate, and score candidates from all strategies."""
        config = self._weights.get("retrieval", {})
        bonus_value = config.get("multi_strategy_bonus_value", 0.08)

        merged: dict[str, CandidateTable] = {}

        for source, candidates in [
            ("semantic", semantic),
            ("keyword", keyword),
            ("fk_walk", fk_walk),
        ]:
            for c in candidates:
                if c.table_id in merged:
                    existing = merged[c.table_id]
                    # Merge scores: take max per strategy
                    existing.semantic_score = max(existing.semantic_score, c.semantic_score)
                    existing.keyword_score = max(existing.keyword_score, c.keyword_score)
                    existing.fk_score = max(existing.fk_score, c.fk_score)
                    # Merge strategies
                    for s in c.contributing_strategies:
                        if s not in existing.contributing_strategies:
                            existing.contributing_strategies.append(s)
                    # Inherit metadata
                    if not existing.description and c.description:
                        existing.description = c.description
                    if not existing.domain and c.domain:
                        existing.domain = c.domain
                    if c.sensitivity_level > existing.sensitivity_level:
                        existing.sensitivity_level = c.sensitivity_level
                    if c.hard_deny:
                        existing.hard_deny = True
                    if c.is_bridge_table:
                        existing.is_bridge_table = True
                else:
                    merged[c.table_id] = c.model_copy()

        # Apply multi-strategy bonus
        for c in merged.values():
            if len(c.contributing_strategies) > 1:
                c.multi_strategy_bonus = bonus_value * (len(c.contributing_strategies) - 1)

            # Compute preliminary final score (ranking engine will refine)
            c.final_score = max(c.semantic_score, c.keyword_score, c.fk_score) + c.multi_strategy_bonus

        return list(merged.values())


# ── Helpers ─────────────────────────────────────────────────


def _vector_to_candidates(results: list[L2VectorSearchResult]) -> list[CandidateTable]:
    """Convert vector search results to CandidateTable objects."""
    seen: set[str] = set()
    candidates: list[CandidateTable] = []

    for r in results:
        # Extract table FQN from entity_fqn
        table_fqn = r.entity_fqn
        if ":col_desc" in table_fqn or ":desc" in table_fqn:
            # Strip embedding key suffix
            table_fqn = table_fqn.rsplit(":", 1)[0]
        if "." in table_fqn and table_fqn.count(".") > 2:
            # Column FQN — extract table portion
            parts = table_fqn.split(".")
            table_fqn = ".".join(parts[:3])

        if table_fqn in seen:
            continue
        seen.add(table_fqn)

        candidates.append(CandidateTable(
            table_id=table_fqn,
            table_name=table_fqn.split(".")[-1] if "." in table_fqn else table_fqn,
            semantic_score=r.similarity,
            contributing_strategies=[RetrievalStrategy.SEMANTIC],
        ))

    return candidates


def _extract_seed_table_ids(
    semantic: list[CandidateTable], keyword: list[CandidateTable],
) -> list[str]:
    """Pick the best seed tables for FK graph walk."""
    seeds: list[str] = []
    seen: set[str] = set()
    for c in sorted(semantic + keyword, key=lambda x: x.final_score or max(x.semantic_score, x.keyword_score), reverse=True):
        if c.table_id not in seen:
            seeds.append(c.table_id)
            seen.add(c.table_id)
        if len(seeds) >= 5:
            break
    return seeds


def _is_bridge_table(table_name: str) -> bool:
    """Heuristic: detect bridge/junction tables by naming patterns."""
    name = table_name.lower()
    patterns = [
        "_to_", "_x_", "_map", "_link", "_bridge", "_assoc",
        "_rel", "_xref", "mapping", "junction",
    ]
    return any(p in name for p in patterns)
