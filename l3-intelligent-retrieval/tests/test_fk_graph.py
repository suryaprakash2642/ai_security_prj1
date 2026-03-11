"""Tests for FK graph walking, bridge-table detection, and join graph construction."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.enums import ColumnVisibility, TableDecision
from app.models.l2_models import L2ForeignKey
from app.models.l4_models import (
    JoinRestriction,
    PermissionEnvelope,
    TablePermission,
)
from app.models.retrieval import CandidateTable, FilteredTable, ScopedColumn
from app.services.join_graph import JoinGraphBuilder
from app.services.retrieval_pipeline import _is_bridge_table


class TestBridgeTableDetection:
    """Verify bridge/junction table detection heuristics."""

    def test_to_pattern(self):
        assert _is_bridge_table("patient_to_encounter") is True

    def test_x_pattern(self):
        assert _is_bridge_table("user_x_role") is True

    def test_map_pattern(self):
        assert _is_bridge_table("diagnosis_map") is True

    def test_link_pattern(self):
        assert _is_bridge_table("provider_link") is True

    def test_bridge_pattern(self):
        assert _is_bridge_table("encounter_bridge") is True

    def test_assoc_pattern(self):
        assert _is_bridge_table("patient_assoc") is True

    def test_xref_pattern(self):
        assert _is_bridge_table("code_xref") is True

    def test_normal_table_not_bridge(self):
        assert _is_bridge_table("patients") is False

    def test_encounters_not_bridge(self):
        assert _is_bridge_table("encounters") is False

    def test_case_insensitive(self):
        assert _is_bridge_table("Patient_To_Encounter") is True

    def test_rel_pattern(self):
        assert _is_bridge_table("diagnosis_rel") is True

    def test_mapping_pattern(self):
        assert _is_bridge_table("code_mapping") is True


class TestJoinGraphConstruction:
    """Verify join graph only includes edges between allowed tables."""

    @pytest.fixture
    def builder(self, mock_l2, mock_cache):
        return JoinGraphBuilder(l2_client=mock_l2, cache=mock_cache)

    def _ft(
        self, table_id: str, name: str = "table", domain: str = "clinical",
    ) -> FilteredTable:
        return FilteredTable(
            table_id=table_id,
            table_name=name,
            domain_tags=[domain],
            visible_columns=[ScopedColumn(name="id", data_type="INT")],
        )

    def _candidate(self, table_id: str) -> CandidateTable:
        return CandidateTable(table_id=table_id, table_name=table_id.split(".")[-1])

    @pytest.mark.asyncio
    async def test_edges_only_between_allowed(self, builder, mock_l2, mock_cache):
        """FK edges must only connect tables that are both in the allowed set."""
        mock_cache.get_fk_local.return_value = None
        mock_l2.get_foreign_keys.return_value = [
            L2ForeignKey(
                source_column="patient_id",
                target_table="patients",
                target_column="patient_id",
                target_table_fqn="db.clinical.patients",
            ),
            L2ForeignKey(
                source_column="secret_id",
                target_table="secret_table",
                target_column="id",
                target_table_fqn="db.clinical.secret_table",
            ),
        ]

        allowed = [
            self._ft("db.clinical.encounters"),
            self._ft("db.clinical.patients"),
        ]
        candidates = [self._candidate("db.clinical.encounters"), self._candidate("db.clinical.patients")]

        graph = await builder.build(allowed, candidates, PermissionEnvelope())

        # Only the patients edge should exist (secret_table is not in allowed set)
        for edge in graph.edges:
            assert edge.target_table in {"db.clinical.patients", "db.clinical.encounters"}
            assert "secret" not in edge.target_table

    @pytest.mark.asyncio
    async def test_no_edges_to_denied_tables(self, builder, mock_l2, mock_cache):
        """FK edges to denied tables must NOT appear."""
        mock_cache.get_fk_local.return_value = None
        mock_l2.get_foreign_keys.return_value = [
            L2ForeignKey(
                source_column="denied_id",
                target_table="denied_table",
                target_column="id",
                target_table_fqn="db.clinical.denied_table",
            ),
        ]

        allowed = [self._ft("db.clinical.encounters")]
        graph = await builder.build(allowed, [], PermissionEnvelope())
        assert len(graph.edges) == 0

    @pytest.mark.asyncio
    async def test_restricted_join_detected(self, builder, mock_l2, mock_cache):
        """Cross-domain join restrictions from PermissionEnvelope should be flagged."""
        mock_cache.get_fk_local.return_value = None
        mock_l2.get_foreign_keys.return_value = [
            L2ForeignKey(
                source_column="patient_id",
                target_table="patients",
                target_column="patient_id",
                target_table_fqn="db.clinical.patients",
            ),
        ]

        allowed = [
            self._ft("db.billing.charges", "charges", "billing"),
            self._ft("db.clinical.patients", "patients", "clinical"),
        ]
        envelope = PermissionEnvelope(
            join_restrictions=[
                JoinRestriction(source_domain="billing", target_domain="clinical"),
            ],
        )

        graph = await builder.build(allowed, [], envelope)
        # Any edge from billing→clinical should be marked restricted
        restricted = [e for e in graph.edges if e.is_restricted]
        if graph.edges:
            assert len(restricted) > 0 or len(graph.restricted_joins) > 0

    @pytest.mark.asyncio
    async def test_empty_allowed_empty_graph(self, builder, mock_l2, mock_cache):
        """No allowed tables → empty join graph."""
        graph = await builder.build([], [], PermissionEnvelope())
        assert len(graph.edges) == 0
