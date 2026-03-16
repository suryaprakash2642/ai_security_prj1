"""Route: POST /api/v1/generate/sql"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException

from app.config import Settings, get_settings
from app.models.api import GenerationRequest, GenerationResponse
from app.services.generation_orchestrator import run

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post("/generate/sql", response_model=GenerationResponse)
async def generate_sql(
    request: GenerationRequest,
    settings: Settings = Depends(get_settings),
) -> GenerationResponse:
    """Generate a SQL query from a natural language question.

    Receives the Permission Envelope (from L4) and filtered schema (from L3),
    assembles a secure prompt, calls the LLM, and returns the raw SQL.

    The generated SQL is NOT validated here — L6 (Multi-Gate Validation)
    performs independent programmatic validation before execution.
    """
    logger.info("Generation request received",
                request_id=request.request_id,
                question_len=len(request.user_question),
                tables=len(request.filtered_schema.tables),
                database_metadata=request.database_metadata)

    response = await run(request, settings)
    return response
