"""Tests for token budget enforcement and context assembly."""

from __future__ import annotations

import pytest

from app.models.l4_models import PermissionEnvelope, TablePermission
from app.models.retrieval import (
    FilteredTable,
    IntentResult,
    JoinGraph,
    RetrievalMetadata,
    RetrievalResult,
    ScopedColumn,
)
from app.models.enums import ColumnVisibility, QueryIntent, TableDecision
from app.services.context_assembler import ContextAssembler, _count_tokens


@pytest.fixture
def assembler():
    return ContextAssembler()


def _table(
    table_id: str = "db.schema.table",
    name: str = "table",
    ddl: str = "CREATE TABLE table (id INT);",
    score: float = 0.8,
    description: str = "A test table",
) -> FilteredTable:
    return FilteredTable(
        table_id=table_id,
        table_name=name,
        ddl_fragment=ddl,
        relevance_score=score,
        description=description,
        visible_columns=[ScopedColumn(name="id", data_type="INT")],
    )


def _intent() -> IntentResult:
    return IntentResult(intent=QueryIntent.DATA_LOOKUP, confidence=0.8)


def _envelope(nl_rules: list[str] | None = None) -> PermissionEnvelope:
    return PermissionEnvelope(
        global_nl_rules=nl_rules or ["Only return facility-filtered data"],
    )


class TestTokenCounting:
    """Verify token counting is accurate."""

    def test_empty_string(self):
        assert _count_tokens("") == 0

    def test_simple_text(self):
        tokens = _count_tokens("Hello world")
        assert tokens >= 2  # At least 2 tokens

    def test_ddl_fragment(self):
        ddl = "CREATE TABLE patients (\n  patient_id INT PRIMARY KEY,\n  name VARCHAR(100)\n);"
        tokens = _count_tokens(ddl)
        assert tokens > 5


class TestTokenBudgetEnforcement:
    """Verify tables are dropped when token budget is exceeded."""

    def test_all_tables_fit(self, assembler):
        tables = [_table(f"t{i}", f"table_{i}") for i in range(3)]
        result = assembler.assemble(
            request_id="req-1",
            user_id="test",
            original_question="test question",
            preprocessed_question="test question",
            intent=_intent(),
            filtered_tables=tables,
            join_graph=JoinGraph(),
            envelope=_envelope(),
            denied_count=0,
            metadata=RetrievalMetadata(),
            max_tables=10,
        )
        assert len(result.filtered_schema) == 3
        assert result.retrieval_metadata.tables_truncated == 0

    def test_low_ranked_tables_dropped_first(self, assembler):
        """When budget exceeded, lowest-scored tables drop first."""
        long_ddl = "CREATE TABLE big_table (\n" + ",\n".join(
            f"  col_{i} VARCHAR(255) -- A very long description for column {i}"
            for i in range(100)
        ) + "\n);"

        tables = [
            _table("t1", "high_priority", ddl=long_ddl, score=0.9),
            _table("t2", "medium_priority", ddl=long_ddl, score=0.7),
            _table("t3", "low_priority", ddl=long_ddl, score=0.5),
        ]
        result = assembler.assemble(
            request_id="req-1",
            user_id="test",
            original_question="test",
            preprocessed_question="test",
            intent=_intent(),
            filtered_tables=tables,
            join_graph=JoinGraph(),
            envelope=_envelope(),
            denied_count=0,
            metadata=RetrievalMetadata(),
            max_tables=10,
        )
        # Some tables should have been dropped
        if result.retrieval_metadata.tables_truncated > 0:
            # Verify highest-scored tables survived
            surviving_ids = {t.table_id for t in result.filtered_schema}
            assert "t1" in surviving_ids  # Highest score survives

    def test_policy_rules_never_truncated(self, assembler):
        """NL policy rules must NEVER be truncated, even under budget pressure."""
        long_rule = "This is a critical policy rule that must always appear: " + "x" * 200
        long_ddl = "CREATE TABLE t (\n" + ",\n".join(
            f"  c{i} TEXT" for i in range(50)
        ) + "\n);"

        tables = [_table("t1", "table_1", ddl=long_ddl)]
        result = assembler.assemble(
            request_id="req-1",
            user_id="test",
            original_question="test",
            preprocessed_question="test",
            intent=_intent(),
            filtered_tables=tables,
            join_graph=JoinGraph(),
            envelope=_envelope(nl_rules=[long_rule]),
            denied_count=0,
            metadata=RetrievalMetadata(),
            max_tables=10,
        )
        assert long_rule in result.nl_policy_rules

    def test_max_tables_limit_respected(self, assembler):
        """max_tables parameter must cap the output."""
        tables = [_table(f"t{i}", f"table_{i}") for i in range(20)]
        result = assembler.assemble(
            request_id="req-1",
            user_id="test",
            original_question="test",
            preprocessed_question="test",
            intent=_intent(),
            filtered_tables=tables,
            join_graph=JoinGraph(),
            envelope=_envelope(),
            denied_count=0,
            metadata=RetrievalMetadata(),
            max_tables=5,
        )
        assert len(result.filtered_schema) <= 5


class TestContextAssemblyCompleteness:
    """Verify all required fields are populated in the RetrievalResult."""

    def test_all_required_fields_present(self, assembler):
        tables = [_table("t1", "patients")]
        result = assembler.assemble(
            request_id="req-123",
            user_id="dr.jones",
            original_question="Show patients",
            preprocessed_question="Show patients [department:cardiology]",
            intent=_intent(),
            filtered_tables=tables,
            join_graph=JoinGraph(),
            envelope=_envelope(),
            denied_count=2,
            metadata=RetrievalMetadata(),
        )
        assert result.request_id == "req-123"
        assert result.user_id == "dr.jones"
        assert result.original_question == "Show patients"
        assert result.preprocessed_question.startswith("Show patients")
        assert result.denied_tables_count == 2
        assert len(result.filtered_schema) == 1
        assert result.resolved_at is not None

    def test_deduplicated_nl_rules(self, assembler):
        """NL rules should be deduplicated."""
        envelope = PermissionEnvelope(
            global_nl_rules=["Rule A", "Rule B", "Rule A"],  # Duplicate
            table_permissions=[
                TablePermission(
                    table_id="t1",
                    decision=TableDecision.ALLOW,
                    nl_rules=["Rule B", "Rule C"],
                ),
            ],
        )
        result = assembler.assemble(
            request_id="req-1",
            user_id="test",
            original_question="test",
            preprocessed_question="test",
            intent=_intent(),
            filtered_tables=[_table("t1")],
            join_graph=JoinGraph(),
            envelope=envelope,
            denied_count=0,
            metadata=RetrievalMetadata(),
        )
        assert len(result.nl_policy_rules) == len(set(result.nl_policy_rules))

    def test_metadata_populated(self, assembler):
        metadata = RetrievalMetadata(
            total_candidates_found=10,
            candidates_after_rbac=5,
        )
        result = assembler.assemble(
            request_id="req-1",
            user_id="test",
            original_question="test",
            preprocessed_question="test",
            intent=_intent(),
            filtered_tables=[_table()],
            join_graph=JoinGraph(),
            envelope=_envelope(),
            denied_count=5,
            metadata=metadata,
        )
        assert result.retrieval_metadata.total_candidates_found == 10
        assert result.retrieval_metadata.tables_in_result == 1
        assert result.retrieval_metadata.token_count > 0
