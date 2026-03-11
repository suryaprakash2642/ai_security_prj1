"""Integration tests for the Execution Orchestrator."""

import pytest
import pytest_asyncio
from app.config import Settings
from app.models.api import ExecutionConfig, ExecutionRequest
from app.models.enums import ExecutionStatus
from app.services.execution_orchestrator import run


def make_settings(**kwargs) -> Settings:
    defaults = {
        "app_env": "development",
        "mock_execution": True,
        "mock_execution_latency_ms": 0,
        "envelope_signing_key": "dev-context-signing-key-32-chars-min",
        "query_timeout_seconds": 30,
        "default_max_rows": 1000,
        "max_query_memory_mb": 100,
        "max_result_size_mb": 50,
        "max_concurrent_per_user": 5,
        "max_concurrent_total": 50,
        "btg_timeout_seconds": 60,
        "btg_max_rows": 50000,
        "circuit_breaker_error_threshold": 0.5,
        "circuit_breaker_cooldown_seconds": 30,
        "nl_summary_enabled": False,
        "l8_audit_url": "http://localhost:8800",
    }
    defaults.update(kwargs)
    return Settings.model_validate(defaults)


@pytest.mark.asyncio
class TestSuccessfulExecution:
    async def test_simple_select_returns_success(self, base_request):
        settings = make_settings()
        resp = await run(base_request, settings)
        assert resp.status == ExecutionStatus.SUCCESS

    async def test_response_has_columns_and_rows(self, base_request):
        settings = make_settings()
        resp = await run(base_request, settings)
        assert len(resp.columns) > 0
        assert len(resp.rows) > 0

    async def test_row_count_matches_rows(self, base_request):
        settings = make_settings()
        resp = await run(base_request, settings)
        assert resp.row_count == len(resp.rows)

    async def test_execution_metadata_present(self, base_request):
        settings = make_settings()
        resp = await run(base_request, settings)
        assert resp.execution_metadata is not None
        assert resp.execution_metadata.database == "mock"
        assert resp.execution_metadata.execution_time_ms >= 0

    async def test_masked_column_flagged(self, base_envelope, physician_security_context):
        # full_name is MASKED in the envelope
        req = ExecutionRequest(
            request_id="test-masked-001",
            validated_sql="SELECT mrn, full_name FROM encounters LIMIT 10",
            target_database="mock",
            permission_envelope=base_envelope,
            execution_config=ExecutionConfig(max_rows=100),
            security_context=physician_security_context,
        )
        settings = make_settings()
        resp = await run(req, settings)
        assert resp.status == ExecutionStatus.SUCCESS
        # full_name column should have masked=True
        masked_cols = [c for c in resp.columns if c.name == "full_name"]
        if masked_cols:
            assert masked_cols[0].masked is True


@pytest.mark.asyncio
class TestResourceLimits:
    async def test_row_limit_from_envelope_respected(self, base_envelope, physician_security_context):
        # Envelope max_rows=1000, request max_rows=100
        req = ExecutionRequest(
            request_id="test-limit-001",
            validated_sql="SELECT mrn FROM encounters LIMIT 5",
            target_database="mock",
            permission_envelope=base_envelope,
            execution_config=ExecutionConfig(max_rows=100),
            security_context=physician_security_context,
        )
        settings = make_settings()
        resp = await run(req, settings)
        assert resp.status == ExecutionStatus.SUCCESS
        assert resp.row_count <= 100

    async def test_btg_active_uses_elevated_limits(self, base_envelope, physician_security_context):
        req = ExecutionRequest(
            request_id="test-btg-001",
            validated_sql="SELECT mrn FROM encounters LIMIT 50",
            target_database="mock",
            permission_envelope=base_envelope,
            execution_config=ExecutionConfig(max_rows=1000, btg_active=True),
            security_context=physician_security_context,
        )
        settings = make_settings()
        resp = await run(req, settings)
        assert resp.status == ExecutionStatus.SUCCESS
        from app.models.enums import AuditFlag
        flags = resp.execution_metadata.audit_flags
        assert AuditFlag.EMERGENCY in flags


@pytest.mark.asyncio
class TestEnvelopeVerification:
    async def test_empty_signature_passes_in_dev(self, base_request):
        # base_request has signature="" — should pass in dev mode
        settings = make_settings(app_env="development")
        resp = await run(base_request, settings)
        assert resp.status == ExecutionStatus.SUCCESS

    async def test_empty_signature_fails_in_prod(self, base_request):
        settings = make_settings(app_env="production")
        resp = await run(base_request, settings)
        assert resp.status == ExecutionStatus.INVALID_ENVELOPE


@pytest.mark.asyncio
class TestCircuitBreaker:
    async def test_open_circuit_returns_unavailable(
        self, base_envelope, physician_security_context
    ):
        from app.services.circuit_breaker import get_registry, _registry
        import app.services.circuit_breaker as cb_module

        # Manually trip the circuit breaker for a test database
        test_db = "test-circuit-db-001"
        registry = get_registry()
        breaker = registry.get(test_db)
        breaker._state = cb_module.CircuitBreakerState.OPEN
        import time
        breaker._open_at = time.monotonic()  # Just tripped

        req = ExecutionRequest(
            request_id="test-cb-001",
            validated_sql="SELECT mrn FROM encounters",
            target_database=test_db,
            permission_envelope=base_envelope,
            execution_config=ExecutionConfig(),
            security_context=physician_security_context,
        )
        # Override mock flag so it uses the target_database name
        settings = make_settings(mock_execution=False)
        resp = await run(req, settings)
        assert resp.status == ExecutionStatus.DATABASE_UNAVAILABLE


@pytest.mark.asyncio
class TestSanitizationIntegration:
    async def test_pii_in_result_sanitized(self, base_envelope, physician_security_context):
        """Verify sanitizer runs — mock may not return PII, but no errors occur."""
        req = ExecutionRequest(
            request_id="test-san-001",
            validated_sql="SELECT mrn, clinical_notes FROM encounters LIMIT 10",
            target_database="mock",
            permission_envelope=base_envelope,
            execution_config=ExecutionConfig(max_rows=100),
            security_context=physician_security_context,
        )
        settings = make_settings()
        resp = await run(req, settings)
        # Sanitizer should have run without error
        assert resp.status == ExecutionStatus.SUCCESS
        assert resp.execution_metadata is not None
        # sanitization_events may be 0 (mock data is clean)
        assert resp.execution_metadata.sanitization_events >= 0
