"""Enumerations for L7 Secure Execution Layer."""

from enum import Enum


class ExecutionStatus(str, Enum):
    SUCCESS = "SUCCESS"
    QUERY_TIMEOUT = "QUERY_TIMEOUT"
    ROW_LIMIT_EXCEEDED = "ROW_LIMIT_EXCEEDED"
    MEMORY_EXCEEDED = "MEMORY_EXCEEDED"
    DATABASE_ERROR = "DATABASE_ERROR"
    SANITIZATION_ERROR = "SANITIZATION_ERROR"
    EXECUTION_NOT_AUTHORIZED = "EXECUTION_NOT_AUTHORIZED"
    DATABASE_UNAVAILABLE = "DATABASE_UNAVAILABLE"
    INVALID_ENVELOPE = "INVALID_ENVELOPE"
    INVALID_REQUEST = "INVALID_REQUEST"


class DatabasePool(str, Enum):
    APOLLO_HIS_SQLSERVER = "apollo-his-sqlserver"
    APOLLO_HR_SQLSERVER = "apollo-hr-sqlserver"
    APOLLO_FIN_ORACLE = "apollo-fin-oracle"
    APOLLO_ANALYTICS_PG = "apollo-analytics-pg"
    APOLLO_AUDIT_PG = "apollo-audit-pg"
    MOCK = "mock"


class CircuitBreakerState(str, Enum):
    CLOSED = "CLOSED"       # Normal operation
    OPEN = "OPEN"           # Tripped — rejecting all requests
    HALF_OPEN = "HALF_OPEN" # Probing — sending one test request


class SQLDialect(str, Enum):
    POSTGRESQL = "postgresql"
    TSQL = "tsql"
    ORACLE = "oracle"


class PIIType(str, Enum):
    SSN = "SSN"
    AADHAAR = "AADHAAR"
    PHONE = "PHONE"
    EMAIL = "EMAIL"
    FULL_NAME = "FULL_NAME"
    DATE_OF_BIRTH = "DATE_OF_BIRTH"


class AuditFlag(str, Enum):
    NORMAL = "NORMAL"
    EMERGENCY = "EMERGENCY"     # BTG active
    TRUNCATED = "TRUNCATED"     # Result was truncated
    SANITIZED = "SANITIZED"     # PII was redacted at runtime
