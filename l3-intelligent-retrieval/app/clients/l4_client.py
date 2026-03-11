"""L4 Policy Resolution client — sends candidates, receives PermissionEnvelope.

L3 calls L4 synchronously within the request lifecycle.
This is a tight coupling by design — policy resolution is not optional.
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from app.auth import create_service_token
from app.config import Settings
from app.models.l4_models import (
    PermissionEnvelope,
    PolicyResolveRequest,
)

logger = structlog.get_logger(__name__)


class L4Client:
    """Async HTTP client for L4 Policy Resolution API."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._http: httpx.AsyncClient | None = None

    async def connect(self) -> None:
        self._http = httpx.AsyncClient(
            base_url=self._settings.l4_base_url,
            timeout=httpx.Timeout(float(self._settings.l4_timeout)),
        )

    async def close(self) -> None:
        if self._http:
            await self._http.aclose()

    def _auth_headers(self) -> dict[str, str]:
        token = create_service_token(
            self._settings.l4_service_id,
            self._settings.l4_service_role,
            self._settings.service_token_secret,
        )
        return {"Authorization": f"Bearer {token}"}

    async def resolve_policies(
        self,
        candidate_table_ids: list[str],
        effective_roles: list[str],
        user_context: dict[str, Any],
        request_id: str = "",
    ) -> PermissionEnvelope:
        """Call L4 to resolve policies for candidate tables.

        This is the primary security gate. If L4 is unreachable,
        fail-secure: raise exception (orchestrator returns 503).
        """
        if not self._http:
            raise RuntimeError("L4 client not connected")

        req = PolicyResolveRequest(
            candidate_table_ids=candidate_table_ids,
            effective_roles=effective_roles,
            user_context=user_context,
            request_id=request_id,
        )

        try:
            resp = await self._http.post(
                "/api/v1/policy/resolve",
                json=req.model_dump(),
                headers=self._auth_headers(),
            )
            resp.raise_for_status()
            body = resp.json()

            # L4 may wrap in its own envelope
            if "data" in body and isinstance(body["data"], dict):
                return PermissionEnvelope(**body["data"])
            return PermissionEnvelope(**body)

        except httpx.HTTPStatusError as exc:
            logger.error(
                "l4_http_error",
                status=exc.response.status_code,
                tables=len(candidate_table_ids),
            )
            raise RuntimeError(
                f"L4 Policy Resolution failed: {exc.response.status_code}"
            ) from exc
        except Exception as exc:
            logger.error("l4_request_failed", error=str(exc))
            raise RuntimeError(f"L4 unreachable: {exc}") from exc

    async def health_check(self) -> bool:
        if not self._http:
            return False
        try:
            resp = await self._http.get("/health")
            return resp.status_code == 200
        except Exception:
            return False
