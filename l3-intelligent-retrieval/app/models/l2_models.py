"""Models representing L2 Knowledge Graph responses.

These mirror the L2 API response schemas so L3 can deserialize them.
"""

from __future__ import annotations

from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator


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
    source_column_fqn: str = ""
    source_column: str = Field(default="", validation_alias=AliasChoices("source_column", "source_column_name"))
    target_table_fqn: str = Field(default="", validation_alias=AliasChoices("target_table_fqn", "target_table"))
    target_table: str = ""
    target_column_fqn: str = ""
    target_column: str = Field(default="", validation_alias=AliasChoices("target_column", "target_column_name"))
    constraint_name: str = ""

    @model_validator(mode="after")
    def _derive_missing_fields(self) -> "L2ForeignKey":
        # Populate source/target table + column names from FQNs when L2 returns
        # only *_fqn and *_name fields.
        if not self.source_table_fqn and self.source_column_fqn and "." in self.source_column_fqn:
            self.source_table_fqn = ".".join(self.source_column_fqn.split(".")[:-1])

        if not self.source_column and self.source_column_fqn:
            self.source_column = self.source_column_fqn.split(".")[-1]

        if not self.target_column and self.target_column_fqn:
            self.target_column = self.target_column_fqn.split(".")[-1]

        if not self.target_table and self.target_table_fqn:
            self.target_table = self.target_table_fqn

        return self


class L2DatabaseInfo(BaseModel):
    """Database metadata from L2 Knowledge Graph."""

    model_config = ConfigDict(extra="ignore")

    name: str
    engine: str = ""
    description: str = ""
    host: str = ""
    port: int = 0
    table_count: int = 0
    domains: list[str] = Field(default_factory=list)


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
