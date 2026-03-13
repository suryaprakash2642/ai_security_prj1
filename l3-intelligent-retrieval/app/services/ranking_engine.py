"""Domain-Aware Ranking Engine — composite scoring model.

Computes final relevance score using configurable weights:
  final = semantic*0.50 + domain_affinity*0.20 + intent_match*0.15
          + join_connectivity*0.10 + multi_strategy*0.05

Includes:
- Universal join anchor boosts (patients, encounters)
- Super-protected table demotion
- Intent-specific scoring adjustments
"""

from __future__ import annotations

import math
import re

import structlog

from app.config import load_ranking_weights
from app.models.enums import DomainHint, QueryIntent
from app.models.retrieval import CandidateTable, EnrichedQuery, IntentResult

logger = structlog.get_logger(__name__)


class RankingEngine:
    """Applies configurable composite scoring to candidate tables."""

    def __init__(self) -> None:
        self._config = load_ranking_weights()
        self._scoring = self._config.get("scoring", {})
        self._domain_config = self._config.get("domain_affinity", {})
        self._intent_config = self._config.get("intent_scoring", {})

    def rank(
        self,
        candidates: list[CandidateTable],
        intent: IntentResult,
        accessible_domains: set[str],
        enriched: EnrichedQuery | None = None,
    ) -> list[CandidateTable]:
        """Score and rank candidates using composite scoring model.

        Args:
            candidates: Pre-fusion candidate tables
            intent: Classified intent with domain hints
            accessible_domains: Domains the user can access
            enriched: Optional enrichment data for TF-IDF scoring

        Returns:
            Candidates sorted by final_score descending.
        """
        # Apply TF-IDF reranking if enrichment available
        if enriched:
            self._apply_tfidf_rerank(candidates, enriched)

        w_semantic = self._scoring.get("semantic_similarity", 0.40)
        w_domain = self._scoring.get("domain_affinity", 0.20)
        w_intent = self._scoring.get("intent_match", 0.15)
        w_join = self._scoring.get("join_connectivity", 0.10)
        w_multi = self._scoring.get("multi_strategy_bonus", 0.05)
        w_tfidf = self._scoring.get("tfidf_score", 0.10)

        universal_anchors = set(
            self._domain_config.get("universal_anchors", ["patients", "encounters", "providers"])
        )
        anchor_boost = self._domain_config.get("universal_anchor_boost", 0.15)
        protected_demotion = self._domain_config.get("super_protected_demotion", 0.40)

        hint_domains = {h.value for h in intent.domain_hints}

        for c in candidates:
            # Domain affinity
            domain_score = 0.0
            if c.domain:
                if c.domain in hint_domains:
                    domain_score = 1.0
                elif c.domain in accessible_domains:
                    domain_score = 0.5
            c.domain_affinity_score = domain_score

            # Universal anchor boost — suppressed for aggregate/trend/comparison
            # intents so analytics/summary tables can outrank transactional anchors.
            _aggregate_intents = (
                QueryIntent.AGGREGATION,
                QueryIntent.TREND,
                QueryIntent.COMPARISON,
            )
            # Also suppress anchor boost if AGGREGATION was among the matched
            # intents (even if another intent won the classification).
            _has_aggregate_signal = (
                intent.intent in _aggregate_intents
                or QueryIntent.AGGREGATION.value in intent.secondary_intents
            )
            if c.table_name.lower() in universal_anchors and not _has_aggregate_signal:
                c.domain_affinity_score = max(c.domain_affinity_score, 0.8)
                c.domain_affinity_score += anchor_boost

            # Intent-specific scoring
            intent_score = self._compute_intent_score(c, intent)
            c.intent_score = intent_score

            # Super-protected demotion (sensitivity 5)
            protection_factor = 1.0
            if c.sensitivity_level >= 5:
                protection_factor = 1.0 - protected_demotion

            # Join connectivity (from FK score + bridge table bonus)
            join_score = c.fk_score
            if c.is_bridge_table and intent.intent == QueryIntent.JOIN_QUERY:
                join_score = min(join_score + 0.2, 1.0)

            # Composite score
            raw_score = (
                c.semantic_score * w_semantic
                + c.domain_affinity_score * w_domain
                + c.intent_score * w_intent
                + join_score * w_join
                + c.multi_strategy_bonus * w_multi
                + c.tfidf_score * w_tfidf
            )

            c.final_score = round(raw_score * protection_factor, 4)

        # Sort descending
        candidates.sort(key=lambda x: x.final_score, reverse=True)
        return candidates

    def _compute_intent_score(
        self, candidate: CandidateTable, intent: IntentResult,
    ) -> float:
        """Compute intent-specific bonus for a candidate."""
        intent_key = intent.intent.value
        rules = self._intent_config.get(intent_key, {})

        score = 0.0
        name = candidate.table_name.lower()
        desc = candidate.description.lower()

        if intent.intent == QueryIntent.AGGREGATION:
            # Let semantic + TF-IDF scoring handle table relevance.
            # No hardcoded table-name boosts — keeps scoring table-agnostic.
            pass

        elif intent.intent == QueryIntent.TREND:
            # Boost tables with time columns
            if any(kw in desc for kw in ["date", "timestamp", "time", "period"]):
                score += rules.get("time_column_boost", 0.15)

        elif intent.intent == QueryIntent.JOIN_QUERY:
            if candidate.is_bridge_table:
                score += rules.get("bridge_table_boost", 0.20)
            if candidate.fk_score > 0:
                score += rules.get("fk_connectivity_boost", 0.15)

        elif intent.intent == QueryIntent.DATA_LOOKUP:
            # Boost if keywords match column names
            for kw in intent.matched_keywords:
                if kw in desc or kw in name:
                    score += rules.get("column_match_boost", 0.20)
                    break

        elif intent.intent == QueryIntent.DEFINITION:
            for kw in intent.matched_keywords:
                if kw in desc or kw in name:
                    score += rules.get("column_match_boost", 0.15)
                    break

        return min(score, 1.0)

    # ── TF-IDF reranking ────────────────────────────────────

    def _apply_tfidf_rerank(
        self,
        candidates: list[CandidateTable],
        enriched: EnrichedQuery,
    ) -> None:
        """Score candidates using manual TF-IDF against enrichment terms."""
        if not candidates:
            return

        # Build query terms from enrichment
        query_terms: list[str] = []
        query_terms.extend(self._tokenize(enriched.original_question))
        for syn in enriched.synonyms:
            query_terms.extend(self._tokenize(syn))
        for hint in enriched.table_hints:
            query_terms.extend(self._tokenize(hint))

        if not query_terms:
            return

        # Build document corpus from candidate descriptions + table names
        docs: list[set[str]] = []
        for c in candidates:
            tokens = set(self._tokenize(c.description)) | set(self._tokenize(c.table_name))
            docs.append(tokens)

        n_docs = len(docs)

        # Compute IDF for each query term
        idf: dict[str, float] = {}
        for term in set(query_terms):
            doc_freq = sum(1 for d in docs if term in d)
            idf[term] = math.log((n_docs + 1) / (doc_freq + 1)) + 1.0

        # Score each candidate
        for i, c in enumerate(candidates):
            doc_tokens = docs[i]
            if not doc_tokens:
                continue

            score = 0.0
            for term in set(query_terms):
                if term in doc_tokens:
                    tf = 1.0  # Binary TF (present or not)
                    score += tf * idf.get(term, 1.0)

            # Normalize to 0-1 range
            max_possible = sum(idf.get(t, 1.0) for t in set(query_terms))
            c.tfidf_score = min(score / max_possible, 1.0) if max_possible > 0 else 0.0

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Simple tokenizer: lowercase, split on non-alphanumeric, filter short tokens."""
        if not text:
            return []
        return [t for t in re.split(r'[^a-z0-9]+', text.lower()) if len(t) >= 2]
