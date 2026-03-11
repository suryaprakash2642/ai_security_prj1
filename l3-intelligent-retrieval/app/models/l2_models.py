"""Models representing L2 Knowledge Graph responses.

These mirror the L2 API response schemas so L3 can deserialize them.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class L2TableInfo(BaseModel):
    """Table metadata from L2 Knowledge Graph."""

    model_config = ConfigDict(extra="ignore")

    fqn: str
    name: str
    description: str = ""
    sensitivity_level: int = 1
    domain: str = ""
    is_active: bool = True
    hard_deny: bool = False
    schema_name: str = ""
    database_name: str = ""
    regulations: list[str] = Field(default_factory=list)


class L2ColumnInfo(BaseModel):
    """Column metadata from L2."""

    model_config = ConfigDict(extra="ignore")

    fqn: str
    name: str
    data_type: str = ""
    is_pk: bool = False
    is_nullable: bool = True
    is_pii: bool = False
    pii_type: str | None = None
    sensitivity_level: int = 1
    masking_strategy: str | None = None
    description: str = ""
    is_active: bool = True
    regulations: list[str] = Field(default_factory=list)


class L2ForeignKey(BaseModel):
    """FK edge from L2."""

    model_config = ConfigDict(extra="ignore")

    source_table_fqn: str = ""
    source_column: str
    target_table_fqn: str = ""
    target_table: str = ""
    target_column: str = ""
    constraint_name: str = ""


class L2RoleDomainAccess(BaseModel):
    """Domain access for a role, from L2."""

    model_config = ConfigDict(extra="ignore")

    role_name: str
    accessible_domains: list[str] = Field(default_factory=list)


class L2VectorSearchResult(BaseModel):
    """Vector search result from L2 / pgvector."""

    model_config = ConfigDict(extra="ignore")

    entity_fqn: str
    source_text: str = ""
    similarity: float = 0.0
    entity_type: str = "table"


class L2APIResponse(BaseModel):
    """Standard L2 API response wrapper."""

    model_config = ConfigDict(extra="ignore")

    success: bool = True
    data: Any = None
    error: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)
