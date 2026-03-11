"""Request and response models for the FastAPI endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    ConditionType,
    MaskingStrategy,
    PIIType,
    PolicyType,
    ReviewStatus,
    SensitivityLevel,
)


class _ResponseBase(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


# ── Generic envelope ─────────────────────────────────────────


class APIResponse(_ResponseBase):
    """Standard API response wrapper."""
    model_config = ConfigDict(frozen=False, extra="forbid")
    success: bool = True
    data: Any = None
    error: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


# ── Schema responses ─────────────────────────────────────────


class TableResponse(_ResponseBase):
    fqn: str
    name: str
    description: str
    sensitivity_level: int
    domain: str
    is_active: bool
    hard_deny: bool = False
    schema_name: str = ""
    database_name: str = ""
    row_count_approx: int = 0
    version: int = 1
    regulations: list[str] = Field(default_factory=list)


class ColumnResponse(_ResponseBase):
    fqn: str
    name: str
    data_type: str
    is_pk: bool
    is_nullable: bool
    is_pii: bool
    pii_type: str | None = None
    sensitivity_level: int
    masking_strategy: str | None = None
    description: str
    is_active: bool
    regulations: list[str] = Field(default_factory=list)


class ForeignKeyResponse(_ResponseBase):
    source_column_fqn: str
    source_column_name: str
    target_column_fqn: str
    target_column_name: str
    target_table_fqn: str
    constraint_name: str = ""


# ── Policy responses ─────────────────────────────────────────


class PolicyResponse(_ResponseBase):
    policy_id: str
    policy_type: PolicyType
    nl_description: str
    structured_rule: dict[str, Any]
    priority: int
    is_hard_deny: bool = False
    is_active: bool = True
    target_tables: list[str] = Field(default_factory=list)
    target_columns: list[str] = Field(default_factory=list)
    target_domains: list[str] = Field(default_factory=list)
    bound_roles: list[str] = Field(default_factory=list)
    conditions: list[ConditionResponse] = Field(default_factory=list)
    version: int = 1


class ConditionResponse(_ResponseBase):
    condition_id: str
    condition_type: ConditionType
    parameters: dict[str, Any] = Field(default_factory=dict)
    description: str = ""


class JoinRestrictionResponse(_ResponseBase):
    policy_id: str
    source_domain: str
    target_domain: str
    bound_roles: list[str] = Field(default_factory=list)


class PolicySimulateRequest(BaseModel):
    """Simulate policy evaluation for given role(s) and table(s)."""
    model_config = ConfigDict(extra="forbid")
    roles: list[str] = Field(..., min_length=1)
    table_fqns: list[str] = Field(..., min_length=1)
    operation: str = "SELECT"  # SELECT, JOIN, AGGREGATE


class PolicySimulateResult(_ResponseBase):
    table_fqn: str
    effective_policy: PolicyType
    is_hard_deny: bool = False
    applicable_policies: list[PolicyResponse] = Field(default_factory=list)
    masked_columns: list[str] = Field(default_factory=list)
    conditions: list[ConditionResponse] = Field(default_factory=list)
    deny_reason: str | None = None


# ── Classification responses ─────────────────────────────────


class PIIColumnResponse(_ResponseBase):
    column_fqn: str
    column_name: str
    table_fqn: str
    table_name: str
    pii_type: str
    sensitivity_level: int
    masking_strategy: str | None = None
    regulations: list[str] = Field(default_factory=list)


class MaskingRuleResponse(_ResponseBase):
    column_fqn: str
    column_name: str
    masking_strategy: MaskingStrategy
    pii_type: PIIType | None = None
    sensitivity_level: int
    policy_ids: list[str] = Field(default_factory=list)


class RegulatedTableResponse(_ResponseBase):
    table_fqn: str
    table_name: str
    regulation_code: str
    regulation_name: str
    sensitivity_level: int
    hard_deny: bool = False


# ── Admin responses ──────────────────────────────────────────


class CrawlRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    database_name: str
    engine: str
    connection_string: str  # encrypted/Vault-referenced
    schemas: list[str] = Field(default_factory=list)  # empty = all


class CrawlSummary(_ResponseBase):
    database_name: str
    status: str
    tables_found: int = 0
    tables_added: int = 0
    tables_updated: int = 0
    tables_deactivated: int = 0
    columns_found: int = 0
    columns_added: int = 0
    columns_updated: int = 0
    errors: list[str] = Field(default_factory=list)
    duration_seconds: float = 0.0


class ClassificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    table_fqns: list[str] = Field(default_factory=list)  # empty = all unclassified
    force_reclassify: bool = False


class ClassificationSummary(_ResponseBase):
    columns_analyzed: int = 0
    pii_detected: int = 0
    review_items_created: int = 0
    auto_approved: int = 0


class ReviewItem(_ResponseBase):
    model_config = ConfigDict(frozen=False, extra="forbid")
    id: int
    column_fqn: str
    suggested_sensitivity: int
    suggested_pii_type: str | None
    suggested_masking: str | None
    confidence: float
    reason: str
    status: ReviewStatus
    created_at: datetime


class HealthCheckResult(_ResponseBase):
    model_config = ConfigDict(frozen=False, extra="forbid")
    check_name: str
    passed: bool
    details: str = ""
    items: list[str] = Field(default_factory=list)


class GraphVersionInfo(_ResponseBase):
    graph_version: int
    updated_at: datetime
    updated_by: str
    node_counts: dict[str, int] = Field(default_factory=dict)
