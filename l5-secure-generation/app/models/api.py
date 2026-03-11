"""API request and response models for L5 Secure Generation Layer."""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import GenerationStatus, SQLDialect


# ── Permission Envelope (received from L4 via caller) ──────────────────────

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
    def allowed_column_names(self) -> list[str]:
        return [c.column_name for c in self.columns if c.visibility != "HIDDEN"]

    @property
    def masked_columns(self) -> list[ColumnDecision]:
        return [c for c in self.columns if c.visibility == "MASKED" and c.masking_expression]


class JoinRestriction(BaseModel):
    model_config = ConfigDict(extra="ignore")
    source_domain: str
    target_domain: str
    policy_id: str = ""
    restriction_type: str = "DENY"


class PermissionEnvelope(BaseModel):
    """Signed permission envelope from L4."""
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
    def all_nl_rules(self) -> list[str]:
        """Collect global + per-table NL rules."""
        rules = list(self.global_nl_rules)
        for tp in self.table_permissions:
            rules.extend(tp.nl_rules)
        return rules


# ── Schema Fragment (received from L3) ────────────────────────────────────

class SchemaColumn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    data_type: str = "VARCHAR"
    nl_description: str = ""
    is_masked: bool = False
    sql_rewrite: str | None = None
    sensitivity_level: int = 1


class JoinEdge(BaseModel):
    model_config = ConfigDict(extra="ignore")
    from_table: str
    from_column: str
    to_table: str
    to_column: str


class FilteredTable(BaseModel):
    model_config = ConfigDict(extra="ignore")
    table_id: str
    table_name: str = ""
    domain: str = ""
    nl_description: str = ""
    relevance_score: float = 0.5
    columns: list[SchemaColumn] = Field(default_factory=list)
    foreign_keys: list[JoinEdge] = Field(default_factory=list)
    row_filters: list[str] = Field(default_factory=list)
    aggregation_only: bool = False

    @property
    def name(self) -> str:
        return self.table_name or self.table_id


class FilteredSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    tables: list[FilteredTable] = Field(default_factory=list)
    join_graph: list[JoinEdge] = Field(default_factory=list)


# ── Request / Response ─────────────────────────────────────────────────────

class GenerationRequest(BaseModel):
    """POST /api/v1/generate/sql"""
    model_config = ConfigDict(extra="forbid")

    request_id: str = ""
    user_question: str = Field(..., min_length=3, max_length=2000)
    permission_envelope: PermissionEnvelope
    filtered_schema: FilteredSchema
    dialect: SQLDialect = SQLDialect.POSTGRESQL
    security_context: dict[str, Any] = Field(default_factory=dict)


class GenerationMetadata(BaseModel):
    model_config = ConfigDict()
    model: str = ""
    attempt: int = 1
    prompt_tokens: int = 0
    completion_tokens: int = 0
    generation_latency_ms: float = 0.0
    temperature: float = 0.0
    schema_tables_included: int = 0
    schema_tables_truncated: int = 0
    policy_rules_count: int = 0
    injection_risk_score: float = 0.0
    dialect: str = ""


class GenerationResponse(BaseModel):
    """Response from POST /api/v1/generate/sql"""
    model_config = ConfigDict()

    request_id: str = ""
    status: GenerationStatus
    sql: str | None = None
    dialect: str = ""
    cannot_answer_reason: str | None = None
    generation_metadata: GenerationMetadata = Field(default_factory=GenerationMetadata)
    permission_envelope: PermissionEnvelope | None = None


class HealthResponse(BaseModel):
    model_config = ConfigDict()
    status: str = "ok"
    service: str = "l5-secure-generation"
    version: str = "1.0.0"
    llm_provider: str = ""
