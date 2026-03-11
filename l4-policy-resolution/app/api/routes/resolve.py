"""Resolve API Endpoint for L4 Policy Resolution.

Accepts requests from L3 containing candidate tables,
resolves constraints via L4 rules engine, and returns a signed envelope.
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from app.models.api_models import PermissionEnvelope, PolicyResolveRequest
from app.services.graph_client import get_graph_client, GraphClient
from app.services.orchestrator import PolicyOrchestrator

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/policy", tags=["Resolution"])


def get_orchestrator(client: GraphClient = Depends(get_graph_client)) -> PolicyOrchestrator:
    return PolicyOrchestrator(client)


@router.post("/resolve", response_model=PermissionEnvelope)
async def resolve_policies(
    request: PolicyResolveRequest,
    orchestrator: PolicyOrchestrator = Depends(get_orchestrator),
) -> PermissionEnvelope:
    """Deterministically resolve graph policies for a set of candidate tables."""
    try:
        result = await orchestrator.resolve(request)
        return result
    except Exception as e:
        logger.exception("resolve_endpoint_error", error=str(e))
        # Per spec Section 17: Neo4j down → 503 with retry-after
        if "ServiceUnavailable" in type(e).__name__ or "neo4j" in str(e).lower():
            return JSONResponse(
                status_code=503,
                content={
                    "error": "POLICY_GRAPH_UNAVAILABLE",
                    "message": "Neo4j is unreachable. Cannot resolve policies.",
                },
                headers={"Retry-After": "5"},
            )
        # Per spec: unexpected error → fail-secure DENY-all envelope
        raise HTTPException(
            status_code=500,
            detail={
                "error": "RESOLUTION_ERROR",
                "message": "Unexpected error during conflict resolution. Fail-secure: DENY-all.",
            },
        )
