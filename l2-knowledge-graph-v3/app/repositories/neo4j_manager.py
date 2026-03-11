"""Neo4j async driver manager with read/write account separation, TLS enforcement,
and EC-4 degraded-mode handling (Section 15).

Edge case EC-4:
  - When Neo4j goes down, the manager serves the most recent cached result for up to 10 seconds.
  - The caller receives a DEGRADED_MODE flag alongside the cached data.
  - After 60 seconds without a live response, ALL read requests raise
    DegradedModeExpiredError — policy data must never be served stale beyond 60s.
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

import structlog
from neo4j import AsyncDriver, AsyncGraphDatabase, AsyncManagedTransaction, AsyncSession

from app.config import Settings

logger = structlog.get_logger(__name__)

# EC-4: Degraded-mode windows
_DEGRADED_WARM_WINDOW_S: float = 10.0   # serve from cache (with DEGRADED_MODE flag)
_DEGRADED_FAIL_WINDOW_S: float = 60.0   # hard fail after this many seconds stale


class DegradedModeExpiredError(RuntimeError):
    """Raised when Neo4j is unavailable and the 60-second stale window has expired."""


class Neo4jManager:
    """Manages two Neo4j driver instances: one read-only, one write-capable.

    - Read driver uses `pipeline_reader` credentials (or equivalent)
    - Write driver uses `schema_writer` credentials (or equivalent)
    - All connections enforce TLS in production
    - Downstream API endpoints only ever get read sessions
    - EC-4: Failed reads use a warm cache (10s) then fail hard (60s)
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._read_driver: AsyncDriver | None = None
        self._write_driver: AsyncDriver | None = None
        # EC-4: Degraded-mode state
        self._last_live_ts: float = 0.0           # last successful live read
        self._query_cache: dict[str, list[dict[str, Any]]] = {}  # key → last result

    async def connect(self) -> None:
        """Initialize both driver pools."""
        common_kwargs: dict[str, Any] = {
            "max_connection_pool_size": self._settings.neo4j_max_pool_size,
            "connection_acquisition_timeout": 30,
            "max_transaction_retry_time": 10,
        }

        # TLS enforcement: only add encrypted/trusted_certificates kwargs when using
        # plain bolt:// or neo4j:// schemes. The +s / +ssc variants encode TLS in the
        # URI scheme itself and the driver raises ConfigurationError if these kwargs
        # are passed alongside them (e.g. neo4j+s://, bolt+s://).
        _tls_in_uri = any(
            self._settings.neo4j_uri.startswith(prefix)
            for prefix in ("bolt+s://", "bolt+ssc://", "neo4j+s://", "neo4j+ssc://")
        )
        if not _tls_in_uri and (self._settings.neo4j_encrypted or self._settings.is_production):
            from neo4j import TrustCustomCAs, TrustSystemCAs

            common_kwargs["encrypted"] = True
            if self._settings.neo4j_ca_cert_path:
                common_kwargs["trusted_certificates"] = TrustCustomCAs(
                    self._settings.neo4j_ca_cert_path
                )
            else:
                common_kwargs["trusted_certificates"] = TrustSystemCAs()

        self._read_driver = AsyncGraphDatabase.driver(
            self._settings.neo4j_uri,
            auth=(self._settings.neo4j_read_user, self._settings.neo4j_read_password),
            **common_kwargs,
        )
        self._write_driver = AsyncGraphDatabase.driver(
            self._settings.neo4j_uri,
            auth=(self._settings.neo4j_write_user, self._settings.neo4j_write_password),
            **common_kwargs,
        )

        # Verify connectivity
        await self._read_driver.verify_connectivity()
        await self._write_driver.verify_connectivity()
        logger.info("neo4j_connected", uri=self._settings.neo4j_uri)

    async def close(self) -> None:
        """Shutdown both driver pools."""
        if self._read_driver:
            await self._read_driver.close()
        if self._write_driver:
            await self._write_driver.close()
        logger.info("neo4j_disconnected")

    @asynccontextmanager
    async def read_session(self) -> AsyncIterator[AsyncSession]:
        """Yield a read-only session from the read driver."""
        if not self._read_driver:
            raise RuntimeError("Neo4j read driver not initialized")
        async with self._read_driver.session(
            database=self._settings.neo4j_database,
            default_access_mode="READ",
        ) as session:
            yield session

    @asynccontextmanager
    async def write_session(self) -> AsyncIterator[AsyncSession]:
        """Yield a write session from the write driver.
        Only admin/batch services should use this.
        """
        if not self._write_driver:
            raise RuntimeError("Neo4j write driver not initialized")
        async with self._write_driver.session(
            database=self._settings.neo4j_database,
            default_access_mode="WRITE",
        ) as session:
            yield session

    async def execute_read(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a parameterized read query and return records as dicts.

        EC-4 Degraded Mode:
          On Neo4j failure, serves cached results for up to WARM_WINDOW_S (10s) with
          a DEGRADED_MODE sentinel injected. Hard-fails after FAIL_WINDOW_S (60s).
        """
        cache_key = f"{query}::{sorted((parameters or {}).items())}"
        try:
            async with self.read_session() as session:
                result = await session.run(query, parameters or {})
                records = [record.data() async for record in result]
                # Update live timestamp and cache result
                self._last_live_ts = time.monotonic()
                self._query_cache[cache_key] = records
                return records
        except Exception as exc:
            staleness = time.monotonic() - self._last_live_ts
            cached = self._query_cache.get(cache_key)

            if staleness <= _DEGRADED_WARM_WINDOW_S and cached is not None:
                # EC-4: Serve from warm cache with DEGRADED_MODE flag
                logger.warning(
                    "neo4j_degraded_mode_warm_cache",
                    staleness_s=round(staleness, 2),
                    max_warm_s=_DEGRADED_WARM_WINDOW_S,
                    query=query[:80],
                    error=str(exc),
                )
                return [{**row, "__DEGRADED_MODE": True} for row in cached]

            elif staleness <= _DEGRADED_FAIL_WINDOW_S and cached is not None:
                # EC-4: Beyond warm window but within fail window — serve cache but warn loudly
                logger.error(
                    "neo4j_degraded_mode_stale_cache",
                    staleness_s=round(staleness, 2),
                    max_fail_s=_DEGRADED_FAIL_WINDOW_S,
                    query=query[:80],
                    error=str(exc),
                )
                return [{**row, "__DEGRADED_MODE": True, "__STALE_WARNING": True} for row in cached]

            else:
                # EC-4: Beyond 60s — hard fail; stale policy data must NOT be served
                logger.critical(
                    "neo4j_degraded_mode_expired_hard_fail",
                    staleness_s=round(staleness, 2),
                    query=query[:80],
                    error=str(exc),
                )
                raise DegradedModeExpiredError(
                    f"Neo4j unavailable for {staleness:.0f}s — exceeds 60s policy safety window. "
                    f"Refusing to serve stale data. Original error: {exc}"
                ) from exc

    async def execute_write(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a parameterized write query and return records as dicts."""
        async with self.write_session() as session:
            result = await session.run(query, parameters or {})
            records = [record.data() async for record in result]
            return records

    async def execute_write_tx(
        self,
        queries: list[tuple[str, dict[str, Any]]],
    ) -> None:
        """Execute multiple write queries in a single transaction."""
        async with self.write_session() as session:

            async def _tx_work(tx: AsyncManagedTransaction) -> None:
                for query, params in queries:
                    await tx.run(query, params)

            await session.execute_write(_tx_work)

    async def health_check(self) -> bool:
        """Return True if read driver can execute a simple query."""
        try:
            records = await self.execute_read("RETURN 1 AS health")
            return len(records) == 1 and records[0].get("health") == 1
        except Exception as exc:
            logger.error("neo4j_health_check_failed", error=str(exc))
            return False
