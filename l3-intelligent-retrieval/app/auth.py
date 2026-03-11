"""Authentication and SecurityContext validation.

Two layers:
1. Inter-service auth (HMAC tokens between L3 and callers like L5)
2. SecurityContext validation (verify L1-signed user context)
"""

from __future__ import annotations

import hashlib
import hmac
import time

import structlog
from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings, get_settings
from app.models.security import SecurityContext, ServiceIdentity

logger = structlog.get_logger(__name__)

_bearer = HTTPBearer(auto_error=True)


# ── Inter-service token management ──────────────────────────


def create_service_token(
    service_id: str, role: str, secret: str, ttl: int = 3600,
) -> str:
    """Create HMAC-signed service token (mirrors L2 format for compatibility)."""
    issued = str(int(time.time()))
    payload = f"{service_id}|{role}|{issued}"
    sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}|{sig}"


def verify_service_token(
    token: str, secret: str, max_age: int = 3600,
) -> ServiceIdentity:
    """Verify and decode inter-service token."""
    parts = token.split("|")
    if len(parts) != 4:
        raise ValueError("Malformed token: expected 4 pipe-delimited segments")

    service_id, role, issued_str, signature = parts

    # Verify signature
    payload = f"{service_id}|{role}|{issued_str}"
    expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise ValueError("Invalid token signature")

    # Verify age
    issued = int(issued_str)
    now = int(time.time())
    if now - issued > max_age:
        raise ValueError("Token expired")
    if issued > now + 60:
        raise ValueError("Token issued in the future")

    return ServiceIdentity(service_id=service_id, role=role, issued_at=issued)


# ── SecurityContext signature verification ──────────────────


def verify_security_context(
    ctx: SecurityContext, signing_key: str,
) -> bool:
    """Verify that the SecurityContext was signed by L1 using the shared key.

    Returns True if valid, raises ValueError otherwise.
    """
    if ctx.is_expired:
        raise ValueError("SecurityContext has expired")

    payload = ctx.to_signable_payload()
    expected = hmac.new(
        signing_key.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(ctx.context_signature, expected):
        raise ValueError("SecurityContext signature mismatch")

    return True


def sign_security_context(ctx_dict: dict, signing_key: str) -> str:
    """Utility to sign a SecurityContext payload (for tests / L1 mock)."""
    from app.models.security import SecurityContext
    temp = SecurityContext(**{**ctx_dict, "context_signature": "placeholder"})
    payload = temp.to_signable_payload()
    return hmac.new(
        signing_key.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()


# ── FastAPI dependencies ────────────────────────────────────


async def require_service_auth(
    creds: HTTPAuthorizationCredentials = Security(_bearer),
    settings: Settings = Depends(get_settings),
) -> ServiceIdentity:
    """Verify inter-service bearer token."""
    try:
        identity = verify_service_token(
            creds.credentials,
            settings.service_token_secret,
            settings.context_max_age_seconds,
        )
    except ValueError as exc:
        logger.warning("auth_rejected", reason=str(exc))
        raise HTTPException(status_code=401, detail="Invalid service token")

    if identity.service_id not in settings.allowed_service_id_set:
        logger.warning("auth_rejected_service", service_id=identity.service_id)
        raise HTTPException(status_code=403, detail="Service not authorized")

    return identity


def require_permission(permission: str):
    """Factory returning a dependency that checks a specific permission."""

    async def _checker(
        identity: ServiceIdentity = Depends(require_service_auth),
    ) -> ServiceIdentity:
        if not identity.has_permission(permission):
            raise HTTPException(
                status_code=403,
                detail=f"Permission '{permission}' not granted for role '{identity.role}'",
            )
        return identity

    return _checker


def validate_request_context(
    ctx: SecurityContext, settings: Settings,
) -> None:
    """Validate SecurityContext — called inside route handlers.

    Raises HTTPException(401) on any validation failure.
    """
    try:
        verify_security_context(ctx, settings.context_signing_key)
    except ValueError as exc:
        logger.warning(
            "security_context_invalid",
            user_id=ctx.user_id,
            reason=str(exc),
        )
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired security context",
        )
