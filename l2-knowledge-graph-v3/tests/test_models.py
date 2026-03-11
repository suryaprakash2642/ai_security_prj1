"""Tests for Pydantic models, enums, and data contract validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.models.api import (
    APIResponse,
    ClassificationSummary,
    ColumnResponse,
    PolicyResponse,
    PolicySimulateRequest,
    TableResponse,
)
from app.models.audit import ChangeRecord
from app.models.enums import (
    ChangeAction,
    ChangeSource,
    ConditionType,
    MaskingStrategy,
    PIIType,
    PolicyType,
    RegulationCode,
    SensitivityLevel,
    ServiceRole,
)
from app.models.graph import PolicyNode


class TestEnumCompleteness:
    """Verify all spec-required enum values exist."""

    def test_policy_types(self):
        assert PolicyType.ALLOW.value == "ALLOW"
        assert PolicyType.DENY.value == "DENY"
        assert PolicyType.MASK.value == "MASK"
        assert PolicyType.FILTER.value == "FILTER"

    def test_condition_types(self):
        required = ["ROW_FILTER", "TIME_WINDOW", "AGGREGATION_ONLY",
                     "JOIN_RESTRICTION", "COLUMN_MASK", "MAX_ROWS"]
        for ct in required:
            assert ConditionType(ct), f"Missing condition type: {ct}"

    def test_masking_strategies(self):
        assert MaskingStrategy.REDACT.value == "REDACT"
        assert MaskingStrategy.HASH.value == "HASH"
        assert MaskingStrategy.PARTIAL_MASK.value == "PARTIAL_MASK"

    def test_sensitivity_levels_1_through_5(self):
        assert SensitivityLevel.PUBLIC == 1
        assert SensitivityLevel.INTERNAL == 2
        assert SensitivityLevel.CONFIDENTIAL == 3
        assert SensitivityLevel.RESTRICTED == 4
        assert SensitivityLevel.TOP_SECRET == 5

    def test_regulation_codes(self):
        required = ["HIPAA", "42_CFR_PART_2", "HIPAA_PSYCHOTHERAPY",
                     "DEA_SCHEDULE_II_V", "STATE_MH_LAWS", "STATE_HIV_LAWS",
                     "DPDPA_2023", "LABOR_LAWS", "TELEHEALTH", "GINA"]
        for code in required:
            assert RegulationCode(code), f"Missing regulation: {code}"

    def test_service_roles(self):
        assert ServiceRole.PIPELINE_READER.value == "pipeline_reader"
        assert ServiceRole.SCHEMA_WRITER.value == "schema_writer"
        assert ServiceRole.POLICY_WRITER.value == "policy_writer"
        assert ServiceRole.ADMIN.value == "admin"


class TestAPIResponseModel:
    def test_default_success(self):
        resp = APIResponse()
        assert resp.success is True
        assert resp.data is None
        assert resp.error is None

    def test_error_response(self):
        resp = APIResponse(success=False, error="Something failed")
        assert resp.success is False
        assert resp.error == "Something failed"

    def test_data_with_meta(self):
        resp = APIResponse(data={"tables": []}, meta={"count": 0})
        assert resp.data == {"tables": []}
        assert resp.meta["count"] == 0


class TestTableResponseModel:
    def test_required_fields(self):
        t = TableResponse(
            fqn="db.schema.table",
            name="table",
            description="desc",
            sensitivity_level=3,
            domain="clinical",
            is_active=True,
        )
        assert t.fqn == "db.schema.table"
        assert t.sensitivity_level == 3

    def test_hard_deny_default_false(self):
        t = TableResponse(
            fqn="a", name="a", description="a",
            sensitivity_level=1, domain="a", is_active=True,
        )
        assert t.hard_deny is False


class TestPolicyResponseModel:
    def test_policy_requires_dual_representation(self):
        """Spec: both nl_description and structured_rule are mandatory."""
        p = PolicyResponse(
            policy_id="p1",
            policy_type=PolicyType.ALLOW,
            nl_description="Allow reading clinical data",
            structured_rule={"effect": "ALLOW", "resources": ["patients"]},
            priority=100,
        )
        assert p.nl_description != ""
        assert p.structured_rule != {}

    def test_policy_frozen(self):
        p = PolicyResponse(
            policy_id="p1",
            policy_type=PolicyType.ALLOW,
            nl_description="Test policy description",
            structured_rule={"effect": "ALLOW"},
            priority=100,
        )
        with pytest.raises(ValidationError):
            p.policy_id = "modified"  # type: ignore


class TestPolicySimulateRequest:
    def test_requires_roles(self):
        with pytest.raises(ValidationError):
            PolicySimulateRequest(roles=[], table_fqns=["t1"])

    def test_requires_table_fqns(self):
        with pytest.raises(ValidationError):
            PolicySimulateRequest(roles=["doctor"], table_fqns=[])

    def test_valid_request(self):
        req = PolicySimulateRequest(
            roles=["doctor", "nurse"],
            table_fqns=["db.clinical.patients"],
            operation="SELECT",
        )
        assert len(req.roles) == 2


class TestChangeRecord:
    def test_change_record_defaults(self):
        cr = ChangeRecord(
            node_type="Table",
            node_id="db.schema.table",
            action=ChangeAction.CREATE,
            changed_by="crawler",
            change_source=ChangeSource.SCHEMA_DISCOVERY,
        )
        assert cr.old_values == {}
        assert cr.new_values == {}
        assert cr.changed_properties == {}


class TestClassificationSummary:
    def test_defaults_to_zero(self):
        s = ClassificationSummary()
        assert s.columns_analyzed == 0
        assert s.pii_detected == 0
        assert s.auto_approved == 0
        assert s.review_items_created == 0
