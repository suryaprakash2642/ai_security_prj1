"""Tests for event normalization and HMAC verification."""

import pytest
from datetime import datetime, timezone

from app.models.enums import EventSeverity, EventSourceLayer
from app.services.event_normalizer import NormalizationError, normalize, verify_hmac
from tests.conftest import make_event


class TestNormalize:
    def test_valid_event(self):
        raw = make_event(event_type="EXECUTION_COMPLETE", source_layer="L7")
        evt = normalize(raw)
        assert evt.event_type == "EXECUTION_COMPLETE"
        assert evt.source_layer == EventSourceLayer.L7

    def test_missing_required_field_raises(self):
        raw = make_event()
        del raw["user_id"]
        with pytest.raises(NormalizationError) as exc:
            normalize(raw)
        assert "user_id" in str(exc.value)
        assert exc.value.error_type == "SCHEMA_VIOLATION"

    def test_unknown_source_layer_raises(self):
        raw = make_event(source_layer="L99")
        with pytest.raises(NormalizationError):
            normalize(raw)

    def test_unknown_severity_defaults_to_info(self):
        raw = make_event()
        raw["severity"] = "BOGUS"
        evt = normalize(raw)
        assert evt.severity == EventSeverity.INFO

    def test_timestamp_parsed_correctly(self):
        raw = make_event()
        raw["timestamp"] = "2026-02-15T14:30:22Z"
        evt = normalize(raw)
        assert evt.timestamp.tzinfo is not None

    def test_naive_timestamp_gets_utc(self):
        raw = make_event()
        raw["timestamp"] = "2026-02-15T14:30:22"
        evt = normalize(raw)
        assert evt.timestamp.tzinfo == timezone.utc

    def test_btg_active_default_false(self):
        raw = make_event()
        del raw["btg_active"]
        evt = normalize(raw)
        assert evt.btg_active is False

    def test_payload_default_empty(self):
        raw = make_event()
        del raw["payload"]
        evt = normalize(raw)
        assert evt.payload == {}

    def test_severity_case_insensitive(self):
        raw = make_event(severity="critical")
        evt = normalize(raw)
        assert evt.severity == EventSeverity.CRITICAL


class TestHMACVerification:
    SIGNING_KEY = "test-signing-key-32-chars-minimum!"

    def _sign(self, event) -> str:
        import hashlib
        import hmac
        import json
        canonical = json.dumps({
            "event_id": event.event_id,
            "event_type": event.event_type,
            "source_layer": event.source_layer,
            "timestamp": event.timestamp.isoformat(),
            "user_id": event.user_id,
            "request_id": event.request_id,
        }, sort_keys=True)
        return hmac.new(
            self.SIGNING_KEY.encode(),
            canonical.encode(),
            hashlib.sha256,
        ).hexdigest()

    def test_non_critical_always_passes(self):
        raw = make_event(severity="HIGH")
        evt = normalize(raw)
        assert verify_hmac(evt, self.SIGNING_KEY) is True

    def test_critical_without_signature_fails(self):
        raw = make_event(severity="CRITICAL")
        evt = normalize(raw)
        assert verify_hmac(evt, self.SIGNING_KEY) is False

    def test_critical_with_valid_signature_passes(self):
        raw = make_event(severity="CRITICAL")
        evt = normalize(raw)
        evt.hmac_signature = self._sign(evt)
        assert verify_hmac(evt, self.SIGNING_KEY) is True

    def test_critical_with_wrong_signature_fails(self):
        raw = make_event(severity="CRITICAL")
        evt = normalize(raw)
        evt.hmac_signature = "deadbeef" * 8
        assert verify_hmac(evt, self.SIGNING_KEY) is False
