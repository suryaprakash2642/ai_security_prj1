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


def _compute_signature_candidates(envelope_dict: dict, signing_key: str) -> list[str]:
    table_permissions = envelope_dict.get("table_permissions", []) or []
    compact_payload = {
        "request_id": envelope_dict.get("request_id", ""),
        "resolved_at": envelope_dict.get("resolved_at"),
        "policy_version": envelope_dict.get("policy_version", 1),
        "tables": [],
    }

    for tp in sorted(table_permissions, key=lambda t: t.get("table_id", "")):
        cols = tp.get("columns", []) or []
        tp_dict = {
            "id": tp.get("table_id", ""),
            "dec": tp.get("decision", "DENY"),
            "cols": [
                {"n": c.get("column_name", ""), "v": c.get("visibility", "VISIBLE")}
                for c in sorted(cols, key=lambda c: c.get("column_name", ""))
            ],
            "agg": bool(tp.get("aggregation_only", False)),
            "rows": tp.get("max_rows"),
        }
        row_filters = tp.get("row_filters", []) or []
        if row_filters:
            tp_dict["rf"] = sorted(row_filters)
        compact_payload["tables"].append(tp_dict)

    compact_bytes = json.dumps(compact_payload, separators=(",", ":"), sort_keys=True).encode()
    compact_sig = hmac.new(signing_key.encode(), compact_bytes, hashlib.sha256).hexdigest()

    legacy_payload = {
        "request_id": envelope_dict.get("request_id", ""),
        "table_permissions": table_permissions,
        "join_restrictions": envelope_dict.get("join_restrictions", []) or [],
        "global_nl_rules": envelope_dict.get("global_nl_rules", []) or [],
        "resolved_at": envelope_dict.get("resolved_at"),
        "policy_version": envelope_dict.get("policy_version", 1),
    }
    legacy_bytes = json.dumps(legacy_payload, sort_keys=True, default=str).encode()
    legacy_sig = hmac.new(signing_key.encode(), legacy_bytes, hashlib.sha256).hexdigest()

    return [compact_sig, legacy_sig]


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

    candidates = _compute_signature_candidates(envelope_dict, signing_key)
    if not any(hmac.compare_digest(expected, signature) for expected in candidates):
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
