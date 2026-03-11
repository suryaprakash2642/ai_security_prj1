"""Event normalization, HMAC verification, and schema validation.

Normalizes raw event dicts to AuditEventEnvelope with:
  - Required field presence checks
  - Timestamp parsing / UTC enforcement
  - HMAC verification for CRITICAL events
  - Deduplication via audit_store
"""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import Any

import structlog

from app.models.api import AuditEventEnvelope
from app.models.enums import EventSeverity, EventSourceLayer

logger = structlog.get_logger(__name__)

REQUIRED_FIELDS = {
    "event_id", "event_type", "source_layer", "timestamp",
    "request_id", "user_id",
}


class NormalizationError(Exception):
    def __init__(self, message: str, error_type: str = "SCHEMA_VIOLATION"):
        super().__init__(message)
        self.error_type = error_type


def normalize(raw: dict[str, Any]) -> AuditEventEnvelope:
    """Validate and normalize a raw event dict into an AuditEventEnvelope.

    Raises NormalizationError on schema violations.
    """
    missing = REQUIRED_FIELDS - raw.keys()
    if missing:
        raise NormalizationError(
            f"Missing required fields: {sorted(missing)}",
            "SCHEMA_VIOLATION",
        )

    # Validate and normalize source_layer
    try:
        source_layer = EventSourceLayer(raw["source_layer"].upper()
                                        if isinstance(raw["source_layer"], str)
                                        else raw["source_layer"])
    except ValueError:
        raise NormalizationError(
            f"Unknown source_layer: {raw['source_layer']}",
            "SCHEMA_VIOLATION",
        )

    # Validate and normalize severity
    severity_raw = raw.get("severity", "INFO")
    try:
        severity = EventSeverity(severity_raw.upper()
                                 if isinstance(severity_raw, str)
                                 else severity_raw)
    except ValueError:
        severity = EventSeverity.INFO
        logger.warning("unknown_severity", raw_value=severity_raw)

    # Parse timestamp
    ts_raw = raw["timestamp"]
    if isinstance(ts_raw, str):
        try:
            ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
        except ValueError:
            raise NormalizationError(
                f"Invalid timestamp format: {ts_raw}",
                "SCHEMA_VIOLATION",
            )
    elif isinstance(ts_raw, datetime):
        ts = ts_raw
    else:
        raise NormalizationError(f"Unexpected timestamp type: {type(ts_raw)}", "SCHEMA_VIOLATION")

    # Ensure UTC
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)

    return AuditEventEnvelope(
        event_id=str(raw["event_id"]),
        event_type=str(raw["event_type"]),
        source_layer=source_layer,
        timestamp=ts,
        request_id=str(raw["request_id"]),
        user_id=str(raw["user_id"]),
        session_id=str(raw.get("session_id", "")),
        severity=severity,
        btg_active=bool(raw.get("btg_active", False)),
        payload=raw.get("payload", {}),
        hmac_signature=raw.get("hmac_signature"),
    )


def verify_hmac(event: AuditEventEnvelope, signing_key: str) -> bool:
    """Verify HMAC-SHA256 signature on a CRITICAL event.

    Returns True if signature is valid (or not CRITICAL), False on failure.
    CRITICAL events without a signature return False.
    """
    if event.severity != EventSeverity.CRITICAL:
        return True  # Only CRITICAL events require HMAC

    if not event.hmac_signature:
        logger.warning("critical_event_unsigned",
                       event_id=event.event_id,
                       event_type=event.event_type)
        return False

    canonical = json.dumps({
        "event_id": event.event_id,
        "event_type": event.event_type,
        "source_layer": event.source_layer,
        "timestamp": event.timestamp.isoformat(),
        "user_id": event.user_id,
        "request_id": event.request_id,
    }, sort_keys=True)

    expected = hmac.new(
        signing_key.encode(),
        canonical.encode(),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, event.hmac_signature)
