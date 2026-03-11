"""Apollo Hospitals seed data loader.

Provides a programmatic alternative to the Cypher seed files.
Can be used in tests or to load data via the Python API layer.

Usage:
    python -m seed_data.apollo_hospitals
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import structlog

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.config import get_settings
from app.dependencies import Container
from app.models.enums import (
    ConditionType,
    DatabaseEngine,
    MaskingStrategy,
    PIIType,
    PolicyType,
    SensitivityLevel,
)
from app.models.graph import (
    ColumnNode,
    DatabaseNode,
    DomainNode,
    PolicyNode,
    RegulationNode,
    RoleNode,
    SchemaNode,
    TableNode,
)

logger = structlog.get_logger("seed_data")


# ── Domain definitions ──────────────────────────────────────

DOMAINS = [
    DomainNode(name="clinical", description="Clinical and patient-facing medical records"),
    DomainNode(name="billing", description="Financial, claims, and insurance data"),
    DomainNode(name="pharmacy", description="Medication and prescription data"),
    DomainNode(name="hr", description="Human resources and employee data"),
    DomainNode(name="admin", description="Administrative and operational data"),
    DomainNode(name="behavioral_health", description="Mental health and substance abuse records"),
]

# ── Regulation definitions ──────────────────────────────────

REGULATIONS = [
    RegulationNode(code="HIPAA", description="US federal law protecting patient health information"),
    RegulationNode(code="42_CFR_PART_2", description="Federal regulation protecting substance use disorder records with stricter consent requirements"),
    RegulationNode(code="HIPAA_PSYCHOTHERAPY", description="Special protection for psychotherapy notes under HIPAA Privacy Rule"),
    RegulationNode(code="DPDPA_2023", description="India's data protection law governing processing of digital personal data"),
    RegulationNode(code="STATE_MH_LAWS", description="State-level regulations providing additional mental health data protections"),
    RegulationNode(code="GINA", description="US federal law prohibiting discrimination based on genetic information"),
]

# ── Role hierarchy ──────────────────────────────────────────

ROLES = [
    RoleNode(name="hospital_admin", description="Hospital administrator with broad access"),
    RoleNode(name="doctor", description="Attending physician"),
    RoleNode(name="nurse", description="Registered nurse"),
    RoleNode(name="billing_staff", description="Billing department staff"),
    RoleNode(name="researcher", description="Medical researcher with anonymized access"),
    RoleNode(name="pharmacist", description="Pharmacy staff with prescription access"),
]

ROLE_INHERITANCE = [
    ("hospital_admin", "doctor"),   # admin inherits doctor permissions
    ("doctor", "nurse"),            # doctor inherits nurse permissions
]

ROLE_DOMAIN_ACCESS = [
    ("hospital_admin", "clinical"),
    ("hospital_admin", "billing"),
    ("hospital_admin", "pharmacy"),
    ("hospital_admin", "admin"),
    ("doctor", "clinical"),
    ("doctor", "pharmacy"),
    ("nurse", "clinical"),
    ("billing_staff", "billing"),
    ("researcher", "clinical"),
    ("pharmacist", "pharmacy"),
]

# ── Database and schemas ────────────────────────────────────

DATABASE = DatabaseNode(
    name="apollo_his",
    engine=DatabaseEngine.SQLSERVER,
    host="apollo-db-primary.internal",
    port=1433,
)

SCHEMAS = [
    SchemaNode(database="apollo_his", name="clinical"),
    SchemaNode(database="apollo_his", name="billing"),
    SchemaNode(database="apollo_his", name="pharmacy"),
    SchemaNode(database="apollo_his", name="behavioral_health"),
]

# ── Tables ──────────────────────────────────────────────────

TABLES = [
    TableNode(fqn="apollo_his.clinical.patients", name="patients",
              schema_database="apollo_his",
              description="Core patient demographics and identifiers",
              sensitivity_level=SensitivityLevel.HIGHLY_SENSITIVE,
              domain="clinical"),
    TableNode(fqn="apollo_his.clinical.encounters", name="encounters",
              schema_database="apollo_his",
              description="Patient visit and encounter records",
              sensitivity_level=SensitivityLevel.CONFIDENTIAL,
              domain="clinical"),
    TableNode(fqn="apollo_his.clinical.diagnoses", name="diagnoses",
              schema_database="apollo_his",
              description="ICD-10 diagnosis codes linked to encounters",
              sensitivity_level=SensitivityLevel.CONFIDENTIAL,
              domain="clinical"),
    TableNode(fqn="apollo_his.billing.claims", name="claims",
              schema_database="apollo_his",
              description="Insurance claims and payment records",
              sensitivity_level=SensitivityLevel.CONFIDENTIAL,
              domain="billing"),
    TableNode(fqn="apollo_his.pharmacy.prescriptions", name="prescriptions",
              schema_database="apollo_his",
              description="Medication prescriptions and dispensing records",
              sensitivity_level=SensitivityLevel.CONFIDENTIAL,
              domain="pharmacy"),
    TableNode(fqn="apollo_his.behavioral_health.substance_abuse_records",
              name="substance_abuse_records",
              schema_database="apollo_his",
              description="Substance use disorder treatment records — HARD DENY",
              sensitivity_level=SensitivityLevel.CRITICAL,
              domain="behavioral_health",
              hard_deny=True),
    TableNode(fqn="apollo_his.behavioral_health.therapy_notes",
              name="therapy_notes",
              schema_database="apollo_his",
              description="Psychotherapy session notes — special HIPAA protection",
              sensitivity_level=SensitivityLevel.CRITICAL,
              domain="behavioral_health"),
]

# ── Column definitions (key columns per table) ──────────────

COLUMNS = [
    # patients
    ColumnNode(fqn="apollo_his.clinical.patients.mrn", table_fqn="apollo_his.clinical.patients",
               data_type="varchar(20)", is_pk=True, is_pii=True, pii_type=PIIType.MEDICAL_RECORD_NUMBER,
               sensitivity_level=SensitivityLevel.CRITICAL, masking_strategy=MaskingStrategy.HASH,
               description="Medical record number — primary patient identifier"),
    ColumnNode(fqn="apollo_his.clinical.patients.full_name", table_fqn="apollo_his.clinical.patients",
               data_type="varchar(200)", is_pii=True, pii_type=PIIType.FULL_NAME,
               sensitivity_level=SensitivityLevel.HIGHLY_SENSITIVE, masking_strategy=MaskingStrategy.REDACT,
               description="Patient full name"),
    ColumnNode(fqn="apollo_his.clinical.patients.date_of_birth", table_fqn="apollo_his.clinical.patients",
               data_type="date", is_pii=True, pii_type=PIIType.DATE_OF_BIRTH,
               sensitivity_level=SensitivityLevel.HIGHLY_SENSITIVE, masking_strategy=MaskingStrategy.GENERALIZE,
               description="Patient date of birth"),
    ColumnNode(fqn="apollo_his.clinical.patients.aadhaar_number", table_fqn="apollo_his.clinical.patients",
               data_type="varchar(12)", is_pii=True, pii_type=PIIType.AADHAAR,
               sensitivity_level=SensitivityLevel.CRITICAL, masking_strategy=MaskingStrategy.REDACT,
               description="Aadhaar unique identity number"),
    ColumnNode(fqn="apollo_his.clinical.patients.email", table_fqn="apollo_his.clinical.patients",
               data_type="varchar(255)", is_pii=True, pii_type=PIIType.EMAIL,
               sensitivity_level=SensitivityLevel.CONFIDENTIAL, masking_strategy=MaskingStrategy.PARTIAL_MASK,
               description="Patient email address"),
    ColumnNode(fqn="apollo_his.clinical.patients.phone", table_fqn="apollo_his.clinical.patients",
               data_type="varchar(15)", is_pii=True, pii_type=PIIType.PHONE,
               sensitivity_level=SensitivityLevel.CONFIDENTIAL, masking_strategy=MaskingStrategy.PARTIAL_MASK,
               description="Patient phone number"),

    # encounters
    ColumnNode(fqn="apollo_his.clinical.encounters.encounter_id", name="encounter_id",
               table_fqn="apollo_his.clinical.encounters", data_type="bigint", is_pk=True,
               description="Unique encounter identifier"),
    ColumnNode(fqn="apollo_his.clinical.encounters.patient_mrn", name="patient_mrn",
               table_fqn="apollo_his.clinical.encounters", data_type="varchar(20)", is_fk=True,
               description="Foreign key to patients.mrn"),
    ColumnNode(fqn="apollo_his.clinical.encounters.admit_date", name="admit_date",
               table_fqn="apollo_his.clinical.encounters", data_type="datetime",
               description="Admission date and time"),

    # diagnoses
    ColumnNode(fqn="apollo_his.clinical.diagnoses.diagnosis_id", name="diagnosis_id",
               table_fqn="apollo_his.clinical.diagnoses", data_type="bigint", is_pk=True,
               description="Unique diagnosis record identifier"),
    ColumnNode(fqn="apollo_his.clinical.diagnoses.encounter_id", name="encounter_id",
               table_fqn="apollo_his.clinical.diagnoses", data_type="bigint", is_fk=True,
               description="Foreign key to encounters"),
    ColumnNode(fqn="apollo_his.clinical.diagnoses.icd10_code", name="icd10_code",
               table_fqn="apollo_his.clinical.diagnoses", data_type="varchar(10)",
               sensitivity_level=SensitivityLevel.CONFIDENTIAL,
               description="ICD-10 diagnosis code"),

    # claims
    ColumnNode(fqn="apollo_his.billing.claims.claim_id", name="claim_id",
               table_fqn="apollo_his.billing.claims", data_type="bigint", is_pk=True,
               description="Unique claim identifier"),
    ColumnNode(fqn="apollo_his.billing.claims.patient_mrn", name="patient_mrn",
               table_fqn="apollo_his.billing.claims", data_type="varchar(20)", is_fk=True,
               description="Foreign key to patients.mrn"),
    ColumnNode(fqn="apollo_his.billing.claims.insurance_id", name="insurance_id",
               table_fqn="apollo_his.billing.claims", data_type="varchar(30)", is_pii=True,
               pii_type=PIIType.INSURANCE_ID, sensitivity_level=SensitivityLevel.HIGHLY_SENSITIVE,
               masking_strategy=MaskingStrategy.HASH,
               description="Insurance policy identifier"),

    # prescriptions
    ColumnNode(fqn="apollo_his.pharmacy.prescriptions.rx_id", name="rx_id",
               table_fqn="apollo_his.pharmacy.prescriptions", data_type="bigint", is_pk=True,
               description="Prescription identifier"),
    ColumnNode(fqn="apollo_his.pharmacy.prescriptions.patient_mrn", name="patient_mrn",
               table_fqn="apollo_his.pharmacy.prescriptions", data_type="varchar(20)", is_fk=True,
               description="Foreign key to patients.mrn"),
    ColumnNode(fqn="apollo_his.pharmacy.prescriptions.medication_name", name="medication_name",
               table_fqn="apollo_his.pharmacy.prescriptions", data_type="varchar(200)",
               description="Name of prescribed medication"),

    # substance_abuse_records (HARD DENY)
    ColumnNode(fqn="apollo_his.behavioral_health.substance_abuse_records.record_id",
               table_fqn="apollo_his.behavioral_health.substance_abuse_records",
               data_type="bigint", is_pk=True,
               sensitivity_level=SensitivityLevel.CRITICAL,
               description="Record identifier — table is HARD DENY protected"),

    # therapy_notes
    ColumnNode(fqn="apollo_his.behavioral_health.therapy_notes.note_id",
               table_fqn="apollo_his.behavioral_health.therapy_notes",
               data_type="bigint", is_pk=True,
               description="Therapy note identifier"),
    ColumnNode(fqn="apollo_his.behavioral_health.therapy_notes.note_text",
               table_fqn="apollo_his.behavioral_health.therapy_notes",
               data_type="text", is_pii=True, pii_type=PIIType.THERAPY_NOTE,
               sensitivity_level=SensitivityLevel.CRITICAL, masking_strategy=MaskingStrategy.REDACT,
               description="Free-text psychotherapy session notes"),
]

# ── Foreign key relationships ───────────────────────────────

FOREIGN_KEYS = [
    ("apollo_his.clinical.encounters.patient_mrn", "apollo_his.clinical.patients.mrn"),
    ("apollo_his.clinical.diagnoses.encounter_id", "apollo_his.clinical.encounters.encounter_id"),
    ("apollo_his.billing.claims.patient_mrn", "apollo_his.clinical.patients.mrn"),
    ("apollo_his.pharmacy.prescriptions.patient_mrn", "apollo_his.clinical.patients.mrn"),
]

# ── Policy definitions ──────────────────────────────────────

POLICIES = [
    {
        "policy_id": "POL-001",
        "policy_type": PolicyType.ALLOW,
        "nl_description": "Doctors may access patient demographic and clinical records for treatment purposes.",
        "structured_rule": {"effect": "ALLOW", "resources": ["patients", "encounters", "diagnoses"]},
        "priority": 100,
        "role_bindings": ["doctor"],
        "domain_bindings": ["clinical"],
    },
    {
        "policy_id": "POL-002",
        "policy_type": PolicyType.MASK,
        "nl_description": "Nurses may view patient records but PII fields (name, DOB, Aadhaar) must be masked.",
        "structured_rule": {"effect": "MASK", "columns": ["full_name", "date_of_birth", "aadhaar_number"]},
        "priority": 90,
        "role_bindings": ["nurse"],
        "domain_bindings": ["clinical"],
    },
    {
        "policy_id": "POL-003",
        "policy_type": PolicyType.FILTER,
        "nl_description": "Researchers may only access aggregated clinical data with minimum group size of 10.",
        "structured_rule": {"effect": "FILTER", "condition": "AGGREGATION_ONLY", "min_group_size": 10},
        "priority": 80,
        "role_bindings": ["researcher"],
        "domain_bindings": ["clinical"],
    },
    {
        "policy_id": "POL-004",
        "policy_type": PolicyType.DENY,
        "nl_description": "HARD DENY: substance_abuse_records table is protected under 42 CFR Part 2. No NL-to-SQL access.",
        "structured_rule": {"effect": "DENY", "hard_deny": True, "regulation": "42_CFR_PART_2"},
        "priority": 1000,
        "is_hard_deny": True,
        "table_bindings": ["apollo_his.behavioral_health.substance_abuse_records"],
    },
    {
        "policy_id": "POL-005",
        "policy_type": PolicyType.ALLOW,
        "nl_description": "Billing staff may access claims and billing domain data for payment processing.",
        "structured_rule": {"effect": "ALLOW", "resources": ["claims"]},
        "priority": 100,
        "role_bindings": ["billing_staff"],
        "domain_bindings": ["billing"],
    },
    {
        "policy_id": "POL-006",
        "policy_type": PolicyType.DENY,
        "nl_description": "Billing staff are denied from joining billing tables with clinical tables to prevent data correlation.",
        "structured_rule": {"effect": "DENY", "condition": "JOIN_RESTRICTION",
                          "restricted_domains": ["billing", "clinical"]},
        "priority": 150,
        "role_bindings": ["billing_staff"],
    },
    {
        "policy_id": "POL-007",
        "policy_type": PolicyType.FILTER,
        "nl_description": "Nurses may only access data during their 12-hour shift window.",
        "structured_rule": {"effect": "FILTER", "condition": "TIME_WINDOW", "window_hours": 12},
        "priority": 85,
        "role_bindings": ["nurse"],
    },
    {
        "policy_id": "POL-008",
        "policy_type": PolicyType.FILTER,
        "nl_description": "Researchers are limited to maximum 1000 rows per query result.",
        "structured_rule": {"effect": "FILTER", "condition": "MAX_ROWS", "max_rows": 1000},
        "priority": 75,
        "role_bindings": ["researcher"],
    },
    {
        "policy_id": "POL-009",
        "policy_type": PolicyType.DENY,
        "nl_description": "Therapy notes are denied to all roles except the treating psychiatrist via explicit override.",
        "structured_rule": {"effect": "DENY", "exception": "treating_psychiatrist_only"},
        "priority": 200,
        "table_bindings": ["apollo_his.behavioral_health.therapy_notes"],
    },
]

# ── Table regulation bindings ───────────────────────────────

TABLE_REGULATIONS = [
    ("apollo_his.clinical.patients", "HIPAA"),
    ("apollo_his.clinical.encounters", "HIPAA"),
    ("apollo_his.clinical.diagnoses", "HIPAA"),
    ("apollo_his.billing.claims", "HIPAA"),
    ("apollo_his.pharmacy.prescriptions", "HIPAA"),
    ("apollo_his.behavioral_health.substance_abuse_records", "42_CFR_PART_2"),
    ("apollo_his.behavioral_health.substance_abuse_records", "HIPAA"),
    ("apollo_his.behavioral_health.therapy_notes", "HIPAA_PSYCHOTHERAPY"),
    ("apollo_his.behavioral_health.therapy_notes", "HIPAA"),
    ("apollo_his.clinical.patients", "DPDPA_2023"),
]


async def load_seed_data() -> dict[str, int]:
    """Load all seed data via the write repository. Returns counts."""
    settings = get_settings()
    container = Container(settings)
    await container.startup()

    writer = container.graph_writer
    stats: dict[str, int] = {}

    try:
        # Domains
        for d in DOMAINS:
            await writer.upsert_domain(d)
        stats["domains"] = len(DOMAINS)

        # Regulations
        for r in REGULATIONS:
            await writer.upsert_regulation(r)
        stats["regulations"] = len(REGULATIONS)

        # Roles
        for r in ROLES:
            await writer.upsert_role(r)
        for parent, child in ROLE_INHERITANCE:
            await writer.add_role_inheritance(parent, child)
        for role, domain in ROLE_DOMAIN_ACCESS:
            await writer.add_role_domain_access(role, domain)
        stats["roles"] = len(ROLES)

        # Database
        await writer.upsert_database(DATABASE)
        stats["databases"] = 1

        # Schemas
        for s in SCHEMAS:
            await writer.upsert_schema(s)
        stats["schemas"] = len(SCHEMAS)

        # Tables
        for t in TABLES:
            await writer.upsert_table(t)
        stats["tables"] = len(TABLES)

        # Columns
        for c in COLUMNS:
            await writer.upsert_column(c)
        stats["columns"] = len(COLUMNS)

        # Foreign keys
        for src, tgt in FOREIGN_KEYS:
            await writer.add_foreign_key(src, tgt)
        stats["foreign_keys"] = len(FOREIGN_KEYS)

        # Policies
        for p in POLICIES:
            node = PolicyNode(
                policy_id=p["policy_id"],
                policy_type=p["policy_type"],
                nl_description=p["nl_description"],
                structured_rule=str(p["structured_rule"]),
                priority=p.get("priority", 100),
                is_hard_deny=p.get("is_hard_deny", False),
            )
            await writer.upsert_policy(node)
            for role in p.get("role_bindings", []):
                await writer.bind_policy_to_role(p["policy_id"], role)
            for table in p.get("table_bindings", []):
                await writer.bind_policy_to_table(p["policy_id"], table)
            for domain in p.get("domain_bindings", []):
                await writer.bind_policy_to_domain(p["policy_id"], domain)
        stats["policies"] = len(POLICIES)

        # Table regulations
        for table_fqn, reg_code in TABLE_REGULATIONS:
            await writer.add_regulation_to_table(table_fqn, reg_code)
        stats["table_regulations"] = len(TABLE_REGULATIONS)

        logger.info("seed_data_loaded", **stats)
        return stats

    finally:
        await container.shutdown()


if __name__ == "__main__":
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ]
    )
    asyncio.run(load_seed_data())
