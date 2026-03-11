"""API access audit logging middleware.

Logs every API request (service_id, endpoint, method, status, latency)
to the PostgreSQL api_access_log table for compliance audit trail.
"""

from __future__ import annotations

import time

import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

logger = structlog.get_logger(__name__)


class APIAccessAuditMiddleware(BaseHTTPMiddleware):
    """Log API access to PostgreSQL audit table."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Skip health/readiness to avoid log flood
        if request.url.path in ("/health", "/ready"):
            return await call_next(request)

        start = time.monotonic()
        response = await call_next(request)
        elapsed_ms = (time.monotonic() - start) * 1000

        # Extract service_id from Authorization header (best-effort)
        service_id = "anonymous"
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            parts = token.split("|")
            if len(parts) >= 4:
                service_id = parts[0]

        # Write to PostgreSQL audit table asynchronously
        try:
            container = request.app.state.container
            if hasattr(container, "audit_repo") and container.audit_repo:
                await container.audit_repo.log_api_access(
                    service_id=service_id,
                    endpoint=request.url.path,
                    method=request.method,
                    status_code=response.status_code,
                    latency_ms=round(elapsed_ms, 2),
                )
        except Exception as exc:
            # Never let audit logging failure break the request
            logger.debug("api_access_log_failed", error=str(exc))

        return response
