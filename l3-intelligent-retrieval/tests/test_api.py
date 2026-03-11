"""Tests for API routes — authentication, request validation, structured errors."""

from __future__ import annotations

import pytest

from tests.conftest import auth_header, make_security_context


class TestResolveEndpoint:
    """Tests for POST /api/v1/retrieval/resolve."""

    def test_no_auth_returns_401(self, client):
        resp = client.post("/api/v1/retrieval/resolve", json={
            "question": "Show patients",
            "security_context": {},
        })
        # HTTPBearer auto_error=True → 403 when no header
        assert resp.status_code in (401, 403)

    def test_invalid_token_returns_401(self, client):
        resp = client.post(
            "/api/v1/retrieval/resolve",
            json={"question": "test", "security_context": {}},
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert resp.status_code == 401

    def test_valid_request_succeeds(self, client, reader_token, test_settings):
        ctx = make_security_context(test_settings)
        resp = client.post(
            "/api/v1/retrieval/resolve",
            json={
                "question": "Show all patients with diabetes",
                "security_context": ctx.model_dump(mode="json"),
            },
            headers=auth_header(reader_token),
        )
        data = resp.json()
        # Should succeed or return a structured error (never a 500)
        assert resp.status_code == 200
        assert "success" in data

    def test_short_question_rejected(self, client, reader_token, test_settings):
        ctx = make_security_context(test_settings)
        resp = client.post(
            "/api/v1/retrieval/resolve",
            json={
                "question": "hi",
                "security_context": ctx.model_dump(mode="json"),
            },
            headers=auth_header(reader_token),
        )
        assert resp.status_code == 422  # Validation error

    def test_missing_question_rejected(self, client, reader_token, test_settings):
        ctx = make_security_context(test_settings)
        resp = client.post(
            "/api/v1/retrieval/resolve",
            json={
                "security_context": ctx.model_dump(mode="json"),
            },
            headers=auth_header(reader_token),
        )
        assert resp.status_code == 422

    def test_expired_context_returns_error(self, client, reader_token, test_settings):
        ctx = make_security_context(test_settings, expired=True)
        resp = client.post(
            "/api/v1/retrieval/resolve",
            json={
                "question": "Show patients",
                "security_context": ctx.model_dump(mode="json"),
            },
            headers=auth_header(reader_token),
        )
        data = resp.json()
        assert data.get("success") is False or resp.status_code >= 400


class TestHealthEndpoint:
    """Tests for GET /api/v1/retrieval/health."""

    def test_health_no_auth_required(self, client):
        resp = client.get("/api/v1/retrieval/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "dependencies" in data


class TestCacheClearEndpoint:
    """Tests for POST /api/v1/retrieval/cache/clear."""

    def test_cache_clear_requires_admin(self, client, reader_token):
        resp = client.post(
            "/api/v1/retrieval/cache/clear",
            headers=auth_header(reader_token),
        )
        # reader token should not have admin permission
        assert resp.status_code == 403

    def test_cache_clear_with_admin(self, client, admin_token):
        resp = client.post(
            "/api/v1/retrieval/cache/clear",
            headers=auth_header(admin_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") is True


class TestStatsEndpoint:
    """Tests for GET /api/v1/retrieval/stats."""

    def test_stats_returns_data(self, client, reader_token):
        resp = client.get(
            "/api/v1/retrieval/stats",
            headers=auth_header(reader_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") is True


class TestSystemHealth:
    """Tests for root /health endpoint."""

    def test_root_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
