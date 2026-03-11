"""Per-service-ID rate limiting middleware using in-memory sliding window.

Enforces `rate_limit_per_minute` from Settings. Falls back to IP-based
tracking for unauthenticated requests (which will be rejected by auth
anyway, but this prevents brute-force token guessing).
"""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Any

import structlog
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.config import get_settings

logger = structlog.get_logger(__name__)


class _SlidingWindow:
    """Per-key sliding window counter."""

    def __init__(self, window_seconds: int = 60) -> None:
        self._window = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key: str, max_requests: int) -> bool:
        now = time.monotonic()
        cutoff = now - self._window

        # Prune old entries
        entries = self._requests[key]
        self._requests[key] = [t for t in entries if t > cutoff]

        if len(self._requests[key]) >= max_requests:
            return False

        self._requests[key].append(now)
        return True

    @property
    def active_keys(self) -> int:
        return len(self._requests)


_limiter = _SlidingWindow(window_seconds=60)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests exceeding the per-minute rate limit per service identity."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Skip health/readiness endpoints
        if request.url.path in ("/health", "/ready"):
            return await call_next(request)

        settings = get_settings()
        max_rpm = settings.rate_limit_per_minute

        # Extract identity key from Authorization header (best-effort)
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            parts = token.split("|")
            key = parts[0] if len(parts) >= 4 else request.client.host if request.client else "unknown"
        else:
            key = request.client.host if request.client else "unknown"

        if not _limiter.is_allowed(key, max_rpm):
            logger.warning("rate_limit_exceeded", key=key, limit=max_rpm)
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "error": f"Rate limit exceeded ({max_rpm} requests/minute)",
                    "data": None,
                    "meta": {},
                },
                headers={"Retry-After": "60"},
            )

        return await call_next(request)
