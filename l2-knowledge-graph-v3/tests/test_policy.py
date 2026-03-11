"""Tests for policy simulation, resolution order, and hard deny enforcement."""

from __future__ import annotations

import pytest

from app.models.api import PolicyResponse, PolicySimulateRequest, PolicySimulateResult
from app.models.enums import PolicyType
from app.services.policy_service import PolicyService
from tests.conftest import make_policy


class TestPolicyResolution:
    """Test the static _resolve_policies method."""

    def test_deny_wins_over_allow(self):
        policies = [
            make_policy("p1", PolicyType.ALLOW, bound_roles=["doctor"]),
            make_policy("p2", PolicyType.DENY, bound_roles=["doctor"]),
        ]
        result = PolicyService._resolve_policies("db.schema.table", policies)
        assert result.effective_policy == PolicyType.DENY

    def test_deny_wins_over_mask(self):
        policies = [
            make_policy("p1", PolicyType.MASK, bound_roles=["nurse"]),
            make_policy("p2", PolicyType.DENY, bound_roles=["nurse"]),
        ]
        result = PolicyService._resolve_policies("db.schema.table", policies)
        assert result.effective_policy == PolicyType.DENY

    def test_mask_wins_over_allow(self):
        policies = [
            make_policy("p1", PolicyType.ALLOW, bound_roles=["nurse"]),
            make_policy("p2", PolicyType.MASK, bound_roles=["nurse"]),
        ]
        result = PolicyService._resolve_policies("db.schema.table", policies)
        assert result.effective_policy == PolicyType.MASK

    def test_filter_wins_over_allow(self):
        policies = [
            make_policy("p1", PolicyType.ALLOW, bound_roles=["analyst"]),
            make_policy("p2", PolicyType.FILTER, bound_roles=["analyst"]),
        ]
        result = PolicyService._resolve_policies("db.schema.table", policies)
        assert result.effective_policy == PolicyType.FILTER

    def test_allow_when_only_allow(self):
        policies = [make_policy("p1", PolicyType.ALLOW)]
        result = PolicyService._resolve_policies("db.schema.table", policies)
        assert result.effective_policy == PolicyType.ALLOW

    def test_hard_deny_flagged_in_result(self):
        policies = [
            make_policy("p_hard", PolicyType.DENY, is_hard_deny=True),
        ]
        result = PolicyService._resolve_policies("db.schema.table", policies)
        assert result.effective_policy == PolicyType.DENY
        assert result.is_hard_deny is True


class TestPolicyAppliesTable:
    def test_exact_table_match(self):
        policy = make_policy(target_tables=["db.clinical.patients"])
        assert PolicyService._policy_applies_to_table(policy, "db.clinical.patients")

    def test_domain_match_via_schema(self):
        policy = PolicyResponse(
            policy_id="p1",
            policy_type=PolicyType.ALLOW,
            nl_description="Allow access to clinical domain",
            structured_rule={"effect": "ALLOW"},
            priority=100,
            target_domains=["clinical"],
        )
        assert PolicyService._policy_applies_to_table(policy, "db.clinical.patients")

    def test_no_match_different_table(self):
        policy = make_policy(target_tables=["db.clinical.patients"])
        assert not PolicyService._policy_applies_to_table(policy, "db.hr.employees")

    def test_wildcard_policy_applies_to_any_table(self):
        policy = PolicyResponse(
            policy_id="p_wild",
            policy_type=PolicyType.ALLOW,
            nl_description="Global policy",
            structured_rule={"effect": "ALLOW"},
            priority=50,
            target_tables=[],
            target_domains=[],
        )
        assert PolicyService._policy_applies_to_table(policy, "any.table.here")


class TestPolicyValidation:
    def test_nl_description_required_minimum_length(self):
        """Policy creation must reject nl_description shorter than 10 chars."""
        from app.services.policy_service import PolicyService

        service = PolicyService(None, None, None)  # type: ignore
        # We can test the validation logic without running async
        with pytest.raises(ValueError, match="nl_description"):
            import asyncio
            asyncio.get_event_loop().run_until_complete(
                service.create_policy(
                    policy_id="bad",
                    policy_type=PolicyType.ALLOW,
                    nl_description="short",  # < 10 chars
                    structured_rule={"effect": "ALLOW"},
                )
            )

    def test_structured_rule_required(self):
        """Policy creation must reject missing structured_rule."""
        from app.services.policy_service import PolicyService

        service = PolicyService(None, None, None)  # type: ignore
        with pytest.raises(ValueError, match="structured_rule"):
            import asyncio
            asyncio.get_event_loop().run_until_complete(
                service.create_policy(
                    policy_id="bad",
                    policy_type=PolicyType.ALLOW,
                    nl_description="A valid description that is long enough",
                    structured_rule={},  # empty
                )
            )


class TestDenyByDefault:
    """Spec: no matching policy → DENY (deny by default)."""

    def test_empty_policies_results_in_deny(self):
        """If no policies apply, resolve should produce DENY."""
        # This is tested via simulation, but we verify the safety-net
        result = PolicyService._resolve_policies("db.schema.unknown_table", [])
        # With empty list, the method should still produce DENY
        # (Note: the method asserts len(policies) > 0, but let's verify behavior)
        assert result.effective_policy == PolicyType.DENY
        assert result.deny_reason is not None
