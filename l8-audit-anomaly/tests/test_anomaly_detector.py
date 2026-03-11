"""Tests for the anomaly detection engine."""

import pytest
from datetime import datetime, timezone, timedelta

from app.models.enums import AnomalyType, EventSeverity
from app.services import anomaly_detector
from app.services.event_normalizer import normalize
from tests.conftest import make_event


def _evt(**kwargs):
    return normalize(make_event(**kwargs))


class TestVolumeAnomaly:
    def test_no_anomaly_with_insufficient_history(self):
        anomaly_detector.configure(z_high=3.0, z_critical=5.0)
        alerts = anomaly_detector.analyze(_evt(user_id="u1"))
        volume_alerts = [a for a in alerts if a.anomaly_type == AnomalyType.VOLUME]
        assert len(volume_alerts) == 0

    def test_volume_anomaly_detected_with_high_z_score(self):
        """Build historical baseline (low counts), then inject a spike."""
        anomaly_detector.configure(z_high=2.0, z_critical=5.0)
        # Seed 7 days of hourly history (low baseline: 2 queries/hour)
        for i in range(7):
            bucket = int(datetime.now(timezone.utc).timestamp() // 3600) - (i + 1) * 24
            anomaly_detector._user_hourly_counts["u-spike"].append(2)

        # Now record 50 queries in the current hour
        for _ in range(50):
            anomaly_detector._increment_user_count(
                "u-spike", datetime.now(timezone.utc)
            )

        # The 51st event should trigger volume anomaly
        alerts = anomaly_detector.analyze(_evt(user_id="u-spike"))
        volume_alerts = [a for a in alerts if a.anomaly_type == AnomalyType.VOLUME]
        assert len(volume_alerts) == 1
        assert volume_alerts[0].severity in (EventSeverity.HIGH, EventSeverity.CRITICAL)


class TestTemporalAnomaly:
    def test_off_hours_triggers_warning(self):
        anomaly_detector.configure(work_start=9, work_end=17)
        # 03:00 UTC is off-hours
        ts = datetime.now(timezone.utc).replace(hour=3, minute=0, second=0, microsecond=0)
        raw = make_event(severity="INFO")
        raw["timestamp"] = ts.isoformat()
        evt = normalize(raw)
        alerts = anomaly_detector.analyze(evt)
        temporal = [a for a in alerts if a.anomaly_type == AnomalyType.TEMPORAL]
        assert len(temporal) == 1
        assert temporal[0].severity == EventSeverity.WARNING

    def test_within_hours_no_temporal_alert(self):
        anomaly_detector.configure(work_start=7, work_end=19)
        ts = datetime.now(timezone.utc).replace(hour=10, minute=0, second=0, microsecond=0)
        raw = make_event(severity="INFO")
        raw["timestamp"] = ts.isoformat()
        evt = normalize(raw)
        alerts = anomaly_detector.analyze(evt)
        temporal = [a for a in alerts if a.anomaly_type == AnomalyType.TEMPORAL]
        assert len(temporal) == 0

    def test_btg_suppresses_temporal_anomaly(self):
        anomaly_detector.configure(work_start=9, work_end=17)
        ts = datetime.now(timezone.utc).replace(hour=3, minute=0, second=0, microsecond=0)
        raw = make_event(btg_active=True)
        raw["timestamp"] = ts.isoformat()
        evt = normalize(raw)
        alerts = anomaly_detector.analyze(evt)
        temporal = [a for a in alerts if a.anomaly_type == AnomalyType.TEMPORAL]
        assert len(temporal) == 0

    def test_off_hours_high_severity_escalates_to_high(self):
        anomaly_detector.configure(work_start=9, work_end=17)
        ts = datetime.now(timezone.utc).replace(hour=2, minute=0, second=0, microsecond=0)
        raw = make_event(severity="HIGH")
        raw["timestamp"] = ts.isoformat()
        evt = normalize(raw)
        alerts = anomaly_detector.analyze(evt)
        temporal = [a for a in alerts if a.anomaly_type == AnomalyType.TEMPORAL]
        assert temporal[0].severity == EventSeverity.HIGH


class TestValidationBlockSpike:
    def test_below_threshold_no_alert(self):
        anomaly_detector.configure(block_threshold=5)
        for _ in range(3):
            alerts = anomaly_detector.analyze(
                _evt(event_type="VALIDATION_BLOCK", user_id="u-blocks")
            )
        block_alerts = [a for a in alerts if a.anomaly_type == AnomalyType.VALIDATION_BLOCK_SPIKE]
        assert len(block_alerts) == 0

    def test_at_threshold_triggers_high_alert(self):
        anomaly_detector.configure(block_threshold=3)
        alerts = []
        for _ in range(3):
            alerts = anomaly_detector.analyze(
                _evt(event_type="VALIDATION_BLOCK", user_id="u-blocks2")
            )
        block_alerts = [a for a in alerts if a.anomaly_type == AnomalyType.VALIDATION_BLOCK_SPIKE]
        assert len(block_alerts) == 1
        assert block_alerts[0].severity == EventSeverity.HIGH

    def test_non_block_event_not_counted(self):
        anomaly_detector.configure(block_threshold=3)
        for _ in range(5):
            alerts = anomaly_detector.analyze(
                _evt(event_type="EXECUTION_COMPLETE", user_id="u-exec")
            )
        block_alerts = [a for a in alerts if a.anomaly_type == AnomalyType.VALIDATION_BLOCK_SPIKE]
        assert len(block_alerts) == 0


class TestSanitizationSpike:
    def test_below_threshold_no_alert(self):
        anomaly_detector.configure(sanitization_threshold=10)
        for _ in range(5):
            alerts = anomaly_detector.analyze(
                _evt(event_type="SANITIZATION_APPLIED",
                     payload={"column": "full_name"})
            )
        san_alerts = [a for a in alerts if a.anomaly_type == AnomalyType.SANITIZATION_SPIKE]
        assert len(san_alerts) == 0

    def test_at_threshold_triggers_high_alert(self):
        anomaly_detector.configure(sanitization_threshold=5)
        alerts = []
        for _ in range(5):
            alerts = anomaly_detector.analyze(
                _evt(event_type="SANITIZATION_APPLIED",
                     payload={"column": "ssn_column"})
            )
        san_alerts = [a for a in alerts if a.anomaly_type == AnomalyType.SANITIZATION_SPIKE]
        assert len(san_alerts) == 1
        assert "ssn_column" in san_alerts[0].description

    def test_different_columns_tracked_independently(self):
        anomaly_detector.configure(sanitization_threshold=3)
        # 3 events for col_a → alert
        # 2 events for col_b → no alert
        for _ in range(3):
            anomaly_detector.analyze(
                _evt(event_type="SANITIZATION_APPLIED", payload={"column": "col_a"})
            )
        alerts = []
        for _ in range(2):
            alerts = anomaly_detector.analyze(
                _evt(event_type="SANITIZATION_APPLIED", payload={"column": "col_b"})
            )
        col_b_alerts = [
            a for a in alerts
            if a.anomaly_type == AnomalyType.SANITIZATION_SPIKE and "col_b" in a.description
        ]
        assert len(col_b_alerts) == 0


class TestBTGDuration:
    def test_short_btg_no_alert(self):
        anomaly_detector.configure(btg_duration_hours=4.0)
        # Start BTG
        anomaly_detector.analyze(_evt(event_type="BTG_ACTIVATION", user_id="nurse-1"))
        # End after 1 hour (simulated via manual state manipulation)
        import datetime as dt
        anomaly_detector._active_btg["nurse-1"]["start"] = (
            datetime.now(timezone.utc) - timedelta(hours=1)
        )
        alerts = anomaly_detector.analyze(_evt(event_type="BTG_EXPIRED", user_id="nurse-1"))
        btg_alerts = [a for a in alerts if a.anomaly_type == AnomalyType.BTG_ABUSE]
        assert len(btg_alerts) == 0

    def test_long_btg_triggers_high_alert(self):
        anomaly_detector.configure(btg_duration_hours=4.0)
        anomaly_detector.analyze(_evt(event_type="BTG_ACTIVATION", user_id="nurse-2"))
        # Simulate 5-hour BTG
        anomaly_detector._active_btg["nurse-2"]["start"] = (
            datetime.now(timezone.utc) - timedelta(hours=5)
        )
        alerts = anomaly_detector.analyze(_evt(event_type="BTG_EXPIRED", user_id="nurse-2"))
        btg_alerts = [a for a in alerts if a.anomaly_type == AnomalyType.BTG_ABUSE]
        assert len(btg_alerts) == 1
        assert btg_alerts[0].severity == EventSeverity.HIGH
