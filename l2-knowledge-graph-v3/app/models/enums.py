"""Enumerations used across the L2 Knowledge Graph layer."""

from __future__ import annotations

from enum import Enum, IntEnum


class PolicyType(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    MASK = "MASK"
    FILTER = "FILTER"


class ConditionType(str, Enum):
    ROW_FILTER = "ROW_FILTER"
    TIME_WINDOW = "TIME_WINDOW"
    AGGREGATION_ONLY = "AGGREGATION_ONLY"
    JOIN_RESTRICTION = "JOIN_RESTRICTION"
    COLUMN_MASK = "COLUMN_MASK"
    MAX_ROWS = "MAX_ROWS"


class MaskingStrategy(str, Enum):
    REDACT = "REDACT"
    HASH = "HASH"
    PARTIAL_MASK = "PARTIAL_MASK"
    GENERALIZE_YEAR = "GENERALIZE_YEAR"
    GENERALIZE_RANGE = "GENERALIZE_RANGE"
    TOKENIZE = "TOKENIZE"
    NULL_OUT = "NULL_OUT"


class SensitivityLevel(IntEnum):
    PUBLIC = 1
    INTERNAL = 2
    CONFIDENTIAL = 3
    RESTRICTED = 4
    TOP_SECRET = 5


class PIIType(str, Enum):
    FULL_NAME = "FULL_NAME"
    FIRST_NAME = "FIRST_NAME"
    LAST_NAME = "LAST_NAME"
    DATE_OF_BIRTH = "DATE_OF_BIRTH"
    SSN = "SSN"
    AADHAAR = "AADHAAR"
    PAN = "PAN"
    NATIONAL_ID = "NATIONAL_ID"
    MEDICAL_RECORD_NUMBER = "MEDICAL_RECORD_NUMBER"
    EMAIL = "EMAIL"
    PHONE = "PHONE"
    ADDRESS = "ADDRESS"
    INSURANCE_ID = "INSURANCE_ID"
    SALARY = "SALARY"
    BANK_ACCOUNT = "BANK_ACCOUNT"
    THERAPY_NOTE = "THERAPY_NOTE"


class RegulationCode(str, Enum):
    HIPAA = "HIPAA"
    CFR_42_PART_2 = "42_CFR_PART_2"
    HIPAA_PSYCHOTHERAPY = "HIPAA_PSYCHOTHERAPY"
    DEA_SCHEDULE_II_V = "DEA_SCHEDULE_II_V"
    STATE_MH_LAWS = "STATE_MH_LAWS"
    STATE_HIV_LAWS = "STATE_HIV_LAWS"
    DPDPA_2023 = "DPDPA_2023"
    LABOR_LAWS = "LABOR_LAWS"
    TELEHEALTH = "TELEHEALTH"
    GINA = "GINA"


class DatabaseEngine(str, Enum):
    SQLSERVER = "sqlserver"
    MYSQL = "mysql"
    ORACLE = "oracle"
    POSTGRESQL = "postgresql"
    MONGODB = "mongodb"


class ChangeAction(str, Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DEACTIVATE = "DEACTIVATE"
    REACTIVATE = "REACTIVATE"
    ADD_RELATIONSHIP = "ADD_RELATIONSHIP"
    REMOVE_RELATIONSHIP = "REMOVE_RELATIONSHIP"


class ChangeSource(str, Enum):
    SCHEMA_DISCOVERY = "schema_discovery"
    CLASSIFICATION_ENGINE = "classification_engine"
    POLICY_ADMIN = "policy_admin"
    MANUAL = "manual"
    SEED = "seed"
    ROLLBACK = "rollback"


class ReviewStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    OVERRIDDEN = "overridden"


class ServiceRole(str, Enum):
    """Service-level access roles for the L2 API."""
    PIPELINE_READER = "pipeline_reader"
    SCHEMA_WRITER = "schema_writer"
    POLICY_WRITER = "policy_writer"
    ADMIN = "admin"
