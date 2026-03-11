"""Resolve API Endpoint for L4 Policy Resolution.

Accepts requests from L3 containing candidate tables, 
resolves constraints via L4 rules engine, and returns a signed envelope.
"""

from fastapi import APIRouter, Depends

from app.models.api_models import PermissionEnvelope, PolicyResolveRequest
from app.services.graph_client import get_graph_client, GraphClient
from app.services.orchestrator import PolicyOrchestrator

router = APIRouter(prefix="/policy", tags=["Resolution"])


def get_orchestrator(client: GraphClient = Depends(get_graph_client)) -> PolicyOrchestrator:
    return PolicyOrchestrator(client)


@router.post("/resolve", response_model=PermissionEnvelope)
async def resolve_policies(
    request: PolicyResolveRequest,
    orchestrator: PolicyOrchestrator = Depends(get_orchestrator)
) -> PermissionEnvelope:
    """Deterministically resolve graph policies for a set of candidate tables."""
    return await orchestrator.resolve(request)
