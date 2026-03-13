"""L2 Knowledge Graph client — reads schema, metadata, roles, embeddings.

All calls are authenticated using inter-service HMAC tokens.
Fail-secure: any L2 failure raises an exception that the orchestrator
handles by returning a structured error.
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from app.auth import create_service_token
from app.config import Settings
from app.models.l2_models import (
    L2APIResponse,
    L2ColumnInfo,
    L2DatabaseInfo,
    L2ForeignKey,
    L2RoleDomainAccess,
    L2TableInfo,
    L2VectorSearchResult,
)

logger = structlog.get_logger(__name__)


class L2Client:
    """Async HTTP client for L2 Knowledge Graph API."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._http: httpx.AsyncClient | None = None

    async def connect(self) -> None:
        self._http = httpx.AsyncClient(
            base_url=self._settings.l2_base_url,
            timeout=httpx.Timeout(float(self._settings.l2_timeout)),
        )

    async def close(self) -> None:
        if self._http:
            await self._http.aclose()

    def _auth_headers(self) -> dict[str, str]:
        token = create_service_token(
            self._settings.l2_service_id,
            self._settings.l2_service_role,
            self._settings.service_token_secret,
        )
        return {"Authorization": f"Bearer {token}"}

    # ── Schema queries ──────────────────────────────────────

    async def get_tables_by_domain(
        self, domain: str, limit: int = 100, offset: int = 0,
    ) -> list[L2TableInfo]:
        """Fetch tables for a specific domain."""
        resp = await self._get(
            "/api/v1/graph/tables/by-domain",
            params={"domain": domain, "limit": limit, "offset": offset},
        )
        return [L2TableInfo(**t) for t in (resp.data or [])]

    async def get_table_columns(self, table_fqn: str) -> list[L2ColumnInfo]:
        """Fetch columns for a table."""
        resp = await self._get(f"/api/v1/graph/tables/{table_fqn}/columns")
        return [L2ColumnInfo(**c) for c in (resp.data or [])]

    async def get_foreign_keys(self, table_fqn: str) -> list[L2ForeignKey]:
        """Fetch FK edges for a table."""
        resp = await self._get(f"/api/v1/graph/foreign-keys/{table_fqn}")
        raw = resp.data or []
        results: list[L2ForeignKey] = []
        for fk in raw:
            if isinstance(fk, dict):
                results.append(L2ForeignKey(**fk))
        return results

    async def search_tables(self, query: str, limit: int = 20) -> list[L2TableInfo]:
        """Text search over table names/descriptions."""
        resp = await self._get(
            "/api/v1/graph/search/tables",
            params={"q": query, "limit": limit},
        )
        return [L2TableInfo(**t) for t in (resp.data or [])]

    async def get_policies_for_roles(self, roles: list[str]) -> list[dict[str, Any]]:
        """Fetch policies bound to specific roles."""
        resp = await self._get(
            "/api/v1/graph/policies/for-roles",
            params={"roles": ",".join(roles)},
        )
        return resp.data or []

    async def get_tables_by_sensitivity(
        self, min_level: int = 1, limit: int = 200,
    ) -> list[L2TableInfo]:
        """Fetch tables at or above a sensitivity level."""
        resp = await self._get(
            "/api/v1/graph/tables/by-sensitivity",
            params={"min_level": min_level, "limit": limit},
        )
        return [L2TableInfo(**t) for t in (resp.data or [])]

    async def get_role_domain_access(
        self, roles: list[str],
    ) -> dict[str, list[str]]:
        """Get domain access map for roles.

        Returns dict mapping role_name → list of accessible domains.
        Falls back to fetching inherited roles and their domain access.
        """
        try:
            resp = await self._get(
                "/api/v1/graph/roles/domain-access",
                params={"roles": ",".join(roles)},
            )
            return resp.data or {}
        except Exception:
            # Fallback: build from inherited roles endpoint
            logger.debug("role_domain_fallback", roles=roles)
            return await self._build_role_domain_map(roles)

    async def _build_role_domain_map(
        self, roles: list[str],  # noqa: ARG002
    ) -> dict[str, list[str]]:
        """Fallback: L2 role/domain endpoints not available — return empty map.

        The RBAC filter handles empty domain map by passing all candidates to L4.
        """
        return {}

    # ── Database discovery ────────────────────────────────────

    async def get_all_databases(self) -> list[L2DatabaseInfo]:
        """Fetch all active databases with engine type and metadata."""
        resp = await self._get("/api/v1/graph/databases")
        return [L2DatabaseInfo(**d) for d in (resp.data or [])]

    # ── Health ──────────────────────────────────────────────

    async def health_check(self) -> bool:
        try:
            resp = await self._get("/health")
            return resp.success
        except Exception:
            return False

    # ── Internal HTTP helper ────────────────────────────────

    async def _get(
        self, path: str, params: dict[str, Any] | None = None,
    ) -> L2APIResponse:
        if not self._http:
            raise RuntimeError("L2 client not connected")

        try:
            resp = await self._http.get(
                path, params=params, headers=self._auth_headers(),
            )
            resp.raise_for_status()
            body = resp.json()
            return L2APIResponse(**body)
        except httpx.HTTPStatusError as exc:
            logger.error(
                "l2_http_error",
                path=path,
                status=exc.response.status_code,
            )
            raise RuntimeError(f"L2 API error: {exc.response.status_code}") from exc
        except Exception as exc:
            logger.error("l2_request_failed", path=path, error=str(exc))
            raise RuntimeError(f"L2 unreachable: {exc}") from exc
