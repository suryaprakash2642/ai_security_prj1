"""Shared test fixtures for L8."""

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app
from app.services import audit_store, anomaly_detector, alert_manager


@pytest.fixture(autouse=True)
def fresh_store():
    """Initialize a fresh in-memory audit store for each test.

    Uses force=True so that the app startup event (which also calls
    initialize()) is a no-op and does not switch to the file-backed store.
    """
    audit_store.initialize(":memory:", force=True)
    anomaly_detector.reset_state()
    anomaly_detector.configure()
    alert_manager.configure(dedup_window_minutes=15)
    yield
    if audit_store._conn:
        audit_store._conn.close()
        audit_store._conn = None


@pytest.fixture
def client():
    """FastAPI test client backed by the in-memory store set up by fresh_store."""
    with TestClient(app) as c:
        yield c


def make_event(
    event_type: str = "EXECUTION_COMPLETE",
    source_layer: str = "L7",
    severity: str = "INFO",
    user_id: str = "dr-patel",
    request_id: str = "req-001",
    btg_active: bool = False,
    payload: dict | None = None,
    **kwargs,
) -> dict:
    """Build a minimal valid audit event dict."""
    from uuid import uuid4
    return {
        "event_id": str(uuid4()),
        "event_type": event_type,
        "source_layer": source_layer,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "request_id": request_id,
        "user_id": user_id,
        "session_id": "sess-test",
        "severity": severity,
        "btg_active": btg_active,
        "payload": payload or {},
        **kwargs,
    }
