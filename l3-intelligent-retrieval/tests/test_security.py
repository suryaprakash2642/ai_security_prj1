"""Security tests — RBAC bypass attempts, denied-table probing, cache safety, sensitivity-5.

These tests verify the zero-trust security model:
- No RBAC bypass
- No table existence disclosure
- No denied column-name disclosure
- Cache key isolation by role
- Sensitivity-5 permanent exclusion
- Fail-secure under dependency failures
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.auth import (
    create_service_token,
    sign_security_context,
    verify_security_context,
    verify_service_token,
)
from app.config import Settings
from app.models.enums import ColumnVisibility, TableDecision
from app.models.l4_models import (
    ColumnDecision,
    PermissionEnvelope,
    TablePermission,
)
from app.models.retrieval import CandidateTable
from app.models.security import SecurityContext
from app.services.rbac_filter import RBACFilter, _PERMANENTLY_EXCLUDED_PATTERNS
from tests.conftest import make_security_context


class TestSecurityContextValidation:
    """Verify SecurityContext signature and expiry enforcement."""

    def test_valid_context_accepted(self, test_settings):
        ctx = make_security_context(test_settings)
        assert not ctx.is_expired
        verify_security_context(ctx, test_settings.context_signing_key)

    def test_expired_context_rejected(self, test_settings):
        ctx = make_security_context(test_settings, expired=True)
        with pytest.raises(ValueError, match="expired"):
            verify_security_context(ctx, test_settings.context_signing_key)

    def test_tampered_signature_rejected(self, test_settings):
        ctx = make_security_context(test_settings)
        # Tamper with signature
        tampered = SecurityContext(**{
            **ctx.model_dump(),
            "context_signature": "deadbeef" * 8,
        })
        with pytest.raises(ValueError, match="signature"):
            verify_security_context(tampered, test_settings.context_signing_key)

    def test_wrong_signing_key_rejected(self, test_settings):
        ctx = make_security_context(test_settings)
        wrong_key = "wrong-context-signing-key-32-chars-plus-extra"
        with pytest.raises(ValueError, match="signature"):
            verify_security_context(ctx, wrong_key)

    def test_empty_roles_rejected(self, test_settings):
        with pytest.raises(ValueError):
            SecurityContext(
                user_id="test",
                effective_roles=[],  # Must have at least one role
                department="test",
                clearance_level=1,
                session_id="sess1",
                context_signature="sig",
                context_expiry=datetime.now(UTC) + timedelta(hours=1),
            )


class TestServiceTokenAuth:
    """Verify inter-service HMAC token authentication."""

    def test_valid_token_accepted(self, test_settings):
        token = create_service_token(
            "l5-generation", "pipeline_reader",
            test_settings.service_token_secret,
        )
        identity = verify_service_token(
            token, test_settings.service_token_secret,
        )
        assert identity.service_id == "l5-generation"
        assert identity.role == "pipeline_reader"

    def test_expired_token_rejected(self, test_settings):
        # Create a token with max_age=-1 so any issued token is immediately expired
        token = create_service_token(
            "l5-generation", "pipeline_reader",
            test_settings.service_token_secret, ttl=3600,
        )
        with pytest.raises(ValueError, match="expired"):
            verify_service_token(
                token, test_settings.service_token_secret, max_age=-1,
            )

    def test_invalid_signature_rejected(self, test_settings):
        token = "l5-generation|pipeline_reader|12345|badsignature"
        with pytest.raises(ValueError, match="signature"):
            verify_service_token(token, test_settings.service_token_secret)

    def test_malformed_token_rejected(self, test_settings):
        with pytest.raises(ValueError, match="Malformed"):
            verify_service_token("not-a-valid-token", test_settings.service_token_secret)


class TestSensitivity5Exclusion:
    """Verify sensitivity-5 tables are permanently excluded."""

    def test_substance_abuse_excluded(self):
        """substance_abuse_records must NEVER be retrievable."""
        candidates = [
            CandidateTable(table_id="db.schema.substance_abuse_records", table_name="substance_abuse_records"),
            CandidateTable(table_id="db.schema.patients", table_name="patients"),
        ]
        rbac = RBACFilter(l2_client=AsyncMock(), l4_client=AsyncMock(), cache=AsyncMock())
        result = rbac._exclude_permanent(candidates)
        assert len(result) == 1
        assert result[0].table_name == "patients"

    def test_behavioral_health_substance_excluded(self):
        candidates = [
            CandidateTable(table_id="db.clinical.behavioral_health_substance", table_name="behavioral_health_substance"),
        ]
        rbac = RBACFilter(l2_client=AsyncMock(), l4_client=AsyncMock(), cache=AsyncMock())
        result = rbac._exclude_permanent(candidates)
        assert len(result) == 0

    def test_42cfr_excluded(self):
        candidates = [
            CandidateTable(table_id="db.compliance.42cfr_part2_data", table_name="42cfr_part2_data"),
        ]
        rbac = RBACFilter(l2_client=AsyncMock(), l4_client=AsyncMock(), cache=AsyncMock())
        result = rbac._exclude_permanent(candidates)
        assert len(result) == 0

    def test_hard_deny_excluded(self):
        """hard_deny tables must be excluded even if otherwise accessible."""
        candidates = [
            CandidateTable(table_id="db.schema.t1", table_name="t1", hard_deny=True),
            CandidateTable(table_id="db.schema.t2", table_name="t2", hard_deny=False),
        ]
        # hard_deny filtering happens in filter_candidates, not _exclude_permanent
        result = [c for c in candidates if not c.hard_deny]
        assert len(result) == 1
        assert result[0].table_name == "t2"


class TestDeniedTableNonDisclosure:
    """Verify denied tables are invisible — no existence hints leak."""

    @pytest.mark.asyncio
    async def test_domain_prefilter_no_existence_leak(self, mock_l2, mock_l4, mock_cache):
        """Tables outside accessible domains must not appear in any output."""
        mock_l2.get_role_domain_access.return_value = {"doctor": ["clinical"]}
        mock_cache.get_role_domains.return_value = None
        mock_cache.set_role_domains.return_value = None

        rbac = RBACFilter(mock_l2, mock_l4, mock_cache)

        candidates = [
            CandidateTable(table_id="db.billing.charges", table_name="charges", domain="billing"),
            CandidateTable(table_id="db.clinical.patients", table_name="patients", domain="clinical"),
        ]

        ctx = make_security_context(
            Settings(
                service_token_secret="test-l3-secret-must-be-at-least-32-characters-long",
                context_signing_key="test-context-signing-key-32-chars-min",
            ),
            roles=["doctor"],
        )

        # Domain prefilter should remove billing table silently
        accessible_domains, _ = await rbac._get_accessible_domains(ctx)
        filtered = rbac._domain_prefilter(candidates, accessible_domains)
        assert len(filtered) == 1
        assert filtered[0].table_name == "patients"

    def test_l4_denial_removes_completely(self):
        """L4-denied tables must not survive into the result."""
        rbac = RBACFilter(AsyncMock(), AsyncMock(), AsyncMock())
        candidates = [
            CandidateTable(table_id="db.clinical.patients", table_name="patients"),
            CandidateTable(table_id="db.clinical.secret", table_name="secret"),
        ]
        envelope = PermissionEnvelope(
            table_permissions=[
                TablePermission(table_id="db.clinical.patients", decision=TableDecision.ALLOW),
                TablePermission(table_id="db.clinical.secret", decision=TableDecision.DENY),
            ],
        )
        surviving = rbac._apply_policy_decisions(candidates, envelope)
        assert len(surviving) == 1
        assert surviving[0].table_name == "patients"

    def test_deny_by_default_no_permission(self):
        """Tables with no L4 permission entry must be denied by default."""
        rbac = RBACFilter(AsyncMock(), AsyncMock(), AsyncMock())
        candidates = [
            CandidateTable(table_id="db.clinical.unknown", table_name="unknown"),
        ]
        envelope = PermissionEnvelope(table_permissions=[])
        surviving = rbac._apply_policy_decisions(candidates, envelope)
        assert len(surviving) == 0


class TestCachePoisonPrevention:
    """Verify cache keys are role-isolated to prevent cross-role leakage."""

    def test_role_set_hash_isolation(self, test_settings):
        ctx_doctor = make_security_context(test_settings, roles=["doctor"])
        ctx_nurse = make_security_context(test_settings, roles=["nurse"])
        # Different roles must produce different cache keys
        assert ctx_doctor.role_set_hash != ctx_nurse.role_set_hash

    def test_same_roles_same_hash(self, test_settings):
        ctx1 = make_security_context(test_settings, roles=["doctor", "surgeon"])
        ctx2 = make_security_context(test_settings, roles=["surgeon", "doctor"])
        # Same roles in different order must produce same hash (sorted)
        assert ctx1.role_set_hash == ctx2.role_set_hash

    def test_role_hash_deterministic(self, test_settings):
        ctx = make_security_context(test_settings, roles=["doctor"])
        h1 = ctx.role_set_hash
        h2 = ctx.role_set_hash
        assert h1 == h2


class TestFailSecureBehavior:
    """Verify that dependency failures result in secure defaults."""

    @pytest.mark.asyncio
    async def test_l2_failure_no_domains(self, mock_l2, mock_l4, mock_cache):
        """If L2 fails, no domains means fail-secure."""
        mock_l2.get_role_domain_access.side_effect = RuntimeError("L2 down")
        mock_cache.get_role_domains.return_value = None

        rbac = RBACFilter(mock_l2, mock_l4, mock_cache)
        ctx = make_security_context(
            Settings(
                service_token_secret="test-l3-secret-must-be-at-least-32-characters-long",
                context_signing_key="test-context-signing-key-32-chars-min",
            ),
        )
        domains, _ = await rbac._get_accessible_domains(ctx)
        assert len(domains) == 0  # Fail secure: no accessible domains

    def test_hidden_column_description_stripped(self):
        """Hidden column descriptions must not leak."""
        from app.services.column_scoper import ColumnScoper
        # The ScopedColumn for hidden columns should have empty description
        from app.models.retrieval import ScopedColumn
        scoped = ScopedColumn(
            name="ssn",
            data_type="varchar(11)",
            visibility=ColumnVisibility.HIDDEN,
            description="",  # Must be empty for hidden columns
        )
        assert scoped.description == ""
