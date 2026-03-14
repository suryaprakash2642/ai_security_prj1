"""Async audit event emitter — sends ExecutionAuditEvent to L8.

Fire-and-forget: never blocks the execution response path.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import structlog

from app.models.api import ExecutionAuditEvent

logger = structlog.get_logger(__name__)


async def emit(event: ExecutionAuditEvent, l8_url: str) -> None:
    """Asynchronously POST the audit event to L8. Swallows errors."""
    try:
        import httpx
        now = datetime.now(timezone.utc).isoformat()
        event.timestamp = now
        if not event.event_id:
            event.event_id = f"evt-{event.request_id}-{int(datetime.now(timezone.utc).timestamp() * 1000)}"
        # Pack execution details into payload for L8 schema compliance
        event.payload = {
            "database": event.database,
            "sql_executed": event.sql_executed,
            "dialect": event.dialect,
            "rows_returned": event.rows_returned,
            "execution_time_ms": event.execution_time_ms,
            "resource_usage": event.resource_usage,
            "sanitization_events": event.sanitization_events,
            "truncated": event.truncated,
            "status": event.status,
            "audit_flags": event.audit_flags,
        }
        # Send only L8-compatible fields
        body = {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "source_layer": event.source_layer,
            "severity": event.severity,
            "timestamp": event.timestamp,
            "request_id": event.request_id,
            "user_id": event.user_id,
            "session_id": event.session_id,
            "btg_active": event.btg_active,
            "payload": event.payload,
        }
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{l8_url}/api/v1/audit/ingest",
                json=body,
            )
            if resp.status_code not in (200, 201, 202):
                logger.warning("audit_emit_failed",
                               status=resp.status_code,
                               url=l8_url)
    except Exception as exc:
        # Never let audit failures affect the execution path
        logger.warning("audit_emit_error", error=str(exc))


def emit_background(event: ExecutionAuditEvent, l8_url: str) -> None:
    """Schedule audit emission as a background task (non-blocking)."""
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(emit(event, l8_url))
    except RuntimeError:
        # No event loop — log only
        logger.info("audit_event_no_loop",
                    request_id=event.request_id,
                    status=event.status)
