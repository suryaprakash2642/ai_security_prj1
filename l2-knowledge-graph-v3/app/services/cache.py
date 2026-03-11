"""Redis-based read cache with TTL for hot graph query paths.

Provides short-lived caching (default 5 min) for read-heavy endpoints.
Cache is invalidated on write operations via explicit key eviction.
Falls back gracefully to direct graph queries on Redis outage.
"""

from __future__ import annotations

import json
from typing import Any

import redis.asyncio as redis
import structlog

from app.config import Settings

logger = structlog.get_logger(__name__)

_PREFIX = "l2:cache:"


class CacheService:
    """Thin async Redis wrapper with graceful degradation."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: redis.Redis | None = None
        self._ttl = settings.cache_ttl_seconds

    async def connect(self) -> None:
        try:
            self._client = redis.from_url(
                self._settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=3,
            )
            await self._client.ping()
            logger.info("redis_connected")
        except Exception as exc:
            logger.warning("redis_connect_failed", error=str(exc))
            self._client = None

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()

    async def get(self, key: str) -> Any | None:
        """Return cached value or None on miss/error."""
        if not self._client:
            return None
        try:
            full_key = f"{_PREFIX}{key}"
            raw = await self._client.get(full_key)
            if raw:
                return json.loads(raw)
        except Exception as exc:
            logger.debug("cache_get_error", error=str(exc))
        return None

    async def set(self, key: str, value: Any) -> None:
        """Store a value with TTL. Silently fails on Redis errors."""
        if not self._client:
            return
        try:
            full_key = f"{_PREFIX}{key}"
            await self._client.setex(full_key, self._ttl, json.dumps(value, default=str))
        except Exception as exc:
            logger.debug("cache_set_error", error=str(exc))

    async def invalidate(self, key_prefix: str) -> None:
        """Delete all keys matching a prefix. Called after write operations."""
        if not self._client:
            return
        try:
            pattern = f"{_PREFIX}{key_prefix}*"
            keys = []
            async for key in self._client.scan_iter(match=pattern, count=100):
                keys.append(key)
            if keys:
                await self._client.delete(*keys)
                logger.info("cache_invalidated", prefix=key_prefix, keys_deleted=len(keys))
        except Exception as exc:
            logger.debug("cache_invalidate_error", error=str(exc))

    async def invalidate_all(self) -> None:
        """Nuclear option — clear entire L2 cache."""
        if not self._client:
            return
        try:
            pattern = f"{_PREFIX}*"
            keys = []
            async for key in self._client.scan_iter(match=pattern, count=200):
                keys.append(key)
            if keys:
                await self._client.delete(*keys)
                logger.info("cache_full_invalidation", keys_deleted=len(keys))
        except Exception as exc:
            logger.debug("cache_invalidate_all_error", error=str(exc))

    @property
    def available(self) -> bool:
        return self._client is not None

    async def health_check(self) -> bool:
        if not self._client:
            return False
        try:
            return await self._client.ping()
        except Exception:
            return False
