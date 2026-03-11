"""Resource Governor — enforces execution limits (timeout, rows, memory).

Used as a context manager around query result streaming.
"""

from __future__ import annotations

import time

import structlog

logger = structlog.get_logger(__name__)

# Approximate bytes per row for memory estimation (conservative)
_BYTES_PER_CELL_EST = 64


class ResourceLimitExceeded(Exception):
    """Raised when a resource limit is exceeded during execution."""
    def __init__(self, limit_type: str, detail: str = ""):
        self.limit_type = limit_type
        self.detail = detail
        super().__init__(f"{limit_type}: {detail}")


class ResourceGovernor:
    """Tracks and enforces resource limits during result streaming.

    Usage:
        gov = ResourceGovernor(timeout_s=30, max_rows=1000, max_memory_mb=100)
        gov.start()
        for row in cursor:
            gov.check_row(len(row))
            results.append(row)
        gov.finalize()
    """

    def __init__(
        self,
        timeout_seconds: int = 30,
        max_rows: int = 10_000,
        max_memory_mb: int = 100,
        max_result_size_mb: int = 50,
        btg_active: bool = False,
        # BTG elevated limits
        btg_timeout_seconds: int = 60,
        btg_max_rows: int = 50_000,
        btg_max_memory_mb: int = 250,
    ):
        if btg_active:
            self.timeout_seconds = btg_timeout_seconds
            self.max_rows = btg_max_rows
            self.max_memory_mb = btg_max_memory_mb
        else:
            self.timeout_seconds = timeout_seconds
            self.max_rows = max_rows
            self.max_memory_mb = max_memory_mb

        self.max_result_size_mb = max_result_size_mb
        self.btg_active = btg_active

        self._row_count = 0
        self._estimated_memory_bytes = 0
        self._start_time: float | None = None
        self._truncated = False

    def start(self) -> None:
        self._start_time = time.monotonic()

    def elapsed_seconds(self) -> float:
        if self._start_time is None:
            return 0.0
        return time.monotonic() - self._start_time

    def check_timeout(self) -> None:
        """Raise ResourceLimitExceeded if timeout exceeded."""
        if self._start_time is None:
            return
        elapsed = time.monotonic() - self._start_time
        if elapsed > self.timeout_seconds:
            raise ResourceLimitExceeded(
                "QUERY_TIMEOUT",
                f"Query exceeded {self.timeout_seconds}s timeout "
                f"(elapsed: {elapsed:.1f}s)",
            )

    def check_row(self, num_columns: int) -> None:
        """Call after each row is fetched. Raises if limits exceeded."""
        self.check_timeout()

        self._row_count += 1
        self._estimated_memory_bytes += num_columns * _BYTES_PER_CELL_EST

        if self._row_count > self.max_rows:
            self._truncated = True
            raise ResourceLimitExceeded(
                "ROW_LIMIT_EXCEEDED",
                f"Row limit of {self.max_rows} exceeded",
            )

        mem_mb = self._estimated_memory_bytes / (1024 * 1024)
        if mem_mb > self.max_memory_mb:
            raise ResourceLimitExceeded(
                "MEMORY_EXCEEDED",
                f"Memory cap of {self.max_memory_mb}MB exceeded "
                f"(estimated: {mem_mb:.1f}MB)",
            )

    @property
    def row_count(self) -> int:
        return self._row_count

    @property
    def memory_mb(self) -> float:
        return self._estimated_memory_bytes / (1024 * 1024)

    @property
    def truncated(self) -> bool:
        return self._truncated

    def finalize(self) -> dict:
        """Returns summary metrics."""
        return {
            "rows_fetched": self._row_count,
            "estimated_memory_mb": round(self.memory_mb, 2),
            "elapsed_seconds": round(self.elapsed_seconds(), 3),
            "truncated": self._truncated,
            "btg_active": self.btg_active,
        }
