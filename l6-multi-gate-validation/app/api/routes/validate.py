"""Route: POST /api/v1/validate/sql"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.models.api import ValidationRequest, ValidationResponse
from app.services.validation_orchestrator import run

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post("/validate/sql", response_model=ValidationResponse)
async def validate_sql(
    request: ValidationRequest,
    settings: Settings = Depends(get_settings),
) -> ValidationResponse:
    """Validate LLM-generated SQL through three independent security gates.

    Gate 1 (Structural): Tables, columns, joins, filters, aggregation rules.
    Gate 2 (Classification): Sensitivity levels, masking compliance.
    Gate 3 (Behavioral): DML/DDL, UNION, dynamic SQL, system tables.

    Runs the Query Rewriter if all gates PASS.
    Returns APPROVED + validated SQL or BLOCKED + violations.
    """
    logger.info("Validation request received",
                request_id=request.request_id,
                dialect=request.dialect,
                sql_len=len(request.raw_sql))

    response = await run(request, settings)
    return response
