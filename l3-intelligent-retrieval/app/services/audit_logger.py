"""Audit Logger — structured security audit events for the Retrieval Layer.

Implements audit requirements from:
  §13.3  SENSITIVE_TABLE_ACCESS logging (sensitivity-5 table attempts)
  §16.   step 12: "Log retrieval metrics to audit system"
  §13.1  hard DENY = log as ATTEMPTED_ACCESS_RESTRICTED_DATA

Break-glass access (Fix 5 from audit):
  When SecurityContext.break_glass=True, emit a dedicated audit event to
  comply with HIPAA §164.312(b) audit control requirements.
  Break-glass sessions must have a TTL ≤ 15 minutes enforced here.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# Maximum allowed duration for a break-glass session (seconds) — 15 minutes
_BREAK_GLASS_MAX_TTL_SECONDS = 900


def log_break_glass_access(
    *,
    request_id: str,
    user_id: str,
    provider_id: str,
    facility_id: str,
    department: str,
    unit_id: str,
    session_id: str,
    purpose: str,
    context_expiry: datetime,
    context_issued: datetime | None = None,
) -> None:
    """Emit a structured break-glass access audit event.

    This event should be routed to an immutable compliance audit log
    (e.g., SIEM, CloudTrail, or a write-once S3 bucket). The log must
    not be writable by the same service that creates it.

    Args:
        request_id: UUID of the current retrieval request
        user_id: Authenticated user identifier from SecurityContext
        provider_id: Provider identifier (e.g., DR-4521)
        facility_id: Facility identifier (e.g., APOLLO-CHN-001)
        department: Clinical department
        unit_id: Hospital unit
        session_id: Session identifier from SecurityContext
        purpose: Stated purpose for the break-glass access
        context_expiry: When the SecurityContext expires
        context_issued: When the SecurityContext was issued (for TTL validation)
    """
    event: dict[str, Any] = {
        "event_type": "BREAK_GLASS_ACCESS",
        "request_id": request_id,
        "user_id": user_id,
        "provider_id": provider_id,
        "facility_id": facility_id,
        "department": department,
        "unit_id": unit_id,
        "session_id": session_id,
        "purpose": purpose or "NOT_STATED",
        "context_expiry_utc": context_expiry.isoformat(),
        "logged_at_utc": datetime.now(UTC).isoformat(),
        # Fingerprint for deduplication in SIEM
        "audit_fingerprint": hashlib.sha256(
            f"{user_id}|{session_id}|{request_id}".encode()
        ).hexdigest()[:16],
    }
    logger.warning("break_glass_access", **event)


def validate_break_glass_ttl(
    context_expiry: datetime,
    request_id: str,
    user_id: str,
) -> bool:
    """Validate that the break-glass session has not exceeded the 15-minute TTL.

    Returns True if valid. Logs a warning and returns False if the window is
    too long, indicating a potentially forged or incorrectly configured token.

    Note: this checks expiry window, not time-since-issued. L1 controls the
    actual TTL; L3 verifies it is within the allowed envelope.
    """
    now = datetime.now(UTC)
    # context_expiry must be within 15 minutes of now (not far in the future)
    remaining_seconds = (context_expiry - now).total_seconds()

    if remaining_seconds > _BREAK_GLASS_MAX_TTL_SECONDS:
        logger.error(
            "break_glass_ttl_violation",
            request_id=request_id,
            user_id=user_id,
            remaining_seconds=remaining_seconds,
            max_allowed_seconds=_BREAK_GLASS_MAX_TTL_SECONDS,
            reason="break_glass_session_window_exceeds_15_minutes",
        )
        return False
    return True


def log_sensitivity5_attempt(
    *,
    request_id: str,
    user_id: str,
    effective_roles: list[str],
    candidate_table_ids: list[str],
    denial_reason: str = "SENSITIVITY_5_RESTRICTED",
) -> None:
    """Log an attempt to access sensitivity-5 restricted data (spec §13.3).

    Triggered when all post-RBAC candidates have sensitivity_level >= 5.
    Per spec §10.4, this should be logged as ATTEMPTED_ACCESS_RESTRICTED_DATA.
    """
    logger.warning(
        "attempted_access_restricted_data",
        request_id=request_id,
        user_id=user_id,
        effective_roles=effective_roles,
        candidate_table_count=len(candidate_table_ids),
        # Log table FQNs for compliance — NOT returned to client (spec §13.2)
        candidate_table_ids=candidate_table_ids,
        denial_reason=denial_reason,
        logged_at_utc=datetime.now(UTC).isoformat(),
    )


def log_retrieval_metrics(
    *,
    request_id: str,
    user_id: str,
    tables_in_result: int,
    denied_count: int,
    total_latency_ms: float,
    strategies_used: list[str],
) -> None:
    """Log retrieval pipeline metrics to audit system (spec §16 step 12)."""
    logger.info(
        "retrieval_metrics",
        request_id=request_id,
        user_id=user_id,
        tables_in_result=tables_in_result,
        denied_count=denied_count,
        total_latency_ms=round(total_latency_ms, 2),
        strategies_used=strategies_used,
    )
