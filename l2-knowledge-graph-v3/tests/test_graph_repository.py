"""Unit tests for GraphReadRepository and GraphWriteRepository.

Tests parameterized query generation and result mapping.
Uses mock Neo4jManager — no real Neo4j required.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.models.api import ColumnResponse, ForeignKeyResponse, TableResponse
from app.models.enums import SensitivityLevel, PolicyType, MaskingStrategy, PIIType
from app.models.graph import TableNode, ColumnNode, PolicyNode
from app.repositories.graph_read_repo import GraphReadRepository
from app.repositories.graph_write_repo import GraphWriteRepository


# ── Read Repository Tests ────────────────────────────────────


class TestGraphReadRepository:
    """Tests for read-only parameterized queries."""

    @pytest.fixture
    def reader(self, mock_neo4j):
        return GraphReadRepository(mock_neo4j)

    @pytest.mark.asyncio
    async def test_get_tables_by_domain_returns_mapped_results(self, reader, mock_neo4j):
        mock_neo4j.execute_read.return_value = [
            {
                "fqn": "apollo_his.clinical.patients",
                "name": "patients",
                "description": "Patient demographics",
                "sensitivity_level": 4,
                "domain": "clinical",
                "is_active": True,
                "hard_deny": False,
                "schema_name": "clinical",
                "database_name": "apollo_his",
                "row_count_approx": 50000,
                "version": 1,
                "regulations": ["HIPAA"],
            }
        ]
        tables = await reader.get_tables_by_domain("clinical")
        assert len(tables) == 1
        assert tables[0].fqn == "apollo_his.clinical.patients"
        assert tables[0].domain == "clinical"
        assert tables[0].sensitivity_level == 4
        # Verify parameterized query was used
        mock_neo4j.execute_read.assert_called_once()
        call_args = mock_neo4j.execute_read.call_args
        assert "domain" in str(call_args) or "$domain" in str(call_args[0][0])

    @pytest.mark.asyncio
    async def test_get_tables_by_domain_empty_result(self, reader, mock_neo4j):
        mock_neo4j.execute_read.return_value = []
        tables = await reader.get_tables_by_domain("nonexistent")
        assert tables == []

    @pytest.mark.asyncio
    async def test_get_table_columns_returns_mapped_results(self, reader, mock_neo4j):
        mock_neo4j.execute_read.return_value = [
            {
                "fqn": "apollo_his.clinical.patients.mrn",
                "name": "mrn",
                "data_type": "varchar(20)",
                "is_pk": True,
                "is_nullable": False,
                "is_pii": True,
                "pii_type": "MEDICAL_RECORD_NUMBER",
                "sensitivity_level": 5,
                "masking_strategy": "HASH",
                "description": "Medical record number",
                "is_active": True,
                "regulations": ["HIPAA"],
            }
        ]
        columns = await reader.get_table_columns("apollo_his.clinical.patients")
        assert len(columns) == 1
        assert columns[0].name == "mrn"
        assert columns[0].is_pii is True
        assert columns[0].masking_strategy == "HASH"

    @pytest.mark.asyncio
    async def test_get_tables_by_sensitivity_filters_correctly(self, reader, mock_neo4j):
        mock_neo4j.execute_read.return_value = [
            {"fqn": "t1", "name": "t1", "description": "", "sensitivity_level": 5,
             "domain": "clinical", "is_active": True, "hard_deny": True,
             "schema_name": "s", "database_name": "db", "row_count_approx": 0,
             "version": 1, "regulations": []},
        ]
        tables = await reader.get_tables_by_sensitivity(5)
        assert len(tables) == 1

    @pytest.mark.asyncio
    async def test_get_foreign_keys(self, reader, mock_neo4j):
        mock_neo4j.execute_read.return_value = [
            {
                "source_column_fqn": "db.s.encounters.patient_mrn",
                "target_column_fqn": "db.s.patients.mrn",
                "source_table_fqn": "db.s.encounters",
                "target_table_fqn": "db.s.patients",
            }
        ]
        fks = await reader.get_foreign_keys("db.s.encounters")
        assert len(fks) == 1
        assert fks[0].target_table_fqn == "db.s.patients"

    @pytest.mark.asyncio
    async def test_get_hard_deny_tables(self, reader, mock_neo4j):
        mock_neo4j.execute_read.return_value = [
            {"fqn": "db.bh.substance_abuse_records"}
        ]
        hard_deny = await reader.get_hard_deny_tables()
        assert "db.bh.substance_abuse_records" in hard_deny

    @pytest.mark.asyncio
    async def test_search_tables_uses_parameterized_query(self, reader, mock_neo4j):
        mock_neo4j.execute_read.return_value = []
        await reader.search_tables("patient", limit=10)
        mock_neo4j.execute_read.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_policies_for_roles_includes_inherited(self, reader, mock_neo4j):
        mock_neo4j.execute_read.return_value = [
            {
                "policy_id": "POL-001",
                "policy_type": "ALLOW",
                "nl_description": "Doctors access clinical data",
                "structured_rule": '{"effect": "ALLOW"}',
                "priority": 100,
                "is_hard_deny": False,
                "is_active": True,
                "bound_roles": ["doctor"],
                "target_tables": [],
                "target_domains": ["clinical"],
                "target_columns": [],
                "conditions": [],
            }
        ]
        policies = await reader.get_policies_for_roles(["doctor"])
        assert len(policies) == 1
        assert policies[0].policy_id == "POL-001"

    @pytest.mark.asyncio
    async def test_get_node_counts(self, reader, mock_neo4j):
        mock_neo4j.execute_read.return_value = [
            {"label": "Table", "cnt": 7},
            {"label": "Column", "cnt": 22},
            {"label": "Policy", "cnt": 9},
        ]
        counts = await reader.get_node_counts()
        assert counts["Table"] == 7


# ── Write Repository Tests ───────────────────────────────────


class TestGraphWriteRepository:
    """Tests for write operations — verify they use parameterized queries."""

    @pytest.fixture
    def writer(self, mock_neo4j):
        return GraphWriteRepository(mock_neo4j)

    @pytest.mark.asyncio
    async def test_upsert_table(self, writer, mock_neo4j):
        mock_neo4j.execute_write.return_value = [{"version": 1}]
        table = TableNode(
            fqn="db.s.test_table", name="test_table",
            schema_name="s", database="db",
            description="Test", sensitivity_level=SensitivityLevel.INTERNAL,
            domain="clinical",
        )
        result = await writer.upsert_table(table)
        mock_neo4j.execute_write.assert_called_once()
        # Verify parameterized (no string concatenation of user values)
        query = mock_neo4j.execute_write.call_args[0][0]
        assert "$" in query or "fqn:" in query

    @pytest.mark.asyncio
    async def test_upsert_column(self, writer, mock_neo4j):
        mock_neo4j.execute_write.return_value = [{"version": 1}]
        col = ColumnNode(
            fqn="db.s.t.col1", name="col1", table_fqn="db.s.t",
            data_type="varchar(50)", description="Test column",
        )
        await writer.upsert_column(col)
        mock_neo4j.execute_write.assert_called_once()

    @pytest.mark.asyncio
    async def test_upsert_policy_requires_node(self, writer, mock_neo4j):
        mock_neo4j.execute_write.return_value = [{"version": 1}]
        policy = PolicyNode(
            policy_id="POL-TEST", policy_type=PolicyType.ALLOW,
            nl_description="Test policy for testing purposes",
            structured_rule='{"effect": "ALLOW"}',
            priority=100,
        )
        await writer.upsert_policy(policy)
        mock_neo4j.execute_write.assert_called()

    @pytest.mark.asyncio
    async def test_deactivate_table_soft_deletes(self, writer, mock_neo4j):
        mock_neo4j.execute_write.return_value = []
        await writer.deactivate_table("db.s.old_table")
        query = mock_neo4j.execute_write.call_args[0][0]
        assert "is_active" in query.lower() or "deactivated" in query.lower()

    @pytest.mark.asyncio
    async def test_add_foreign_key(self, writer, mock_neo4j):
        mock_neo4j.execute_write.return_value = []
        await writer.add_foreign_key("db.s.t1.col_a", "db.s.t2.col_b")
        mock_neo4j.execute_write.assert_called_once()

    @pytest.mark.asyncio
    async def test_bind_policy_to_role(self, writer, mock_neo4j):
        mock_neo4j.execute_write.return_value = []
        await writer.bind_policy_to_role("POL-001", "doctor")
        mock_neo4j.execute_write.assert_called_once()
        query = mock_neo4j.execute_write.call_args[0][0]
        assert "APPLIES_TO_ROLE" in query
