"""Shared test fixtures for the L2 Knowledge Graph test suite.

Provides mock versions of all infrastructure (Neo4j, PostgreSQL, Redis)
so unit tests run without external dependencies. Integration tests
requiring actual services should be marked @pytest.mark.integration.
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth import ServiceIdentity, create_service_token
from app.config import Settings
from app.dependencies import Container, set_container
from app.models.api import (
    ColumnResponse,
    ConditionResponse,
    ForeignKeyResponse,
    MaskingRuleResponse,
    PIIColumnResponse,
    PolicyResponse,
    RegulatedTableResponse,
    TableResponse,
)
from app.models.enums import (
    ConditionType,
    MaskingStrategy,
    PIIType,
    PolicyType,
    SensitivityLevel,
    ServiceRole,
)


# ── Settings fixture ────────────────────────────────────────


@pytest.fixture
def test_settings() -> Settings:
    """Settings configured for testing (no real infra connections)."""
    return Settings(
        app_env="development",
        neo4j_uri="bolt://localhost:7687",
        neo4j_read_user="neo4j",
        neo4j_read_password="testpass",
        neo4j_write_user="neo4j_writer",
        neo4j_write_password="testpass_writer",
        neo4j_encrypted=False,
        pg_audit_dsn="postgresql+asyncpg://test:test@localhost:5432/l2_test",
        pg_vector_dsn="postgresql+asyncpg://test:test@localhost:5432/l2_test",
        redis_url="redis://localhost:6379/15",
        vault_enabled=False,
        service_token_secret="test-secret-must-be-at-least-32-characters-long",
        allowed_service_ids="l1-identity,l3-retrieval,l4-policy,l6-validation,test-service",
        embedding_api_key="",
        llm_api_key="",
    )


# ── Auth helpers ─────────────────────────────────────────────


@pytest.fixture
def reader_token(test_settings: Settings) -> str:
    """Valid service token with pipeline_reader role."""
    return create_service_token(
        service_id="l3-retrieval",
        role=ServiceRole.PIPELINE_READER,
        secret=test_settings.service_token_secret,
    )


@pytest.fixture
def writer_token(test_settings: Settings) -> str:
    """Valid service token with schema_writer role."""
    return create_service_token(
        service_id="test-service",
        role=ServiceRole.SCHEMA_WRITER,
        secret=test_settings.service_token_secret,
    )


@pytest.fixture
def admin_token(test_settings: Settings) -> str:
    """Valid service token with admin role."""
    return create_service_token(
        service_id="test-service",
        role=ServiceRole.ADMIN,
        secret=test_settings.service_token_secret,
    )


def auth_header(token: str) -> dict[str, str]:
    """Create Authorization header dict from a token."""
    return {"Authorization": f"Bearer {token}"}


# ── Sample data factories ────────────────────────────────────


def make_table(
    fqn: str = "apollo_his.clinical.patients",
    name: str = "patients",
    domain: str = "clinical",
    sensitivity: int = 4,
    hard_deny: bool = False,
) -> TableResponse:
    return TableResponse(
        fqn=fqn,
        name=name,
        description=f"{name} table",
        sensitivity_level=sensitivity,
        domain=domain,
        is_active=True,
        hard_deny=hard_deny,
        schema_name="clinical",
        database_name="apollo_his",
        regulations=["HIPAA"] if sensitivity >= 3 else [],
    )


def make_column(
    fqn: str = "apollo_his.clinical.patients.mrn",
    name: str = "mrn",
    data_type: str = "varchar(20)",
    is_pii: bool = True,
    pii_type: str = "MEDICAL_RECORD_NUMBER",
    sensitivity: int = 5,
    masking: str = "HASH",
) -> ColumnResponse:
    return ColumnResponse(
        fqn=fqn,
        name=name,
        data_type=data_type,
        is_pk=name == "mrn",
        is_nullable=False,
        is_pii=is_pii,
        pii_type=pii_type,
        sensitivity_level=sensitivity,
        masking_strategy=masking,
        description=f"{name} column",
        is_active=True,
        regulations=["HIPAA"] if sensitivity >= 3 else [],
    )


def make_policy(
    policy_id: str = "pol_clinical_read",
    policy_type: PolicyType = PolicyType.ALLOW,
    bound_roles: list[str] | None = None,
    target_tables: list[str] | None = None,
    is_hard_deny: bool = False,
) -> PolicyResponse:
    return PolicyResponse(
        policy_id=policy_id,
        policy_type=policy_type,
        nl_description="Allow clinical staff to read patient demographic data",
        structured_rule={"effect": policy_type.value, "resources": target_tables or []},
        priority=100,
        is_hard_deny=is_hard_deny,
        bound_roles=bound_roles or ["doctor"],
        target_tables=target_tables or ["apollo_his.clinical.patients"],
    )


# ── Mock infrastructure ──────────────────────────────────────


@pytest.fixture
def mock_neo4j():
    """Mock Neo4jManager that returns empty results by default."""
    manager = AsyncMock()
    manager.execute_read = AsyncMock(return_value=[])
    manager.execute_write = AsyncMock(return_value=[])
    manager.verify_connectivity = AsyncMock(return_value=True)
    return manager


@pytest.fixture
def mock_graph_reader():
    """Mock GraphReadRepository with pre-configured return values."""
    reader = AsyncMock()
    reader.get_tables_by_domain = AsyncMock(return_value=[])
    reader.get_table_columns = AsyncMock(return_value=[])
    reader.get_tables_by_sensitivity = AsyncMock(return_value=[])
    reader.get_foreign_keys = AsyncMock(return_value=[])
    reader.search_tables = AsyncMock(return_value=[])
    reader.get_all_active_tables = AsyncMock(return_value=[])
    reader.get_policies_for_roles = AsyncMock(return_value=[])
    reader.get_policies_for_table = AsyncMock(return_value=[])
    reader.get_join_restrictions = AsyncMock(return_value=[])
    reader.get_hard_deny_tables = AsyncMock(return_value=[])
    reader.get_pii_columns = AsyncMock(return_value=[])
    reader.get_tables_regulated_by = AsyncMock(return_value=[])
    reader.get_masking_rules = AsyncMock(return_value=[])
    reader.get_inherited_roles = AsyncMock(return_value=[])
    reader.get_role_domains = AsyncMock(return_value=[])
    reader.get_node_counts = AsyncMock(return_value={"Table": 10, "Column": 50, "Policy": 5})
    return reader


@pytest.fixture
def mock_graph_writer():
    """Mock GraphWriteRepository."""
    writer = AsyncMock()
    writer.upsert_policy = AsyncMock(return_value={"version": 1})
    writer.bind_policy_to_role = AsyncMock()
    writer.bind_policy_to_table = AsyncMock()
    writer.bind_policy_to_domain = AsyncMock()
    writer.deactivate_policy = AsyncMock()
    writer.update_column_classification = AsyncMock()
    return writer


@pytest.fixture
def mock_audit_repo():
    """Mock AuditRepository."""
    repo = AsyncMock()
    repo.increment_graph_version = AsyncMock(return_value=1)
    repo.log_change = AsyncMock()
    repo.log_changes_batch = AsyncMock()
    repo.save_policy_version = AsyncMock()
    repo.get_policy_version = AsyncMock(return_value=None)
    repo.get_pending_reviews = AsyncMock(return_value=[])
    repo.approve_review = AsyncMock()
    repo.reject_review = AsyncMock()
    repo.add_review_item = AsyncMock(return_value=1)
    repo.get_current_version = AsyncMock(return_value={"version": 1, "updated_at": None, "updated_by": "system"})
    repo.get_changes = AsyncMock(return_value=[])
    repo.health_check = AsyncMock(return_value=True)
    return repo


@pytest.fixture
def mock_cache():
    """Mock CacheService that always returns None (cache miss)."""
    cache = AsyncMock()
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock()
    return cache


# ── Mock Container & Test Client ─────────────────────────────


@pytest.fixture
def mock_container(
    test_settings, mock_neo4j, mock_graph_reader, mock_graph_writer,
    mock_audit_repo, mock_cache,
):
    """Fully mocked DI container."""
    container = MagicMock(spec=Container)
    container.settings = test_settings
    container.neo4j = mock_neo4j
    container.graph_reader = mock_graph_reader
    container.graph_writer = mock_graph_writer
    container.audit_repo = mock_audit_repo
    container.cache = mock_cache
    container.policy_service = MagicMock()
    container.classification_engine = MagicMock()
    container.schema_discovery = MagicMock()
    container.embedding_pipeline = MagicMock()
    container.health_check = MagicMock()
    return container


@pytest.fixture
def client(mock_container, test_settings) -> TestClient:
    """FastAPI test client with mocked dependencies."""
    # Patch get_settings to use test_settings
    with patch("app.config.get_settings", return_value=test_settings):
        from app.main import create_app
        from app.dependencies import set_container

        set_container(mock_container)
        app = create_app()
        app.state.container = mock_container
        return TestClient(app)
