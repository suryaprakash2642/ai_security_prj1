"""API request and response models for L6 Multi-Gate Validation."""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    GateStatus, RewriteType, ValidationDecision, ViolationCode, ViolationSeverity
)


# ── Shared: Permission Envelope (mirrors L4/L5 models) ────────────────────

class ColumnDecision(BaseModel):
    model_config = ConfigDict(extra="ignore")
    column_name: str
    visibility: str = "VISIBLE"
    masking_expression: str | None = None
    reason: str = ""


class TablePermission(BaseModel):
    model_config = ConfigDict(extra="ignore")
    table_id: str
    decision: str = "DENY"
    columns: list[ColumnDecision] = Field(default_factory=list)
    row_filters: list[str] = Field(default_factory=list)
    aggregation_only: bool = False
    max_rows: int | None = None
    nl_rules: list[str] = Field(default_factory=list)
    reason: str = ""

    @property
    def allowed_column_names(self) -> set[str]:
        return {c.column_name for c in self.columns if c.visibility != "HIDDEN"}

    @property
    def denied_column_names(self) -> set[str]:
        return {c.column_name for c in self.columns if c.visibility == "HIDDEN"}

    @property
    def masked_columns(self) -> dict[str, str]:
        """column_name -> masking_expression"""
        return {
            c.column_name: c.masking_expression
            for c in self.columns
            if c.visibility == "MASKED" and c.masking_expression
        }


class JoinRestriction(BaseModel):
    model_config = ConfigDict(extra="ignore")
    source_domain: str
    target_domain: str
    policy_id: str = ""
    restriction_type: str = "DENY"


class PermissionEnvelope(BaseModel):
    model_config = ConfigDict(extra="ignore")
    request_id: str = ""
    table_permissions: list[TablePermission] = Field(default_factory=list)
    join_restrictions: list[JoinRestriction] = Field(default_factory=list)
    global_nl_rules: list[str] = Field(default_factory=list)
    resolved_at: str = ""
    policy_version: int = 0
    signature: str = ""

    def get_table_permission(self, table_id: str) -> TablePermission | None:
        for tp in self.table_permissions:
            if tp.table_id == table_id:
                return tp
        return None

    @property
    def allowed_table_ids(self) -> set[str]:
        return {
            tp.table_id for tp in self.table_permissions
            if tp.decision.upper() not in ("DENY",)
        }

    @property
    def restricted_domain_pairs(self) -> list[tuple[str, str]]:
        return [(jr.source_domain, jr.target_domain) for jr in self.join_restrictions]


# ── Validation Result Models ───────────────────────────────────────────────

class Violation(BaseModel):
    model_config = ConfigDict()
    gate: int
    code: ViolationCode
    severity: ViolationSeverity
    table: str | None = None
    column: str | None = None
    detail: str = ""
    policy: str = ""


class RewriteRecord(BaseModel):
    model_config = ConfigDict()
    rewrite_type: RewriteType
    column: str | None = None
    table: str | None = None
    strategy: str = ""
    original_fragment: str = ""
    rewritten_fragment: str = ""


class GateResult(BaseModel):
    model_config = ConfigDict()
    status: GateStatus = GateStatus.PASS
    violations: list[Violation] = Field(default_factory=list)
    latency_ms: float = 0.0


class ValidationRequest(BaseModel):
    """POST /api/v1/validate/sql"""
    model_config = ConfigDict(extra="forbid")
    request_id: str = ""
    raw_sql: str = Field(..., min_length=1)
    dialect: str = "postgresql"
    permission_envelope: PermissionEnvelope
    security_context: dict[str, Any] = Field(default_factory=dict)
    generation_metadata: dict[str, Any] = Field(default_factory=dict)


class ValidationResponse(BaseModel):
    """Response from POST /api/v1/validate/sql"""
    model_config = ConfigDict()
    request_id: str = ""
    decision: ValidationDecision
    validated_sql: str | None = None
    rewrites_applied: list[RewriteRecord] = Field(default_factory=list)
    gate_results: dict[str, GateResult] = Field(default_factory=dict)
    violations: list[Violation] = Field(default_factory=list)
    validation_latency_ms: float = 0.0


class HealthResponse(BaseModel):
    model_config = ConfigDict()
    status: str = "ok"
    service: str = "l6-multi-gate-validation"
    version: str = "1.0.0"
    dependencies: dict[str, bool] = Field(default_factory=dict)
