"""Audit log query endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.models.api import AuditQueryRequest, AuditQueryResponse
from app.services import audit_store

router = APIRouter(prefix="/api/v1/audit", tags=["query"])


@router.post("/query", response_model=AuditQueryResponse)
async def query_events(req: AuditQueryRequest) -> AuditQueryResponse:
    """Query the immutable audit log with optional filters, pagination, and sorting."""
    f = req.filters
    tr = req.time_range
    events, total = audit_store.query(
        from_time=tr.from_time if tr else None,
        to_time=tr.to_time if tr else None,
        source_layers=[layer for layer in f.source_layer] if f.source_layer else None,
        severities=[s for s in f.severity] if f.severity else None,
        user_id=f.user_id,
        event_types=f.event_type,
        request_id=f.request_id,
        btg_active=f.btg_active,
        sort_order=req.sort.order,
        offset=req.pagination.offset,
        limit=req.pagination.limit,
    )
    return AuditQueryResponse(
        events=events,
        total=total,
        offset=req.pagination.offset,
        limit=req.pagination.limit,
    )


@router.get("/replay/{request_id}")
async def replay_pipeline(request_id: str) -> dict:
    """Reconstruct the full pipeline execution for a given request_id."""
    events = audit_store.get_by_request_id(request_id)
    return {
        "request_id": request_id,
        "event_count": len(events),
        "layers_present": sorted({e.source_layer for e in events}),
        "events": [e.model_dump() for e in events],
    }


@router.get("/integrity/{source_layer}")
async def verify_chain(source_layer: str) -> dict:
    """Verify hash chain integrity for the given source layer."""
    valid, detail = audit_store.verify_hash_chain(source_layer.upper())
    return {
        "source_layer": source_layer.upper(),
        "valid": valid,
        "detail": detail,
    }
