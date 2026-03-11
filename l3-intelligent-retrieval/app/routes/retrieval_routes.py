"""L3 Retrieval API routes.

Endpoints:
- POST /api/v1/retrieval/resolve  — primary retrieval
- GET  /api/v1/retrieval/health   — health check
- POST /api/v1/retrieval/explain  — admin-only debug trace
- POST /api/v1/retrieval/cache/clear — clear caches
- GET  /api/v1/retrieval/stats    — runtime stats
"""

from __future__ import annotations

import time

import structlog
from fastapi import APIRouter, Depends, HTTPException

from app.auth import require_permission, require_service_auth
from app.models.api import (
    APIResponse,
    ExplainRequest,
    HealthResponse,
    RetrievalRequest,
    RetrievalResponse,
    StatsResponse,
)
from app.models.enums import RetrievalErrorCode
from app.models.security import ServiceIdentity
from app.services.orchestrator import RetrievalError

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/retrieval", tags=["retrieval"])


def _get_orchestrator():
    """Get the orchestrator from the app container."""
    from app.dependencies import get_container
    return get_container().orchestrator


def _get_cache():
    from app.dependencies import get_container
    return get_container().cache


def _get_container():
    from app.dependencies import get_container
    return get_container()


# ── POST /resolve ───────────────────────────────────────────


@router.post("/resolve", response_model=RetrievalResponse)
async def resolve(
    request: RetrievalRequest,
    _identity: ServiceIdentity = Depends(require_permission("resolve")),
):
    """Execute the full retrieval pipeline.

    Validates SecurityContext, embeds question, retrieves schema,
    applies RBAC filtering, scopes columns, and returns a
    policy-filtered RetrievalResult for downstream L5 consumption.

    HTTP status mapping (spec §8 / §16):
    - 200: Success
    - 401: Invalid or expired SecurityContext / break-glass TTL exceeded
    - 400: Bad input (invalid question, missing roles, etc.)
    - 503: Embedding service unavailable — L5 must retry, NOT fall back to
           raw schema. Returning 200 here would be a security regression
           because L5 might proceed without a policy-scoped schema.
    """
    orchestrator = _get_orchestrator()

    try:
        result = await orchestrator.resolve(request)
        return RetrievalResponse(success=True, data=result)

    except RetrievalError as exc:
        logger.warning(
            "retrieval_error",
            error_code=exc.code.value,
            message=exc.message,
            status=exc.status,
            user_id=request.security_context.user_id,
        )
        # SECURITY: Propagate the exact HTTP status from RetrievalError.
        # Do NOT flatten all errors to 200 with success=False — callers
        # (L5, API gateways, retry logic) depend on the status code to
        # decide whether to retry (503) or abort (401/400).
        raise HTTPException(
            status_code=exc.status,
            detail={"error_code": exc.code.value, "message": exc.message},
        )
    except Exception as exc:
        logger.error("retrieval_unexpected_error", error=str(exc))
        raise HTTPException(
            status_code=500,
            detail={"error_code": RetrievalErrorCode.INTERNAL_ERROR.value, "message": "Internal retrieval error"},
        )


# ── GET /health ─────────────────────────────────────────────


@router.get("/health", response_model=HealthResponse)
async def health():
    """Health check — no auth required."""
    container = _get_container()
    deps: dict[str, bool] = {}

    try:
        deps["l2_knowledge_graph"] = await container.l2_client.health_check()
    except Exception:
        deps["l2_knowledge_graph"] = False

    try:
        deps["l4_policy"] = await container.l4_client.health_check()
    except Exception:
        deps["l4_policy"] = False

    try:
        deps["redis"] = await container.cache.health_check()
    except Exception:
        deps["redis"] = False

    try:
        deps["pgvector"] = await container.vector_client.health_check()
    except Exception:
        deps["pgvector"] = False

    deps["embedding_client"] = await container.embedding_client.health_check()

    all_ok = all(deps.values())
    return HealthResponse(
        status="ok" if all_ok else "degraded",
        dependencies=deps,
    )


# ── POST /explain ───────────────────────────────────────────


@router.post("/explain", response_model=APIResponse)
async def explain(
    request: ExplainRequest,
    _identity: ServiceIdentity = Depends(require_permission("admin")),
):
    """Admin-only: explain the retrieval pipeline execution.

    Returns detailed trace of each pipeline stage.
    Only available to admin-role services.
    """
    orchestrator = _get_orchestrator()

    try:
        # Run the full pipeline
        from app.models.api import RetrievalRequest as RR
        full_request = RR(
            question=request.question,
            security_context=request.security_context,
            request_id=request.request_id,
        )
        result = await orchestrator.resolve(full_request)

        # Build explain output with pipeline details
        explain_data = {
            "request_id": result.request_id,
            "preprocessed_question": result.preprocessed_question,
            "intent": result.intent.model_dump(),
            "tables_found": len(result.filtered_schema),
            "denied_count": result.denied_tables_count,
            "join_edges": len(result.join_graph.edges),
            "nl_rules": result.nl_policy_rules,
            "metadata": result.retrieval_metadata.model_dump(),
            "table_scores": [
                {
                    "table": t.table_id,
                    "score": t.relevance_score,
                    "visible_cols": len(t.visible_columns),
                    "masked_cols": len(t.masked_columns),
                    "hidden_cols": t.hidden_column_count,
                }
                for t in result.filtered_schema
            ],
        }
        return APIResponse(success=True, data=explain_data)

    except RetrievalError as exc:
        return APIResponse(
            success=False,
            error=exc.message,
            error_code=exc.code,
        )
    except Exception as exc:
        logger.error("explain_error", error=str(exc))
        return APIResponse(
            success=False,
            error="Explain failed",
            error_code=RetrievalErrorCode.INTERNAL_ERROR,
        )


# ── POST /cache/clear ──────────────────────────────────────


@router.post("/cache/clear", response_model=APIResponse)
async def clear_cache(
    _identity: ServiceIdentity = Depends(require_permission("admin")),
):
    """Clear all L3 caches. Admin-only."""
    cache = _get_cache()
    cleared = await cache.invalidate_all()
    return APIResponse(
        success=True,
        data={"keys_cleared": cleared},
    )


# ── GET /stats ──────────────────────────────────────────────


@router.get("/stats", response_model=APIResponse)
async def stats(
    _identity: ServiceIdentity = Depends(require_permission("stats")),
):
    """Runtime statistics."""
    container = _get_container()
    return APIResponse(
        success=True,
        data=container.cache.stats,
    )
