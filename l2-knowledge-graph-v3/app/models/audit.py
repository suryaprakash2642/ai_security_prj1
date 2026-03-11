"""Audit and versioning models for PostgreSQL change log."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ChangeAction, ChangeSource


class ChangeRecord(BaseModel):
    """Represents a single graph mutation for the audit log."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    node_type: str
    node_id: str
    action: ChangeAction
    changed_properties: dict[str, Any] = Field(default_factory=dict)
    old_values: dict[str, Any] = Field(default_factory=dict)
    new_values: dict[str, Any] = Field(default_factory=dict)
    changed_by: str
    change_source: ChangeSource = ChangeSource.MANUAL


class PolicyVersionRecord(BaseModel):
    """Snapshot of a policy at a specific version."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    policy_id: str
    version: int
    policy_type: str
    nl_description: str
    structured_rule: dict[str, Any]
    priority: int
    is_active: bool
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CrawlRecord(BaseModel):
    """Tracks a schema crawl execution."""
    model_config = ConfigDict(extra="forbid")

    database_name: str
    status: str = "running"
    tables_found: int = 0
    tables_added: int = 0
    tables_updated: int = 0
    tables_deactivated: int = 0
    columns_found: int = 0
    columns_added: int = 0
    columns_updated: int = 0
    errors: list[dict[str, Any]] = Field(default_factory=list)
    triggered_by: str = "system"
