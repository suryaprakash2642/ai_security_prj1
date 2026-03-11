"""Permission Envelope HMAC Verifier.

Independently verifies that the Permission Envelope has not been
tampered with and has not expired.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time

import structlog

from app.models.api import PermissionEnvelope

logger = structlog.get_logger(__name__)

# Envelope TTL in seconds (60s per spec)
ENVELOPE_TTL_SECONDS = 60


def _compute_signature(envelope: PermissionEnvelope, signing_key: str) -> str:
    """Recompute the HMAC-SHA256 signature for the envelope payload."""
    payload = {
        "request_id": envelope.request_id,
        "table_permissions": [tp.model_dump() for tp in envelope.table_permissions],
        "join_restrictions": [jr.model_dump() for jr in envelope.join_restrictions],
        "global_nl_rules": envelope.global_nl_rules,
        "resolved_at": envelope.resolved_at,
        "policy_version": envelope.policy_version,
    }
    payload_bytes = json.dumps(payload, sort_keys=True, default=str).encode()
    return hmac.new(signing_key.encode(), payload_bytes, hashlib.sha256).hexdigest()


def verify(envelope: PermissionEnvelope, signing_key: str) -> tuple[bool, str]:
    """Verify the envelope signature and freshness.

    Returns (is_valid, reason). reason is empty on success.
    """
    if not envelope.signature:
        return False, "Missing envelope signature"

    expected_sig = _compute_signature(envelope, signing_key)
    if not hmac.compare_digest(expected_sig, envelope.signature):
        logger.warning("Envelope signature mismatch",
                       request_id=envelope.request_id)
        return False, "Invalid envelope signature"

    # Freshness check (resolved_at is ISO format timestamp)
    if envelope.resolved_at:
        try:
            from datetime import datetime, timezone
            resolved_ts = datetime.fromisoformat(envelope.resolved_at).timestamp()
            age = time.time() - resolved_ts
            if age > ENVELOPE_TTL_SECONDS:
                logger.warning("Envelope expired", age_seconds=age,
                               request_id=envelope.request_id)
                return False, f"Envelope expired ({age:.0f}s ago, TTL={ENVELOPE_TTL_SECONDS}s)"
        except (ValueError, TypeError):
            pass  # If we can't parse the timestamp, allow it through

    return True, ""
