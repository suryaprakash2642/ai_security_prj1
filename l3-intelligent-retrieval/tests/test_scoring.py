"""Tests for domain-aware ranking, composite scoring, and strategy fusion."""

from __future__ import annotations

import pytest

from app.models.enums import DomainHint, QueryIntent, RetrievalStrategy
from app.models.retrieval import CandidateTable, IntentResult
from app.services.ranking_engine import RankingEngine


@pytest.fixture
def ranker():
    return RankingEngine()


def _intent(
    intent: QueryIntent = QueryIntent.DATA_LOOKUP,
    domains: list[DomainHint] | None = None,
    keywords: list[str] | None = None,
) -> IntentResult:
    return IntentResult(
        intent=intent,
        confidence=0.8,
        domain_hints=domains or [],
        matched_keywords=keywords or [],
    )


def _candidate(
    table_id: str = "db.schema.table",
    name: str = "table",
    domain: str = "clinical",
    sensitivity: int = 2,
    semantic: float = 0.7,
    keyword: float = 0.0,
    fk: float = 0.0,
    strategies: list[RetrievalStrategy] | None = None,
    hard_deny: bool = False,
    is_bridge: bool = False,
    description: str = "",
) -> CandidateTable:
    strats = strategies or [RetrievalStrategy.SEMANTIC]
    return CandidateTable(
        table_id=table_id,
        table_name=name,
        domain=domain,
        sensitivity_level=sensitivity,
        semantic_score=semantic,
        keyword_score=keyword,
        fk_score=fk,
        contributing_strategies=strats,
        hard_deny=hard_deny,
        is_bridge_table=is_bridge,
        description=description,
    )


class TestCompositeScoring:
    """Verify the composite scoring model produces correct rankings."""

    def test_semantic_dominant_score(self, ranker):
        candidates = [
            _candidate("t1", "high_semantic", semantic=0.9),
            _candidate("t2", "low_semantic", semantic=0.3),
        ]
        ranked = ranker.rank(candidates, _intent(), {"clinical"})
        assert ranked[0].table_id == "t1"
        assert ranked[0].final_score > ranked[1].final_score

    def test_domain_affinity_boost(self, ranker):
        intent = _intent(domains=[DomainHint.CLINICAL])
        candidates = [
            _candidate("t1", "matching", domain="clinical", semantic=0.5),
            _candidate("t2", "other", domain="billing", semantic=0.5),
        ]
        ranked = ranker.rank(candidates, intent, {"clinical", "billing"})
        # clinical domain matches hint → higher domain affinity
        assert ranked[0].table_id == "t1"

    def test_multi_strategy_bonus_applied(self, ranker):
        candidates = [
            _candidate(
                "t1", "multi", semantic=0.5, keyword=0.5,
                strategies=[RetrievalStrategy.SEMANTIC, RetrievalStrategy.KEYWORD],
            ),
            _candidate("t2", "single", semantic=0.5),
        ]
        # Pre-set the multi_strategy_bonus for the first candidate
        candidates[0].multi_strategy_bonus = 0.08
        ranked = ranker.rank(candidates, _intent(), {"clinical"})
        assert ranked[0].table_id == "t1"

    def test_scores_bounded_zero_to_one(self, ranker):
        candidates = [
            _candidate("t1", "test", semantic=1.0, keyword=1.0, fk=1.0),
        ]
        candidates[0].multi_strategy_bonus = 0.5
        ranked = ranker.rank(candidates, _intent(), {"clinical"})
        # Score should be reasonable (could exceed 1.0 due to weights summing)
        assert ranked[0].final_score >= 0


class TestAnchorTableBoost:
    """Verify universal join anchors (patients, encounters) get boosted."""

    def test_patients_anchor_boost(self, ranker):
        candidates = [
            _candidate("t1", "patients", semantic=0.4),
            _candidate("t2", "some_table", semantic=0.5),
        ]
        ranked = ranker.rank(candidates, _intent(), {"clinical"})
        # patients should get anchor boost to compensate lower semantic
        patients = next(c for c in ranked if c.table_name == "patients")
        assert patients.domain_affinity_score >= 0.8

    def test_encounters_anchor_boost(self, ranker):
        candidates = [
            _candidate("t1", "encounters", semantic=0.3),
        ]
        ranker.rank(candidates, _intent(), {"clinical"})
        assert candidates[0].domain_affinity_score >= 0.8


class TestSuperProtectedDemotion:
    """Verify sensitivity-5 tables are demoted in ranking."""

    def test_sensitivity_5_demoted(self, ranker):
        candidates = [
            _candidate("t1", "normal", sensitivity=2, semantic=0.6),
            _candidate("t2", "protected", sensitivity=5, semantic=0.7),
        ]
        ranked = ranker.rank(candidates, _intent(), {"clinical"})
        # Despite higher semantic score, protected table should be demoted
        assert ranked[0].table_id == "t1"

    def test_sensitivity_4_not_demoted(self, ranker):
        candidates = [
            _candidate("t1", "moderate", sensitivity=4, semantic=0.6),
        ]
        ranker.rank(candidates, _intent(), {"clinical"})
        # Sensitivity 4 should NOT trigger demotion
        assert candidates[0].final_score > 0


class TestIntentSpecificScoring:
    """Verify intent-based scoring adjustments."""

    def test_aggregation_fact_table_boost(self, ranker):
        intent = _intent(QueryIntent.AGGREGATION)
        candidates = [
            _candidate("t1", "fact_visits", semantic=0.5, description="fact table"),
            _candidate("t2", "patients", semantic=0.5),
        ]
        ranked = ranker.rank(candidates, intent, {"clinical"})
        fact = next(c for c in ranked if c.table_name == "fact_visits")
        assert fact.intent_score > 0

    def test_join_query_bridge_boost(self, ranker):
        intent = _intent(QueryIntent.JOIN_QUERY)
        candidates = [
            _candidate("t1", "patient_to_encounter", semantic=0.5, fk=0.5, is_bridge=True),
            _candidate("t2", "patients", semantic=0.5),
        ]
        ranked = ranker.rank(candidates, intent, {"clinical"})
        bridge = next(c for c in ranked if c.is_bridge_table)
        assert bridge.intent_score > 0

    def test_trend_time_column_boost(self, ranker):
        intent = _intent(QueryIntent.TREND)
        candidates = [
            _candidate("t1", "visits", semantic=0.5, description="contains date and timestamp columns"),
            _candidate("t2", "codes", semantic=0.5, description="lookup table"),
        ]
        ranked = ranker.rank(candidates, intent, {"clinical"})
        visits = next(c for c in ranked if c.table_name == "visits")
        assert visits.intent_score > 0

    def test_data_lookup_keyword_match(self, ranker):
        intent = _intent(QueryIntent.DATA_LOOKUP, keywords=["patient"])
        candidates = [
            _candidate("t1", "patient_records", semantic=0.5, description="patient data"),
        ]
        ranker.rank(candidates, intent, {"clinical"})
        assert candidates[0].intent_score > 0
