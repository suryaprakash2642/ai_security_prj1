"""Alert Manager — deduplication, persistence, escalation, and dispatch.

Alert lifecycle:
  1. Anomaly detected → AnomalyAlert created with dedup_key
  2. Dedup check: if same (dedup_key) alert exists and is OPEN within the
     dedup window, increment occurrence_count instead of creating new alert.
     Escalate severity if occurrence_count > 5.
  3. Persist alert to SQLite alerts table (via audit_store connection).
  4. Dispatch alert to configured channels (log in dev, HTTP in prod).
"""

from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog

from app.models.api import AnomalyAlert
from app.models.enums import AlertStatus, EventSeverity
from app.services import audit_store

logger = structlog.get_logger(__name__)

_lock = threading.Lock()
_dedup_window_minutes: int = 15

_SEVERITY_ORDER = [
    EventSeverity.INFO,
    EventSeverity.WARNING,
    EventSeverity.HIGH,
    EventSeverity.CRITICAL,
]


def configure(dedup_window_minutes: int = 15) -> None:
    global _dedup_window_minutes
    _dedup_window_minutes = dedup_window_minutes


def _escalate(severity: EventSeverity) -> EventSeverity:
    idx = _SEVERITY_ORDER.index(severity)
    return _SEVERITY_ORDER[min(idx + 1, len(_SEVERITY_ORDER) - 1)]


def _save_alert(alert: AnomalyAlert) -> None:
    conn = audit_store._get_conn()
    import json
    conn.execute(
        """INSERT OR REPLACE INTO alerts
           (alert_id, anomaly_type, severity, user_id, description,
            event_ids_json, status, created_at, acknowledged_at, resolved_at,
            occurrence_count, dedup_key)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            alert.alert_id,
            alert.anomaly_type,
            alert.severity,
            alert.user_id,
            alert.description,
            json.dumps(alert.contributing_event_ids),
            alert.status,
            alert.created_at.isoformat(),
            alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
            alert.resolved_at.isoformat() if alert.resolved_at else None,
            alert.occurrence_count,
            alert.dedup_key,
        ),
    )
    conn.commit()


def _load_open_by_dedup_key(dedup_key: str) -> AnomalyAlert | None:
    """Return open alert with matching dedup_key within the dedup window."""
    conn = audit_store._get_conn()
    import json
    from app.models.enums import AnomalyType
    cutoff = (
        datetime.now(timezone.utc) - timedelta(minutes=_dedup_window_minutes)
    ).isoformat()
    row = conn.execute(
        """SELECT * FROM alerts
           WHERE dedup_key = ? AND status = 'OPEN' AND created_at >= ?
           ORDER BY created_at DESC LIMIT 1""",
        (dedup_key, cutoff),
    ).fetchone()
    if not row:
        return None
    return AnomalyAlert(
        alert_id=row["alert_id"],
        anomaly_type=AnomalyType(row["anomaly_type"]),
        severity=EventSeverity(row["severity"]),
        user_id=row["user_id"],
        description=row["description"],
        contributing_event_ids=json.loads(row["event_ids_json"]),
        status=AlertStatus(row["status"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        acknowledged_at=(
            datetime.fromisoformat(row["acknowledged_at"])
            if row["acknowledged_at"] else None
        ),
        occurrence_count=row["occurrence_count"],
        dedup_key=row["dedup_key"],
    )


def _dispatch(alert: AnomalyAlert) -> None:
    """Dispatch alert to configured channels. Dev: structured log only."""
    log_fn = {
        EventSeverity.INFO: logger.info,
        EventSeverity.WARNING: logger.warning,
        EventSeverity.HIGH: logger.warning,
        EventSeverity.CRITICAL: logger.error,
    }.get(alert.severity, logger.warning)

    log_fn(
        "alert_dispatched",
        alert_id=alert.alert_id,
        anomaly_type=alert.anomaly_type,
        severity=alert.severity,
        user_id=alert.user_id,
        description=alert.description,
        occurrence_count=alert.occurrence_count,
    )
    # In production: POST to PagerDuty, Slack, SIEM, email here.


def process(alert: AnomalyAlert) -> AnomalyAlert:
    """Deduplicate, persist, escalate, and dispatch an alert.

    Returns the final (possibly merged/escalated) alert.
    """
    with _lock:
        existing = _load_open_by_dedup_key(alert.dedup_key) if alert.dedup_key else None

        if existing:
            # Merge: increment count, escalate if threshold exceeded
            existing.occurrence_count += 1
            existing.contributing_event_ids.extend(alert.contributing_event_ids)
            if existing.occurrence_count > 5:
                existing.severity = _escalate(existing.severity)
                existing.description += (
                    f" [ESCALATED: {existing.occurrence_count} occurrences]"
                )
            _save_alert(existing)
            _dispatch(existing)
            return existing

        _save_alert(alert)
        _dispatch(alert)
        return alert


def get_alerts(
    status: AlertStatus | None = None,
    severity: EventSeverity | None = None,
    user_id: str | None = None,
    limit: int = 100,
) -> list[AnomalyAlert]:
    """Return alerts matching the given filters."""
    conn = audit_store._get_conn()
    import json
    from app.models.enums import AnomalyType

    conditions: list[str] = []
    params: list[Any] = []
    if status:
        conditions.append("status = ?")
        params.append(status)
    if severity:
        conditions.append("severity = ?")
        params.append(severity)
    if user_id:
        conditions.append("user_id = ?")
        params.append(user_id)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    rows = conn.execute(
        f"SELECT * FROM alerts {where} ORDER BY created_at DESC LIMIT ?",
        params + [limit],
    ).fetchall()

    result = []
    for row in rows:
        result.append(AnomalyAlert(
            alert_id=row["alert_id"],
            anomaly_type=AnomalyType(row["anomaly_type"]),
            severity=EventSeverity(row["severity"]),
            user_id=row["user_id"],
            description=row["description"],
            contributing_event_ids=json.loads(row["event_ids_json"]),
            status=AlertStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            acknowledged_at=(
                datetime.fromisoformat(row["acknowledged_at"])
                if row["acknowledged_at"] else None
            ),
            occurrence_count=row["occurrence_count"],
            dedup_key=row["dedup_key"],
        ))
    return result


def acknowledge(alert_id: str, notes: str = "") -> AnomalyAlert | None:
    conn = audit_store._get_conn()
    now = datetime.now(timezone.utc).isoformat()
    with _lock:
        conn.execute(
            "UPDATE alerts SET status='ACKNOWLEDGED', acknowledged_at=? WHERE alert_id=?",
            (now, alert_id),
        )
        conn.commit()
    alerts = get_alerts()
    for a in alerts:
        if a.alert_id == alert_id:
            return a
    return None


def resolve(alert_id: str) -> AnomalyAlert | None:
    conn = audit_store._get_conn()
    now = datetime.now(timezone.utc).isoformat()
    with _lock:
        conn.execute(
            "UPDATE alerts SET status='RESOLVED', resolved_at=? WHERE alert_id=?",
            (now, alert_id),
        )
        conn.commit()
    alerts = get_alerts()
    for a in alerts:
        if a.alert_id == alert_id:
            return a
    return None
