"""L8 Pydantic models."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from app.models.enums import (
    AlertStatus, AnomalyType, EventSeverity, EventSourceLayer, ReportType,
)


# ── Audit Event ───────────────────────────────────────────────────────────────

class AuditEventEnvelope(BaseModel):
    """Common event envelope — all layers emit this structure."""
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: str
    source_layer: EventSourceLayer
    timestamp: datetime
    request_id: str
    user_id: str
    session_id: str = ""
    severity: EventSeverity = EventSeverity.INFO
    btg_active: bool = False
    payload: dict[str, Any] = Field(default_factory=dict)
    hmac_signature: str | None = None


class StoredAuditEvent(AuditEventEnvelope):
    """Event as persisted in the audit store (adds hash chain fields)."""
    chain_hash: str
    ingested_at: datetime
    integrity_verified: bool = True  # False if HMAC check failed


# ── Anomaly Alert ─────────────────────────────────────────────────────────────

class AnomalyAlert(BaseModel):
    alert_id: str = Field(default_factory=lambda: str(uuid4()))
    anomaly_type: AnomalyType
    severity: EventSeverity
    user_id: str
    description: str
    contributing_event_ids: list[str] = Field(default_factory=list)
    status: AlertStatus = AlertStatus.OPEN
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged_at: datetime | None = None
    resolved_at: datetime | None = None
    occurrence_count: int = 1
    dedup_key: str = ""  # (user_id, anomaly_type, window)


class AlertAcknowledge(BaseModel):
    notes: str = ""


# ── Audit Query ───────────────────────────────────────────────────────────────

class TimeRange(BaseModel):
    from_time: datetime = Field(alias="from")
    to_time: datetime = Field(alias="to")

    model_config = {"populate_by_name": True}


class AuditQueryFilters(BaseModel):
    source_layer: list[EventSourceLayer] | None = None
    severity: list[EventSeverity] | None = None
    user_id: str | None = None
    event_type: list[str] | None = None
    request_id: str | None = None
    btg_active: bool | None = None


class AuditQueryPagination(BaseModel):
    offset: int = 0
    limit: int = Field(default=100, le=1000)


class AuditQuerySort(BaseModel):
    field: str = "timestamp"
    order: str = "desc"


class AuditQueryRequest(BaseModel):
    time_range: TimeRange | None = None
    filters: AuditQueryFilters = Field(default_factory=AuditQueryFilters)
    pagination: AuditQueryPagination = Field(default_factory=AuditQueryPagination)
    sort: AuditQuerySort = Field(default_factory=AuditQuerySort)


class AuditQueryResponse(BaseModel):
    events: list[StoredAuditEvent]
    total: int
    offset: int
    limit: int


# ── Compliance Report ─────────────────────────────────────────────────────────

class ReportRequest(BaseModel):
    report_type: ReportType
    time_range: TimeRange | None = None
    filters: dict[str, Any] = Field(default_factory=dict)


class ComplianceReport(BaseModel):
    report_id: str = Field(default_factory=lambda: str(uuid4()))
    report_type: ReportType
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    time_range_from: datetime | None = None
    time_range_to: datetime | None = None
    data: dict[str, Any]
