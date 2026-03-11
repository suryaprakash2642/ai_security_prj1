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

ENVELOPE_TTL_SECONDS = 300


def verify(envelope_dict: dict, signing_key: str,
           skip_in_dev: bool = True) -> tuple[bool, str]:
    """Verify envelope HMAC signature using same compact payload as L4 _sign_envelope.

    Returns (is_valid, reason). reason is "" on success.
    """
    signature = envelope_dict.get("signature", "")

    if not signature:
        if skip_in_dev:
            logger.debug("Skipping envelope verification (no signature, dev mode)")
            return True, ""
        return False, "Missing envelope signature"

    # Recompute using the same compact format as L4's _sign_envelope
    tables = []
    for tp in sorted(envelope_dict.get("table_permissions", []), key=lambda t: t.get("table_id", "")):
        tp_dict = {
            "id": tp.get("table_id", ""),
            "dec": tp.get("decision", ""),
            "cols": [
                {"n": c.get("column_name", ""), "v": c.get("visibility", "")}
                for c in sorted(tp.get("columns", []), key=lambda x: x.get("column_name", ""))
            ],
            "agg": tp.get("aggregation_only", False),
            "rows": tp.get("max_rows"),
        }
        if tp.get("row_filters"):
            tp_dict["rf"] = sorted(tp["row_filters"])
        tables.append(tp_dict)

    payload = {
        "request_id": envelope_dict.get("request_id", ""),
        "resolved_at": envelope_dict.get("resolved_at"),
        "policy_version": envelope_dict.get("policy_version", 1),
        "tables": tables,
    }
    payload_bytes = json.dumps(payload, separators=(',', ':'), sort_keys=True).encode("utf-8")
    expected = hmac.new(
        signing_key.encode("utf-8"), payload_bytes, hashlib.sha256
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
