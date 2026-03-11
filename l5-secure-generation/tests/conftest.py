"""Shared fixtures for L5 tests."""

import pytest

from app.models.api import (
    ColumnDecision, FilteredSchema, FilteredTable, JoinEdge,
    PermissionEnvelope, SchemaColumn, TablePermission,
)


@pytest.fixture
def physician_envelope() -> PermissionEnvelope:
    """Permission Envelope for Dr. Patel (Attending Physician, cardiology, clearance=3)."""
    return PermissionEnvelope(
        request_id="test-001",
        table_permissions=[
            TablePermission(
                table_id="encounters",
                decision="ALLOW",
                columns=[
                    ColumnDecision(column_name="encounter_id", visibility="VISIBLE"),
                    ColumnDecision(column_name="mrn", visibility="VISIBLE"),
                    ColumnDecision(column_name="admission_date", visibility="VISIBLE"),
                    ColumnDecision(column_name="discharge_date", visibility="VISIBLE"),
                    ColumnDecision(column_name="treating_provider_id", visibility="VISIBLE"),
                    ColumnDecision(column_name="unit_id", visibility="VISIBLE"),
                    ColumnDecision(column_name="encounter_type", visibility="VISIBLE"),
                ],
                row_filters=["treating_provider_id = 'DR-4521' OR unit_id = '3B'"],
                nl_rules=[
                    "Filter encounters to only rows where treating_provider_id = 'DR-4521' OR unit_id = '3B'.",
                ],
                max_rows=1000,
            ),
            TablePermission(
                table_id="patients",
                decision="ALLOW",
                columns=[
                    ColumnDecision(column_name="mrn", visibility="VISIBLE"),
                    ColumnDecision(column_name="full_name", visibility="MASKED",
                                   masking_expression="LEFT(full_name,1)||'. '||SPLIT_PART(full_name,' ',-1)"),
                    ColumnDecision(column_name="date_of_birth", visibility="VISIBLE"),
                    ColumnDecision(column_name="ssn", visibility="HIDDEN"),
                ],
                nl_rules=[
                    "Do not include ssn in any query.",
                    "When selecting full_name, use the first initial + last name format.",
                ],
                max_rows=1000,
            ),
        ],
        global_nl_rules=["Limit results to a maximum of 1000 rows."],
        signature="",  # Dev mode — no signature required
    )


@pytest.fixture
def billing_envelope() -> PermissionEnvelope:
    """Permission Envelope for billing staff."""
    return PermissionEnvelope(
        request_id="test-002",
        table_permissions=[
            TablePermission(
                table_id="claims",
                decision="ALLOW",
                columns=[
                    ColumnDecision(column_name="claim_id", visibility="VISIBLE"),
                    ColumnDecision(column_name="mrn", visibility="VISIBLE"),
                    ColumnDecision(column_name="total_amount", visibility="VISIBLE"),
                    ColumnDecision(column_name="service_date", visibility="VISIBLE"),
                    ColumnDecision(column_name="insurance_id", visibility="VISIBLE"),
                ],
                nl_rules=["Do not include clinical_notes, vital_signs, or lab_results."],
                max_rows=1000,
            ),
            TablePermission(
                table_id="patients",
                decision="ALLOW",
                columns=[
                    ColumnDecision(column_name="mrn", visibility="VISIBLE"),
                    ColumnDecision(column_name="full_name", visibility="VISIBLE"),
                    ColumnDecision(column_name="insurance_id", visibility="VISIBLE"),
                    ColumnDecision(column_name="ssn", visibility="HIDDEN"),
                    ColumnDecision(column_name="date_of_birth", visibility="HIDDEN"),
                ],
                max_rows=1000,
            ),
        ],
        global_nl_rules=["Limit results to a maximum of 1000 rows."],
        signature="",
    )


@pytest.fixture
def simple_schema() -> FilteredSchema:
    """Minimal schema with encounters and patients tables."""
    return FilteredSchema(
        tables=[
            FilteredTable(
                table_id="encounters",
                table_name="encounters",
                domain="Clinical",
                nl_description="Patient encounter records",
                relevance_score=0.95,
                columns=[
                    SchemaColumn(name="encounter_id", data_type="UUID", nl_description="Unique encounter ID"),
                    SchemaColumn(name="mrn", data_type="VARCHAR(20)", nl_description="Medical record number"),
                    SchemaColumn(name="admission_date", data_type="TIMESTAMP"),
                    SchemaColumn(name="discharge_date", data_type="TIMESTAMP"),
                    SchemaColumn(name="treating_provider_id", data_type="VARCHAR(20)"),
                    SchemaColumn(name="unit_id", data_type="VARCHAR(10)"),
                    SchemaColumn(name="encounter_type", data_type="VARCHAR(50)"),
                ],
                row_filters=["treating_provider_id = 'DR-4521' OR unit_id = '3B'"],
            ),
            FilteredTable(
                table_id="patients",
                table_name="patients",
                domain="Clinical",
                nl_description="Patient demographic data",
                relevance_score=0.82,
                columns=[
                    SchemaColumn(name="mrn", data_type="VARCHAR(20)", nl_description="Medical record number"),
                    SchemaColumn(name="full_name", data_type="VARCHAR(100)", is_masked=True,
                                 sql_rewrite="LEFT(full_name,1)||'. '||SPLIT_PART(full_name,' ',-1)"),
                    SchemaColumn(name="date_of_birth", data_type="DATE"),
                    SchemaColumn(name="ssn", data_type="VARCHAR(20)", sensitivity_level=4),
                ],
                foreign_keys=[
                    JoinEdge(from_table="encounters", from_column="mrn",
                             to_table="patients", to_column="mrn"),
                ],
            ),
        ]
    )
