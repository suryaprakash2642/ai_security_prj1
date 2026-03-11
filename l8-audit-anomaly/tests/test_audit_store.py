"""Tests for the immutable audit store."""

import pytest
from datetime import datetime, timezone, timedelta

from app.models.api import AuditEventEnvelope
from app.models.enums import EventSourceLayer, EventSeverity
from app.services import audit_store
from tests.conftest import make_event


def _build_envelope(**kwargs) -> AuditEventEnvelope:
    raw = make_event(**kwargs)
    from app.services.event_normalizer import normalize
    return normalize(raw)


class TestAppendAndQuery:
    def test_append_stores_event(self):
        evt = _build_envelope(user_id="alice", event_type="EXECUTION_COMPLETE")
        stored = audit_store.append(evt)
        assert stored.event_id == evt.event_id
        assert stored.chain_hash  # must have a chain hash

    def test_query_returns_stored_event(self):
        evt = _build_envelope(user_id="bob")
        audit_store.append(evt)
        events, total = audit_store.query(user_id="bob")
        assert total == 1
        assert events[0].event_id == evt.event_id

    def test_query_by_source_layer(self):
        audit_store.append(_build_envelope(source_layer="L6"))
        audit_store.append(_build_envelope(source_layer="L7"))
        events, total = audit_store.query(source_layers=["L6"])
        assert total == 1
        assert events[0].source_layer == EventSourceLayer.L6

    def test_query_by_severity(self):
        audit_store.append(_build_envelope(severity="WARNING"))
        audit_store.append(_build_envelope(severity="INFO"))
        events, _ = audit_store.query(severities=["WARNING"])
        assert all(e.severity == EventSeverity.WARNING for e in events)

    def test_query_by_request_id(self):
        audit_store.append(_build_envelope(request_id="req-xyz"))
        audit_store.append(_build_envelope(request_id="req-abc"))
        events, total = audit_store.query(request_id="req-xyz")
        assert total == 1
        assert events[0].request_id == "req-xyz"

    def test_pagination(self):
        for i in range(5):
            audit_store.append(_build_envelope(user_id="pg-user"))
        events, total = audit_store.query(user_id="pg-user", limit=2, offset=0)
        assert total == 5
        assert len(events) == 2

    def test_sort_order_desc(self):
        import time
        for _ in range(3):
            audit_store.append(_build_envelope())
            time.sleep(0.01)
        events, _ = audit_store.query(sort_order="desc", limit=3)
        timestamps = [e.timestamp for e in events]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_get_by_request_id_chronological(self):
        import time
        rid = "req-replay-test"
        for layer in ["L1", "L4", "L6", "L7"]:
            audit_store.append(_build_envelope(source_layer=layer, request_id=rid))
            time.sleep(0.01)
        events = audit_store.get_by_request_id(rid)
        assert len(events) == 4
        layers = [e.source_layer for e in events]
        assert layers == sorted(layers, key=lambda l: int(l[1:]))


class TestImmutability:
    def test_update_rejected(self):
        evt = _build_envelope()
        audit_store.append(evt)
        conn = audit_store._get_conn()
        with pytest.raises(Exception, match="TAMPER_ALERT"):
            conn.execute(
                "UPDATE audit_events SET event_type='HACKED' WHERE event_id=?",
                (evt.event_id,),
            )

    def test_delete_rejected(self):
        evt = _build_envelope()
        audit_store.append(evt)
        conn = audit_store._get_conn()
        with pytest.raises(Exception, match="TAMPER_ALERT"):
            conn.execute(
                "DELETE FROM audit_events WHERE event_id=?",
                (evt.event_id,),
            )


class TestHashChain:
    def test_chain_valid_after_inserts(self):
        for _ in range(5):
            audit_store.append(_build_envelope(source_layer="L7"))
        valid, detail = audit_store.verify_hash_chain("L7")
        assert valid, detail

    def test_chain_valid_per_layer(self):
        for layer in ["L6", "L7"]:
            for _ in range(3):
                audit_store.append(_build_envelope(source_layer=layer))
        valid_l6, _ = audit_store.verify_hash_chain("L6")
        valid_l7, _ = audit_store.verify_hash_chain("L7")
        assert valid_l6 and valid_l7

    def test_chain_broken_on_tamper(self):
        for _ in range(3):
            audit_store.append(_build_envelope(source_layer="L5"))
        # Drop the immutability trigger temporarily to simulate a tamper
        conn = audit_store._get_conn()
        conn.execute("DROP TRIGGER IF EXISTS trg_no_update")
        conn.execute("UPDATE audit_events SET chain_hash='deadbeef' WHERE rowid=2")
        conn.commit()
        # Restore trigger
        conn.execute("""
            CREATE TRIGGER trg_no_update BEFORE UPDATE ON audit_events
            BEGIN SELECT RAISE(ABORT, 'TAMPER_ALERT: audit_events is append-only'); END
        """)
        valid, detail = audit_store.verify_hash_chain("L5")
        assert not valid
        assert "broken" in detail.lower()

    def test_empty_chain_is_valid(self):
        valid, detail = audit_store.verify_hash_chain("L2")
        assert valid


class TestDeduplication:
    def test_duplicate_event_detected(self):
        from uuid import uuid4
        eid = str(uuid4())
        assert not audit_store.is_duplicate(eid, window_minutes=60)
        evt = _build_envelope()
        evt = AuditEventEnvelope(**{**evt.model_dump(), "event_id": eid})
        audit_store.append(evt)
        assert audit_store.is_duplicate(eid, window_minutes=60)

    def test_different_event_ids_not_duplicate(self):
        from uuid import uuid4
        assert not audit_store.is_duplicate(str(uuid4()), window_minutes=60)
        assert not audit_store.is_duplicate(str(uuid4()), window_minutes=60)
