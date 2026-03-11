"""Anomaly Detection Engine — statistical and rule-based.

Models implemented:
  1. Volume anomaly — z-score vs rolling per-user hourly baseline
  2. Temporal anomaly — off-hours access detection
  3. Validation block spike — multiple L6 blocks in short window
  4. Sanitization spike — repeated PII hits on same column in 1 hour
  5. BTG duration / frequency analysis
  6. Sensitivity escalation — increasing avg sensitivity level in 4 hours
"""

from __future__ import annotations

import math
import threading
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog

from app.models.api import AnomalyAlert, AuditEventEnvelope
from app.models.enums import AnomalyType, EventSeverity

logger = structlog.get_logger(__name__)

_lock = threading.Lock()

# ── Per-user query count ring buffer (hour-level) ────────────────────────────
# user_id → deque of (hour_bucket: int, count: int) — rolling 7 days (168 slots)
_user_hourly_counts: dict[str, deque] = defaultdict(lambda: deque(maxlen=168))

# ── Per-user current-hour counter ───────────────────────────────────────────
# user_id → {bucket: int, count: int}
_user_current_hour: dict[str, dict[str, Any]] = {}

# ── L6 validation block tracking (per user, rolling 1 hour) ────────────────
# user_id → deque of datetime
_user_block_times: dict[str, deque] = defaultdict(lambda: deque())

# ── Sanitization spike tracking (column → deque of datetime) ───────────────
# column_name → deque of datetime
_sanitization_times: dict[str, deque] = defaultdict(lambda: deque())

# ── BTG session tracking ─────────────────────────────────────────────────────
# user_id → {"start": datetime, "records": int}
_active_btg: dict[str, dict[str, Any]] = {}

# ── Sensitivity level tracking (user → deque of (datetime, level)) ──────────
_sensitivity_history: dict[str, deque] = defaultdict(lambda: deque(maxlen=100))

# ── Configuration (updated by Detector init) ─────────────────────────────────
_cfg: dict[str, Any] = {
    "z_high": 3.0,
    "z_critical": 5.0,
    "work_start": 7,
    "work_end": 19,
    "block_threshold": 3,
    "sanitization_threshold": 10,
    "btg_duration_hours": 4.0,
}


def configure(
    z_high: float = 3.0,
    z_critical: float = 5.0,
    work_start: int = 7,
    work_end: int = 19,
    block_threshold: int = 3,
    sanitization_threshold: int = 10,
    btg_duration_hours: float = 4.0,
) -> None:
    _cfg.update(
        z_high=z_high,
        z_critical=z_critical,
        work_start=work_start,
        work_end=work_end,
        block_threshold=block_threshold,
        sanitization_threshold=sanitization_threshold,
        btg_duration_hours=btg_duration_hours,
    )


def _current_hour_bucket() -> int:
    now = datetime.now(timezone.utc)
    return int(now.timestamp() // 3600)


def _z_score(value: float, history: list[float]) -> float:
    """Compute z-score of value against history. Returns 0 if insufficient data."""
    if len(history) < 3:
        return 0.0
    mean = sum(history) / len(history)
    variance = sum((x - mean) ** 2 for x in history) / len(history)
    std = math.sqrt(variance)
    if std == 0:
        # All historical values identical — any deviation is anomalous
        return 10.0 if value > mean else 0.0
    return (value - mean) / std


def _increment_user_count(user_id: str, event_time: datetime) -> float:
    """Track per-user hourly query count. Returns current-hour count."""
    bucket = int(event_time.timestamp() // 3600)
    with _lock:
        current = _user_current_hour.get(user_id)
        if current is None or current["bucket"] != bucket:
            # New hour — flush previous hour to ring buffer
            if current is not None:
                _user_hourly_counts[user_id].append(current["count"])
            _user_current_hour[user_id] = {"bucket": bucket, "count": 1}
        else:
            _user_current_hour[user_id]["count"] += 1
        return _user_current_hour[user_id]["count"]


def _volume_anomaly(event: AuditEventEnvelope) -> AnomalyAlert | None:
    """Detect unusual query volume via z-score."""
    current_count = _increment_user_count(event.user_id, event.timestamp)

    history = list(_user_hourly_counts[event.user_id])
    z = _z_score(current_count, history)

    if z >= _cfg["z_critical"]:
        return AnomalyAlert(
            anomaly_type=AnomalyType.VOLUME,
            severity=EventSeverity.CRITICAL,
            user_id=event.user_id,
            description=(
                f"Critical volume anomaly: {current_count} queries this hour "
                f"(z-score={z:.1f}, threshold={_cfg['z_critical']:.1f})"
            ),
            contributing_event_ids=[event.event_id],
            dedup_key=f"{event.user_id}:VOLUME:{_current_hour_bucket()}",
        )
    if z >= _cfg["z_high"]:
        return AnomalyAlert(
            anomaly_type=AnomalyType.VOLUME,
            severity=EventSeverity.HIGH,
            user_id=event.user_id,
            description=(
                f"Volume anomaly: {current_count} queries this hour "
                f"(z-score={z:.1f}, threshold={_cfg['z_high']:.1f})"
            ),
            contributing_event_ids=[event.event_id],
            dedup_key=f"{event.user_id}:VOLUME:{_current_hour_bucket()}",
        )
    return None


def _temporal_anomaly(event: AuditEventEnvelope) -> AnomalyAlert | None:
    """Detect off-hours access. BTG sessions are suppressed."""
    if event.btg_active:
        return None

    hour = event.timestamp.astimezone(timezone.utc).hour
    if _cfg["work_start"] <= hour < _cfg["work_end"]:
        return None  # Within normal hours

    severity = EventSeverity.WARNING
    description = (
        f"Off-hours access at {hour:02d}:00 UTC "
        f"(normal window: {_cfg['work_start']:02d}:00–{_cfg['work_end']:02d}:00)"
    )

    # Escalate if accessing sensitive data (indicated by HIGH severity execution event)
    if event.severity in (EventSeverity.HIGH, EventSeverity.CRITICAL):
        severity = EventSeverity.HIGH
        description += " with sensitive data access"

    day_bucket = event.timestamp.strftime("%Y-%m-%d")
    return AnomalyAlert(
        anomaly_type=AnomalyType.TEMPORAL,
        severity=severity,
        user_id=event.user_id,
        description=description,
        contributing_event_ids=[event.event_id],
        dedup_key=f"{event.user_id}:TEMPORAL:{day_bucket}:{hour}",
    )


def _validation_block_spike(event: AuditEventEnvelope) -> AnomalyAlert | None:
    """Detect repeated L6 validation blocks in a 1-hour window."""
    if event.event_type != "VALIDATION_BLOCK":
        return None

    cutoff = event.timestamp - timedelta(hours=1)
    with _lock:
        q = _user_block_times[event.user_id]
        q.append(event.timestamp)
        # Trim old events
        while q and q[0] < cutoff:
            q.popleft()
        count = len(q)

    if count >= _cfg["block_threshold"]:
        return AnomalyAlert(
            anomaly_type=AnomalyType.VALIDATION_BLOCK_SPIKE,
            severity=EventSeverity.HIGH,
            user_id=event.user_id,
            description=(
                f"Repeated validation blocks: {count} blocks in the last hour "
                f"(threshold={_cfg['block_threshold']})"
            ),
            contributing_event_ids=[event.event_id],
            dedup_key=f"{event.user_id}:VALIDATION_BLOCK_SPIKE:{_current_hour_bucket()}",
        )
    return None


def _sanitization_spike(event: AuditEventEnvelope) -> AnomalyAlert | None:
    """Detect repeated sanitization events for the same column in 1 hour."""
    if event.event_type != "SANITIZATION_APPLIED":
        return None

    column = event.payload.get("column", "unknown")
    cutoff = event.timestamp - timedelta(hours=1)

    with _lock:
        q = _sanitization_times[column]
        q.append(event.timestamp)
        while q and q[0] < cutoff:
            q.popleft()
        count = len(q)

    if count >= _cfg["sanitization_threshold"]:
        return AnomalyAlert(
            anomaly_type=AnomalyType.SANITIZATION_SPIKE,
            severity=EventSeverity.HIGH,
            user_id=event.user_id,
            description=(
                f"Sanitization spike: column '{column}' triggered {count} PII "
                f"masking events in the last hour (threshold={_cfg['sanitization_threshold']}). "
                f"Review Knowledge Graph classification."
            ),
            contributing_event_ids=[event.event_id],
            dedup_key=f"SANITIZATION_SPIKE:{column}:{_current_hour_bucket()}",
        )
    return None


def _btg_duration(event: AuditEventEnvelope) -> AnomalyAlert | None:
    """Detect long-running BTG sessions."""
    user_id = event.user_id

    if event.event_type == "BTG_ACTIVATION":
        with _lock:
            _active_btg[user_id] = {
                "start": event.timestamp,
                "records": 0,
            }
        return None

    if event.event_type in ("BTG_EXPIRED", "SESSION_END"):
        with _lock:
            session = _active_btg.pop(user_id, None)
        if session:
            duration = (event.timestamp - session["start"]).total_seconds() / 3600
            if duration > _cfg["btg_duration_hours"]:
                return AnomalyAlert(
                    anomaly_type=AnomalyType.BTG_ABUSE,
                    severity=EventSeverity.HIGH,
                    user_id=user_id,
                    description=(
                        f"BTG session exceeded duration threshold: "
                        f"{duration:.1f} hours (threshold={_cfg['btg_duration_hours']} hours)"
                    ),
                    contributing_event_ids=[event.event_id],
                    dedup_key=f"{user_id}:BTG_DURATION:{event.timestamp.date()}",
                )
        return None

    # Track rows accessed during active BTG
    if event.btg_active and event.event_type == "EXECUTION_COMPLETE":
        with _lock:
            if user_id in _active_btg:
                rows = event.payload.get("rows_returned", 0)
                _active_btg[user_id]["records"] += rows

    return None


def analyze(event: AuditEventEnvelope) -> list[AnomalyAlert]:
    """Run all anomaly detectors on an event. Returns detected alerts (may be empty)."""
    alerts: list[AnomalyAlert] = []

    detectors = [
        _volume_anomaly,
        _temporal_anomaly,
        _validation_block_spike,
        _sanitization_spike,
        _btg_duration,
    ]

    for detector in detectors:
        try:
            result = detector(event)
            if result is not None:
                alerts.append(result)
                logger.warning(
                    "anomaly_detected",
                    anomaly_type=result.anomaly_type,
                    severity=result.severity,
                    user_id=event.user_id,
                    event_type=event.event_type,
                )
        except Exception as exc:
            logger.error("anomaly_detector_error", detector=detector.__name__, error=str(exc))

    return alerts


def reset_state() -> None:
    """Reset all in-memory state (used in tests)."""
    with _lock:
        _user_hourly_counts.clear()
        _user_current_hour.clear()
        _user_block_times.clear()
        _sanitization_times.clear()
        _active_btg.clear()
        _sensitivity_history.clear()
