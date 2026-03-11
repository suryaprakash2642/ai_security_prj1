"""Tests for service-to-service authentication (HMAC tokens, permissions)."""

from __future__ import annotations

import time

import pytest

from app.auth import (
    ServiceIdentity,
    _ROLE_PERMISSIONS,
    create_service_token,
    verify_service_token,
)
from app.models.enums import ServiceRole


class TestTokenCreation:
    def test_creates_valid_token(self):
        token = create_service_token("l3-retrieval", ServiceRole.PIPELINE_READER, "a" * 32)
        parts = token.split("|")
        assert len(parts) == 4
        assert parts[0] == "l3-retrieval"
        assert parts[1] == "pipeline_reader"

    def test_different_roles_produce_different_tokens(self):
        secret = "x" * 32
        t1 = create_service_token("svc", ServiceRole.PIPELINE_READER, secret)
        t2 = create_service_token("svc", ServiceRole.ADMIN, secret)
        assert t1 != t2

    def test_different_services_produce_different_tokens(self):
        secret = "x" * 32
        t1 = create_service_token("svc-a", ServiceRole.ADMIN, secret)
        t2 = create_service_token("svc-b", ServiceRole.ADMIN, secret)
        assert t1 != t2


class TestTokenVerification:
    def test_valid_token_verifies(self):
        secret = "correct-secret-that-is-minimum-32-chars"
        token = create_service_token("l1-identity", ServiceRole.PIPELINE_READER, secret)
        identity = verify_service_token(token, secret)
        assert identity.service_id == "l1-identity"
        assert identity.role == ServiceRole.PIPELINE_READER

    def test_wrong_secret_rejects(self):
        secret = "correct-secret-that-is-minimum-32-chars"
        wrong = "wrong-secret-definitely-not-the-right-one"
        token = create_service_token("l1-identity", ServiceRole.PIPELINE_READER, secret)
        with pytest.raises(ValueError, match="Invalid token signature"):
            verify_service_token(token, wrong)

    def test_malformed_token_rejects(self):
        with pytest.raises(ValueError, match="Malformed token"):
            verify_service_token("not|a|valid-token", "x" * 32)

    def test_expired_token_rejects(self):
        secret = "correct-secret-that-is-minimum-32-chars"
        token = create_service_token("svc", ServiceRole.ADMIN, secret)
        # Tamper with the issued_at to simulate expiry
        parts = token.split("|")
        old_time = str(int(time.time()) - 7200)  # 2 hours ago
        payload = f"{parts[0]}|{parts[1]}|{old_time}"
        import hashlib, hmac as _hmac

        sig = _hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        expired_token = f"{payload}|{sig}"
        with pytest.raises(ValueError, match="Token expired"):
            verify_service_token(expired_token, secret, max_age_seconds=3600)

    def test_future_token_rejects(self):
        secret = "correct-secret-that-is-minimum-32-chars"
        parts_base = "svc|admin"
        future_time = str(int(time.time()) + 300)  # 5 min in future
        payload = f"{parts_base}|{future_time}"
        import hashlib, hmac as _hmac

        sig = _hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        future_token = f"{payload}|{sig}"
        with pytest.raises(ValueError, match="Token issued in the future"):
            verify_service_token(future_token, secret)


class TestPermissions:
    def test_reader_has_read_schema(self):
        identity = ServiceIdentity("l3", ServiceRole.PIPELINE_READER, time.time())
        assert identity.has_permission("read_schema")
        assert identity.has_permission("read_policy")
        assert identity.has_permission("read_classification")

    def test_reader_cannot_write(self):
        identity = ServiceIdentity("l3", ServiceRole.PIPELINE_READER, time.time())
        assert not identity.has_permission("write_schema")
        assert not identity.has_permission("write_policy")
        assert not identity.has_permission("crawl")
        assert not identity.has_permission("admin")

    def test_schema_writer_can_crawl(self):
        identity = ServiceIdentity("crawler", ServiceRole.SCHEMA_WRITER, time.time())
        assert identity.has_permission("crawl")
        assert identity.has_permission("classify")
        assert identity.has_permission("write_schema")
        assert not identity.has_permission("write_policy")

    def test_policy_writer_can_write_policy(self):
        identity = ServiceIdentity("admin-svc", ServiceRole.POLICY_WRITER, time.time())
        assert identity.has_permission("write_policy")
        assert identity.has_permission("read_policy")
        assert not identity.has_permission("crawl")

    def test_admin_has_all_permissions(self):
        identity = ServiceIdentity("super", ServiceRole.ADMIN, time.time())
        for perm_set in _ROLE_PERMISSIONS.values():
            for perm in perm_set:
                assert identity.has_permission(perm), f"Admin missing {perm}"

    def test_unknown_permission_denied(self):
        identity = ServiceIdentity("l3", ServiceRole.ADMIN, time.time())
        assert not identity.has_permission("launch_missiles")
