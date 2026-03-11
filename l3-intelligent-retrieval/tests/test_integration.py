"""Integration tests — full retrieval flow with realistic healthcare questions.

Tests the complete pipeline end-to-end with mocked external dependencies
but real internal service logic.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.enums import (
    ColumnVisibility,
    DomainHint,
    QueryIntent,
    TableDecision,
)
from app.models.l2_models import L2ColumnInfo, L2ForeignKey, L2TableInfo, L2VectorSearchResult
from app.models.l4_models import (
    ColumnDecision,
    PermissionEnvelope,
    TablePermission,
)
from app.models.api import RetrievalRequest
from app.services.orchestrator import RetrievalError, RetrievalOrchestrator
from tests.conftest import (
    make_column,
    make_fk,
    make_security_context,
    make_table,
)


class TestFullRetrievalPipeline:
    """End-to-end pipeline tests with realistic healthcare questions."""

    @pytest.mark.asyncio
    async def test_clinical_data_lookup(self, mock_container, test_settings):
        """Full flow: 'Show all patients with diabetes'"""
        orchestrator = mock_container.orchestrator
        ctx = make_security_context(test_settings, roles=["doctor"], department="endocrinology")

        request = RetrievalRequest(
            question="Show all patients with diabetes",
            security_context=ctx,
        )

        result = await orchestrator.resolve(request)

        assert result.request_id != ""
        assert result.user_id == "dr.jones"
        assert result.intent.intent == QueryIntent.DATA_LOOKUP
        assert DomainHint.CLINICAL in result.intent.domain_hints
        assert result.denied_tables_count >= 0
        assert result.resolved_at is not None

    @pytest.mark.asyncio
    async def test_aggregation_query(self, mock_container, test_settings):
        """Full flow: 'How many patients were admitted this month?'"""
        orchestrator = mock_container.orchestrator
        ctx = make_security_context(test_settings)

        request = RetrievalRequest(
            question="How many patients were admitted this month?",
            security_context=ctx,
        )

        result = await orchestrator.resolve(request)
        assert result.intent.intent == QueryIntent.AGGREGATION

    @pytest.mark.asyncio
    async def test_trend_query(self, mock_container, test_settings):
        """Full flow: 'Show admission trends over the last 12 months'"""
        orchestrator = mock_container.orchestrator
        ctx = make_security_context(test_settings)

        request = RetrievalRequest(
            question="Show admission trends over the last 12 months",
            security_context=ctx,
        )

        result = await orchestrator.resolve(request)
        assert result.intent.intent == QueryIntent.TREND

    @pytest.mark.asyncio
    async def test_join_query(self, mock_container, test_settings):
        """Full flow: 'Join patients with their lab results'"""
        orchestrator = mock_container.orchestrator
        ctx = make_security_context(test_settings)

        request = RetrievalRequest(
            question="Join patients with their lab results and diagnoses",
            security_context=ctx,
        )

        result = await orchestrator.resolve(request)
        assert result.intent.intent == QueryIntent.JOIN_QUERY

    @pytest.mark.asyncio
    async def test_expired_context_rejected(self, mock_container, test_settings):
        """Expired SecurityContext must be rejected with 401."""
        orchestrator = mock_container.orchestrator
        ctx = make_security_context(test_settings, expired=True)

        request = RetrievalRequest(
            question="Show patients",
            security_context=ctx,
        )

        with pytest.raises(RetrievalError) as exc_info:
            await orchestrator.resolve(request)
        assert exc_info.value.code.value == "INVALID_SECURITY_CONTEXT"
        assert exc_info.value.status == 401


class TestRoleSpecificRetrieval:
    """Verify different roles get different schema packages."""

    @pytest.mark.asyncio
    async def test_doctor_sees_clinical(self, mock_container, test_settings):
        """Doctors should see clinical domain tables."""
        orchestrator = mock_container.orchestrator
        ctx = make_security_context(test_settings, roles=["doctor"], department="cardiology")

        request = RetrievalRequest(
            question="Show patient vital signs",
            security_context=ctx,
        )

        result = await orchestrator.resolve(request)
        assert len(result.filtered_schema) > 0

    @pytest.mark.asyncio
    async def test_different_roles_different_cache_keys(self, test_settings):
        """Different roles must produce different cache keys for security."""
        ctx_doctor = make_security_context(test_settings, roles=["doctor"])
        ctx_nurse = make_security_context(test_settings, roles=["nurse"])
        assert ctx_doctor.role_set_hash != ctx_nurse.role_set_hash


class TestSensitivity5Integration:
    """Verify sensitivity-5 substance abuse tables are excluded end-to-end."""

    @pytest.mark.asyncio
    async def test_substance_abuse_never_in_result(self, mock_container, test_settings):
        """substance_abuse_records must NEVER appear in results."""
        # Override L2 search to include substance_abuse
        mock_container.l2_client.search_tables.return_value = [
            make_table("db.clinical.substance_abuse_records", "substance_abuse_records",
                       "clinical", sensitivity=5),
            make_table("db.clinical.patients", "patients", "clinical"),
        ]

        orchestrator = mock_container.orchestrator
        ctx = make_security_context(test_settings, roles=["doctor"], clearance=5)

        request = RetrievalRequest(
            question="Show substance abuse records",
            security_context=ctx,
        )

        result = await orchestrator.resolve(request)
        # substance_abuse must not be in filtered_schema
        for table in result.filtered_schema:
            assert "substance_abuse" not in table.table_id.lower()
            assert "substance_abuse" not in table.table_name.lower()


class TestEmbeddingFailover:
    """Verify embedding failures are handled correctly."""

    @pytest.mark.asyncio
    async def test_embedding_failure_returns_503(self, mock_container, test_settings):
        """If all embedding providers fail, return 503."""
        mock_container.embedding_client.embed.side_effect = RuntimeError("API down")

        orchestrator = mock_container.orchestrator
        ctx = make_security_context(test_settings)

        request = RetrievalRequest(
            question="Show patients",
            security_context=ctx,
        )

        with pytest.raises(RetrievalError) as exc_info:
            await orchestrator.resolve(request)
        assert exc_info.value.code.value == "EMBEDDING_SERVICE_UNAVAILABLE"
        assert exc_info.value.status == 503

    @pytest.mark.asyncio
    async def test_embedding_cache_hit_skips_api(self, mock_container, test_settings):
        """Cached embeddings should bypass the API call."""
        mock_container.cache.get_embedding = AsyncMock(return_value=[0.5] * 1536)

        orchestrator = mock_container.orchestrator
        ctx = make_security_context(test_settings)

        request = RetrievalRequest(
            question="Show patients",
            security_context=ctx,
        )

        result = await orchestrator.resolve(request)
        assert result.retrieval_metadata.embedding_cache_hit is True
        # Embedding API should not have been called
        mock_container.embedding_client.embed.assert_not_called()


class TestPolicyResolutionIntegration:
    """Verify L4 policy resolution is enforced."""

    @pytest.mark.asyncio
    async def test_l4_denial_respected(self, mock_container, test_settings):
        """Tables denied by L4 must not appear in results."""
        mock_container.l4_client.resolve_policies.return_value = PermissionEnvelope(
            table_permissions=[
                TablePermission(
                    table_id="apollo_his.clinical.patients",
                    decision=TableDecision.DENY,
                    reason="Insufficient clearance",
                ),
                TablePermission(
                    table_id="apollo_his.clinical.encounters",
                    decision=TableDecision.ALLOW,
                    columns=[
                        ColumnDecision(column_name="patient_id", visibility=ColumnVisibility.VISIBLE),
                    ],
                ),
            ],
        )

        orchestrator = mock_container.orchestrator
        ctx = make_security_context(test_settings)

        request = RetrievalRequest(
            question="Show patient encounters",
            security_context=ctx,
        )

        result = await orchestrator.resolve(request)
        table_ids = {t.table_id for t in result.filtered_schema}
        assert "apollo_his.clinical.patients" not in table_ids

    @pytest.mark.asyncio
    async def test_l4_unavailable_returns_503(self, mock_container, test_settings):
        """If L4 is unreachable, fail-secure with 503."""
        mock_container.l4_client.resolve_policies.side_effect = RuntimeError(
            "L4 unreachable: Connection refused"
        )

        orchestrator = mock_container.orchestrator
        ctx = make_security_context(test_settings)

        request = RetrievalRequest(
            question="Show patients",
            security_context=ctx,
        )

        with pytest.raises(RetrievalError) as exc_info:
            await orchestrator.resolve(request)
        assert exc_info.value.status == 503
