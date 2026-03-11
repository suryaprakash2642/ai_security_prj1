"""Classification query endpoints — PII, regulation tags, masking rules.

Consumed by L6 Validation Layer for sensitivity checks and masking enforcement.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.auth import ServiceIdentity, require_permission
from app.dependencies import get_container
from app.models.api import APIResponse

router = APIRouter(prefix="/api/v1/graph", tags=["classification"])


@router.get("/columns/pii", response_model=APIResponse)
async def get_pii_columns(
    table_fqn: str | None = Query(None, description="Filter by table FQN (optional)"),
    pii_type: str | None = Query(None, description="Filter by PII type (optional)"),
    limit: int = Query(200, ge=1, le=1000, description="Max results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    _identity: ServiceIdentity = Depends(require_permission("read_classification")),
):
    """Return all PII-flagged columns, optionally filtered by table or PII type."""
    container = get_container()
    columns = await container.graph_reader.get_pii_columns(
        table_fqn=table_fqn, pii_type=pii_type, limit=limit, offset=offset
    )
    return APIResponse(
        data=[c.model_dump() for c in columns],
        meta={"count": len(columns), "limit": limit, "offset": offset},
    )


@router.get("/tables/regulated-by", response_model=APIResponse)
async def get_tables_regulated_by(
    regulation: str = Query(..., description="Regulation code (e.g., HIPAA, DPDPA_2023)"),
    _identity: ServiceIdentity = Depends(require_permission("read_classification")),
):
    """Return all tables subject to a specific regulation."""
    container = get_container()
    tables = await container.graph_reader.get_tables_regulated_by(regulation)
    return APIResponse(
        data=[t.model_dump() for t in tables],
        meta={"count": len(tables), "regulation": regulation},
    )


@router.get("/masking-rules/{table_fqn}", response_model=APIResponse)
async def get_masking_rules(
    table_fqn: str,
    _identity: ServiceIdentity = Depends(require_permission("read_classification")),
):
    """Return masking rules for all columns of a given table."""
    container = get_container()
    cached = await container.cache.get(f"masking:{table_fqn}")
    if cached:
        return APIResponse(data=cached)

    rules = await container.graph_reader.get_masking_rules(table_fqn)
    data = [r.model_dump() for r in rules]
    await container.cache.set(f"masking:{table_fqn}", data)
    return APIResponse(data=data, meta={"count": len(data)})


@router.get("/roles/{role_name}/inherited", response_model=APIResponse)
async def get_inherited_roles(
    role_name: str,
    _identity: ServiceIdentity = Depends(require_permission("read_schema")),
):
    """Return the full inheritance chain for a role (used by L1)."""
    container = get_container()
    roles = await container.graph_reader.get_inherited_roles(role_name)
    return APIResponse(data=roles, meta={"role": role_name, "depth": len(roles)})


@router.get("/roles/{role_name}/domains", response_model=APIResponse)
async def get_role_domains(
    role_name: str,
    _identity: ServiceIdentity = Depends(require_permission("read_schema")),
):
    """Return domains a role has ACCESSES_DOMAIN relationships with."""
    container = get_container()
    domains = await container.graph_reader.get_role_domains(role_name)
    return APIResponse(data=domains, meta={"role": role_name})
