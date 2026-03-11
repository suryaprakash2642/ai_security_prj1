"""Integration tests for L8 API endpoints."""

from uuid import uuid4

from app.services import alert_manager
from tests.conftest import make_event


class TestIngest:
    def test_ingest_valid_event(self, client):
        raw = make_event(event_type="EXECUTION_COMPLETE", source_layer="L7")
        resp = client.post("/api/v1/audit/ingest", json=raw)
        assert resp.status_code == 201
        body = resp.json()
        assert body["event_id"] == raw["event_id"]
        assert "chain_hash" in body

    def test_ingest_missing_field_returns_422(self, client):
        raw = make_event()
        del raw["user_id"]
        resp = client.post("/api/v1/audit/ingest", json=raw)
        assert resp.status_code == 422

    def test_ingest_duplicate_returns_409(self, client):
        raw = make_event()
        client.post("/api/v1/audit/ingest", json=raw)
        resp = client.post("/api/v1/audit/ingest", json=raw)  # Same event_id
        assert resp.status_code == 409

    def test_ingest_multiple_layers(self, client):
        rid = str(uuid4())
        for layer in ["L1", "L4", "L6", "L7"]:
            raw = make_event(source_layer=layer, request_id=rid)
            resp = client.post("/api/v1/audit/ingest", json=raw)
            assert resp.status_code == 201


class TestQuery:
    def test_query_all_events(self, client):
        for _ in range(5):
            client.post("/api/v1/audit/ingest", json=make_event())
        resp = client.post("/api/v1/audit/query", json={})
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 5
        assert len(body["events"]) == 5

    def test_query_by_user_id(self, client):
        client.post("/api/v1/audit/ingest", json=make_event(user_id="alice"))
        client.post("/api/v1/audit/ingest", json=make_event(user_id="bob"))
        resp = client.post("/api/v1/audit/query", json={"filters": {"user_id": "alice"}})
        assert resp.status_code == 200
        assert resp.json()["total"] == 1
        assert resp.json()["events"][0]["user_id"] == "alice"

    def test_query_by_severity(self, client):
        client.post("/api/v1/audit/ingest", json=make_event(severity="WARNING"))
        client.post("/api/v1/audit/ingest", json=make_event(severity="INFO"))
        resp = client.post(
            "/api/v1/audit/query",
            json={"filters": {"severity": ["WARNING"]}},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_query_pagination(self, client):
        for _ in range(10):
            client.post("/api/v1/audit/ingest", json=make_event())
        resp = client.post(
            "/api/v1/audit/query",
            json={"pagination": {"offset": 0, "limit": 3}},
        )
        assert resp.json()["total"] == 10
        assert len(resp.json()["events"]) == 3


class TestReplay:
    def test_pipeline_replay(self, client):
        rid = str(uuid4())
        layers = ["L1", "L4", "L6", "L7"]
        for layer in layers:
            client.post(
                "/api/v1/audit/ingest",
                json=make_event(source_layer=layer, request_id=rid),
            )
        resp = client.get(f"/api/v1/audit/replay/{rid}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["event_count"] == 4
        assert body["request_id"] == rid

    def test_replay_unknown_request_id_empty(self, client):
        resp = client.get("/api/v1/audit/replay/no-such-request-id")
        assert resp.status_code == 200
        assert resp.json()["event_count"] == 0


class TestHashChainIntegrity:
    def test_integrity_endpoint_valid(self, client):
        for _ in range(3):
            client.post("/api/v1/audit/ingest", json=make_event(source_layer="L7"))
        resp = client.get("/api/v1/audit/integrity/L7")
        assert resp.status_code == 200
        assert resp.json()["valid"] is True

    def test_integrity_empty_layer_valid(self, client):
        resp = client.get("/api/v1/audit/integrity/L3")
        assert resp.json()["valid"] is True


class TestAlerts:
    def test_list_alerts_empty(self, client):
        resp = client.get("/api/v1/alerts")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_acknowledge_alert(self, client):
        from app.models.api import AnomalyAlert
        from app.models.enums import AnomalyType, EventSeverity
        alert = AnomalyAlert(
            anomaly_type=AnomalyType.VOLUME,
            severity=EventSeverity.HIGH,
            user_id="test-user",
            description="Test volume spike",
        )
        alert_manager.process(alert)

        alerts = client.get("/api/v1/alerts").json()
        assert len(alerts) == 1
        alert_id = alerts[0]["alert_id"]

        resp = client.post(f"/api/v1/alerts/{alert_id}/acknowledge", json={"notes": "reviewed"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "ACKNOWLEDGED"

    def test_resolve_alert(self, client):
        from app.models.api import AnomalyAlert
        from app.models.enums import AnomalyType, EventSeverity
        alert = AnomalyAlert(
            anomaly_type=AnomalyType.TEMPORAL,
            severity=EventSeverity.WARNING,
            user_id="night-owl",
            description="Off-hours access",
        )
        alert_manager.process(alert)

        alerts = client.get("/api/v1/alerts").json()
        alert_id = alerts[0]["alert_id"]
        resp = client.post(f"/api/v1/alerts/{alert_id}/resolve")
        assert resp.status_code == 200
        assert resp.json()["status"] == "RESOLVED"


class TestReports:
    def test_daily_summary_report(self, client):
        for event_type in ["EXECUTION_COMPLETE", "VALIDATION_BLOCK", "BTG_ACTIVATION"]:
            client.post(
                "/api/v1/audit/ingest",
                json=make_event(event_type=event_type),
            )
        resp = client.post(
            "/api/v1/audit/reports/generate",
            json={"report_type": "daily_summary"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["report_type"] == "daily_summary"
        assert body["data"]["total_events"] == 3
        assert body["data"]["btg_activations"] == 1
        assert body["data"]["validation_blocks"] == 1

    def test_breach_investigation_report(self, client):
        rid = str(uuid4())
        for layer in ["L1", "L6", "L7"]:
            client.post(
                "/api/v1/audit/ingest",
                json=make_event(source_layer=layer, request_id=rid),
            )
        resp = client.post(
            "/api/v1/audit/reports/generate",
            json={
                "report_type": "breach_investigation",
                "filters": {"request_id": rid},
            },
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total_events"] == 3
        assert rid in data["cross_layer_chains"]

    def test_weekly_security_report(self, client):
        resp = client.post(
            "/api/v1/audit/reports/generate",
            json={"report_type": "weekly_security"},
        )
        assert resp.status_code == 200
        assert "validation_blocks_by_type" in resp.json()["data"]

    def test_btg_justification_report(self, client):
        client.post(
            "/api/v1/audit/ingest",
            json=make_event(
                event_type="BTG_ACTIVATION",
                user_id="nurse-raj",
                payload={
                    "justification_text": "ER patient critical - need full access",
                    "emergency_type": "clinical",
                },
            ),
        )
        resp = client.post(
            "/api/v1/audit/reports/generate",
            json={
                "report_type": "btg_justification",
                "filters": {"user_id": "nurse-raj"},
            },
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["btg_activation_count"] == 1
        assert "ER patient" in data["btg_activations"][0]["justification"]


class TestHealth:
    def test_health_endpoint(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
