"""Domain models representing Neo4j graph entities.

These models map exactly to the Section 5 node definitions in the
Knowledge Graph, providing structured representation for the L4 rules engine.
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class ConditionNode(BaseModel):
    """Mapping of the Condition node in Neo4j."""
    
    model_config = ConfigDict(extra="ignore")
    
    condition_id: str
    condition_type: str = Field(..., description="ROW_FILTER | MASKING_RULE | JOIN_RESTRICTION | AGGREGATION")
    expression: str = Field(..., description="The parameter-injected string (e.g. department_id = $dept)")
    parameters_required: list[str] = Field(default_factory=list)


class PolicyNode(BaseModel):
    """Mapping of the Policy node in Neo4j."""

    model_config = ConfigDict(extra="ignore")

    policy_id: str
    name: str = ""
    effect: str = Field(..., description="ALLOW | DENY | FILTER | MASK")
    priority: int = 100
    description: str = ""
    conditions: list[ConditionNode] = Field(default_factory=list)
    exception_roles: list[str] = Field(default_factory=list, description="Roles bypassing this policy")

    @property
    def is_deny(self) -> bool:
        return self.effect.upper() == "DENY"

    @property
    def is_allow(self) -> bool:
        return self.effect.upper() == "ALLOW"


class ColumnMetadata(BaseModel):
    """Schema context for a column."""
    
    model_config = ConfigDict(extra="ignore")

    column_id: str
    column_name: str
    data_type: str
    sensitivity_level: int = 1
    is_pii: bool = False
    masking_strategy: str | None = None
    policies: list[PolicyNode] = Field(default_factory=list)


class TableMetadata(BaseModel):
    """Schema context for a candidate table."""
    
    model_config = ConfigDict(extra="ignore")

    table_id: str
    table_name: str
    domain_tags: list[str] = Field(default_factory=list)
    sensitivity_level: int = 1
    columns: dict[str, ColumnMetadata] = Field(default_factory=dict)
    table_policies: list[PolicyNode] = Field(default_factory=list)
    domain_policies: list[PolicyNode] = Field(default_factory=list)
