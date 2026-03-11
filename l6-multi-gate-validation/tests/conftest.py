"""Shared fixtures for L6 tests."""

import pytest
from app.models.api import (
    ColumnDecision, JoinRestriction, PermissionEnvelope, TablePermission,
)


@pytest.fixture
def physician_envelope() -> PermissionEnvelope:
    """Permission Envelope for an Attending Physician (clearance=3)."""
    return PermissionEnvelope(
        request_id="test-g1-001",
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
            ),
            TablePermission(
                table_id="patients",
                decision="ALLOW",
                columns=[
                    ColumnDecision(column_name="mrn", visibility="VISIBLE"),
                    ColumnDecision(
                        column_name="full_name",
                        visibility="MASKED",
                        masking_expression="LEFT(full_name,1)||'. '||SPLIT_PART(full_name,' ',-1)",
                    ),
                    ColumnDecision(column_name="date_of_birth", visibility="VISIBLE"),
                    ColumnDecision(column_name="ssn", visibility="HIDDEN"),
                ],
                max_rows=1000,
            ),
        ],
        join_restrictions=[
            JoinRestriction(
                source_domain="Clinical",
                target_domain="HR",
                policy_id="SEC-001",
                restriction_type="DENY",
            )
        ],
        global_nl_rules=["Limit results to 1000 rows."],
        signature="",
    )


@pytest.fixture
def billing_envelope() -> PermissionEnvelope:
    """Permission Envelope for billing staff."""
    return PermissionEnvelope(
        request_id="test-billing-001",
        table_permissions=[
            TablePermission(
                table_id="claims",
                decision="ALLOW",
                columns=[
                    ColumnDecision(column_name="claim_id", visibility="VISIBLE"),
                    ColumnDecision(column_name="mrn", visibility="VISIBLE"),
                    ColumnDecision(column_name="total_amount", visibility="VISIBLE"),
                    ColumnDecision(column_name="service_date", visibility="VISIBLE"),
                    ColumnDecision(column_name="clinical_notes", visibility="HIDDEN"),
                ],
                max_rows=1000,
            ),
            TablePermission(
                table_id="patients",
                decision="ALLOW",
                columns=[
                    ColumnDecision(column_name="mrn", visibility="VISIBLE"),
                    ColumnDecision(column_name="full_name", visibility="VISIBLE"),
                    ColumnDecision(column_name="ssn", visibility="HIDDEN"),
                ],
                max_rows=1000,
            ),
        ],
        signature="",
    )


@pytest.fixture
def agg_only_envelope() -> PermissionEnvelope:
    """Permission Envelope with aggregation_only=True for Revenue Cycle Manager."""
    return PermissionEnvelope(
        request_id="test-agg-001",
        table_permissions=[
            TablePermission(
                table_id="encounters",
                decision="ALLOW",
                aggregation_only=True,
                columns=[
                    ColumnDecision(column_name="encounter_id", visibility="VISIBLE"),
                    ColumnDecision(column_name="unit_id", visibility="VISIBLE"),
                    ColumnDecision(column_name="admission_date", visibility="VISIBLE"),
                    ColumnDecision(column_name="discharge_date", visibility="VISIBLE"),
                    ColumnDecision(column_name="mrn", visibility="HIDDEN"),
                    ColumnDecision(column_name="full_name", visibility="HIDDEN"),
                ],
                max_rows=1000,
            ),
        ],
        signature="",
    )


@pytest.fixture
def physician_context() -> dict:
    return {
        "user_id": "DR-4521",
        "effective_roles": ["ATTENDING_PHYSICIAN"],
        "department": "CARDIOLOGY",
        "clearance_level": 3,
        "session_id": "ses-test-001",
    }


@pytest.fixture
def nurse_context() -> dict:
    return {
        "user_id": "nurse-001",
        "effective_roles": ["REGISTERED_NURSE"],
        "department": "ICU",
        "clearance_level": 2,
        "session_id": "ses-nurse-001",
    }
