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


def _compute_signature_candidates(envelope: PermissionEnvelope, signing_key: str) -> list[str]:

    def _enum_or_str(value: object) -> str:
        return str(getattr(value, "value", value))

    compact_payload = {
        "request_id": envelope.request_id,
        "resolved_at": envelope.resolved_at,
        "policy_version": envelope.policy_version,
        "tables": [],
    }

    for tp in sorted(envelope.table_permissions, key=lambda t: t.table_id):
        tp_dict = {
            "id": tp.table_id,
            "dec": _enum_or_str(tp.decision),
            "cols": [
                {"n": c.column_name, "v": _enum_or_str(c.visibility)}
                for c in sorted(tp.columns, key=lambda x: x.column_name)
            ],
            "agg": tp.aggregation_only,
            "rows": tp.max_rows,
        }
        if tp.row_filters:
            tp_dict["rf"] = sorted(tp.row_filters)
        compact_payload["tables"].append(tp_dict)

    compact_bytes = json.dumps(compact_payload, separators=(",", ":"), sort_keys=True).encode()
    compact_sig = hmac.new(signing_key.encode(), compact_bytes, hashlib.sha256).hexdigest()

    legacy_payload = {
        "request_id": envelope.request_id,
        "table_permissions": [tp.model_dump() for tp in envelope.table_permissions],
        "join_restrictions": [jr.model_dump() for jr in envelope.join_restrictions],
        "global_nl_rules": envelope.global_nl_rules,
        "resolved_at": envelope.resolved_at,
        "policy_version": envelope.policy_version,
    }
    legacy_bytes = json.dumps(legacy_payload, sort_keys=True, default=str).encode()
    legacy_sig = hmac.new(signing_key.encode(), legacy_bytes, hashlib.sha256).hexdigest()

    return [compact_sig, legacy_sig]


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

    candidates = _compute_signature_candidates(envelope, signing_key)
    if not any(hmac.compare_digest(expected, envelope.signature) for expected in candidates):
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
