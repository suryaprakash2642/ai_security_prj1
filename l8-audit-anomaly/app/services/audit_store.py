"""Immutable append-only audit log backed by SQLite (dev) or PostgreSQL (prod).

Hash chain implementation:
  chain_hash = SHA-256(previous_chain_hash + event_id + canonical_event_json)

Immutability enforced via:
  - SQLite triggers that REJECT any UPDATE or DELETE on audit_events
  - Insert-only API (no update/delete methods exposed)
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Any

import structlog

from app.models.api import AuditEventEnvelope, StoredAuditEvent
from app.models.enums import EventSourceLayer, EventSeverity

logger = structlog.get_logger(__name__)

# Sentinel genesis hash (chain starts here)
_GENESIS_HASH = "0" * 64

_lock = threading.Lock()
_db_path: str = ":memory:"
_conn: sqlite3.Connection | None = None


def initialize(db_path: str = ":memory:", force: bool = False) -> None:
    """Create the audit store database and enforce immutability via triggers.

    If already initialized and `force` is False, this is a no-op (idempotent).
    Pass force=True to reinitialize (e.g., in tests).
    """
    global _db_path, _conn
    if _conn is not None and not force:
        return  # Already initialized — skip
    if _conn is not None:
        try:
            _conn.close()
        except Exception:
            pass
    _db_path = db_path
    _conn = sqlite3.connect(db_path, check_same_thread=False)
    _conn.row_factory = sqlite3.Row

    with _conn:
        _conn.executescript("""
            CREATE TABLE IF NOT EXISTS audit_events (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id        TEXT    NOT NULL UNIQUE,
                event_type      TEXT    NOT NULL,
                source_layer    TEXT    NOT NULL,
                timestamp       TEXT    NOT NULL,
                request_id      TEXT    NOT NULL,
                user_id         TEXT    NOT NULL,
                session_id      TEXT    NOT NULL DEFAULT '',
                severity        TEXT    NOT NULL DEFAULT 'INFO',
                btg_active      INTEGER NOT NULL DEFAULT 0,
                payload_json    TEXT    NOT NULL DEFAULT '{}',
                hmac_signature  TEXT,
                chain_hash      TEXT    NOT NULL,
                ingested_at     TEXT    NOT NULL,
                integrity_verified INTEGER NOT NULL DEFAULT 1
            );

            CREATE INDEX IF NOT EXISTS idx_ae_timestamp    ON audit_events(timestamp);
            CREATE INDEX IF NOT EXISTS idx_ae_user_id      ON audit_events(user_id);
            CREATE INDEX IF NOT EXISTS idx_ae_request_id   ON audit_events(request_id);
            CREATE INDEX IF NOT EXISTS idx_ae_source_layer ON audit_events(source_layer);
            CREATE INDEX IF NOT EXISTS idx_ae_severity     ON audit_events(severity);

            -- Reject UPDATE: immutability enforcement
            CREATE TRIGGER IF NOT EXISTS trg_no_update
            BEFORE UPDATE ON audit_events
            BEGIN
                SELECT RAISE(ABORT, 'TAMPER_ALERT: audit_events is append-only');
            END;

            -- Reject DELETE: immutability enforcement
            CREATE TRIGGER IF NOT EXISTS trg_no_delete
            BEFORE DELETE ON audit_events
            BEGIN
                SELECT RAISE(ABORT, 'TAMPER_ALERT: audit_events is append-only');
            END;

            -- Deduplication table (24-hour event_id window)
            CREATE TABLE IF NOT EXISTS event_dedup (
                event_id   TEXT    PRIMARY KEY,
                seen_at    TEXT    NOT NULL
            );

            -- Alert store
            CREATE TABLE IF NOT EXISTS alerts (
                alert_id        TEXT    PRIMARY KEY,
                anomaly_type    TEXT    NOT NULL,
                severity        TEXT    NOT NULL,
                user_id         TEXT    NOT NULL,
                description     TEXT    NOT NULL,
                event_ids_json  TEXT    NOT NULL DEFAULT '[]',
                status          TEXT    NOT NULL DEFAULT 'OPEN',
                created_at      TEXT    NOT NULL,
                acknowledged_at TEXT,
                resolved_at     TEXT,
                occurrence_count INTEGER NOT NULL DEFAULT 1,
                dedup_key       TEXT    NOT NULL DEFAULT ''
            );
        """)

    logger.info("audit_store_initialized", db_path=db_path)


def _get_conn() -> sqlite3.Connection:
    if _conn is None:
        raise RuntimeError("audit_store not initialized — call initialize() first")
    return _conn


def _last_chain_hash(source_layer: str) -> str:
    """Return the most recent chain_hash for a given source layer."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT chain_hash FROM audit_events WHERE source_layer = ? ORDER BY id DESC LIMIT 1",
        (source_layer,),
    ).fetchone()
    return row["chain_hash"] if row else _GENESIS_HASH


def _compute_chain_hash(prev_hash: str, event: AuditEventEnvelope) -> str:
    canonical = json.dumps({
        "event_id": event.event_id,
        "event_type": event.event_type,
        "source_layer": event.source_layer,
        "timestamp": event.timestamp.isoformat(),
        "user_id": event.user_id,
        "request_id": event.request_id,
    }, sort_keys=True)
    return hashlib.sha256((prev_hash + canonical).encode()).hexdigest()


def is_duplicate(event_id: str, window_minutes: int = 15) -> bool:
    """Return True if event_id was seen within the dedup window."""
    conn = _get_conn()
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=window_minutes)).isoformat()
    row = conn.execute(
        "SELECT event_id FROM event_dedup WHERE event_id = ? AND seen_at > ?",
        (event_id, cutoff),
    ).fetchone()
    return row is not None


def _record_dedup(event_id: str) -> None:
    conn = _get_conn()
    with _lock:
        conn.execute(
            "INSERT OR REPLACE INTO event_dedup (event_id, seen_at) VALUES (?, ?)",
            (event_id, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()


def append(event: AuditEventEnvelope, integrity_verified: bool = True) -> StoredAuditEvent:
    """Append an event to the immutable audit log. Thread-safe."""
    conn = _get_conn()
    ingested_at = datetime.now(timezone.utc)

    with _lock:
        prev_hash = _last_chain_hash(event.source_layer)
        chain_hash = _compute_chain_hash(prev_hash, event)

        conn.execute(
            """INSERT INTO audit_events
               (event_id, event_type, source_layer, timestamp, request_id,
                user_id, session_id, severity, btg_active, payload_json,
                hmac_signature, chain_hash, ingested_at, integrity_verified)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                event.event_id,
                event.event_type,
                event.source_layer,
                event.timestamp.isoformat(),
                event.request_id,
                event.user_id,
                event.session_id,
                event.severity,
                int(event.btg_active),
                json.dumps(event.payload),
                event.hmac_signature,
                chain_hash,
                ingested_at.isoformat(),
                int(integrity_verified),
            ),
        )
        conn.commit()

    _record_dedup(event.event_id)

    stored = StoredAuditEvent(
        **event.model_dump(),
        chain_hash=chain_hash,
        ingested_at=ingested_at,
        integrity_verified=integrity_verified,
    )
    logger.info("event_appended",
                event_id=event.event_id,
                source_layer=event.source_layer,
                event_type=event.event_type)
    return stored


def _row_to_stored(row: sqlite3.Row) -> StoredAuditEvent:
    return StoredAuditEvent(
        event_id=row["event_id"],
        event_type=row["event_type"],
        source_layer=EventSourceLayer(row["source_layer"]),
        timestamp=datetime.fromisoformat(row["timestamp"]),
        request_id=row["request_id"],
        user_id=row["user_id"],
        session_id=row["session_id"],
        severity=EventSeverity(row["severity"]),
        btg_active=bool(row["btg_active"]),
        payload=json.loads(row["payload_json"]),
        hmac_signature=row["hmac_signature"],
        chain_hash=row["chain_hash"],
        ingested_at=datetime.fromisoformat(row["ingested_at"]),
        integrity_verified=bool(row["integrity_verified"]),
    )


def query(
    from_time: datetime | None = None,
    to_time: datetime | None = None,
    source_layers: list[str] | None = None,
    severities: list[str] | None = None,
    user_id: str | None = None,
    event_types: list[str] | None = None,
    request_id: str | None = None,
    btg_active: bool | None = None,
    sort_order: str = "desc",
    offset: int = 0,
    limit: int = 100,
) -> tuple[list[StoredAuditEvent], int]:
    """Query the audit log with optional filters. Returns (events, total_count)."""
    conn = _get_conn()

    conditions: list[str] = []
    params: list[Any] = []

    if from_time:
        conditions.append("timestamp >= ?")
        params.append(from_time.isoformat())
    if to_time:
        conditions.append("timestamp <= ?")
        params.append(to_time.isoformat())
    if source_layers:
        placeholders = ",".join("?" * len(source_layers))
        conditions.append(f"source_layer IN ({placeholders})")
        params.extend(source_layers)
    if severities:
        placeholders = ",".join("?" * len(severities))
        conditions.append(f"severity IN ({placeholders})")
        params.extend(severities)
    if user_id:
        conditions.append("user_id = ?")
        params.append(user_id)
    if event_types:
        placeholders = ",".join("?" * len(event_types))
        conditions.append(f"event_type IN ({placeholders})")
        params.extend(event_types)
    if request_id:
        conditions.append("request_id = ?")
        params.append(request_id)
    if btg_active is not None:
        conditions.append("btg_active = ?")
        params.append(int(btg_active))

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    order = "DESC" if sort_order.lower() == "desc" else "ASC"

    total = conn.execute(
        f"SELECT COUNT(*) FROM audit_events {where}", params
    ).fetchone()[0]

    rows = conn.execute(
        f"SELECT * FROM audit_events {where} ORDER BY timestamp {order} LIMIT ? OFFSET ?",
        params + [limit, offset],
    ).fetchall()

    return [_row_to_stored(r) for r in rows], total


def get_by_request_id(request_id: str) -> list[StoredAuditEvent]:
    """Return all events for a request_id in chronological order (pipeline replay)."""
    events, _ = query(request_id=request_id, sort_order="asc", limit=1000)
    return events


def verify_hash_chain(source_layer: str) -> tuple[bool, str]:
    """Re-compute the hash chain for a source_layer. Returns (valid, detail)."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM audit_events WHERE source_layer = ? ORDER BY id ASC",
        (source_layer,),
    ).fetchall()

    if not rows:
        return True, "No events — chain is trivially valid"

    prev_hash = _GENESIS_HASH
    for row in rows:
        event = _row_to_stored(row)
        expected = _compute_chain_hash(prev_hash, event)
        if expected != row["chain_hash"]:
            return False, (
                f"Hash chain broken at event_id={row['event_id']} "
                f"(expected={expected[:16]}…, stored={row['chain_hash'][:16]}…)"
            )
        prev_hash = row["chain_hash"]

    return True, f"Hash chain valid — {len(rows)} events verified"


def count_events(
    user_id: str | None = None,
    source_layer: str | None = None,
    event_type: str | None = None,
    from_time: datetime | None = None,
) -> int:
    """Fast count query for anomaly detection."""
    _, total = query(
        from_time=from_time,
        source_layers=[source_layer] if source_layer else None,
        user_id=user_id,
        event_types=[event_type] if event_type else None,
        limit=1,
    )
    return total
