"""Schema query endpoints — parameterized, read-only.

Consumed by L3 Retrieval, L6 Validation, L8 Audit.
All queries go through GraphReadRepository — no raw Cypher.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.auth import ServiceIdentity, require_permission
from app.dependencies import get_container
from app.models.api import APIResponse, ColumnResponse, ForeignKeyResponse, TableResponse

router = APIRouter(prefix="/api/v1/graph", tags=["schema"])


@router.get("/tables/by-domain", response_model=APIResponse)
async def get_tables_by_domain(
    domain: str = Query(..., min_length=1, description="Domain name to filter tables"),
    limit: int = Query(100, ge=1, le=500, description="Max results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    _identity: ServiceIdentity = Depends(require_permission("read_schema")),
):
    """Return all active tables belonging to a given domain."""
    container = get_container()
    cached = await container.cache.get(f"tables:domain:{domain}:L{limit}:O{offset}")
    if cached:
        return APIResponse(data=cached)

    tables = await container.graph_reader.get_tables_by_domain(domain, limit=limit, offset=offset)
    data = [t.model_dump() for t in tables]
    await container.cache.set(f"tables:domain:{domain}:L{limit}:O{offset}", data)
    return APIResponse(data=data, meta={"count": len(data), "limit": limit, "offset": offset})


@router.get("/tables/{table_fqn}/columns", response_model=APIResponse)
async def get_table_columns(
    table_fqn: str,
    _identity: ServiceIdentity = Depends(require_permission("read_schema")),
):
    """Return all columns for a given table (by fully-qualified name)."""
    container = get_container()
    cached = await container.cache.get(f"columns:{table_fqn}")
    if cached:
        return APIResponse(data=cached)

    columns = await container.graph_reader.get_table_columns(table_fqn)
    data = [c.model_dump() for c in columns]
    await container.cache.set(f"columns:{table_fqn}", data)
    return APIResponse(data=data, meta={"count": len(data)})


@router.get("/tables/by-sensitivity", response_model=APIResponse)
async def get_tables_by_sensitivity(
    min_level: int = Query(3, ge=1, le=5, description="Minimum sensitivity level (1-5)"),
    limit: int = Query(100, ge=1, le=500, description="Max results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    _identity: ServiceIdentity = Depends(require_permission("read_schema")),
):
    """Return tables with sensitivity at or above the specified level."""
    container = get_container()
    tables = await container.graph_reader.get_tables_by_sensitivity(
        min_level, limit=limit, offset=offset
    )
    return APIResponse(
        data=[t.model_dump() for t in tables],
        meta={"count": len(tables), "limit": limit, "offset": offset},
    )


@router.get("/foreign-keys/{table_fqn}", response_model=APIResponse)
async def get_foreign_keys(
    table_fqn: str,
    _identity: ServiceIdentity = Depends(require_permission("read_schema")),
):
    """Return all foreign key relationships for a table."""
    container = get_container()
    cached = await container.cache.get(f"fks:{table_fqn}")
    if cached:
        return APIResponse(data=cached)

    fks = await container.graph_reader.get_foreign_keys(table_fqn)
    data = [fk.model_dump() for fk in fks]
    await container.cache.set(f"fks:{table_fqn}", data)
    return APIResponse(data=data, meta={"count": len(data)})


@router.get("/search/tables", response_model=APIResponse)
async def search_tables(
    q: str = Query(..., min_length=2, description="Full-text search query"),
    limit: int = Query(20, ge=1, le=100),
    _identity: ServiceIdentity = Depends(require_permission("search")),
):
    """Full-text search over table names and descriptions."""
    container = get_container()
    tables = await container.graph_reader.search_tables(q, limit=limit)
    return APIResponse(data=[t.model_dump() for t in tables], meta={"count": len(tables)})


@router.get("/tables/{table_fqn}/info", response_model=APIResponse)
async def get_table_info(
    table_fqn: str,
    _identity: ServiceIdentity = Depends(require_permission("read_schema")),
):
    """Get detailed info for a single table including domain and regulations."""
    container = get_container()
    tables = await container.graph_reader.search_tables(table_fqn, limit=1)
    if not tables:
        return APIResponse(success=False, error=f"Table '{table_fqn}' not found")
    return APIResponse(data=tables[0].model_dump())
