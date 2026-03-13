"""API models for L4 Policy Resolution.

Defines the request payload from L3 and the strict, cryptographically
signed PermissionEnvelope response expected by L5/L6.
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ColumnVisibility, TableDecision


class BTGToken(BaseModel):
    """Break-the-Glass emergency access token."""

    model_config = ConfigDict(extra="ignore")

    token_id: str
    user_id: str
    patient_mrn: str | None = None
    reason: str = ""
    emergency_level: str = "CLINICAL_EMERGENCY"  # CLINICAL_EMERGENCY | SAFETY_CONCERN | ADMINISTRATIVE
    granted_at: str = ""
    expires_at: str = ""
    granted_by: str = ""
    still_denied: list[str] = Field(default_factory=list, description="Tables denied even under BTG")
    signature: str = ""


class PolicyResolveRequest(BaseModel):
    """Request payload from L3 Intelligent Retrieval."""

    model_config = ConfigDict(extra="forbid")

    candidate_table_ids: list[str] = Field(..., description="Tables matching the user's intent")
    effective_roles: list[str] = Field(..., description="Active roles from L1 SecurityContext")
    user_context: dict[str, Any] = Field(default_factory=dict, description="Variables for row filters (e.g. user_id)")
    request_id: str = Field(default="", description="Tracing ID")
    candidate_domains: list[str] = Field(default_factory=list, description="Domains of candidate tables")
    btg_token: BTGToken | None = Field(default=None, description="Active Break-the-Glass token")


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
    denied_in_select: list[str] = Field(default_factory=list, description="Columns forbidden in SELECT under aggregation_only")
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

    # Metadata (per spec Section 9.2)
    envelope_id: str = Field(default="", description="Unique envelope UUID")
    request_id: str = ""
    user_id: str = Field(default="", description="User who requested resolution")
    effective_roles: list[str] = Field(default_factory=list, description="Roles used for resolution")
    resolved_at: str = ""
    expires_at: str = Field(default="", description="Envelope expiry (resolved_at + 60s)")
    policy_graph_version: str = Field(default="", description="Neo4j graph version hash")
    btg_active: bool = Field(default=False, description="Whether BTG override was applied")

    # Table decisions
    table_permissions: list[TablePermission] = Field(default_factory=list)

    # Join restrictions
    join_restrictions: list[JoinRestriction] = Field(default_factory=list)

    # NL rules for L5
    global_nl_rules: list[str] = Field(default_factory=list)

    # Signing
    policy_version: int = 0
    signature: str = Field(default="", description="HMAC-SHA256 signature")

    # Audit fields (per spec Section 9.2)
    total_policies_evaluated: int = 0
    total_tables_allowed: int = 0
    total_tables_denied: int = 0
    resolution_latency_ms: float = 0.0

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
