"""API models for L4 Policy Resolution.

Defines the request payload from L3 and the strict, cryptographically
signed PermissionEnvelope response expected by L5/L6.
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ColumnVisibility, TableDecision


class PolicyResolveRequest(BaseModel):
    """Request payload from L3 Intelligent Retrieval."""

    model_config = ConfigDict(extra="forbid")

    candidate_table_ids: list[str] = Field(..., description="Tables matching the user's intent")
    effective_roles: list[str] = Field(..., description="Active roles from L1 SecurityContext")
    user_context: dict[str, Any] = Field(default_factory=dict, description="Variables for row filters (e.g. user_id)")
    request_id: str = Field(default="", description="Tracing ID")


class ColumnDecision(BaseModel):
    """Per-column access decision."""

    model_config = ConfigDict(extra="ignore")

    column_name: str
    visibility: ColumnVisibility = ColumnVisibility.VISIBLE
    masking_expression: str | None = None
    computed_expression: str | None = None
    reason: str = ""


class TablePermission(BaseModel):
    """Per-table permission definition."""

    model_config = ConfigDict(extra="ignore")

    table_id: str
    decision: TableDecision = TableDecision.DENY
    columns: list[ColumnDecision] = Field(default_factory=list)
    row_filters: list[str] = Field(default_factory=list)
    aggregation_only: bool = False
    max_rows: int | None = None
    nl_rules: list[str] = Field(default_factory=list)
    reason: str = ""


class JoinRestriction(BaseModel):
    """Cross-domain or cross-table join restriction."""

    model_config = ConfigDict(extra="ignore")

    source_domain: str
    target_domain: str
    policy_id: str = ""
    restriction_type: str = "DENY"


class PermissionEnvelope(BaseModel):
    """The authoritative access decision from L4 policy resolution.
    
    This is cryptographically signed and has a strict TTL (60s).
    """

    model_config = ConfigDict(extra="ignore")

    request_id: str = ""
    table_permissions: list[TablePermission] = Field(default_factory=list)
    join_restrictions: list[JoinRestriction] = Field(default_factory=list)
    global_nl_rules: list[str] = Field(default_factory=list)
    resolved_at: str = ""
    policy_version: int = 0
    signature: str = Field(default="", description="HMAC-SHA256 signature")

    def get_table_permission(self, table_id: str) -> TablePermission | None:
        for tp in self.table_permissions:
            if tp.table_id == table_id:
                return tp
        return None

    @property
    def allowed_table_ids(self) -> set[str]:
        return {
            tp.table_id for tp in self.table_permissions
            if tp.decision != TableDecision.DENY
        }

    @property
    def denied_table_ids(self) -> set[str]:
        return {
            tp.table_id for tp in self.table_permissions
            if tp.decision == TableDecision.DENY
        }
