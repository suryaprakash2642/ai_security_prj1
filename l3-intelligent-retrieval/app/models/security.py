"""Security context models — validated on every retrieval request.

The SecurityContext is produced by L1 (Identity & Context) and signed
with an HMAC. L3 verifies the signature and expiry before processing.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SecurityContext(BaseModel):
    """Signed security context from L1 Identity service.

    Every retrieval request must carry a valid SecurityContext.
    Missing, expired, or tampered contexts result in immediate 401.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    user_id: str = Field(..., min_length=1, description="Authenticated user identifier")
    effective_roles: list[str] = Field(
        ..., min_length=1, description="Active roles after MFA / session elevation"
    )
    department: str = Field(..., min_length=1)
    unit_id: str = Field(default="")
    provider_id: str = Field(default="")
    facility_id: str = Field(default="")
    clearance_level: int = Field(
        ..., ge=1, le=5, description="1=public, 5=top-secret"
    )
    session_id: str = Field(..., min_length=1)
    context_signature: str = Field(
        ..., min_length=1, description="HMAC-SHA256 of context payload"
    )
    context_expiry: datetime = Field(
        ..., description="UTC expiry timestamp"
    )

    # Optional enrichment fields
    purpose: str = Field(default="", description="Stated query purpose")
    break_glass: bool = Field(default=False, description="Emergency access flag")
    btg_patient_id: str = Field(default="", description="Patient ID scoped by BTG (if any)")
    mfa_verified: bool = Field(default=False)

    @field_validator("effective_roles")
    @classmethod
    def validate_roles_not_empty(cls, v: list[str]) -> list[str]:
        if not v or not any(r.strip() for r in v):
            raise ValueError("At least one effective role is required")
        return [r.strip() for r in v if r.strip()]

    @property
    def is_expired(self) -> bool:
        return datetime.now(UTC) > self.context_expiry

    @property
    def role_set_hash(self) -> str:
        """Deterministic hash of sorted roles for cache keying."""
        import hashlib
        joined = "|".join(sorted(self.effective_roles))
        return hashlib.sha256(joined.encode()).hexdigest()[:16]

    def to_signable_payload(self) -> str:
        """Reconstruct the payload that L1 signed (excluding signature)."""
        parts = [
            self.user_id,
            ",".join(sorted(self.effective_roles)),
            self.department,
            self.session_id,
            str(int(self.context_expiry.timestamp())),
            str(self.clearance_level),
        ]
        return "|".join(parts)


class ServiceIdentity(BaseModel):
    """Parsed inter-service auth identity (from L5, admin console, etc.)."""

    model_config = ConfigDict(frozen=True)

    service_id: str
    role: str
    issued_at: float

    def has_permission(self, permission: str) -> bool:
        from app.models.enums import ServiceRole

        _perms: dict[str, set[str]] = {
            ServiceRole.PIPELINE_READER.value: {"resolve", "explain", "health", "stats"},
            ServiceRole.POLICY_RESOLVER.value: {"resolve", "health"},
            ServiceRole.ADMIN.value: {
                "resolve", "explain", "health", "stats", "cache_clear", "admin",
            },
        }
        return permission in _perms.get(self.role, set())
