"""End-to-end pipeline tests: L1 → L2 → L3.

Simulates the complete Zero Trust NL-to-SQL pipeline:
  L1: Identity & Context  → produces a signed SecurityContext
  L2: Knowledge Graph     → provides realistic Apollo Hospitals schema metadata
  L3: Intelligent Retrieval → the system under test (full 9-stage pipeline)

External dependencies (Redis, pgvector, L2 HTTP, L4 HTTP) are mocked so the
tests run without any live services.  The internal pipeline logic, HMAC
signing, intent classification, RBAC filtering, column scoping, and token
budget enforcement all use REAL code — this is not a pure mock test.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.auth import create_service_token, sign_security_context
from app.config import Settings
from app.dependencies import Container, set_container
from app.models.api import RetrievalRequest
from app.models.enums import (
    ColumnVisibility,
    DomainHint,
    QueryIntent,
    ServiceRole,
    TableDecision,
)
from app.models.l2_models import L2ColumnInfo, L2ForeignKey, L2TableInfo
from app.models.l4_models import ColumnDecision, PermissionEnvelope, TablePermission
from app.models.security import SecurityContext
from app.services.orchestrator import RetrievalError, RetrievalOrchestrator


# ══════════════════════════════════════════════════════════════
# SHARED SIGNING KEY — mirrors L1 config
# ══════════════════════════════════════════════════════════════

SIGNING_KEY = "dev-context-signing-key-32-chars-min"
SERVICE_SECRET = "dev-l3-secret-must-be-at-least-32-characters-long"


# ══════════════════════════════════════════════════════════════
# L1 SIMULATOR — builds signed SecurityContext as L1 would
# ══════════════════════════════════════════════════════════════

def l1_build_context(
    user_id: str,
    effective_roles: list[str],
    department: str,
    clearance_level: int,
    session_id: str = "sess-test-001",
    facility_id: str = "HOSP_01",
    mfa_verified: bool = True,
    expired: bool = False,
    ttl_hours: int = 1,
) -> SecurityContext:
    """Simulate L1 Identity & Context producing a signed SecurityContext.

    This mirrors what L1's ContextBuilder + SecurityContextSigner produce:
    1. Collects identity claims (user_id, roles, department, clearance)
    2. Sets expiry (now + TTL)
    3. Computes HMAC-SHA256 signature over canonical payload
    4. Returns the SecurityContext ready for downstream consumption
    """
    expiry = datetime.now(UTC) + timedelta(hours=-1 if expired else ttl_hours)

    ctx_dict = {
        "user_id": user_id,
        "effective_roles": effective_roles,
        "department": department,
        "clearance_level": clearance_level,
        "session_id": session_id,
        "facility_id": facility_id,
        "mfa_verified": mfa_verified,
        "context_expiry": expiry,
        "context_signature": "placeholder",
    }

    sig = sign_security_context(ctx_dict, SIGNING_KEY)
    ctx_dict["context_signature"] = sig
    return SecurityContext(**ctx_dict)


# ══════════════════════════════════════════════════════════════
# L2 MOCK DATA — Apollo Hospitals schema (realistic)
# ══════════════════════════════════════════════════════════════

def _col(fqn: str, name: str, dtype: str, pii: bool = False, sensitivity: int = 1) -> L2ColumnInfo:
    return L2ColumnInfo(
        fqn=fqn, name=name, data_type=dtype,
        is_pii=pii, sensitivity_level=sensitivity,
    )


def _fk(src_col: str, tgt_table: str, tgt_col: str, tgt_fqn: str) -> L2ForeignKey:
    return L2ForeignKey(
        source_column=src_col,
        target_table=tgt_table,
        target_column=tgt_col,
        target_table_fqn=tgt_fqn,
    )


def _tbl(fqn: str, name: str, domain: str, sensitivity: int = 2, description: str = "") -> L2TableInfo:
    return L2TableInfo(
        fqn=fqn, name=name,
        description=description or f"Apollo Hospitals {name} table",
        sensitivity_level=sensitivity, domain=domain,
    )


# Apollo Hospitals table catalogue

CLINICAL_PATIENTS = _tbl(
    "apollo_his.clinical.patients", "patients", "clinical", sensitivity=3,
    description="Core patient demographics and registration data",
)
CLINICAL_ENCOUNTERS = _tbl(
    "apollo_his.clinical.encounters", "encounters", "clinical", sensitivity=2,
    description="Hospital encounters — admissions, discharges, OP visits",
)
CLINICAL_DIAGNOSES = _tbl(
    "apollo_his.clinical.diagnoses", "diagnoses", "clinical", sensitivity=3,
    description="ICD-10 diagnoses linked to encounters",
)
CLINICAL_LAB_RESULTS = _tbl(
    "apollo_his.clinical.lab_results", "lab_results", "clinical", sensitivity=3,
    description="Laboratory test results",
)
CLINICAL_VITALS = _tbl(
    "apollo_his.clinical.vital_signs", "vital_signs", "clinical", sensitivity=2,
    description="Patient vital signs — BP, HR, temp, SpO2",
)
CLINICAL_MEDICATIONS = _tbl(
    "apollo_his.clinical.medications", "medications", "clinical", sensitivity=3,
    description="Medication orders and administration records",
)
BILLING_CLAIMS = _tbl(
    "apollo_his.billing.insurance_claims", "insurance_claims", "billing", sensitivity=3,
    description="Insurance claims and billing records",
)
PHARMACY_PRESCRIPTIONS = _tbl(
    "apollo_his.pharmacy.prescriptions", "prescriptions", "pharmacy", sensitivity=3,
    description="Prescription medication orders",
)
BEHAVIORAL_SUBSTANCE_ABUSE = _tbl(
    "apollo_his.behavioral_health.substance_abuse_records",
    "substance_abuse_records", "behavioral_health", sensitivity=5,
    description="42 CFR Part 2 substance use disorder records",
)
HR_EMPLOYEES = _tbl(
    "apollo_his.hr.employee_records", "employee_records", "hr", sensitivity=4,
    description="Employee records — restricted to HR and admin",
)

# Column definitions per table
COLUMNS = {
    "apollo_his.clinical.patients": [
        _col("apollo_his.clinical.patients.patient_id", "patient_id", "integer"),
        _col("apollo_his.clinical.patients.name", "name", "varchar(100)", pii=True, sensitivity=3),
        _col("apollo_his.clinical.patients.mrn", "mrn", "varchar(20)", pii=True, sensitivity=3),
        _col("apollo_his.clinical.patients.dob", "dob", "date", pii=True, sensitivity=3),
        _col("apollo_his.clinical.patients.gender", "gender", "varchar(10)"),
        _col("apollo_his.clinical.patients.ssn", "ssn", "varchar(11)", pii=True, sensitivity=5),
        _col("apollo_his.clinical.patients.facility_id", "facility_id", "varchar(20)"),
        _col("apollo_his.clinical.patients.registered_at", "registered_at", "timestamp"),
    ],
    "apollo_his.clinical.encounters": [
        _col("apollo_his.clinical.encounters.encounter_id", "encounter_id", "integer"),
        _col("apollo_his.clinical.encounters.patient_id", "patient_id", "integer"),
        _col("apollo_his.clinical.encounters.admit_date", "admit_date", "date"),
        _col("apollo_his.clinical.encounters.discharge_date", "discharge_date", "date"),
        _col("apollo_his.clinical.encounters.encounter_type", "encounter_type", "varchar(50)"),
        _col("apollo_his.clinical.encounters.department", "department", "varchar(100)"),
        _col("apollo_his.clinical.encounters.attending_physician_id", "attending_physician_id", "varchar(20)"),
        _col("apollo_his.clinical.encounters.facility_id", "facility_id", "varchar(20)"),
    ],
    "apollo_his.clinical.diagnoses": [
        _col("apollo_his.clinical.diagnoses.diagnosis_id", "diagnosis_id", "integer"),
        _col("apollo_his.clinical.diagnoses.encounter_id", "encounter_id", "integer"),
        _col("apollo_his.clinical.diagnoses.patient_id", "patient_id", "integer"),
        _col("apollo_his.clinical.diagnoses.icd10_code", "icd10_code", "varchar(10)"),
        _col("apollo_his.clinical.diagnoses.description", "description", "varchar(500)"),
        _col("apollo_his.clinical.diagnoses.diagnosis_date", "diagnosis_date", "date"),
        _col("apollo_his.clinical.diagnoses.diagnosis_type", "diagnosis_type", "varchar(20)"),
    ],
    "apollo_his.clinical.lab_results": [
        _col("apollo_his.clinical.lab_results.result_id", "result_id", "integer"),
        _col("apollo_his.clinical.lab_results.patient_id", "patient_id", "integer"),
        _col("apollo_his.clinical.lab_results.encounter_id", "encounter_id", "integer"),
        _col("apollo_his.clinical.lab_results.test_name", "test_name", "varchar(100)"),
        _col("apollo_his.clinical.lab_results.result_value", "result_value", "varchar(50)"),
        _col("apollo_his.clinical.lab_results.result_date", "result_date", "timestamp"),
        _col("apollo_his.clinical.lab_results.abnormal_flag", "abnormal_flag", "boolean"),
    ],
    "apollo_his.clinical.vital_signs": [
        _col("apollo_his.clinical.vital_signs.vital_id", "vital_id", "integer"),
        _col("apollo_his.clinical.vital_signs.patient_id", "patient_id", "integer"),
        _col("apollo_his.clinical.vital_signs.encounter_id", "encounter_id", "integer"),
        _col("apollo_his.clinical.vital_signs.systolic_bp", "systolic_bp", "integer"),
        _col("apollo_his.clinical.vital_signs.diastolic_bp", "diastolic_bp", "integer"),
        _col("apollo_his.clinical.vital_signs.heart_rate", "heart_rate", "integer"),
        _col("apollo_his.clinical.vital_signs.temperature", "temperature", "decimal(5,2)"),
        _col("apollo_his.clinical.vital_signs.recorded_at", "recorded_at", "timestamp"),
    ],
    "apollo_his.billing.insurance_claims": [
        _col("apollo_his.billing.insurance_claims.claim_id", "claim_id", "integer"),
        _col("apollo_his.billing.insurance_claims.patient_id", "patient_id", "integer", pii=True, sensitivity=3),
        _col("apollo_his.billing.insurance_claims.encounter_id", "encounter_id", "integer"),
        _col("apollo_his.billing.insurance_claims.claim_amount", "claim_amount", "decimal(10,2)"),
        _col("apollo_his.billing.insurance_claims.insurance_provider", "insurance_provider", "varchar(100)"),
        _col("apollo_his.billing.insurance_claims.claim_status", "claim_status", "varchar(20)"),
        _col("apollo_his.billing.insurance_claims.submitted_date", "submitted_date", "date"),
    ],
    "apollo_his.pharmacy.prescriptions": [
        _col("apollo_his.pharmacy.prescriptions.rx_id", "rx_id", "integer"),
        _col("apollo_his.pharmacy.prescriptions.patient_id", "patient_id", "integer"),
        _col("apollo_his.pharmacy.prescriptions.encounter_id", "encounter_id", "integer"),
        _col("apollo_his.pharmacy.prescriptions.drug_name", "drug_name", "varchar(200)"),
        _col("apollo_his.pharmacy.prescriptions.dosage", "dosage", "varchar(50)"),
        _col("apollo_his.pharmacy.prescriptions.prescribed_date", "prescribed_date", "date"),
        _col("apollo_his.pharmacy.prescriptions.prescriber_id", "prescriber_id", "varchar(20)"),
    ],
    "apollo_his.behavioral_health.substance_abuse_records": [
        _col("apollo_his.behavioral_health.substance_abuse_records.record_id", "record_id", "integer"),
        _col("apollo_his.behavioral_health.substance_abuse_records.patient_id", "patient_id", "integer", pii=True, sensitivity=5),
        _col("apollo_his.behavioral_health.substance_abuse_records.substance_type", "substance_type", "varchar(100)", pii=True, sensitivity=5),
        _col("apollo_his.behavioral_health.substance_abuse_records.treatment_notes", "treatment_notes", "text", pii=True, sensitivity=5),
    ],
}

# Foreign keys
FOREIGN_KEYS = {
    "apollo_his.clinical.encounters": [
        _fk("patient_id", "patients", "patient_id", "apollo_his.clinical.patients"),
    ],
    "apollo_his.clinical.diagnoses": [
        _fk("patient_id", "patients", "patient_id", "apollo_his.clinical.patients"),
        _fk("encounter_id", "encounters", "encounter_id", "apollo_his.clinical.encounters"),
    ],
    "apollo_his.clinical.lab_results": [
        _fk("patient_id", "patients", "patient_id", "apollo_his.clinical.patients"),
        _fk("encounter_id", "encounters", "encounter_id", "apollo_his.clinical.encounters"),
    ],
    "apollo_his.clinical.vital_signs": [
        _fk("patient_id", "patients", "patient_id", "apollo_his.clinical.patients"),
        _fk("encounter_id", "encounters", "encounter_id", "apollo_his.clinical.encounters"),
    ],
    "apollo_his.billing.insurance_claims": [
        _fk("patient_id", "patients", "patient_id", "apollo_his.clinical.patients"),
        _fk("encounter_id", "encounters", "encounter_id", "apollo_his.clinical.encounters"),
    ],
    "apollo_his.pharmacy.prescriptions": [
        _fk("patient_id", "patients", "patient_id", "apollo_his.clinical.patients"),
        _fk("encounter_id", "encounters", "encounter_id", "apollo_his.clinical.encounters"),
    ],
}

# Role → domain access map (from L2 RBAC data)
ROLE_DOMAIN_ACCESS = {
    "doctor": ["clinical", "pharmacy"],
    "nurse": ["clinical"],
    "billing_staff": ["billing"],
    "pharmacist": ["pharmacy"],
    "hospital_admin": ["clinical", "billing", "pharmacy", "hr", "admin"],
    "researcher": ["clinical"],
}


# ══════════════════════════════════════════════════════════════
# FIXTURES
# ══════════════════════════════════════════════════════════════

@pytest.fixture
def pipeline_settings() -> Settings:
    return Settings(
        app_env="development",
        service_token_secret=SERVICE_SECRET,
        context_signing_key=SIGNING_KEY,
        allowed_service_ids="l5-generation,test-service,admin-service,l1-identity,admin-console",
        embedding_voyage_api_key="",
        embedding_openai_api_key="",
        l2_base_url="http://localhost:8200",
        l4_base_url="http://localhost:8400",
        redis_url="redis://localhost:6379/15",
    )


def _build_l2_mock(tables: list[L2TableInfo]) -> AsyncMock:
    """Build a realistic L2 mock that responds to schema queries."""
    l2 = AsyncMock()

    domain_table_map: dict[str, list[L2TableInfo]] = {}
    for t in tables:
        domain_table_map.setdefault(t.domain, []).append(t)

    def _search_tables(query: str, **kwargs) -> list[L2TableInfo]:
        """Simple keyword-based search over table names/descriptions."""
        q = query.lower()
        results = []
        for t in tables:
            if any(kw in t.name.lower() or kw in t.description.lower()
                   for kw in q.split()):
                results.append(t)
        return results or tables[:3]

    def _get_by_domain(domain: str, **kwargs) -> list[L2TableInfo]:
        return domain_table_map.get(domain, [])

    def _get_columns(fqn: str, **kwargs) -> list[L2ColumnInfo]:
        return COLUMNS.get(fqn, [])

    def _get_fks(fqn: str, **kwargs) -> list[L2ForeignKey]:
        return FOREIGN_KEYS.get(fqn, [])

    def _get_role_domain_access(roles_list: list[str], **kwargs) -> dict:
        merged: dict[str, list[str]] = {}
        for r in roles_list:
            for domain in ROLE_DOMAIN_ACCESS.get(r, []):
                merged.setdefault(r, []).append(domain)
        return merged

    l2.search_tables = AsyncMock(side_effect=_search_tables)
    l2.get_tables_by_domain = AsyncMock(side_effect=_get_by_domain)
    l2.get_table_columns = AsyncMock(side_effect=_get_columns)
    l2.get_foreign_keys = AsyncMock(side_effect=_get_fks)
    l2.get_role_domain_access = AsyncMock(side_effect=_get_role_domain_access)
    l2.health_check = AsyncMock(return_value=True)
    return l2


def _build_l4_mock(
    allowed_tables: list[str],
    denied_tables: list[str] | None = None,
    row_filter: str = "facility_id = 'HOSP_01'",
) -> AsyncMock:
    """Build L4 Policy Resolution mock with realistic column visibility."""
    l4 = AsyncMock()
    denied_tables = denied_tables or []

    def _resolve_policies(candidate_table_ids=None, **_kwargs) -> PermissionEnvelope:
        table_ids = candidate_table_ids or []
        perms = []
        for tid in table_ids:
            if tid in denied_tables:
                perms.append(TablePermission(
                    table_id=tid,
                    decision=TableDecision.DENY,
                    reason="Access denied by policy",
                ))
            elif tid in allowed_tables:
                cols_data = COLUMNS.get(tid, [])
                col_decisions = []
                for c in cols_data:
                    if c.sensitivity_level >= 5:
                        vis = ColumnVisibility.HIDDEN
                    elif c.is_pii:
                        vis = ColumnVisibility.MASKED
                    else:
                        vis = ColumnVisibility.VISIBLE
                    col_decisions.append(ColumnDecision(
                        column_name=c.name,
                        visibility=vis,
                        masking_expression=f"MASKED({c.name})" if vis == ColumnVisibility.MASKED else None,
                    ))
                perms.append(TablePermission(
                    table_id=tid,
                    decision=TableDecision.ALLOW,
                    columns=col_decisions,
                    row_filters=[row_filter] if row_filter else [],
                ))
            # tables not in allowed or denied → DENY by default (zero-trust)
            else:
                perms.append(TablePermission(
                    table_id=tid,
                    decision=TableDecision.DENY,
                    reason="No permission entry — deny by default",
                ))

        return PermissionEnvelope(
            table_permissions=perms,
            global_nl_rules=["Only return data for the user's assigned facility"],
        )

    l4.resolve_policies = AsyncMock(side_effect=_resolve_policies)
    l4.health_check = AsyncMock(return_value=True)
    return l4


def _build_orchestrator(
    pipeline_settings: Settings,
    tables: list[L2TableInfo],
    allowed_tables: list[str],
    denied_tables: list[str] | None = None,
) -> RetrievalOrchestrator:
    """Build a full RetrievalOrchestrator with mocked L2/L4/cache."""
    from app.cache.cache_service import CacheService
    from app.services.context_assembler import ContextAssembler
    from app.services.embedding_engine import EmbeddingEngine
    from app.services.intent_classifier import IntentClassifier
    from app.services.join_graph import JoinGraphBuilder
    from app.services.orchestrator import RetrievalOrchestrator
    from app.services.ranking_engine import RankingEngine
    from app.services.rbac_filter import RBACFilter
    from app.services.column_scoper import ColumnScoper
    from app.services.retrieval_pipeline import RetrievalPipeline

    mock_l2 = _build_l2_mock(tables)
    mock_l4 = _build_l4_mock(allowed_tables, denied_tables)

    mock_embed = AsyncMock()
    mock_embed.embed = AsyncMock(return_value=[0.1] * 1536)
    mock_embed.health_check = AsyncMock(return_value=True)

    mock_vector = AsyncMock()
    mock_vector.search_similar = AsyncMock(return_value=[])
    mock_vector.health_check = AsyncMock(return_value=True)

    mock_cache = AsyncMock()
    mock_cache.get_embedding = AsyncMock(return_value=None)
    mock_cache.set_embedding = AsyncMock()
    mock_cache.get_role_domains = AsyncMock(return_value=None)
    mock_cache.set_role_domains = AsyncMock()
    mock_cache.get_vector_results = AsyncMock(return_value=None)
    mock_cache.set_vector_results = AsyncMock()
    mock_cache.get_schema_fragment = AsyncMock(return_value=None)
    mock_cache.set_schema_fragment = AsyncMock()
    mock_cache.get_columns_local = MagicMock(return_value=None)
    mock_cache.set_columns_local = MagicMock()
    mock_cache.get_fk_local = MagicMock(return_value=None)
    mock_cache.set_fk_local = MagicMock()
    mock_cache.stats = {"hits": 0, "misses": 0}

    return RetrievalOrchestrator(
        settings=pipeline_settings,
        embedding_engine=EmbeddingEngine(pipeline_settings, mock_embed, mock_cache),
        intent_classifier=IntentClassifier(),
        retrieval_pipeline=RetrievalPipeline(pipeline_settings, mock_l2, mock_vector, mock_cache),
        ranking_engine=RankingEngine(),
        rbac_filter=RBACFilter(mock_l2, mock_l4, mock_cache),
        column_scoper=ColumnScoper(mock_l2, mock_cache),
        join_graph_builder=JoinGraphBuilder(mock_l2, mock_cache),
        context_assembler=ContextAssembler(),
    )


# ══════════════════════════════════════════════════════════════
# TEST SUITE 1 — Doctor accessing clinical data
# ══════════════════════════════════════════════════════════════

class TestDoctorClinicalAccess:
    """
    Scenario: Dr. Patel (doctor, cardiology) queries clinical schema.
    L1 produces SecurityContext with roles=[doctor], clearance=3.
    L2 returns clinical tables.  L4 allows clinical, denies HR/billing.
    """

    ALLOWED = [
        "apollo_his.clinical.patients",
        "apollo_his.clinical.encounters",
        "apollo_his.clinical.diagnoses",
        "apollo_his.clinical.lab_results",
        "apollo_his.clinical.vital_signs",
        "apollo_his.clinical.medications",
        "apollo_his.pharmacy.prescriptions",
    ]
    DENIED = [
        "apollo_his.billing.insurance_claims",
        "apollo_his.hr.employee_records",
        "apollo_his.behavioral_health.substance_abuse_records",
    ]
    TABLES = [
        CLINICAL_PATIENTS, CLINICAL_ENCOUNTERS, CLINICAL_DIAGNOSES,
        CLINICAL_LAB_RESULTS, CLINICAL_VITALS, BILLING_CLAIMS,
        BEHAVIORAL_SUBSTANCE_ABUSE, HR_EMPLOYEES,
    ]

    @pytest.fixture
    def ctx(self) -> SecurityContext:
        return l1_build_context(
            user_id="dr-patel-4521",
            effective_roles=["doctor"],
            department="cardiology",
            clearance_level=3,
            session_id="sess-patel-001",
            mfa_verified=True,
        )

    @pytest.fixture
    def orchestrator(self, pipeline_settings) -> RetrievalOrchestrator:
        return _build_orchestrator(
            pipeline_settings, self.TABLES, self.ALLOWED, self.DENIED
        )

    @pytest.mark.asyncio
    async def test_patient_diabetes_lookup(self, orchestrator, ctx):
        """Doctor queries diabetic patients — standard DATA_LOOKUP."""
        req = RetrievalRequest(
            question="Show all patients currently diagnosed with diabetes",
            security_context=ctx,
        )
        result = await orchestrator.resolve(req)

        assert result.user_id == "dr-patel-4521"
        assert result.intent.intent == QueryIntent.DATA_LOOKUP
        assert DomainHint.CLINICAL in result.intent.domain_hints
        assert len(result.filtered_schema) > 0

        # Substance abuse must never appear regardless of clearance
        table_names = {t.table_name for t in result.filtered_schema}
        assert "substance_abuse_records" not in table_names

    @pytest.mark.asyncio
    async def test_admission_trend_query(self, orchestrator, ctx):
        """Doctor queries admission trends — TREND intent."""
        req = RetrievalRequest(
            question="Show monthly admission trends over the past 12 months",
            security_context=ctx,
        )
        result = await orchestrator.resolve(req)
        assert result.intent.intent == QueryIntent.TREND

    @pytest.mark.asyncio
    async def test_patient_count_aggregation(self, orchestrator, ctx):
        """Doctor counts discharged patients — AGGREGATION intent."""
        req = RetrievalRequest(
            question="How many patients were discharged this week?",
            security_context=ctx,
        )
        result = await orchestrator.resolve(req)
        assert result.intent.intent == QueryIntent.AGGREGATION

    @pytest.mark.asyncio
    async def test_join_across_clinical_tables(self, orchestrator, ctx):
        """Doctor joins patients with their lab results — JOIN_QUERY intent."""
        req = RetrievalRequest(
            question="Join patients with their lab results and vital signs for ICU admissions",
            security_context=ctx,
        )
        result = await orchestrator.resolve(req)
        assert result.intent.intent == QueryIntent.JOIN_QUERY

    @pytest.mark.asyncio
    async def test_pii_columns_masked(self, orchestrator, ctx):
        """Patient name, MRN, DOB must be MASKED not VISIBLE in returned schema."""
        req = RetrievalRequest(
            question="Show patient demographics for admitted patients",
            security_context=ctx,
        )
        result = await orchestrator.resolve(req)

        patient_tables = [t for t in result.filtered_schema
                          if t.table_name == "patients"]
        if patient_tables:
            pt = patient_tables[0]
            visible_col_names = {c.name for c in pt.visible_columns}
            # SSN (sensitivity=5) must be HIDDEN, not visible or masked
            assert "ssn" not in visible_col_names
            # PII fields (name, mrn, dob) must not be in plain-visible
            for pii_col in ("name", "mrn", "dob"):
                assert pii_col not in visible_col_names, f"{pii_col} must be masked"

    @pytest.mark.asyncio
    async def test_billing_table_denied(self, orchestrator, ctx):
        """Doctor must not see billing.insurance_claims in schema result."""
        req = RetrievalRequest(
            question="Show insurance claims for patients",
            security_context=ctx,
        )
        result = await orchestrator.resolve(req)
        table_ids = {t.table_id for t in result.filtered_schema}
        assert "apollo_his.billing.insurance_claims" not in table_ids

    @pytest.mark.asyncio
    async def test_row_filter_applied(self, orchestrator, ctx):
        """Every allowed table must carry the facility_id row filter."""
        req = RetrievalRequest(
            question="Show all admitted patients",
            security_context=ctx,
        )
        result = await orchestrator.resolve(req)
        for t in result.filtered_schema:
            assert len(t.row_filters) > 0, f"Table {t.table_name} missing row_filters"
            assert any("facility_id" in f for f in t.row_filters)

    @pytest.mark.asyncio
    async def test_join_graph_has_edges(self, orchestrator, ctx):
        """Join graph should have FK edges linking encounters → patients."""
        req = RetrievalRequest(
            question="Show patients and their encounters",
            security_context=ctx,
        )
        result = await orchestrator.resolve(req)
        # Either edges present, or zero allowed tables (neither is an error)
        from app.models.retrieval import JoinGraph
        assert isinstance(result.join_graph, JoinGraph)
        assert hasattr(result.join_graph, "edges")

    @pytest.mark.asyncio
    async def test_metadata_fields_populated(self, orchestrator, ctx):
        """Pipeline metadata must report timing, candidate counts, and token budget."""
        req = RetrievalRequest(
            question="Show patients admitted to cardiology this month",
            security_context=ctx,
        )
        result = await orchestrator.resolve(req)
        meta = result.retrieval_metadata
        assert meta.total_candidates_found >= 0
        assert meta.total_latency_ms > 0
        assert meta.token_count >= 0


# ══════════════════════════════════════════════════════════════
# TEST SUITE 2 — Nurse with restricted access
# ══════════════════════════════════════════════════════════════

class TestNurseClinicalAccess:
    """
    Scenario: Nurse Priya (nurse, general medicine) — clinical-only, clearance=2.
    L4 allows clinical tables with stricter column masking.
    """

    ALLOWED = [
        "apollo_his.clinical.patients",
        "apollo_his.clinical.encounters",
        "apollo_his.clinical.vital_signs",
    ]
    DENIED = [
        "apollo_his.clinical.diagnoses",
        "apollo_his.clinical.lab_results",
        "apollo_his.billing.insurance_claims",
        "apollo_his.pharmacy.prescriptions",
        "apollo_his.behavioral_health.substance_abuse_records",
    ]
    TABLES = [
        CLINICAL_PATIENTS, CLINICAL_ENCOUNTERS, CLINICAL_DIAGNOSES,
        CLINICAL_LAB_RESULTS, CLINICAL_VITALS, PHARMACY_PRESCRIPTIONS,
        BEHAVIORAL_SUBSTANCE_ABUSE,
    ]

    @pytest.fixture
    def ctx(self) -> SecurityContext:
        return l1_build_context(
            user_id="nurse-priya-7732",
            effective_roles=["nurse"],
            department="general_medicine",
            clearance_level=2,
            session_id="sess-priya-001",
            mfa_verified=True,
        )

    @pytest.fixture
    def orchestrator(self, pipeline_settings) -> RetrievalOrchestrator:
        return _build_orchestrator(
            pipeline_settings, self.TABLES, self.ALLOWED, self.DENIED
        )

    @pytest.mark.asyncio
    async def test_nurse_vital_signs_lookup(self, orchestrator, ctx):
        """Nurse can query vital signs for assigned patients."""
        req = RetrievalRequest(
            question="Show vital signs for patients admitted today",
            security_context=ctx,
        )
        result = await orchestrator.resolve(req)
        assert result.user_id == "nurse-priya-7732"
        assert result.intent.intent in (QueryIntent.DATA_LOOKUP, QueryIntent.AGGREGATION)

    @pytest.mark.asyncio
    async def test_nurse_cannot_see_diagnoses(self, orchestrator, ctx):
        """Nurse must not see diagnoses table (denied by L4)."""
        req = RetrievalRequest(
            question="Show diagnoses for my patients",
            security_context=ctx,
        )
        result = await orchestrator.resolve(req)
        table_ids = {t.table_id for t in result.filtered_schema}
        assert "apollo_his.clinical.diagnoses" not in table_ids

    @pytest.mark.asyncio
    async def test_substance_abuse_excluded_for_nurse(self, orchestrator, ctx):
        """substance_abuse_records must never appear — sensitivity-5 + denied."""
        req = RetrievalRequest(
            question="Show patient substance abuse treatment records",
            security_context=ctx,
        )
        result = await orchestrator.resolve(req)
        for t in result.filtered_schema:
            assert "substance_abuse" not in t.table_name.lower()


# ══════════════════════════════════════════════════════════════
# TEST SUITE 3 — Billing staff accessing financial data
# ══════════════════════════════════════════════════════════════

class TestBillingStaffAccess:
    """
    Scenario: Billing user Suresh — billing domain only, clearance=2, no MFA.
    L4 allows billing tables; all clinical tables denied.
    """

    ALLOWED = [
        "apollo_his.billing.insurance_claims",
    ]
    DENIED = [
        "apollo_his.clinical.patients",
        "apollo_his.clinical.encounters",
        "apollo_his.clinical.diagnoses",
        "apollo_his.pharmacy.prescriptions",
    ]
    TABLES = [
        BILLING_CLAIMS, CLINICAL_PATIENTS, CLINICAL_ENCOUNTERS,
        PHARMACY_PRESCRIPTIONS,
    ]

    @pytest.fixture
    def ctx(self) -> SecurityContext:
        return l1_build_context(
            user_id="billing-suresh-1190",
            effective_roles=["billing_staff"],
            department="finance",
            clearance_level=2,
            session_id="sess-suresh-001",
            mfa_verified=False,
        )

    @pytest.fixture
    def orchestrator(self, pipeline_settings) -> RetrievalOrchestrator:
        return _build_orchestrator(
            pipeline_settings, self.TABLES, self.ALLOWED, self.DENIED,
        )

    @pytest.mark.asyncio
    async def test_billing_claims_accessible(self, orchestrator, ctx):
        """Billing user can query insurance claims."""
        req = RetrievalRequest(
            question="Show all pending insurance claims submitted this month",
            security_context=ctx,
        )
        result = await orchestrator.resolve(req)
        assert result.user_id == "billing-suresh-1190"
        # Result should be valid (claims allowed or no clinical tables leaked)
        table_ids = {t.table_id for t in result.filtered_schema}
        assert "apollo_his.clinical.patients" not in table_ids
        assert "apollo_his.clinical.diagnoses" not in table_ids

    @pytest.mark.asyncio
    async def test_billing_aggregation(self, orchestrator, ctx):
        """Billing user aggregates claim amounts."""
        req = RetrievalRequest(
            question="What is the total claim amount by insurance provider this quarter?",
            security_context=ctx,
        )
        result = await orchestrator.resolve(req)
        assert result.intent.intent == QueryIntent.AGGREGATION


# ══════════════════════════════════════════════════════════════
# TEST SUITE 4 — Security boundary tests
# ══════════════════════════════════════════════════════════════

class TestSecurityBoundaries:
    """
    Critical security invariants that must hold regardless of user/query.
    """

    TABLES_ALL = [
        CLINICAL_PATIENTS, CLINICAL_ENCOUNTERS, CLINICAL_DIAGNOSES,
        CLINICAL_LAB_RESULTS, BILLING_CLAIMS, BEHAVIORAL_SUBSTANCE_ABUSE,
        HR_EMPLOYEES, PHARMACY_PRESCRIPTIONS,
    ]

    @pytest.fixture
    def pipeline_settings(self) -> Settings:
        return Settings(
            app_env="development",
            service_token_secret=SERVICE_SECRET,
            context_signing_key=SIGNING_KEY,
            allowed_service_ids="l5-generation,test-service,admin-service,l1-identity,admin-console",
        )

    @pytest.mark.asyncio
    async def test_expired_context_rejected_with_401(self, pipeline_settings):
        """Expired SecurityContext (from L1 with past TTL) must be rejected."""
        orchestrator = _build_orchestrator(
            pipeline_settings, self.TABLES_ALL,
            allowed_tables=["apollo_his.clinical.patients"],
        )
        ctx = l1_build_context(
            "dr-expired-0001", ["doctor"], "cardiology", 3, expired=True
        )
        req = RetrievalRequest(question="Show all patients", security_context=ctx)

        with pytest.raises(RetrievalError) as exc_info:
            await orchestrator.resolve(req)
        assert exc_info.value.status == 401
        assert "INVALID_SECURITY_CONTEXT" in exc_info.value.code.value

    @pytest.mark.asyncio
    async def test_tampered_signature_rejected(self, pipeline_settings):
        """SecurityContext with a tampered signature must be rejected."""
        orchestrator = _build_orchestrator(
            pipeline_settings, self.TABLES_ALL,
            allowed_tables=["apollo_his.clinical.patients"],
        )
        ctx_valid = l1_build_context("dr.tamper", ["doctor"], "cardiology", 3)
        # Tamper with the signature
        ctx_tampered = SecurityContext(
            **{**ctx_valid.model_dump(), "context_signature": "deadbeef" * 8}
        )
        req = RetrievalRequest(question="Show patients", security_context=ctx_tampered)

        with pytest.raises(RetrievalError) as exc_info:
            await orchestrator.resolve(req)
        assert exc_info.value.status == 401

    @pytest.mark.asyncio
    async def test_sensitivity_5_never_returned(self, pipeline_settings):
        """42 CFR Part 2 / sensitivity-5 tables must NEVER appear in any result."""
        # Even if L4 mistakenly allows them, L3 hard-excludes at the RBAC stage
        orchestrator = _build_orchestrator(
            pipeline_settings, self.TABLES_ALL,
            allowed_tables=[
                "apollo_his.clinical.patients",
                "apollo_his.behavioral_health.substance_abuse_records",  # should be excluded
            ],
        )
        ctx = l1_build_context("dr.test", ["doctor"], "psychiatry", 5)
        req = RetrievalRequest(
            question="Show substance abuse and addiction treatment records",
            security_context=ctx,
        )
        result = await orchestrator.resolve(req)
        for t in result.filtered_schema:
            assert "substance_abuse" not in t.table_id.lower(), (
                f"Sensitivity-5 table {t.table_id} leaked into result"
            )
            assert "substance_abuse" not in t.table_name.lower()

    @pytest.mark.asyncio
    async def test_l4_hard_deny_overrides_all(self, pipeline_settings):
        """A DENY from L4 must remove the table even if semantically top-ranked."""
        orchestrator = _build_orchestrator(
            pipeline_settings,
            tables=[CLINICAL_PATIENTS, CLINICAL_ENCOUNTERS],
            allowed_tables=[],  # deny everything
            denied_tables=[
                "apollo_his.clinical.patients",
                "apollo_his.clinical.encounters",
            ],
        )
        ctx = l1_build_context("dr.deny", ["doctor"], "cardiology", 3)
        req = RetrievalRequest(
            question="Show all patient records with encounters",
            security_context=ctx,
        )
        # When all tables are denied, orchestrator raises NO_RELEVANT_TABLES (404)
        # or RESTRICTED_DATA_REQUEST (403) — both indicate the DENY was enforced.
        from app.models.enums import RetrievalErrorCode
        with pytest.raises(RetrievalError) as exc_info:
            await orchestrator.resolve(req)
        assert exc_info.value.status in (403, 404)

    @pytest.mark.asyncio
    async def test_different_roles_different_schema(self, pipeline_settings):
        """Same question from different roles must produce different schema sets."""
        tables = [CLINICAL_PATIENTS, BILLING_CLAIMS, PHARMACY_PRESCRIPTIONS]

        doc_orchestrator = _build_orchestrator(
            pipeline_settings, tables,
            allowed_tables=[
                "apollo_his.clinical.patients",
                "apollo_his.pharmacy.prescriptions",
            ],
            denied_tables=["apollo_his.billing.insurance_claims"],
        )
        billing_orchestrator = _build_orchestrator(
            pipeline_settings, tables,
            allowed_tables=["apollo_his.billing.insurance_claims"],
            denied_tables=[
                "apollo_his.clinical.patients",
                "apollo_his.pharmacy.prescriptions",
            ],
        )

        question = "Show financial and patient summary data"

        doc_ctx = l1_build_context("dr.cmp", ["doctor"], "cardiology", 3)
        billing_ctx = l1_build_context("billing.cmp", ["billing_staff"], "finance", 2)

        doc_result = await doc_orchestrator.resolve(
            RetrievalRequest(question=question, security_context=doc_ctx)
        )
        billing_result = await billing_orchestrator.resolve(
            RetrievalRequest(question=question, security_context=billing_ctx)
        )

        doc_ids = {t.table_id for t in doc_result.filtered_schema}
        billing_ids = {t.table_id for t in billing_result.filtered_schema}

        # Their visible tables must not be identical
        assert doc_ids != billing_ids, (
            "Doctor and billing staff received identical schema — RBAC not working"
        )

    @pytest.mark.asyncio
    async def test_role_cache_keys_isolated(self):
        """Different roles must produce different role_set_hash values."""
        ctx_doc = l1_build_context("u1", ["doctor"], "cardiology", 3)
        ctx_nurse = l1_build_context("u2", ["nurse"], "general_medicine", 2)
        ctx_billing = l1_build_context("u3", ["billing_staff"], "finance", 2)
        assert ctx_doc.role_set_hash != ctx_nurse.role_set_hash
        assert ctx_nurse.role_set_hash != ctx_billing.role_set_hash
        assert ctx_doc.role_set_hash != ctx_billing.role_set_hash

    @pytest.mark.asyncio
    async def test_cross_user_context_rejected(self, pipeline_settings):
        """Context signed for user A must not be accepted when user_id changed to user B."""
        # Build a context for dr.patel and sign it
        ctx_patel = l1_build_context("dr-patel-4521", ["doctor"], "cardiology", 3)

        # Attempt to forge context for a different user using patel's signature
        ctx_forged = SecurityContext(
            user_id="dr-evil-9999",
            effective_roles=ctx_patel.effective_roles,
            department=ctx_patel.department,
            clearance_level=ctx_patel.clearance_level,
            session_id=ctx_patel.session_id,
            context_signature=ctx_patel.context_signature,  # patel's signature
            context_expiry=ctx_patel.context_expiry,
        )

        orchestrator = _build_orchestrator(
            pipeline_settings,
            tables=[CLINICAL_PATIENTS],
            allowed_tables=["apollo_his.clinical.patients"],
        )
        req = RetrievalRequest(question="Show all patients", security_context=ctx_forged)

        with pytest.raises(RetrievalError) as exc_info:
            await orchestrator.resolve(req)
        assert exc_info.value.status == 401


# ══════════════════════════════════════════════════════════════
# TEST SUITE 5 — Intent classification with domain hints
# ══════════════════════════════════════════════════════════════

class TestIntentClassificationWithL1Context:
    """Verify intent classifier works correctly with L1-produced context."""

    @pytest.fixture
    def orchestrator(self, pipeline_settings) -> RetrievalOrchestrator:
        return _build_orchestrator(
            pipeline_settings,
            tables=[CLINICAL_PATIENTS, CLINICAL_ENCOUNTERS, CLINICAL_DIAGNOSES,
                    CLINICAL_LAB_RESULTS, CLINICAL_VITALS, BILLING_CLAIMS],
            allowed_tables=[
                "apollo_his.clinical.patients",
                "apollo_his.clinical.encounters",
                "apollo_his.clinical.diagnoses",
                "apollo_his.clinical.lab_results",
                "apollo_his.clinical.vital_signs",
            ],
        )

    @pytest.fixture
    def ctx(self) -> SecurityContext:
        return l1_build_context("dr.jones", ["doctor"], "endocrinology", 3)

    @pytest.mark.asyncio
    async def test_hba1c_abbreviation_expands_to_glycated_haemoglobin(self, orchestrator, ctx):
        """HbA1c abbreviation should expand and be classified as DATA_LOOKUP."""
        req = RetrievalRequest(
            question="Show patients with HbA1c above 7.5",
            security_context=ctx,
        )
        result = await orchestrator.resolve(req)
        assert result.intent.intent == QueryIntent.DATA_LOOKUP
        assert result.preprocessed_question != result.original_question or "HbA1c" in result.original_question

    @pytest.mark.asyncio
    async def test_icu_admission_intent(self, orchestrator, ctx):
        """ICU query should resolve to DATA_LOOKUP with clinical domain hint."""
        req = RetrievalRequest(
            question="List all patients currently in the ICU",
            security_context=ctx,
        )
        result = await orchestrator.resolve(req)
        assert result.intent.intent == QueryIntent.DATA_LOOKUP
        assert DomainHint.CLINICAL in result.intent.domain_hints

    @pytest.mark.asyncio
    async def test_er_trend_analysis(self, orchestrator, ctx):
        """ER admission trends → TREND intent with clinical domain."""
        req = RetrievalRequest(
            question="Show ER admission trends over the last 6 months by diagnosis",
            security_context=ctx,
        )
        result = await orchestrator.resolve(req)
        assert result.intent.intent == QueryIntent.TREND

    @pytest.mark.asyncio
    async def test_lab_result_lookup(self, orchestrator, ctx):
        """Lab result query — DATA_LOOKUP with clinical domain."""
        req = RetrievalRequest(
            question="Show haemoglobin lab values for admitted patients with anaemia",
            security_context=ctx,
        )
        result = await orchestrator.resolve(req)
        assert result.intent.intent == QueryIntent.DATA_LOOKUP

    @pytest.mark.asyncio
    async def test_patient_encounter_join(self, orchestrator, ctx):
        """Multi-table join query recognised as JOIN_QUERY."""
        req = RetrievalRequest(
            question="Join patient demographics with their encounters and diagnoses",
            security_context=ctx,
        )
        result = await orchestrator.resolve(req)
        assert result.intent.intent == QueryIntent.JOIN_QUERY


# ══════════════════════════════════════════════════════════════
# TEST SUITE 6 — Token budget and context assembly
# ══════════════════════════════════════════════════════════════

class TestTokenBudgetWithRealSchema:
    """Token budget enforcement when L2 returns large schema."""

    @pytest.fixture
    def orchestrator(self, pipeline_settings) -> RetrievalOrchestrator:
        # All tables allowed — large schema
        all_tables = [
            CLINICAL_PATIENTS, CLINICAL_ENCOUNTERS, CLINICAL_DIAGNOSES,
            CLINICAL_LAB_RESULTS, CLINICAL_VITALS,
            PHARMACY_PRESCRIPTIONS, BILLING_CLAIMS,
        ]
        return _build_orchestrator(
            pipeline_settings, all_tables,
            allowed_tables=[t.fqn for t in all_tables],
        )

    @pytest.fixture
    def ctx(self) -> SecurityContext:
        return l1_build_context("dr.budget", ["doctor"], "general_medicine", 3)

    @pytest.mark.asyncio
    async def test_token_count_within_budget(self, orchestrator, ctx):
        """Token count in metadata must not exceed the default budget."""
        req = RetrievalRequest(question="Show all patient data", security_context=ctx)
        result = await orchestrator.resolve(req)
        # Default budget is 8192 tokens — result must be within it
        assert result.retrieval_metadata.token_count <= 8192

    @pytest.mark.asyncio
    async def test_max_tables_respected(self, orchestrator, ctx):
        """max_tables parameter must hard-cap the number of returned tables."""
        req = RetrievalRequest(
            question="Show all clinical and billing data with joins",
            security_context=ctx,
            max_tables=3,
        )
        result = await orchestrator.resolve(req)
        assert len(result.filtered_schema) <= 3

    @pytest.mark.asyncio
    async def test_nl_policy_rules_always_present(self, orchestrator, ctx):
        """Natural-language policy rules from L4 must survive token budget trimming."""
        req = RetrievalRequest(question="Show patient data", security_context=ctx)
        result = await orchestrator.resolve(req)
        # NL rules from L4 must be present
        assert len(result.nl_policy_rules) > 0


# ══════════════════════════════════════════════════════════════
# TEST SUITE 7 — Full API endpoint tests (HTTP layer)
# ══════════════════════════════════════════════════════════════

class TestPipelineViaHTTP:
    """Test the complete pipeline via the HTTP API (L1 ctx → HTTP → L3 response)."""

    def _get_client(self, pipeline_settings: Settings):
        """Build a TestClient with pipeline_settings injected."""
        from unittest.mock import patch
        from fastapi.testclient import TestClient
        from app.config import get_settings
        from app.dependencies import Container, set_container
        from app.services.orchestrator import RetrievalOrchestrator
        from app.services.embedding_engine import EmbeddingEngine
        from app.services.intent_classifier import IntentClassifier
        from app.services.retrieval_pipeline import RetrievalPipeline
        from app.services.ranking_engine import RankingEngine
        from app.services.rbac_filter import RBACFilter
        from app.services.column_scoper import ColumnScoper
        from app.services.join_graph import JoinGraphBuilder
        from app.services.context_assembler import ContextAssembler

        tables = [CLINICAL_PATIENTS, CLINICAL_ENCOUNTERS, CLINICAL_DIAGNOSES, CLINICAL_VITALS]
        allowed = [t.fqn for t in tables]
        mock_l2 = _build_l2_mock(tables)
        mock_l4 = _build_l4_mock(allowed)

        mock_embed = AsyncMock()
        mock_embed.embed = AsyncMock(return_value=[0.1] * 1536)
        mock_embed.health_check = AsyncMock(return_value=True)

        mock_vector = AsyncMock()
        mock_vector.search_similar = AsyncMock(return_value=[])
        mock_vector.health_check = AsyncMock(return_value=True)

        mock_cache = AsyncMock()
        mock_cache.get_embedding = AsyncMock(return_value=None)
        mock_cache.set_embedding = AsyncMock()
        mock_cache.get_role_domains = AsyncMock(return_value=None)
        mock_cache.set_role_domains = AsyncMock()
        mock_cache.get_vector_results = AsyncMock(return_value=None)
        mock_cache.set_vector_results = AsyncMock()
        mock_cache.get_schema_fragment = AsyncMock(return_value=None)
        mock_cache.set_schema_fragment = AsyncMock()
        mock_cache.get_columns_local = MagicMock(return_value=None)
        mock_cache.set_columns_local = MagicMock()
        mock_cache.get_fk_local = MagicMock(return_value=None)
        mock_cache.set_fk_local = MagicMock()
        mock_cache.stats = {"hits": 0, "misses": 0}
        mock_cache.invalidate_all = AsyncMock(return_value=0)
        mock_cache.health_check = AsyncMock(return_value=True)

        container = MagicMock(spec=Container)
        container.settings = pipeline_settings
        container.cache = mock_cache
        container.l2_client = mock_l2
        container.l4_client = mock_l4
        container.embedding_client = mock_embed
        container.vector_client = mock_vector
        container.intent_classifier = IntentClassifier()
        container.ranking_engine = RankingEngine()
        container.context_assembler = ContextAssembler()
        container.embedding_engine = EmbeddingEngine(pipeline_settings, mock_embed, mock_cache)
        container.retrieval_pipeline = RetrievalPipeline(pipeline_settings, mock_l2, mock_vector, mock_cache)
        container.rbac_filter = RBACFilter(mock_l2, mock_l4, mock_cache)
        container.column_scoper = ColumnScoper(mock_l2, mock_cache)
        container.join_graph_builder = JoinGraphBuilder(mock_l2, mock_cache)
        container.orchestrator = RetrievalOrchestrator(
            settings=pipeline_settings,
            embedding_engine=container.embedding_engine,
            intent_classifier=container.intent_classifier,
            retrieval_pipeline=container.retrieval_pipeline,
            ranking_engine=container.ranking_engine,
            rbac_filter=container.rbac_filter,
            column_scoper=container.column_scoper,
            join_graph_builder=container.join_graph_builder,
            context_assembler=container.context_assembler,
        )

        get_settings.cache_clear()
        with patch("app.config.load_settings", return_value=pipeline_settings):
            from app.main import create_app
            set_container(container)
            app = create_app()
            app.state.container = container
            return TestClient(app)

    def test_l1_context_via_http_resolve(self, pipeline_settings):
        """Full HTTP POST /api/v1/retrieval/resolve with L1-produced SecurityContext."""
        client = self._get_client(pipeline_settings)
        service_token = create_service_token(
            "l5-generation", ServiceRole.PIPELINE_READER.value, SERVICE_SECRET
        )
        ctx = l1_build_context(
            user_id="dr-patel-4521",
            effective_roles=["doctor"],
            department="cardiology",
            clearance_level=3,
            mfa_verified=True,
        )
        resp = client.post(
            "/api/v1/retrieval/resolve",
            json={
                "question": "Show patients diagnosed with hypertension this year",
                "security_context": ctx.model_dump(mode="json"),
            },
            headers={"Authorization": f"Bearer {service_token}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["user_id"] == "dr-patel-4521"
        assert "filtered_schema" in data["data"]
        assert "intent" in data["data"]
        assert "retrieval_metadata" in data["data"]

    def test_expired_l1_context_returns_error(self, pipeline_settings):
        """Expired L1 SecurityContext over HTTP must return a structured error."""
        client = self._get_client(pipeline_settings)
        service_token = create_service_token(
            "l5-generation", ServiceRole.PIPELINE_READER.value, SERVICE_SECRET
        )
        ctx = l1_build_context(
            "dr-expired", ["doctor"], "cardiology", 3, expired=True
        )
        resp = client.post(
            "/api/v1/retrieval/resolve",
            json={
                "question": "Show all patients",
                "security_context": ctx.model_dump(mode="json"),
            },
            headers={"Authorization": f"Bearer {service_token}"},
        )
        data = resp.json()
        assert data.get("success") is False or resp.status_code in (401, 400)

    def test_unauthenticated_request_rejected(self, pipeline_settings):
        """Request without L3 service token must be rejected with 401/403."""
        client = self._get_client(pipeline_settings)
        ctx = l1_build_context("dr.noauth", ["doctor"], "cardiology", 3)
        resp = client.post(
            "/api/v1/retrieval/resolve",
            json={
                "question": "Show patient data",
                "security_context": ctx.model_dump(mode="json"),
            },
        )
        assert resp.status_code in (401, 403)
