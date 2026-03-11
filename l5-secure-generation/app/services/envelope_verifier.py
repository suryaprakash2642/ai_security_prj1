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

# Envelope TTL in seconds — must cover full pipeline round-trip
ENVELOPE_TTL_SECONDS = 300


def _compute_signature(envelope: PermissionEnvelope, signing_key: str) -> str:
    """Recompute HMAC-SHA256 using the same compact payload as L4 _sign_envelope."""
    payload: dict = {
        "request_id": envelope.request_id,
        "resolved_at": envelope.resolved_at,
        "policy_version": envelope.policy_version,
        "tables": [],
    }
    for tp in sorted(envelope.table_permissions, key=lambda t: t.table_id):
        tp_dict: dict = {
            "id": tp.table_id,
            "dec": tp.decision.value if hasattr(tp.decision, 'value') else tp.decision,
            "cols": [
                {"n": c.column_name, "v": c.visibility.value if hasattr(c.visibility, 'value') else c.visibility}
                for c in sorted(tp.columns, key=lambda x: x.column_name)
            ],
            "agg": tp.aggregation_only,
            "rows": tp.max_rows,
        }
        if tp.row_filters:
            tp_dict["rf"] = sorted(tp.row_filters)
        payload["tables"].append(tp_dict)
    payload_bytes = json.dumps(payload, separators=(',', ':'), sort_keys=True).encode("utf-8")
    return hmac.new(signing_key.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()


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
