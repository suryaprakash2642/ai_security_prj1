"""Permission Envelope HMAC Verifier (L6 independent copy).

L6 independently verifies the envelope — it does NOT trust that L5
already verified it. This is a core principle of the zero-trust model.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time

import structlog

from app.models.api import PermissionEnvelope

logger = structlog.get_logger(__name__)

ENVELOPE_TTL_SECONDS = 60


def _compute_signature(envelope: PermissionEnvelope, signing_key: str) -> str:
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


def verify(envelope: PermissionEnvelope, signing_key: str,
           skip_in_dev: bool = True) -> tuple[bool, str]:
    """Verify envelope HMAC signature and TTL.

    Returns (is_valid, reason). reason is "" on success.
    In development mode (skip_in_dev=True), skips verification if no signature present.
    """
    if not envelope.signature:
        if skip_in_dev:
            logger.debug("Skipping envelope verification (no signature, dev mode)")
            return True, ""
        return False, "Missing envelope signature"

    expected = _compute_signature(envelope, signing_key)
    if not hmac.compare_digest(expected, envelope.signature):
        logger.warning("Envelope signature mismatch", request_id=envelope.request_id)
        return False, "Invalid envelope signature"

    if envelope.resolved_at:
        try:
            from datetime import datetime, timezone
            ts = datetime.fromisoformat(envelope.resolved_at).timestamp()
            age = time.time() - ts
            if age > ENVELOPE_TTL_SECONDS:
                return False, f"Envelope expired ({age:.0f}s > {ENVELOPE_TTL_SECONDS}s TTL)"
        except (ValueError, TypeError):
            pass

    return True, ""
