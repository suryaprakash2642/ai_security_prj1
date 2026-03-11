"""Alert management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.models.api import AlertAcknowledge, AnomalyAlert
from app.models.enums import AlertStatus, EventSeverity
from app.services import alert_manager

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


@router.get("", response_model=list[AnomalyAlert])
async def list_alerts(
    alert_status: str | None = None,
    severity: str | None = None,
    user_id: str | None = None,
    limit: int = 100,
) -> list[AnomalyAlert]:
    """List alerts with optional filters."""
    status_enum = AlertStatus(alert_status.upper()) if alert_status else None
    severity_enum = EventSeverity(severity.upper()) if severity else None
    return alert_manager.get_alerts(
        status=status_enum,
        severity=severity_enum,
        user_id=user_id,
        limit=limit,
    )


@router.post("/{alert_id}/acknowledge", response_model=AnomalyAlert)
async def acknowledge_alert(
    alert_id: str,
    body: AlertAcknowledge | None = None,
) -> AnomalyAlert:
    result = alert_manager.acknowledge(alert_id, notes=(body.notes if body else ""))
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found",
        )
    return result


@router.post("/{alert_id}/resolve", response_model=AnomalyAlert)
async def resolve_alert(alert_id: str) -> AnomalyAlert:
    result = alert_manager.resolve(alert_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found",
        )
    return result
