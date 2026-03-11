"""Permission Envelope HMAC Verifier (L7 independent copy).

L7 independently verifies the envelope — defense in depth per spec.
In dev mode, empty signatures are skipped.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time

import structlog

logger = structlog.get_logger(__name__)

ENVELOPE_TTL_SECONDS = 60


def verify(envelope_dict: dict, signing_key: str,
           skip_in_dev: bool = True) -> tuple[bool, str]:
    """Verify envelope HMAC signature.

    Returns (is_valid, reason). reason is "" on success.
    """
    signature = envelope_dict.get("signature", "")

    if not signature:
        if skip_in_dev:
            logger.debug("Skipping envelope verification (no signature, dev mode)")
            return True, ""
        return False, "Missing envelope signature"

    # Recompute signature over canonical payload
    payload = {
        "request_id": envelope_dict.get("request_id", ""),
        "table_permissions": envelope_dict.get("table_permissions", []),
        "join_restrictions": envelope_dict.get("join_restrictions", []),
        "global_nl_rules": envelope_dict.get("global_nl_rules", []),
        "resolved_at": envelope_dict.get("resolved_at"),
        "policy_version": envelope_dict.get("policy_version", 1),
    }
    payload_bytes = json.dumps(payload, sort_keys=True, default=str).encode()
    expected = hmac.new(
        signing_key.encode(), payload_bytes, hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected, signature):
        logger.warning("envelope_signature_mismatch",
                       request_id=envelope_dict.get("request_id"))
        return False, "Invalid envelope signature"

    # TTL check
    resolved_at = envelope_dict.get("resolved_at")
    if resolved_at:
        try:
            from datetime import datetime, timezone
            ts = datetime.fromisoformat(resolved_at).timestamp()
            age = time.time() - ts
            if age > ENVELOPE_TTL_SECONDS:
                return False, f"Envelope expired ({age:.0f}s > {ENVELOPE_TTL_SECONDS}s TTL)"
        except (ValueError, TypeError):
            pass

    return True, ""
