"""Shared fixtures for L7 tests."""

import pytest
from app.models.api import (
    ColumnDecision, ExecutionConfig, ExecutionRequest,
    JoinRestriction, PermissionEnvelope, TablePermission,
)


@pytest.fixture
def base_envelope() -> PermissionEnvelope:
    return PermissionEnvelope(
        request_id="test-env-001",
        table_permissions=[
            TablePermission(
                table_id="encounters",
                decision="ALLOW",
                columns=[
                    ColumnDecision(column_name="encounter_id", visibility="VISIBLE"),
                    ColumnDecision(column_name="mrn", visibility="VISIBLE"),
                    ColumnDecision(column_name="admission_date", visibility="VISIBLE"),
                    ColumnDecision(column_name="treating_provider_id", visibility="VISIBLE"),
                    ColumnDecision(column_name="unit_id", visibility="VISIBLE"),
                    ColumnDecision(
                        column_name="full_name",
                        visibility="MASKED",
                        masking_expression="LEFT(full_name,1)||'. '||SPLIT_PART(full_name,' ',-1)",
                    ),
                ],
                row_filters=["treating_provider_id = 'DR-4521'"],
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
                max_rows=500,
            ),
        ],
        signature="",
    )


@pytest.fixture
def physician_security_context() -> dict:
    return {
        "user_id": "DR-4521",
        "effective_roles": ["ATTENDING_PHYSICIAN"],
        "department": "CARDIOLOGY",
        "clearance_level": 3,
        "session_id": "ses-test-001",
    }


@pytest.fixture
def base_request(base_envelope, physician_security_context) -> ExecutionRequest:
    return ExecutionRequest(
        request_id="exec-test-001",
        validated_sql="SELECT mrn, admission_date FROM encounters WHERE treating_provider_id = 'DR-4521' LIMIT 100",
        dialect="postgresql",
        target_database="mock",
        permission_envelope=base_envelope,
        execution_config=ExecutionConfig(timeout_seconds=30, max_rows=1000),
        security_context=physician_security_context,
    )
