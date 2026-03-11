"""Policy query and simulation endpoints.

Consumed primarily by L4 Policy Resolution Layer.
Supports role-based policy lookup, table-specific policies,
join restriction checks, and policy simulation.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.auth import ServiceIdentity, require_permission
from app.dependencies import get_container
from app.models.api import APIResponse, PolicySimulateRequest

router = APIRouter(prefix="/api/v1/graph/policies", tags=["policies"])


@router.get("/for-roles", response_model=APIResponse)
async def get_policies_for_roles(
    roles: str = Query(..., description="Comma-separated role names"),
    include_inherited: bool = Query(True, description="Include inherited role policies"),
    _identity: ServiceIdentity = Depends(require_permission("read_policy")),
):
    """Return all active policies applicable to the given role(s).

    If include_inherited is True, traverses the INHERITS_FROM hierarchy.
    """
    container = get_container()
    role_list = [r.strip() for r in roles.split(",") if r.strip()]
    if not role_list:
        return APIResponse(success=False, error="At least one role is required")

    policies = await container.graph_reader.get_policies_for_roles(
        role_list, include_inherited=include_inherited
    )
    return APIResponse(
        data=[p.model_dump() for p in policies],
        meta={"count": len(policies), "queried_roles": role_list},
    )


@router.get("/for-table", response_model=APIResponse)
async def get_policies_for_table(
    table_fqn: str = Query(..., description="Fully-qualified table name"),
    _identity: ServiceIdentity = Depends(require_permission("read_policy")),
):
    """Return all active policies governing a specific table."""
    container = get_container()
    policies = await container.graph_reader.get_policies_for_table(table_fqn)
    return APIResponse(
        data=[p.model_dump() for p in policies],
        meta={"count": len(policies), "table": table_fqn},
    )


@router.get("/join-restrictions", response_model=APIResponse)
async def get_join_restrictions(
    roles: str = Query(..., description="Comma-separated role names"),
    _identity: ServiceIdentity = Depends(require_permission("read_policy")),
):
    """Return all active join restrictions applicable to the given roles."""
    container = get_container()
    role_list = [r.strip() for r in roles.split(",") if r.strip()]
    restrictions = await container.graph_reader.get_join_restrictions(role_list)
    return APIResponse(
        data=[r.model_dump() for r in restrictions],
        meta={"count": len(restrictions)},
    )


@router.post("/simulate", response_model=APIResponse)
async def simulate_policy(
    request: PolicySimulateRequest,
    _identity: ServiceIdentity = Depends(require_permission("simulate")),
):
    """Simulate policy evaluation for given roles against specified tables.

    Resolution order:
    1. HARD DENY (substance_abuse_records) → immediate deny
    2. Explicit DENY → deny with reason
    3. MASK → allow with masked columns
    4. FILTER → allow with conditions
    5. ALLOW → allow
    6. No match → DENY (deny-by-default)
    """
    container = get_container()
    results = await container.policy_service.simulate(request)
    return APIResponse(
        data=[r.model_dump() for r in results],
        meta={"roles": request.roles, "tables_checked": len(request.table_fqns)},
    )


@router.get("/hard-deny-tables", response_model=APIResponse)
async def get_hard_deny_tables(
    _identity: ServiceIdentity = Depends(require_permission("read_policy")),
):
    """Return all table FQNs that are under hard-deny protection."""
    container = get_container()
    tables = await container.graph_reader.get_hard_deny_tables()
    return APIResponse(data=tables, meta={"count": len(tables)})
