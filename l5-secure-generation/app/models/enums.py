"""Enumerations for L5 Secure Generation Layer."""

from enum import Enum


class GenerationStatus(str, Enum):
    GENERATED = "GENERATED"
    CANNOT_ANSWER = "CANNOT_ANSWER"
    GENERATION_FAILED = "GENERATION_FAILED"
    INJECTION_DETECTED = "INJECTION_DETECTED"
    INVALID_ENVELOPE = "INVALID_ENVELOPE"


class SQLDialect(str, Enum):
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    TSQL = "tsql"
    ORACLE = "oracle"


class LLMProvider(str, Enum):
    ANTHROPIC = "anthropic"
    AZURE_OPENAI = "azure_openai"
    OPENAI = "openai"


class InjectionRisk(str, Enum):
    CLEAN = "clean"       # < 0.3
    SUSPICIOUS = "suspicious"  # 0.3–0.7
    INJECTION = "injection"    # > 0.7


class TableDecision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    FILTER = "FILTER"
    MASK = "MASK"
