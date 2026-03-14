"""Pydantic models for L7 Secure Execution Layer API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AuditFlag, ExecutionStatus, PIIType


# ── Permission Envelope (mirror of L6 model) ──────────────────────────────

class ColumnDecision(BaseModel):
    model_config = ConfigDict(extra="allow")
    column_name: str
    visibility: str = "VISIBLE"
    masking_expression: str | None = None


class TablePermission(BaseModel):
    model_config = ConfigDict(extra="allow")
    table_id: str
    decision: str = "ALLOW"
    columns: list[ColumnDecision] = []
    row_filters: list[str] = []
    nl_rules: list[str] = []
    max_rows: int | None = None
    aggregation_only: bool = False
    denied_in_select: list[str] = []


class JoinRestriction(BaseModel):
    model_config = ConfigDict(extra="allow")
    source_domain: str = ""
    target_domain: str = ""
    policy_id: str = ""
    restriction_type: str = "DENY"


class PermissionEnvelope(BaseModel):
    model_config = ConfigDict(extra="allow")
    request_id: str = ""
    table_permissions: list[TablePermission] = []
    join_restrictions: list[JoinRestriction] = []
    global_nl_rules: list[str] = []
    resolved_at: str | None = None
    policy_version: int = 1
    signature: str = ""


# ── Execution Config ───────────────────────────────────────────────────────

class ExecutionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    timeout_seconds: int = Field(default=30, ge=1, le=120)
    max_rows: int = Field(default=10_000, ge=1, le=100_000)
    btg_active: bool = False
    include_nl_summary: bool = False


# ── Request ────────────────────────────────────────────────────────────────

class ExecutionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: str = Field(..., min_length=1)
    validated_sql: str = Field(..., min_length=1)
    dialect: str = "postgresql"
    target_database: str = "mock"
    parameters: dict[str, Any] = {}
    permission_envelope: PermissionEnvelope
    execution_config: ExecutionConfig = ExecutionConfig()
    security_context: dict[str, Any] = {}
    original_question: str = ""


# ── Response ───────────────────────────────────────────────────────────────

class ColumnMetadata(BaseModel):
    name: str
    type: str = "VARCHAR"
    masked: bool = False
    masking_strategy: str | None = None


class SanitizationEvent(BaseModel):
    row_index: int
    column: str
    pii_type: PIIType
    original_snippet: str  # First few chars only — never log full PII
    masked_value: str


class ExecutionMetadata(BaseModel):
    database: str
    execution_time_ms: float
    rows_fetched: int
    sanitization_events: int
    memory_used_mb: float
    truncated: bool = False
    audit_flags: list[AuditFlag] = []


class ExecutionResponse(BaseModel):
    request_id: str
    status: ExecutionStatus
    columns: list[ColumnMetadata] = []
    rows: list[list[Any]] = []
    row_count: int = 0
    total_rows_available: int | None = None
    truncated: bool = False
    execution_metadata: ExecutionMetadata | None = None
    nl_summary: str | None = None
    error_detail: str | None = None


# ── Audit Event (emitted to L8) ────────────────────────────────────────────

class ExecutionAuditEvent(BaseModel):
    event_id: str = ""
    event_type: str = "QUERY_EXECUTED"
    source_layer: str = "L7"
    severity: str = "INFO"
    request_id: str
    user_id: str
    session_id: str
    timestamp: str = ""
    payload: dict[str, Any] = {}
    # Legacy fields kept for backward compat — also packed into payload
    database: str = ""
    sql_executed: str = ""
    dialect: str = ""
    rows_returned: int = 0
    execution_time_ms: float = 0.0
    resource_usage: dict[str, Any] = {}
    sanitization_events: int = 0
    btg_active: bool = False
    truncated: bool = False
    status: str = ""
    audit_flags: list[str] = []
