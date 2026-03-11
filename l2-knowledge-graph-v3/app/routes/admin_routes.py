"""Admin and operational endpoints.

Edge Cases Implemented (Section 15):
  EC-1  Table exists in DB but not in graph → POST /api/v1/admin/crawl/on-demand
  EC-5  Circular role inheritance → pre-write cycle detection in POST /api/v1/admin/roles/add-inheritance
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.auth import ServiceIdentity, require_permission
from app.dependencies import get_container
from app.models.api import (
    APIResponse,
    ClassificationRequest,
    CrawlRequest,
    ReviewItem,
)
from app.models.enums import DatabaseEngine

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


# ── Schema Discovery ───────────────────────────────────────────


@router.post("/crawl", response_model=APIResponse)
async def trigger_crawl(
    request: CrawlRequest,
    _identity: ServiceIdentity = Depends(require_permission("crawl")),
):
    """Trigger a schema discovery crawl for a specific database.

    The crawler connects to the source DB with read-only credentials,
    extracts metadata, diffs against the existing graph, and applies
    inserts/updates/deactivations. Never hard-deletes.
    """
    container = get_container()
    summary = await container.schema_discovery.run_crawl(
        database_name=request.database_name,
        engine=DatabaseEngine(request.engine),
        connection_string=request.connection_string,
        schema_filter=request.schemas or None,
        triggered_by=_identity.service_id,
    )
    return APIResponse(data=summary.model_dump(), meta={"crawled_by": _identity.service_id})


class OnDemandCrawlRequest(BaseModel):
    """EC-1: On-demand re-crawl request for a specific schema."""
    database_name: str
    engine: str
    connection_string: str
    schema_name: str


@router.post("/crawl/on-demand", response_model=APIResponse)
async def trigger_on_demand_crawl(
    request: OnDemandCrawlRequest,
    _identity: ServiceIdentity = Depends(require_permission("crawl")),
):
    """EC-1 (Section 15): On-demand schema re-crawl.

    Called when the query layer discovers a table that exists in the source DB
    but has not yet been catalogued in the graph (e.g., table added after last scheduled crawl).

    Triggers a targeted crawl scoped to one schema rather than a full database scan.
    Queries that reference uncatalogued tables must NOT be executed until the re-crawl completes.
    """
    container = get_container()
    summary = await container.schema_discovery.run_on_demand_crawl_for_schema(
        database_name=request.database_name,
        engine=DatabaseEngine(request.engine),
        connection_string=request.connection_string,
        schema_name=request.schema_name,
        triggered_by=_identity.service_id,
    )
    return APIResponse(
        data=summary.model_dump(),
        meta={
            "crawled_by": _identity.service_id,
            "scope": f"{request.database_name}.{request.schema_name}",
            "trigger": "table_not_in_graph",
        },
    )


# ── Classification Admin ───────────────────────────────────────


@router.post("/classify", response_model=APIResponse)
async def trigger_classification(
    request: ClassificationRequest,
    _identity: ServiceIdentity = Depends(require_permission("classify")),
):
    """Run auto-classification on specified tables (or all unclassified).

    High-confidence matches (>=90%) are auto-approved.
    Lower-confidence results go to the human review queue.
    Ambiguous cases default to HIGHER sensitivity.
    """
    container = get_container()
    summary = await container.classification_engine.classify_columns(
        table_fqns=request.table_fqns or None,
        force_reclassify=request.force_reclassify,
        classifier_id=_identity.service_id,
    )
    return APIResponse(data=summary.model_dump())


@router.get("/reviews/pending", response_model=APIResponse)
async def get_pending_reviews(
    limit: int = Query(100, ge=1, le=1000),
    _identity: ServiceIdentity = Depends(require_permission("review")),
):
    """Return pending classification review items."""
    container = get_container()
    items = await container.audit_repo.get_pending_reviews(limit=limit)
    return APIResponse(data=items, meta={"count": len(items)})


@router.post("/reviews/{review_id}/approve", response_model=APIResponse)
async def approve_review(
    review_id: int,
    _identity: ServiceIdentity = Depends(require_permission("review")),
):
    """Approve a classification suggestion and apply it to the graph."""
    container = get_container()
    try:
        await container.classification_engine.apply_approved_review(
            review_id=review_id, approver=_identity.service_id
        )
    except ValueError as exc:
        return APIResponse(success=False, error=str(exc))
    return APIResponse(data={"review_id": review_id, "status": "approved"})


@router.post("/reviews/{review_id}/reject", response_model=APIResponse)
async def reject_review(
    review_id: int,
    _identity: ServiceIdentity = Depends(require_permission("review")),
):
    """Reject a classification suggestion."""
    container = get_container()
    await container.audit_repo.reject_review(review_id, _identity.service_id)
    return APIResponse(data={"review_id": review_id, "status": "rejected"})


# ── Health Checks ──────────────────────────────────────────────


@router.get("/health-checks", response_model=APIResponse)
async def run_health_checks(
    _identity: ServiceIdentity = Depends(require_permission("health")),
):
    """Run all graph health checks (orphan policies, circular inheritance, etc.)."""
    container = get_container()
    results = await container.health_check.run_all()
    passed_all = all(r.passed for r in results)
    return APIResponse(
        data=[r.model_dump() for r in results],
        meta={"passed_all": passed_all, "total_checks": len(results)},
    )


# ── Embedding Pipeline ─────────────────────────────────────────


@router.post("/embeddings/refresh", response_model=APIResponse)
async def refresh_embeddings(
    force_rebuild: bool = Query(False, description="Force complete rebuild"),
    _identity: ServiceIdentity = Depends(require_permission("admin")),
):
    """Refresh semantic embeddings from current graph metadata.

    If force_rebuild=True, clears all embeddings first.
    Otherwise, only re-embeds changed metadata (hash-based).
    """
    container = get_container()
    if force_rebuild:
        stats = await container.embedding_pipeline.rebuild_all()
    else:
        stats = await container.embedding_pipeline.embed_all_tables()
    return APIResponse(data=stats)


@router.get("/embeddings/search", response_model=APIResponse)
async def search_embeddings(
    q: str = Query(..., min_length=3, description="Semantic search query"),
    limit: int = Query(10, ge=1, le=50),
    _identity: ServiceIdentity = Depends(require_permission("search")),
):
    """Semantic search over table/column descriptions using embeddings."""
    container = get_container()
    results = await container.embedding_pipeline.search_similar(q, limit=limit)
    return APIResponse(data=results, meta={"query": q, "count": len(results)})


# ── Audit Queries ──────────────────────────────────────────────


@router.get("/audit/version", response_model=APIResponse)
async def get_graph_version(
    _identity: ServiceIdentity = Depends(require_permission("read_schema")),
):
    """Return current graph version number and last update info."""
    container = get_container()
    info = await container.audit_repo.get_current_version()
    return APIResponse(data=info)


@router.get("/audit/changes", response_model=APIResponse)
async def get_change_log(
    node_type: str | None = Query(None),
    node_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    _identity: ServiceIdentity = Depends(require_permission("read_schema")),
):
    """Return recent change log entries from the PostgreSQL audit table."""
    container = get_container()
    changes = await container.audit_repo.get_changes(
        node_type=node_type, node_id=node_id, limit=limit
    )
    return APIResponse(data=changes, meta={"count": len(changes)})


# ── Policy Admin ───────────────────────────────────────────────


@router.post("/policies/rollback", response_model=APIResponse)
async def rollback_policy(
    policy_id: str = Query(..., description="Policy ID to roll back"),
    target_version: int = Query(..., ge=1, description="Version number to restore"),
    _identity: ServiceIdentity = Depends(require_permission("write_policy")),
):
    """Roll back a policy to a specific previous version."""
    container = get_container()
    try:
        result = await container.policy_service.rollback_policy(
            policy_id=policy_id,
            target_version=target_version,
            rolled_back_by=_identity.service_id,
        )
    except ValueError as exc:
        return APIResponse(success=False, error=str(exc))
    return APIResponse(data=result.model_dump() if result else None)


# ── Role Hierarchy (EC-5) ─────────────────────────────────────


class AddRoleInheritanceRequest(BaseModel):
    """EC-5: Request to add a INHERITS_FROM edge between two roles."""
    child_role: str
    parent_role: str


@router.post("/roles/add-inheritance", response_model=APIResponse)
async def add_role_inheritance(
    request: AddRoleInheritanceRequest,
    _identity: ServiceIdentity = Depends(require_permission("admin")),
):
    """EC-5 (Section 15): Add a role inheritance link with cycle prevention.

    Before writing the INHERITS_FROM edge, this endpoint queries the graph to detect
    whether the proposed edge would create a circular inheritance path.
    If a cycle would result, the change is BLOCKED and the admin is alerted.

    Safe to call multiple times: uses MERGE so duplicate calls are idempotent.
    """
    container = get_container()

    # EC-5: Cycle detection BEFORE the write
    cycle_check_query = """
        MATCH (child:Role {name: $child}), (parent:Role {name: $parent})
        WITH child, parent
        // Would adding child→parent create a cycle? Check if parent can reach child already.
        OPTIONAL MATCH path = (parent)-[:INHERITS_FROM*1..20]->(child)
        RETURN path IS NOT NULL AS would_cycle
    """
    try:
        records = await container.neo4j.execute_read(
            cycle_check_query,
            {"child": request.child_role, "parent": request.parent_role},
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Graph unavailable during cycle check: {exc}")

    if records and records[0].get("would_cycle"):
        # EC-5: Block the write and alert admin
        raise HTTPException(
            status_code=409,
            detail=(
                f"Adding '{request.child_role}' → '{request.parent_role}' would create "
                f"a circular role inheritance. Change BLOCKED. "
                f"Current path: {request.parent_role} already inherits from {request.child_role}."
            ),
        )

    # Safe to write
    add_edge_query = """
        MATCH (child:Role {name: $child}), (parent:Role {name: $parent})
        MERGE (child)-[:INHERITS_FROM]->(parent)
        RETURN child.name AS child, parent.name AS parent
    """
    result = await container.neo4j.execute_write(add_edge_query,
                                                  {"child": request.child_role,
                                                   "parent": request.parent_role})
    if not result:
        return APIResponse(success=False, error="One or both roles not found in graph")

    return APIResponse(
        data={"child": request.child_role, "parent": request.parent_role, "edge": "INHERITS_FROM"},
        meta={"cycle_checked": True, "blocked": False},
    )
