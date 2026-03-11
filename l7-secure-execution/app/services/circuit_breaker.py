"""Per-database circuit breaker implementation.

States:
  CLOSED   → normal operation; errors counted in rolling 60s window
  OPEN     → all requests immediately rejected (503)
  HALF_OPEN → one probe request allowed; success → CLOSED, failure → OPEN
"""

from __future__ import annotations

import time
from collections import deque
from threading import Lock

import structlog

from app.models.enums import CircuitBreakerState

logger = structlog.get_logger(__name__)


class CircuitBreaker:
    """Thread-safe per-database circuit breaker."""

    def __init__(
        self,
        database_id: str,
        error_threshold: float = 0.5,
        cooldown_seconds: int = 30,
        window_seconds: int = 60,
        min_requests: int = 5,
    ):
        self.database_id = database_id
        self.error_threshold = error_threshold
        self.cooldown_seconds = cooldown_seconds
        self.window_seconds = window_seconds
        self.min_requests = min_requests

        self._state = CircuitBreakerState.CLOSED
        self._open_at: float | None = None
        # Timestamps of recent requests: (timestamp, is_error)
        self._request_window: deque[tuple[float, bool]] = deque()
        self._probe_in_flight = False
        self._lock = Lock()

    @property
    def state(self) -> CircuitBreakerState:
        with self._lock:
            self._maybe_transition_to_half_open()
            return self._state

    def _maybe_transition_to_half_open(self) -> None:
        """Call with lock held. Transition OPEN → HALF_OPEN after cooldown."""
        if (
            self._state == CircuitBreakerState.OPEN
            and self._open_at is not None
            and time.monotonic() - self._open_at >= self.cooldown_seconds
            and not self._probe_in_flight
        ):
            self._state = CircuitBreakerState.HALF_OPEN
            logger.info("circuit_breaker_half_open", database=self.database_id)

    def _prune_window(self) -> None:
        """Remove entries older than window_seconds. Call with lock held."""
        cutoff = time.monotonic() - self.window_seconds
        while self._request_window and self._request_window[0][0] < cutoff:
            self._request_window.popleft()

    def is_open(self) -> bool:
        """Returns True if the breaker is open (requests should be rejected)."""
        with self._lock:
            self._maybe_transition_to_half_open()
            if self._state == CircuitBreakerState.OPEN:
                return True
            if self._state == CircuitBreakerState.HALF_OPEN:
                if self._probe_in_flight:
                    return True  # Only one probe at a time
                self._probe_in_flight = True
                return False
            return False

    def record_success(self) -> None:
        with self._lock:
            now = time.monotonic()
            self._request_window.append((now, False))
            self._prune_window()
            if self._state == CircuitBreakerState.HALF_OPEN:
                self._state = CircuitBreakerState.CLOSED
                self._probe_in_flight = False
                logger.info("circuit_breaker_closed", database=self.database_id)

    def record_failure(self) -> None:
        with self._lock:
            now = time.monotonic()
            self._request_window.append((now, True))
            self._prune_window()

            if self._state == CircuitBreakerState.HALF_OPEN:
                self._state = CircuitBreakerState.OPEN
                self._open_at = now
                self._probe_in_flight = False
                logger.warning("circuit_breaker_open", database=self.database_id,
                               reason="probe_failed")
                return

            if self._state == CircuitBreakerState.CLOSED:
                total = len(self._request_window)
                if total >= self.min_requests:
                    errors = sum(1 for _, is_err in self._request_window if is_err)
                    rate = errors / total
                    if rate >= self.error_threshold:
                        self._state = CircuitBreakerState.OPEN
                        self._open_at = now
                        logger.warning(
                            "circuit_breaker_open",
                            database=self.database_id,
                            error_rate=f"{rate:.2%}",
                            total_requests=total,
                        )

    def get_status(self) -> dict:
        with self._lock:
            self._maybe_transition_to_half_open()
            self._prune_window()
            total = len(self._request_window)
            errors = sum(1 for _, is_err in self._request_window if is_err)
            return {
                "database": self.database_id,
                "state": self._state.value,
                "error_count": errors,
                "total_requests": total,
                "error_rate": errors / total if total > 0 else 0.0,
            }


class CircuitBreakerRegistry:
    """Global registry of per-database circuit breakers."""

    def __init__(self, error_threshold: float = 0.5, cooldown_seconds: int = 30):
        self._breakers: dict[str, CircuitBreaker] = {}
        self._error_threshold = error_threshold
        self._cooldown_seconds = cooldown_seconds

    def get(self, database_id: str) -> CircuitBreaker:
        if database_id not in self._breakers:
            self._breakers[database_id] = CircuitBreaker(
                database_id=database_id,
                error_threshold=self._error_threshold,
                cooldown_seconds=self._cooldown_seconds,
            )
        return self._breakers[database_id]

    def all_statuses(self) -> list[dict]:
        return [cb.get_status() for cb in self._breakers.values()]


# Module-level singleton
_registry: CircuitBreakerRegistry | None = None


def get_registry(error_threshold: float = 0.5, cooldown_seconds: int = 30) -> CircuitBreakerRegistry:
    global _registry
    if _registry is None:
        _registry = CircuitBreakerRegistry(error_threshold, cooldown_seconds)
    return _registry
