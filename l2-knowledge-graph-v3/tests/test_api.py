"""Integration tests for the L2 Knowledge Graph API endpoints.

Uses FastAPI TestClient with a fully mocked backend (no real Neo4j/Postgres).
Tests authentication, authorization, and endpoint contracts.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.models.api import HealthCheckResult, PolicySimulateResult
from app.models.enums import PolicyType, ServiceRole
from tests.conftest import auth_header, make_column, make_policy, make_table


class TestSystemEndpoints:
    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["service"] == "l2-knowledge-graph"

    def test_readiness_check(self, client, mock_container):
        mock_container.neo4j.verify_connectivity = AsyncMock(return_value=True)
        resp = client.get("/ready")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ready"


class TestAuthRequired:
    """All data endpoints require a valid service token."""

    PROTECTED_ENDPOINTS = [
        ("GET", "/api/v1/graph/tables/by-domain?domain=clinical"),
        ("GET", "/api/v1/graph/tables/test/columns"),
        ("GET", "/api/v1/graph/tables/by-sensitivity?min_level=3"),
        ("GET", "/api/v1/graph/foreign-keys/test"),
        ("GET", "/api/v1/graph/search/tables?q=patients"),
        ("GET", "/api/v1/graph/policies/for-roles?roles=doctor"),
        ("GET", "/api/v1/graph/policies/for-table?table_fqn=test"),
        ("GET", "/api/v1/graph/columns/pii"),
        ("GET", "/api/v1/graph/masking-rules/test"),
    ]

    @pytest.mark.parametrize("method,path", PROTECTED_ENDPOINTS)
    def test_missing_auth_returns_403(self, client, method, path):
        resp = client.request(method, path)
        assert resp.status_code == 403  # HTTPBearer returns 403 if no token

    @pytest.mark.parametrize("method,path", PROTECTED_ENDPOINTS)
    def test_invalid_token_returns_401(self, client, method, path):
        resp = client.request(method, path, headers={"Authorization": "Bearer invalid-token"})
        assert resp.status_code == 401


class TestSchemaEndpoints:
    def test_get_tables_by_domain(self, client, reader_token, mock_container):
        tables = [make_table(domain="clinical")]
        mock_container.graph_reader.get_tables_by_domain = AsyncMock(return_value=tables)
        resp = client.get(
            "/api/v1/graph/tables/by-domain?domain=clinical",
            headers=auth_header(reader_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert len(data["data"]) == 1
        assert data["meta"]["count"] == 1

    def test_get_table_columns(self, client, reader_token, mock_container):
        cols = [
            make_column(name="mrn", is_pii=True),
            make_column(fqn="db.schema.t.first_name", name="first_name", pii_type="FIRST_NAME"),
        ]
        mock_container.graph_reader.get_table_columns = AsyncMock(return_value=cols)
        resp = client.get(
            "/api/v1/graph/tables/db.schema.t/columns",
            headers=auth_header(reader_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["data"]) == 2

    def test_get_tables_by_sensitivity(self, client, reader_token, mock_container):
        tables = [make_table(sensitivity=5), make_table(fqn="db.s.t2", name="t2", sensitivity=4)]
        mock_container.graph_reader.get_tables_by_sensitivity = AsyncMock(return_value=tables)
        resp = client.get(
            "/api/v1/graph/tables/by-sensitivity?min_level=4",
            headers=auth_header(reader_token),
        )
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 2

    def test_search_tables(self, client, reader_token, mock_container):
        mock_container.graph_reader.search_tables = AsyncMock(
            return_value=[make_table(name="patients")]
        )
        resp = client.get(
            "/api/v1/graph/search/tables?q=patient",
            headers=auth_header(reader_token),
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True


class TestPolicyEndpoints:
    def test_get_policies_for_roles(self, client, reader_token, mock_container):
        policies = [make_policy("p1", PolicyType.ALLOW, bound_roles=["doctor"])]
        mock_container.graph_reader.get_policies_for_roles = AsyncMock(return_value=policies)
        resp = client.get(
            "/api/v1/graph/policies/for-roles?roles=doctor",
            headers=auth_header(reader_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert len(data["data"]) == 1

    def test_get_policies_for_table(self, client, reader_token, mock_container):
        policies = [make_policy("p1", PolicyType.MASK)]
        mock_container.graph_reader.get_policies_for_table = AsyncMock(return_value=policies)
        resp = client.get(
            "/api/v1/graph/policies/for-table?table_fqn=db.clinical.patients",
            headers=auth_header(reader_token),
        )
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 1

    def test_simulate_hard_deny(self, client, reader_token, mock_container):
        """substance_abuse_records must always be HARD DENY."""
        hard_deny_result = PolicySimulateResult(
            table_fqn="db.clinical.substance_abuse_records",
            effective_policy=PolicyType.DENY,
            is_hard_deny=True,
            deny_reason="Table is under HARD DENY protection (42 CFR Part 2)",
        )
        mock_container.policy_service.simulate = AsyncMock(return_value=[hard_deny_result])
        resp = client.post(
            "/api/v1/graph/policies/simulate",
            json={
                "roles": ["doctor"],
                "table_fqns": ["db.clinical.substance_abuse_records"],
            },
            headers=auth_header(reader_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"][0]["effective_policy"] == "DENY"
        assert data["data"][0]["is_hard_deny"] is True

    def test_simulate_deny_by_default(self, client, reader_token, mock_container):
        """No matching policy → DENY."""
        default_deny = PolicySimulateResult(
            table_fqn="db.unknown.table",
            effective_policy=PolicyType.DENY,
            deny_reason="No applicable policy found — deny by default",
        )
        mock_container.policy_service.simulate = AsyncMock(return_value=[default_deny])
        resp = client.post(
            "/api/v1/graph/policies/simulate",
            json={"roles": ["intern"], "table_fqns": ["db.unknown.table"]},
            headers=auth_header(reader_token),
        )
        data = resp.json()
        assert data["data"][0]["effective_policy"] == "DENY"

    def test_get_hard_deny_tables(self, client, reader_token, mock_container):
        mock_container.graph_reader.get_hard_deny_tables = AsyncMock(
            return_value=["db.clinical.substance_abuse_records"]
        )
        resp = client.get(
            "/api/v1/graph/policies/hard-deny-tables",
            headers=auth_header(reader_token),
        )
        assert resp.status_code == 200
        assert "substance_abuse" in resp.json()["data"][0]


class TestClassificationEndpoints:
    def test_get_pii_columns(self, client, reader_token, mock_container):
        from app.models.api import PIIColumnResponse

        pii_cols = [
            PIIColumnResponse(
                column_fqn="db.clinical.patients.ssn",
                column_name="ssn",
                table_fqn="db.clinical.patients",
                table_name="patients",
                pii_type="SSN",
                sensitivity_level=5,
                masking_strategy="HASH",
            )
        ]
        mock_container.graph_reader.get_pii_columns = AsyncMock(return_value=pii_cols)
        resp = client.get(
            "/api/v1/graph/columns/pii",
            headers=auth_header(reader_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["pii_type"] == "SSN"

    def test_get_masking_rules(self, client, reader_token, mock_container):
        from app.models.api import MaskingRuleResponse

        rules = [
            MaskingRuleResponse(
                column_fqn="db.clinical.patients.ssn",
                column_name="ssn",
                masking_strategy="HASH",
                sensitivity_level=5,
            )
        ]
        mock_container.graph_reader.get_masking_rules = AsyncMock(return_value=rules)
        resp = client.get(
            "/api/v1/graph/masking-rules/db.clinical.patients",
            headers=auth_header(reader_token),
        )
        assert resp.status_code == 200
        assert resp.json()["data"][0]["masking_strategy"] == "HASH"

    def test_get_inherited_roles(self, client, reader_token, mock_container):
        mock_container.graph_reader.get_inherited_roles = AsyncMock(
            return_value=["clinical_staff", "employee", "base_user"]
        )
        resp = client.get(
            "/api/v1/graph/roles/doctor/inherited",
            headers=auth_header(reader_token),
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "clinical_staff" in data
        assert "base_user" in data


class TestAuthorizationBoundaries:
    """Test that role-based permission enforcement works on endpoints."""

    def test_reader_cannot_trigger_crawl(self, client, reader_token):
        resp = client.post(
            "/api/v1/admin/crawl",
            json={"database_name": "test", "engine": "postgresql", "connection_string": "fake"},
            headers=auth_header(reader_token),
        )
        assert resp.status_code == 403

    def test_reader_cannot_run_health_checks(self, client, reader_token):
        resp = client.get(
            "/api/v1/admin/health-checks",
            headers=auth_header(reader_token),
        )
        assert resp.status_code == 403

    def test_reader_cannot_refresh_embeddings(self, client, reader_token):
        resp = client.post(
            "/api/v1/admin/embeddings/refresh",
            headers=auth_header(reader_token),
        )
        assert resp.status_code == 403

    def test_writer_cannot_admin_endpoints(self, client, writer_token):
        resp = client.post(
            "/api/v1/admin/embeddings/refresh",
            headers=auth_header(writer_token),
        )
        assert resp.status_code == 403

    def test_admin_can_access_all(self, client, admin_token, mock_container):
        mock_container.health_check.run_all = AsyncMock(return_value=[])
        resp = client.get(
            "/api/v1/admin/health-checks",
            headers=auth_header(admin_token),
        )
        assert resp.status_code == 200


class TestAdminEndpoints:
    def test_classify_endpoint(self, client, writer_token, mock_container):
        from app.models.api import ClassificationSummary

        summary = ClassificationSummary(
            columns_analyzed=50, pii_detected=12, auto_approved=10, review_items_created=2
        )
        mock_container.classification_engine.classify_columns = AsyncMock(return_value=summary)
        resp = client.post(
            "/api/v1/admin/classify",
            json={"force_reclassify": False},
            headers=auth_header(writer_token),
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["columns_analyzed"] == 50
        assert data["pii_detected"] == 12

    def test_health_checks_endpoint(self, client, admin_token, mock_container):
        results = [
            HealthCheckResult(check_name="orphan_policies", passed=True, details="OK"),
            HealthCheckResult(check_name="circular_inheritance", passed=True, details="OK"),
            HealthCheckResult(
                check_name="substance_abuse_deny",
                passed=True,
                details="All substance abuse tables are HARD DENY",
            ),
        ]
        mock_container.health_check.run_all = AsyncMock(return_value=results)
        resp = client.get(
            "/api/v1/admin/health-checks",
            headers=auth_header(admin_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["meta"]["passed_all"] is True
        assert len(data["data"]) == 3

    def test_audit_version_endpoint(self, client, reader_token, mock_container):
        mock_container.audit_repo.get_current_version = AsyncMock(
            return_value={"version": 42, "updated_at": "2026-03-01", "updated_by": "crawler"}
        )
        resp = client.get(
            "/api/v1/admin/audit/version",
            headers=auth_header(reader_token),
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["version"] == 42
