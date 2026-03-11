"""Shared test fixtures for the L3 Intelligent Retrieval test suite.

Provides mock versions of all external dependencies (L2, L4, Redis, pgvector)
so unit tests run without external services.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth import create_service_token, sign_security_context
from app.config import Settings
from app.dependencies import Container, set_container
from app.models.enums import (
    ColumnVisibility,
    DomainHint,
    QueryIntent,
    ServiceRole,
    TableDecision,
)
from app.models.l2_models import L2ColumnInfo, L2ForeignKey, L2TableInfo
from app.models.l4_models import (
    ColumnDecision,
    JoinRestriction,
    PermissionEnvelope,
    TablePermission,
)
from app.models.retrieval import CandidateTable, IntentResult
from app.models.security import SecurityContext


# ── Settings ────────────────────────────────────────────────


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        app_env="development",
        service_token_secret="dev-l3-secret-must-be-at-least-32-characters-long",
        allowed_service_ids="l5-generation,test-service,admin-service,l1-identity,admin-console",
        context_signing_key="dev-context-signing-key-32-chars-min",
        embedding_voyage_api_key="",
        embedding_openai_api_key="",
        l2_base_url="http://localhost:8200",
        l4_base_url="http://localhost:8400",
        redis_url="redis://localhost:6379/15",
        pgvector_dsn="postgresql+asyncpg://test:test@localhost:5432/l3_test",
    )


# ── Auth helpers ────────────────────────────────────────────


@pytest.fixture
def reader_token(test_settings: Settings) -> str:
    return create_service_token(
        "l5-generation", ServiceRole.PIPELINE_READER.value,
        test_settings.service_token_secret,
    )


@pytest.fixture
def admin_token(test_settings: Settings) -> str:
    return create_service_token(
        "admin-service", ServiceRole.ADMIN.value,
        test_settings.service_token_secret,
    )


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ── SecurityContext helpers ──────────────────────────────────


def make_security_context(
    test_settings: Settings,
    user_id: str = "dr.jones",
    roles: list[str] | None = None,
    department: str = "cardiology",
    clearance: int = 3,
    expired: bool = False,
) -> SecurityContext:
    """Create a properly signed SecurityContext for testing."""
    if roles is None:
        roles = ["doctor"]

    expiry = datetime.now(UTC) + timedelta(hours=-1 if expired else 1)

    ctx_dict = {
        "user_id": user_id,
        "effective_roles": roles,
        "department": department,
        "clearance_level": clearance,
        "session_id": "test-session-001",
        "context_expiry": expiry,
        "context_signature": "placeholder",
    }

    sig = sign_security_context(ctx_dict, test_settings.context_signing_key)
    ctx_dict["context_signature"] = sig

    return SecurityContext(**ctx_dict)


# ── Sample L2 data ──────────────────────────────────────────


def make_table(
    fqn: str = "apollo_his.clinical.patients",
    name: str = "patients",
    domain: str = "clinical",
    sensitivity: int = 3,
) -> L2TableInfo:
    return L2TableInfo(
        fqn=fqn, name=name, description=f"{name} table",
        sensitivity_level=sensitivity, domain=domain,
    )


def make_column(
    fqn: str = "apollo_his.clinical.patients.mrn",
    name: str = "mrn",
    data_type: str = "varchar(20)",
    is_pii: bool = True,
) -> L2ColumnInfo:
    return L2ColumnInfo(
        fqn=fqn, name=name, data_type=data_type,
        is_pii=is_pii, sensitivity_level=5 if is_pii else 1,
    )


def make_fk(
    src_col: str = "patient_id",
    tgt_table: str = "patients",
    tgt_col: str = "patient_id",
    tgt_fqn: str = "apollo_his.clinical.patients",
) -> L2ForeignKey:
    return L2ForeignKey(
        source_column=src_col,
        target_table=tgt_table,
        target_column=tgt_col,
        target_table_fqn=tgt_fqn,
    )


# ── Sample L4 envelope ──────────────────────────────────────


def make_permission_envelope(
    tables: list[tuple[str, TableDecision]] | None = None,
) -> PermissionEnvelope:
    """Create a mock PermissionEnvelope."""
    if tables is None:
        tables = [
            ("apollo_his.clinical.patients", TableDecision.ALLOW),
            ("apollo_his.clinical.encounters", TableDecision.ALLOW),
        ]

    perms = []
    for table_id, decision in tables:
        cols = []
        if decision != TableDecision.DENY:
            cols = [
                ColumnDecision(column_name="patient_id", visibility=ColumnVisibility.VISIBLE),
                ColumnDecision(column_name="name", visibility=ColumnVisibility.MASKED,
                               masking_expression="MASKED(name)"),
                ColumnDecision(column_name="ssn", visibility=ColumnVisibility.HIDDEN),
            ]
        perms.append(TablePermission(
            table_id=table_id,
            decision=decision,
            columns=cols,
            row_filters=["facility_id = 'HOSP_01'"] if decision != TableDecision.DENY else [],
        ))

    return PermissionEnvelope(
        table_permissions=perms,
        global_nl_rules=["Only return data for the user's assigned facility"],
    )


# ── Mock infrastructure ─────────────────────────────────────


@pytest.fixture
def mock_cache():
    cache = AsyncMock()
    cache.get_embedding = AsyncMock(return_value=None)
    cache.set_embedding = AsyncMock()
    cache.get_role_domains = AsyncMock(return_value=None)
    cache.set_role_domains = AsyncMock()
    cache.get_vector_results = AsyncMock(return_value=None)
    cache.set_vector_results = AsyncMock()
    cache.get_schema_fragment = AsyncMock(return_value=None)
    cache.set_schema_fragment = AsyncMock()
    cache.get_columns_local = MagicMock(return_value=None)
    cache.set_columns_local = MagicMock()
    cache.get_fk_local = MagicMock(return_value=None)
    cache.set_fk_local = MagicMock()
    cache.invalidate_all = AsyncMock(return_value=0)
    cache.health_check = AsyncMock(return_value=True)
    cache.stats = {"hits": 0, "misses": 0}
    return cache


@pytest.fixture
def mock_l2():
    l2 = AsyncMock()
    l2.search_tables = AsyncMock(return_value=[
        make_table("apollo_his.clinical.patients", "patients", "clinical"),
        make_table("apollo_his.clinical.encounters", "encounters", "clinical"),
    ])
    l2.get_tables_by_domain = AsyncMock(return_value=[
        make_table("apollo_his.clinical.patients", "patients", "clinical"),
    ])
    l2.get_table_columns = AsyncMock(return_value=[
        make_column("apollo_his.clinical.patients.patient_id", "patient_id", "integer", False),
        make_column("apollo_his.clinical.patients.name", "name", "varchar(100)", True),
        make_column("apollo_his.clinical.patients.mrn", "mrn", "varchar(20)", True),
        make_column("apollo_his.clinical.patients.ssn", "ssn", "varchar(11)", True),
    ])
    l2.get_foreign_keys = AsyncMock(return_value=[
        make_fk("patient_id", "patients", "patient_id", "apollo_his.clinical.patients"),
    ])
    l2.get_role_domain_access = AsyncMock(return_value={
        "doctor": ["clinical", "laboratory"],
    })
    l2.health_check = AsyncMock(return_value=True)
    return l2


@pytest.fixture
def mock_l4():
    l4 = AsyncMock()
    l4.resolve_policies = AsyncMock(return_value=make_permission_envelope())
    l4.health_check = AsyncMock(return_value=True)
    return l4


@pytest.fixture
def mock_embedding_client():
    ec = AsyncMock()
    ec.embed = AsyncMock(return_value=[0.1] * 1536)
    ec.health_check = AsyncMock(return_value=True)
    return ec


@pytest.fixture
def mock_vector_client():
    vc = AsyncMock()
    vc.search_similar = AsyncMock(return_value=[])
    vc.health_check = AsyncMock(return_value=True)
    return vc


# ── Mock Container & Test Client ────────────────────────────


@pytest.fixture
def mock_container(
    test_settings, mock_cache, mock_l2, mock_l4,
    mock_embedding_client, mock_vector_client,
):
    """Fully mocked DI container."""
    container = MagicMock(spec=Container)
    container.settings = test_settings
    container.cache = mock_cache
    container.l2_client = mock_l2
    container.l4_client = mock_l4
    container.embedding_client = mock_embedding_client
    container.vector_client = mock_vector_client

    # Build real services with mocked dependencies
    from app.services.embedding_engine import EmbeddingEngine
    from app.services.intent_classifier import IntentClassifier
    from app.services.retrieval_pipeline import RetrievalPipeline
    from app.services.ranking_engine import RankingEngine
    from app.services.rbac_filter import RBACFilter
    from app.services.column_scoper import ColumnScoper
    from app.services.join_graph import JoinGraphBuilder
    from app.services.context_assembler import ContextAssembler
    from app.services.orchestrator import RetrievalOrchestrator

    container.intent_classifier = IntentClassifier()
    container.ranking_engine = RankingEngine()
    container.context_assembler = ContextAssembler()

    container.embedding_engine = EmbeddingEngine(
        settings=test_settings,
        embedding_client=mock_embedding_client,
        cache=mock_cache,
    )
    container.retrieval_pipeline = RetrievalPipeline(
        settings=test_settings,
        l2_client=mock_l2,
        vector_client=mock_vector_client,
        cache=mock_cache,
    )
    container.rbac_filter = RBACFilter(
        l2_client=mock_l2, l4_client=mock_l4, cache=mock_cache,
    )
    container.column_scoper = ColumnScoper(l2_client=mock_l2, cache=mock_cache)
    container.join_graph_builder = JoinGraphBuilder(l2_client=mock_l2, cache=mock_cache)

    container.orchestrator = RetrievalOrchestrator(
        settings=test_settings,
        embedding_engine=container.embedding_engine,
        intent_classifier=container.intent_classifier,
        retrieval_pipeline=container.retrieval_pipeline,
        ranking_engine=container.ranking_engine,
        rbac_filter=container.rbac_filter,
        column_scoper=container.column_scoper,
        join_graph_builder=container.join_graph_builder,
        context_assembler=container.context_assembler,
    )

    return container


@pytest.fixture
def client(mock_container, test_settings) -> TestClient:
    from app.config import get_settings
    get_settings.cache_clear()
    # Patch load_settings (the underlying function) so that the lru_cache'd
    # get_settings() returns test_settings when FastAPI's DI resolves Depends(get_settings).
    with patch("app.config.load_settings", return_value=test_settings):
        from app.main import create_app
        set_container(mock_container)
        app = create_app()
        app.state.container = mock_container
        yield TestClient(app)
    get_settings.cache_clear()  # Restore clean state after test
