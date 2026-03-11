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

import structlog

from app.config import load_ranking_weights
from app.models.enums import DomainHint, QueryIntent
from app.models.retrieval import CandidateTable, IntentResult

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
    ) -> list[CandidateTable]:
        """Score and rank candidates using composite scoring model.

        Args:
            candidates: Pre-fusion candidate tables
            intent: Classified intent with domain hints
            accessible_domains: Domains the user can access

        Returns:
            Candidates sorted by final_score descending.
        """
        w_semantic = self._scoring.get("semantic_similarity", 0.50)
        w_domain = self._scoring.get("domain_affinity", 0.20)
        w_intent = self._scoring.get("intent_match", 0.15)
        w_join = self._scoring.get("join_connectivity", 0.10)
        w_multi = self._scoring.get("multi_strategy_bonus", 0.05)

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

            # Universal anchor boost
            if c.table_name.lower() in universal_anchors:
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
            # Boost fact-like tables
            if any(kw in name for kw in ["fact_", "summary", "stats", "metric"]):
                score += rules.get("fact_table_boost", 0.15)
            if any(kw in name for kw in ["dim_", "lookup", "reference"]):
                score += rules.get("dimension_table_boost", 0.10)

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
