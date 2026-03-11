"""Service-to-service authentication using HMAC-signed tokens.

Downstream layers (L1, L3, L4, L6, L8) present a signed service token.
No end-user connects directly to L2 — only trusted services.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any

import structlog
from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings, get_settings
from app.models.enums import ServiceRole

logger = structlog.get_logger(__name__)

_bearer_scheme = HTTPBearer(auto_error=True)

# Allowed operations per service role
_ROLE_PERMISSIONS: dict[ServiceRole, set[str]] = {
    ServiceRole.PIPELINE_READER: {"read_schema", "read_policy", "read_classification", "simulate", "search"},
    ServiceRole.SCHEMA_WRITER: {"read_schema", "write_schema", "crawl", "classify"},
    ServiceRole.POLICY_WRITER: {"read_schema", "read_policy", "write_policy", "read_classification"},
    ServiceRole.ADMIN: {
        "read_schema", "write_schema", "read_policy", "write_policy",
        "read_classification", "crawl", "classify", "simulate", "search",
        "health", "admin", "review",
    },
}


class ServiceIdentity:
    """Parsed and validated service identity from the auth token."""

    def __init__(self, service_id: str, role: ServiceRole, issued_at: float) -> None:
        self.service_id = service_id
        self.role = role
        self.issued_at = issued_at

    def has_permission(self, permission: str) -> bool:
        return permission in _ROLE_PERMISSIONS.get(self.role, set())


def create_service_token(
    service_id: str,
    role: ServiceRole,
    secret: str,
    ttl_seconds: int = 3600,
) -> str:
    """Create an HMAC-signed service token for inter-service auth.

    Format: service_id|role|issued_at|signature
    """
    issued_at = str(int(time.time()))
    payload = f"{service_id}|{role.value}|{issued_at}"
    sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}|{sig}"


def verify_service_token(token: str, secret: str, max_age_seconds: int = 3600) -> ServiceIdentity:
    """Verify and parse a service token. Raises ValueError on failure."""
    parts = token.split("|")
    if len(parts) != 4:
        raise ValueError("Malformed token: expected 4 pipe-delimited segments")

    service_id, role_str, issued_at_str, signature = parts

    # Verify signature
    payload = f"{service_id}|{role_str}|{issued_at_str}"
    expected_sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected_sig):
        raise ValueError("Invalid token signature")

    # Verify expiry
    try:
        issued_at = float(issued_at_str)
    except (ValueError, TypeError):
        raise ValueError("Invalid issued_at timestamp")

    age = time.time() - issued_at
    if age > max_age_seconds:
        raise ValueError(f"Token expired ({age:.0f}s old, max {max_age_seconds}s)")
    if age < -60:  # Allow 60s clock skew
        raise ValueError("Token issued in the future")

    # Parse role
    try:
        role = ServiceRole(role_str)
    except ValueError:
        raise ValueError(f"Unknown service role: {role_str}")

    return ServiceIdentity(service_id=service_id, role=role, issued_at=issued_at)


async def get_current_service(
    credentials: HTTPAuthorizationCredentials = Security(_bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> ServiceIdentity:
    """FastAPI dependency: extract and verify service identity from Bearer token."""
    try:
        identity = verify_service_token(credentials.credentials, settings.service_token_secret)
    except ValueError as exc:
        logger.warning("auth_failed", error=str(exc))
        raise HTTPException(status_code=401, detail=str(exc))

    if identity.service_id not in settings.allowed_services:
        logger.warning("service_not_allowed", service_id=identity.service_id)
        raise HTTPException(status_code=403, detail=f"Service '{identity.service_id}' is not in the allow-list")

    return identity


def require_permission(permission: str):
    """Factory for a FastAPI dependency that checks a specific permission."""

    async def _check(identity: ServiceIdentity = Depends(get_current_service)) -> ServiceIdentity:
        if not identity.has_permission(permission):
            raise HTTPException(
                status_code=403,
                detail=f"Service '{identity.service_id}' (role={identity.role.value}) "
                       f"lacks permission '{permission}'",
            )
        return identity

    return _check
