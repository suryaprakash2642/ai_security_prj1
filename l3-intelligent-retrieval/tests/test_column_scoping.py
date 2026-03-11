"""Tests for column-level scoping, DDL generation, and hidden column handling."""

from __future__ import annotations

import pytest

from app.models.enums import ColumnVisibility, TableDecision
from app.models.l2_models import L2ColumnInfo
from app.models.l4_models import ColumnDecision, PermissionEnvelope, TablePermission
from app.models.retrieval import CandidateTable
from app.services.column_scoper import ColumnScoper
from tests.conftest import make_column


@pytest.fixture
def scoper(mock_l2, mock_cache):
    return ColumnScoper(l2_client=mock_l2, cache=mock_cache)


def _candidate(
    table_id: str = "db.schema.patients",
    name: str = "patients",
    score: float = 0.8,
) -> CandidateTable:
    return CandidateTable(
        table_id=table_id,
        table_name=name,
        final_score=score,
        domain="clinical",
    )


def _envelope(
    table_id: str = "db.schema.patients",
    columns: list[ColumnDecision] | None = None,
    row_filters: list[str] | None = None,
    aggregation_only: bool = False,
    max_rows: int | None = None,
) -> PermissionEnvelope:
    if columns is None:
        columns = [
            ColumnDecision(column_name="patient_id", visibility=ColumnVisibility.VISIBLE),
            ColumnDecision(column_name="name", visibility=ColumnVisibility.MASKED,
                           masking_expression="LEFT(name, 1) || '***'"),
            ColumnDecision(column_name="ssn", visibility=ColumnVisibility.HIDDEN),
            ColumnDecision(column_name="dob", visibility=ColumnVisibility.COMPUTED,
                           computed_expression="EXTRACT(YEAR FROM dob)"),
        ]
    return PermissionEnvelope(
        table_permissions=[
            TablePermission(
                table_id=table_id,
                decision=TableDecision.ALLOW,
                columns=columns,
                row_filters=row_filters or [],
                aggregation_only=aggregation_only,
                max_rows=max_rows,
            )
        ],
    )


class TestColumnVisibilityClassification:
    """Verify columns are correctly classified into VISIBLE/MASKED/HIDDEN/COMPUTED."""

    @pytest.mark.asyncio
    async def test_visible_columns_included(self, scoper, mock_l2):
        mock_l2.get_table_columns.return_value = [
            make_column("db.schema.patients.patient_id", "patient_id", "integer", False),
        ]
        envelope = _envelope(columns=[
            ColumnDecision(column_name="patient_id", visibility=ColumnVisibility.VISIBLE),
        ])
        tables, _ = await scoper.scope_tables([_candidate()], envelope)
        assert len(tables) == 1
        assert len(tables[0].visible_columns) == 1
        assert tables[0].visible_columns[0].name == "patient_id"

    @pytest.mark.asyncio
    async def test_masked_columns_annotated(self, scoper, mock_l2):
        mock_l2.get_table_columns.return_value = [
            make_column("db.schema.patients.name", "name", "varchar(100)", True),
        ]
        envelope = _envelope(columns=[
            ColumnDecision(
                column_name="name",
                visibility=ColumnVisibility.MASKED,
                masking_expression="LEFT(name, 1) || '***'",
            ),
        ])
        tables, _ = await scoper.scope_tables([_candidate()], envelope)
        assert len(tables[0].masked_columns) == 1
        assert tables[0].masked_columns[0].masking_expression == "LEFT(name, 1) || '***'"

    @pytest.mark.asyncio
    async def test_hidden_columns_counted_not_named(self, scoper, mock_l2):
        """CRITICAL: Hidden columns must be counted but NEVER named."""
        mock_l2.get_table_columns.return_value = [
            make_column("db.schema.patients.ssn", "ssn", "varchar(11)", True),
        ]
        envelope = _envelope(columns=[
            ColumnDecision(column_name="ssn", visibility=ColumnVisibility.HIDDEN),
        ])
        tables, _ = await scoper.scope_tables([_candidate()], envelope)
        assert tables[0].hidden_column_count == 1
        # ssn must NOT appear in visible or masked columns
        all_named = [c.name for c in tables[0].visible_columns + tables[0].masked_columns]
        assert "ssn" not in all_named

    @pytest.mark.asyncio
    async def test_computed_columns_in_visible(self, scoper, mock_l2):
        mock_l2.get_table_columns.return_value = [
            make_column("db.schema.patients.dob", "dob", "date", True),
        ]
        envelope = _envelope(columns=[
            ColumnDecision(
                column_name="dob",
                visibility=ColumnVisibility.COMPUTED,
                computed_expression="EXTRACT(YEAR FROM dob)",
            ),
        ])
        tables, _ = await scoper.scope_tables([_candidate()], envelope)
        # Computed columns appear in visible list with expression
        assert any(c.name == "dob" for c in tables[0].visible_columns)
        computed = next(c for c in tables[0].visible_columns if c.name == "dob")
        assert computed.computed_expression == "EXTRACT(YEAR FROM dob)"


class TestDDLGeneration:
    """Verify DDL fragments are correctly generated for LLM consumption."""

    @pytest.mark.asyncio
    async def test_ddl_contains_table_name(self, scoper, mock_l2):
        mock_l2.get_table_columns.return_value = [
            make_column("db.schema.patients.id", "id", "integer", False),
        ]
        envelope = _envelope(columns=[
            ColumnDecision(column_name="id", visibility=ColumnVisibility.VISIBLE),
        ])
        tables, _ = await scoper.scope_tables([_candidate()], envelope)
        assert "patients" in tables[0].ddl_fragment

    @pytest.mark.asyncio
    async def test_ddl_includes_masked_annotation(self, scoper, mock_l2):
        mock_l2.get_table_columns.return_value = [
            make_column("db.schema.patients.name", "name", "varchar", True),
        ]
        envelope = _envelope(columns=[
            ColumnDecision(
                column_name="name",
                visibility=ColumnVisibility.MASKED,
                masking_expression="MASKED(name)",
            ),
        ])
        tables, _ = await scoper.scope_tables([_candidate()], envelope)
        assert "MASKED" in tables[0].ddl_fragment

    @pytest.mark.asyncio
    async def test_ddl_row_filter_annotation(self, scoper, mock_l2):
        mock_l2.get_table_columns.return_value = [
            make_column("db.schema.patients.id", "id", "integer", False),
        ]
        envelope = _envelope(
            columns=[ColumnDecision(column_name="id", visibility=ColumnVisibility.VISIBLE)],
            row_filters=["facility_id = 'HOSP_01'"],
        )
        tables, _ = await scoper.scope_tables([_candidate()], envelope)
        assert "REQUIRED FILTER" in tables[0].ddl_fragment

    @pytest.mark.asyncio
    async def test_ddl_aggregation_only_annotation(self, scoper, mock_l2):
        mock_l2.get_table_columns.return_value = [
            make_column("db.schema.patients.id", "id", "integer", False),
        ]
        envelope = _envelope(
            columns=[ColumnDecision(column_name="id", visibility=ColumnVisibility.VISIBLE)],
            aggregation_only=True,
        )
        tables, _ = await scoper.scope_tables([_candidate()], envelope)
        assert "AGGREGATION ONLY" in tables[0].ddl_fragment

    @pytest.mark.asyncio
    async def test_ddl_max_rows_annotation(self, scoper, mock_l2):
        mock_l2.get_table_columns.return_value = [
            make_column("db.schema.patients.id", "id", "integer", False),
        ]
        envelope = _envelope(
            columns=[ColumnDecision(column_name="id", visibility=ColumnVisibility.VISIBLE)],
            max_rows=1000,
        )
        tables, _ = await scoper.scope_tables([_candidate()], envelope)
        assert "LIMIT 1000" in tables[0].ddl_fragment


class TestColumnDefaultBehavior:
    """Verify behavior when L4 provides no explicit column decision."""

    @pytest.mark.asyncio
    async def test_pii_column_hidden_by_default(self, scoper, mock_l2):
        """PII columns with no explicit decision must default to HIDDEN."""
        mock_l2.get_table_columns.return_value = [
            make_column("db.schema.patients.ssn", "ssn", "varchar(11)", True),
        ]
        # Envelope with no column decisions for ssn
        envelope = _envelope(columns=[])
        tables, _ = await scoper.scope_tables([_candidate()], envelope)
        assert tables[0].hidden_column_count == 1
        assert len(tables[0].visible_columns) == 0

    @pytest.mark.asyncio
    async def test_non_pii_column_visible_by_default(self, scoper, mock_l2):
        """Non-PII columns with no explicit decision default to VISIBLE."""
        mock_l2.get_table_columns.return_value = [
            make_column("db.schema.patients.status", "status", "varchar(20)", False),
        ]
        envelope = _envelope(columns=[])
        tables, _ = await scoper.scope_tables([_candidate()], envelope)
        assert len(tables[0].visible_columns) == 1
        assert tables[0].visible_columns[0].name == "status"
