"""Multi-tier caching service for L3 retrieval pipeline.

Caches:
- question_embedding  (Redis, TTL 15m)
- role_domain_access  (Redis, TTL 5m)
- schema_fragment     (Redis, TTL 5m, role-keyed)
- column_metadata     (in-process, TTL 10m)
- vector_search       (Redis, TTL 60s)
- fk_graph            (in-process, TTL 10m)

All policy-dependent caches include role_set_hash in the key.
"""

from __future__ import annotations

import json
import time
from typing import Any

import structlog

from app.config import Settings

logger = structlog.get_logger(__name__)

_PREFIX = "l3:"


class _LocalCache:
    """Simple in-process LRU cache with TTL."""

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 600) -> None:
        self._store: dict[str, tuple[float, Any]] = {}
        self._max_size = max_size
        self._ttl = ttl_seconds

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        ts, value = entry
        if time.monotonic() - ts > self._ttl:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        # Evict oldest if at capacity
        if len(self._store) >= self._max_size and key not in self._store:
            oldest = min(self._store, key=lambda k: self._store[k][0])
            del self._store[oldest]
        self._store[key] = (time.monotonic(), value)

    def invalidate(self, prefix: str = "") -> int:
        if not prefix:
            count = len(self._store)
            self._store.clear()
            return count
        keys = [k for k in self._store if k.startswith(prefix)]
        for k in keys:
            del self._store[k]
        return len(keys)

    @property
    def size(self) -> int:
        return len(self._store)


class CacheService:
    """Unified cache facade for Redis-backed and local caches."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._redis: Any | None = None

        # Local caches
        self._column_cache = _LocalCache(max_size=5000, ttl_seconds=600)
        self._fk_cache = _LocalCache(max_size=500, ttl_seconds=600)

        # Stats
        self.hits = 0
        self.misses = 0

    async def connect(self) -> None:
        """Connect to Redis."""
        try:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(
                self._settings.redis_url,
                max_connections=self._settings.redis_max_connections,
                decode_responses=True,
            )
            await self._redis.ping()
            logger.info("redis_connected", url=self._settings.redis_url)
        except Exception as exc:
            logger.warning("redis_connect_failed", error=str(exc))
            self._redis = None

    async def close(self) -> None:
        if self._redis:
            await self._redis.close()

    @property
    def redis_available(self) -> bool:
        return self._redis is not None

    # ── Redis-backed caches ─────────────────────────────────

    async def get_embedding(self, cache_key: str) -> list[float] | None:
        return await self._redis_get(f"emb:{cache_key}")

    async def set_embedding(self, cache_key: str, embedding: list[float]) -> None:
        await self._redis_set(
            f"emb:{cache_key}", embedding, ttl=self._settings.embedding_cache_ttl
        )

    async def get_role_domains(self, role_hash: str) -> dict[str, list[str]] | None:
        return await self._redis_get(f"rd:{role_hash}")

    async def set_role_domains(self, role_hash: str, data: dict[str, list[str]]) -> None:
        await self._redis_set(f"rd:{role_hash}", data, ttl=300)

    async def get_schema_fragment(self, key: str) -> Any | None:
        return await self._redis_get(f"sf:{key}")

    async def set_schema_fragment(self, key: str, data: Any) -> None:
        await self._redis_set(f"sf:{key}", data, ttl=300)

    async def get_vector_results(self, key: str) -> list[dict] | None:
        return await self._redis_get(f"vs:{key}")

    async def set_vector_results(self, key: str, data: list[dict]) -> None:
        await self._redis_set(f"vs:{key}", data, ttl=60)

    # ── Local caches ────────────────────────────────────────

    def get_columns_local(self, table_id: str) -> Any | None:
        return self._column_cache.get(table_id)

    def set_columns_local(self, table_id: str, data: Any) -> None:
        self._column_cache.set(table_id, data)

    def get_fk_local(self, table_id: str) -> Any | None:
        return self._fk_cache.get(table_id)

    def set_fk_local(self, table_id: str, data: Any) -> None:
        self._fk_cache.set(table_id, data)

    # ── Invalidation ────────────────────────────────────────

    async def invalidate_all(self) -> int:
        """Nuclear clear — all caches."""
        count = 0
        count += self._column_cache.invalidate()
        count += self._fk_cache.invalidate()
        if self._redis:
            try:
                keys: list[str] = []
                async for key in self._redis.scan_iter(match=f"{_PREFIX}*", count=200):
                    keys.append(key)
                if keys:
                    await self._redis.delete(*keys)
                    count += len(keys)
            except Exception as exc:
                logger.debug("cache_invalidate_all_error", error=str(exc))
        return count

    async def invalidate_prefix(self, prefix: str) -> int:
        count = 0
        if self._redis:
            try:
                keys: list[str] = []
                async for key in self._redis.scan_iter(
                    match=f"{_PREFIX}{prefix}*", count=200
                ):
                    keys.append(key)
                if keys:
                    await self._redis.delete(*keys)
                    count += len(keys)
            except Exception as exc:
                logger.debug("cache_invalidate_error", error=str(exc))
        return count

    # ── Health ──────────────────────────────────────────────

    async def health_check(self) -> bool:
        if not self._redis:
            return False
        try:
            return await self._redis.ping()
        except Exception:
            return False

    @property
    def stats(self) -> dict[str, int]:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "local_column_entries": self._column_cache.size,
            "local_fk_entries": self._fk_cache.size,
        }

    # ── Internal Redis helpers ──────────────────────────────

    async def _redis_get(self, key: str) -> Any | None:
        if not self._redis:
            self.misses += 1
            return None
        try:
            full_key = f"{_PREFIX}{key}"
            raw = await self._redis.get(full_key)
            if raw:
                self.hits += 1
                return json.loads(raw)
            self.misses += 1
            return None
        except Exception as exc:
            logger.debug("cache_get_error", key=key, error=str(exc))
            self.misses += 1
            return None

    async def _redis_set(self, key: str, value: Any, ttl: int = 300) -> None:
        if not self._redis:
            return
        try:
            full_key = f"{_PREFIX}{key}"
            await self._redis.setex(full_key, ttl, json.dumps(value, default=str))
        except Exception as exc:
            logger.debug("cache_set_error", key=key, error=str(exc))
