"""Pydantic models representing Neo4j graph nodes and relationships."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    ConditionType,
    DatabaseEngine,
    MaskingStrategy,
    PIIType,
    PolicyType,
    SensitivityLevel,
)


class _FrozenBase(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


# ── Node models ──────────────────────────────────────────────


class DatabaseNode(_FrozenBase):
    name: str
    engine: DatabaseEngine
    host: str = ""
    port: int = 0
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    version: int = 1


class SchemaNode(_FrozenBase):
    fqn: str  # e.g. "apollo_emr.clinical"
    name: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    version: int = 1


class TableNode(_FrozenBase):
    fqn: str  # e.g. "apollo_emr.clinical.patients"
    name: str
    description: str = ""
    sensitivity_level: SensitivityLevel = SensitivityLevel.INTERNAL
    is_active: bool = True
    hard_deny: bool = False
    domain: str = ""
    row_count_approx: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    version: int = 1


class ColumnNode(_FrozenBase):
    fqn: str  # e.g. "apollo_emr.clinical.patients.mrn"
    name: str
    data_type: str = ""
    is_pk: bool = False
    is_nullable: bool = True
    is_pii: bool = False
    pii_type: PIIType | None = None
    sensitivity_level: SensitivityLevel = SensitivityLevel.PUBLIC
    masking_strategy: MaskingStrategy | None = None
    description: str = ""
    is_active: bool = True
    version: int = 1


class DomainNode(_FrozenBase):
    name: str
    description: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    version: int = 1


class RoleNode(_FrozenBase):
    name: str
    description: str = ""
    is_active: bool = True
    version: int = 1


class PolicyNode(_FrozenBase):
    policy_id: str
    policy_type: PolicyType
    nl_description: str = Field(..., min_length=10)
    structured_rule: str = Field(..., min_length=5)  # JSON string
    priority: int = 100
    is_active: bool = True
    is_hard_deny: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    version: int = 1


class ConditionNode(_FrozenBase):
    condition_id: str
    condition_type: ConditionType
    parameters: str = "{}"  # JSON string
    description: str = ""


class RegulationNode(_FrozenBase):
    code: str
    full_name: str = ""
    description: str = ""
    jurisdiction: str = ""
    version: int = 1


# ── Relationship models ─────────────────────────────────────


class ForeignKeyRelation(_FrozenBase):
    source_column_fqn: str
    target_column_fqn: str
    constraint_name: str = ""


class PolicyBinding(_FrozenBase):
    """Represents a fully resolved policy with its bindings."""
    policy_id: str
    policy_type: PolicyType
    nl_description: str
    structured_rule: str
    priority: int
    is_hard_deny: bool = False
    target_tables: list[str] = Field(default_factory=list)
    target_columns: list[str] = Field(default_factory=list)
    target_domains: list[str] = Field(default_factory=list)
    bound_roles: list[str] = Field(default_factory=list)
    conditions: list[dict[str, Any]] = Field(default_factory=list)


class JoinRestriction(_FrozenBase):
    policy_id: str
    source_domain: str
    target_domain: str
    bound_roles: list[str] = Field(default_factory=list)


class MaskingRule(_FrozenBase):
    column_fqn: str
    column_name: str
    masking_strategy: MaskingStrategy
    pii_type: PIIType | None = None
    sensitivity_level: SensitivityLevel
    policy_ids: list[str] = Field(default_factory=list)
