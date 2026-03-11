"""POST /api/v1/audit/ingest — receive events from all layers."""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, status

from app.config import Settings, get_settings
from app.models.api import AuditEventEnvelope, StoredAuditEvent
from app.services import audit_store, anomaly_detector, alert_manager
from app.services.event_normalizer import NormalizationError, normalize, verify_hmac

router = APIRouter(prefix="/api/v1/audit", tags=["ingest"])
logger = structlog.get_logger(__name__)


class IngestResponse(StoredAuditEvent):
    pass


@router.post(
    "/ingest",
    response_model=IngestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def ingest_event(
    raw_event: dict[str, Any],
    settings: Settings = Depends(get_settings),
) -> IngestResponse:
    """Ingest a single audit event from any layer (L1–L7).

    Steps:
      1. Normalize and validate schema
      2. Deduplicate (event_id within dedup window)
      3. Verify HMAC for CRITICAL events (flag but still store if invalid)
      4. Append to immutable audit log
      5. Run anomaly detection
      6. Process any detected anomaly alerts
    """
    # Step 1 — normalize
    try:
        event = normalize(raw_event)
    except NormalizationError as exc:
        logger.warning("ingest_schema_violation",
                       error_type=exc.error_type,
                       detail=str(exc))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error_type": exc.error_type, "message": str(exc)},
        )

    # Step 2 — deduplication
    if audit_store.is_duplicate(event.event_id, settings.dedup_window_minutes):
        logger.info("event_deduplicated", event_id=event.event_id)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error_type": "DUPLICATE_EVENT", "event_id": event.event_id},
        )

    # Step 3 — HMAC verification (CRITICAL events only)
    integrity_ok = verify_hmac(event, settings.envelope_signing_key)
    if not integrity_ok and not settings.is_dev:
        logger.error("critical_event_hmac_failure",
                     event_id=event.event_id,
                     event_type=event.event_type)
        # Still store it — mark as integrity_verified=False

    # Step 4 — append to immutable audit log
    stored = audit_store.append(event, integrity_verified=integrity_ok or settings.is_dev)

    # Step 5+6 — anomaly detection and alerting
    try:
        alerts = anomaly_detector.analyze(event)
        for raw_alert in alerts:
            alert_manager.process(raw_alert)
    except Exception as exc:
        # Anomaly engine failure must never block ingestion
        logger.error("anomaly_detection_error", error=str(exc))

    return IngestResponse(**stored.model_dump())


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "l8-audit-anomaly"}
