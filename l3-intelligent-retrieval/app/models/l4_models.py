"""Models for L4 Policy Resolution integration.

L3 sends candidate table IDs + roles to L4, and receives a
PermissionEnvelope with per-table/per-column access decisions.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ColumnVisibility, TableDecision


class PolicyResolveRequest(BaseModel):
    """Request to L4 to resolve policies for candidate tables."""

    model_config = ConfigDict(extra="forbid")

    candidate_table_ids: list[str]
    effective_roles: list[str]
    user_context: dict[str, Any] = Field(default_factory=dict)
    request_id: str = ""


class ColumnDecision(BaseModel):
    """Per-column access decision from L4."""

    model_config = ConfigDict(extra="ignore")

    column_name: str
    visibility: ColumnVisibility = ColumnVisibility.VISIBLE
    masking_expression: str | None = None
    computed_expression: str | None = None
    reason: str = ""


class TablePermission(BaseModel):
    """Per-table permission from L4."""

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
    """Cross-table join restriction from L4."""

    model_config = ConfigDict(extra="ignore")

    source_domain: str
    target_domain: str
    policy_id: str = ""
    restriction_type: str = "DENY"


class PermissionEnvelope(BaseModel):
    """Complete policy resolution response from L4.

    This is the authoritative access decision for the current request.
    """

    model_config = ConfigDict(extra="ignore")

    request_id: str = ""
    table_permissions: list[TablePermission] = Field(default_factory=list)
    join_restrictions: list[JoinRestriction] = Field(default_factory=list)
    global_nl_rules: list[str] = Field(default_factory=list)
    resolved_at: str = ""
    policy_version: int = 0
    signature: str = ""

    def get_table_permission(self, table_id: str) -> TablePermission | None:
        """Look up permission for a specific table."""
        for tp in self.table_permissions:
            if tp.table_id == table_id:
                return tp
        return None

    @property
    def allowed_table_ids(self) -> set[str]:
        """Set of table IDs that are not DENIED."""
        return {
            tp.table_id
            for tp in self.table_permissions
            if tp.decision != TableDecision.DENY
        }

    @property
    def denied_table_ids(self) -> set[str]:
        return {
            tp.table_id
            for tp in self.table_permissions
            if tp.decision == TableDecision.DENY
        }
