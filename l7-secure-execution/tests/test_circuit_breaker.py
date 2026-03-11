"""Tests for the per-database Circuit Breaker."""

import time
import pytest
from app.services.circuit_breaker import CircuitBreaker
from app.models.enums import CircuitBreakerState


class TestNormalOperation:
    def test_starts_closed(self):
        cb = CircuitBreaker("test-db")
        assert cb.state == CircuitBreakerState.CLOSED

    def test_success_keeps_closed(self):
        cb = CircuitBreaker("test-db")
        for _ in range(10):
            cb.record_success()
        assert cb.state == CircuitBreakerState.CLOSED

    def test_few_failures_stays_closed(self):
        cb = CircuitBreaker("test-db", min_requests=5)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitBreakerState.CLOSED

    def test_is_open_false_when_closed(self):
        cb = CircuitBreaker("test-db")
        assert not cb.is_open()


class TestTripToOpen:
    def test_trips_at_error_threshold(self):
        cb = CircuitBreaker("test-db", error_threshold=0.5, min_requests=4)
        cb.record_success()
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()  # 3/4 = 75% >= 50% threshold with min 4
        assert cb.state == CircuitBreakerState.OPEN

    def test_is_open_true_when_tripped(self):
        cb = CircuitBreaker("test-db", error_threshold=0.5, min_requests=4)
        cb.record_success()
        for _ in range(3):
            cb.record_failure()
        assert cb.is_open()

    def test_trips_when_all_fail(self):
        cb = CircuitBreaker("test-db", min_requests=5)
        for _ in range(5):
            cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN


class TestHalfOpen:
    def test_transitions_to_half_open_after_cooldown(self):
        cb = CircuitBreaker("test-db", min_requests=2, cooldown_seconds=0.05)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN
        time.sleep(0.1)  # Wait for cooldown to expire
        # Accessing state triggers the transition check
        assert cb.state == CircuitBreakerState.HALF_OPEN

    def test_half_open_closes_on_success(self):
        cb = CircuitBreaker("test-db", min_requests=2, cooldown_seconds=0)
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.01)
        _ = cb.state  # Trigger HALF_OPEN transition
        cb.record_success()
        assert cb.state == CircuitBreakerState.CLOSED

    def test_half_open_reopens_on_failure(self):
        cb = CircuitBreaker("test-db", min_requests=2, cooldown_seconds=0.05)
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.1)  # Wait for cooldown to expire
        assert cb.state == CircuitBreakerState.HALF_OPEN  # Trigger transition
        cb.record_failure()
        # Use a long cooldown so it stays OPEN after probe failure
        cb._cooldown_seconds = 60
        assert cb.state == CircuitBreakerState.OPEN


class TestIndependence:
    def test_two_dbs_independent(self):
        cb1 = CircuitBreaker("db-1", min_requests=2)
        cb2 = CircuitBreaker("db-2", min_requests=2)
        for _ in range(2):
            cb1.record_failure()
        assert cb1.state == CircuitBreakerState.OPEN
        assert cb2.state == CircuitBreakerState.CLOSED

    def test_status_dict(self):
        cb = CircuitBreaker("test-db")
        cb.record_success()
        status = cb.get_status()
        assert status["database"] == "test-db"
        assert status["state"] == "CLOSED"
        assert "error_rate" in status
