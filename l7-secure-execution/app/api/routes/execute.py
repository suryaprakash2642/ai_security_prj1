"""L7 Execution API routes."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException

from app.config import Settings, get_settings
from app.models.api import ExecutionRequest, ExecutionResponse
from app.models.enums import ExecutionStatus
from app.services.circuit_breaker import get_registry
from app.services.execution_orchestrator import run

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/execute", tags=["execution"])


@router.post("/sql", response_model=ExecutionResponse)
async def execute_sql(
    request: ExecutionRequest,
    settings: Settings = Depends(get_settings),
) -> ExecutionResponse:
    """Execute a validated SQL query against the target database.

    This endpoint accepts SQL that has been APPROVED by L6 (Multi-Gate Validation).
    It applies resource limits, executes against a read-only connection, sanitizes
    results for PII, and returns a structured response.
    """
    response = await run(request, settings)

    # Map terminal error statuses to HTTP error codes
    error_http_map = {
        ExecutionStatus.INVALID_ENVELOPE: 401,
        ExecutionStatus.EXECUTION_NOT_AUTHORIZED: 403,
        ExecutionStatus.QUERY_TIMEOUT: 408,
        ExecutionStatus.DATABASE_UNAVAILABLE: 503,
        ExecutionStatus.INVALID_REQUEST: 400,
    }
    if response.status in error_http_map:
        raise HTTPException(
            status_code=error_http_map[response.status],
            detail={
                "error_code": response.status.value,
                "message": response.error_detail or response.status.value,
            },
        )

    return response


@router.get("/health")
async def health(settings: Settings = Depends(get_settings)) -> dict:
    registry = get_registry(
        settings.circuit_breaker_error_threshold,
        settings.circuit_breaker_cooldown_seconds,
    )
    return {
        "status": "ok",
        "mock_execution": settings.mock_execution,
        "circuit_breakers": registry.all_statuses(),
    }
