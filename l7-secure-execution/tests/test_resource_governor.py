"""Tests for the Resource Governor."""

import time
import pytest
from app.services.resource_governor import ResourceGovernor, ResourceLimitExceeded


class TestRowLimit:
    def test_under_limit_ok(self):
        gov = ResourceGovernor(max_rows=10)
        gov.start()
        for _ in range(5):
            gov.check_row(3)  # 3 columns
        assert gov.row_count == 5
        assert not gov.truncated

    def test_at_limit_raises(self):
        gov = ResourceGovernor(max_rows=3)
        gov.start()
        gov.check_row(2)
        gov.check_row(2)
        gov.check_row(2)
        with pytest.raises(ResourceLimitExceeded) as exc_info:
            gov.check_row(2)  # 4th row exceeds limit of 3
        assert exc_info.value.limit_type == "ROW_LIMIT_EXCEEDED"
        assert gov.truncated

    def test_row_count_tracked(self):
        gov = ResourceGovernor(max_rows=100)
        gov.start()
        for _ in range(7):
            gov.check_row(5)
        assert gov.row_count == 7


class TestMemoryLimit:
    def test_memory_exceeded_raises(self):
        # 64 bytes per cell * 1 col * 200 rows = 12800 bytes = 0.012 MB
        # Force tiny limit to trigger
        gov = ResourceGovernor(max_rows=1000, max_memory_mb=0.001)
        gov.start()
        with pytest.raises(ResourceLimitExceeded) as exc_info:
            for _ in range(200):
                gov.check_row(1)
        assert exc_info.value.limit_type == "MEMORY_EXCEEDED"


class TestBTGLimits:
    def test_btg_uses_elevated_limits(self):
        gov = ResourceGovernor(
            max_rows=1000,
            btg_active=True,
            btg_timeout_seconds=60,
            btg_max_rows=5000,
        )
        assert gov.max_rows == 5000
        assert gov.timeout_seconds == 60

    def test_normal_uses_standard_limits(self):
        gov = ResourceGovernor(max_rows=1000, timeout_seconds=30, btg_active=False)
        assert gov.max_rows == 1000
        assert gov.timeout_seconds == 30


class TestTimeout:
    def test_elapsed_seconds_increases(self):
        gov = ResourceGovernor(timeout_seconds=30)
        gov.start()
        time.sleep(0.01)
        assert gov.elapsed_seconds() > 0

    def test_timeout_raises_when_exceeded(self):
        gov = ResourceGovernor(timeout_seconds=0)  # 0s timeout
        gov.start()
        time.sleep(0.01)  # Should exceed
        with pytest.raises(ResourceLimitExceeded) as exc_info:
            gov.check_timeout()
        assert exc_info.value.limit_type == "QUERY_TIMEOUT"


class TestFinalize:
    def test_finalize_returns_metrics(self):
        gov = ResourceGovernor(max_rows=100)
        gov.start()
        for _ in range(3):
            gov.check_row(4)
        metrics = gov.finalize()
        assert metrics["rows_fetched"] == 3
        assert metrics["truncated"] is False
        assert "estimated_memory_mb" in metrics
