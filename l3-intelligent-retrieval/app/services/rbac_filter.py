"""RBAC Intersection Filter — primary security gate.

Two stages:
1. Permanent exclusion (substance_abuse, etc.) — hardcoded, no override
2. Policy-Level Resolution (L4 authoritative Permission Envelope) — fine-grained

L4 is the authoritative source for domain-based access control.  It queries
Neo4j directly for table policies, clearance gating, and domain membership.
Domain pre-filtering was removed from L3 because candidate tables retrieved
via vector search do not carry domain metadata (pgvector stores embeddings,
not domain tags).  Filtering on incomplete domain data caused valid tables
to be incorrectly denied.

Tables removed here are INVISIBLE to the LLM.
No downgrade, no hints, no metadata leaks (§13.2).
"""

from __future__ import annotations

import time

import structlog

from app.cache.cache_service import CacheService
from app.clients.l2_client import L2Client
from app.clients.l4_client import L4Client
from app.models.enums import TableDecision
from app.models.l4_models import PermissionEnvelope
from app.models.retrieval import CandidateTable
from app.models.security import SecurityContext

logger = structlog.get_logger(__name__)

# Tables that must NEVER be retrievable regardless of role (§13.1 hard DENY).
# These are hard-coded at ingestion time — not stored in vector DB (§13.3).
_PERMANENTLY_EXCLUDED_PATTERNS = [
    "substance_abuse",
    "behavioral_health_substance",
    "42cfr_part2",
]

# Sensitivity level at which ALL roles must EXPLICITLY allow a table (Fix 3 / §13.3).
_HIGH_SENSITIVITY_THRESHOLD = 5


class RBACFilter:
    """Enforces zero-trust access filtering on candidate tables.

    Stage 0: Permanent exclusion + hard_deny
    Stage 1: L4 policy resolution — authoritative PermissionEnvelope
    """

    def __init__(
        self,
        l2_client: L2Client,
        l4_client: L4Client,
        cache: CacheService,
    ) -> None:
        self._l2 = l2_client
        self._l4 = l4_client
        self._cache = cache

    async def filter_candidates(
        self,
        candidates: list[CandidateTable],
        context: SecurityContext,
        request_id: str = "",
    ) -> tuple[list[CandidateTable], PermissionEnvelope, dict[str, float]]:
        """Apply RBAC filtering.

        Returns:
            (surviving_candidates, permission_envelope, timing_ms)

        Surviving candidates have passed:
        0. Permanent exclusion (substance_abuse, 42CFR, hard_deny)
        1. L4 policy resolution (full PermissionEnvelope, deny-by-default)
        """
        timing: dict[str, float] = {}

        # Stage 0: Remove permanently excluded tables (hardcoded, no override)
        candidates = self._exclude_permanent(candidates)

        # Stage 0.5: Remove hard_deny tables (§13.1 hard DENY overrides everything)
        candidates = [c for c in candidates if not c.hard_deny]

        if not candidates:
            return [], PermissionEnvelope(request_id=request_id), timing

        # Stage 1: L4 policy resolution (authoritative — handles domain, clearance, policies)
        t1 = time.monotonic()
        envelope = await self._resolve_policies(
            candidates, context, request_id
        )
        timing["rbac_policy_ms"] = (time.monotonic() - t1) * 1000

        # Apply L4 decisions (deny-by-default — no explicit permit = deny)
        surviving = self._apply_policy_decisions(candidates, envelope)

        return surviving, envelope, timing

    # ── Stage 0: Permanent exclusions ──────────────────────

    def _exclude_permanent(
        self, candidates: list[CandidateTable],
    ) -> list[CandidateTable]:
        """Remove tables that must never be retrievable (spec §13.3).

        Checks both table_name and table_id (FQN) to prevent bypass via
        aliasing or schema qualification.
        """
        result: list[CandidateTable] = []
        for c in candidates:
            name_lower = c.table_name.lower()
            id_lower = c.table_id.lower()
            excluded = any(
                pattern in name_lower or pattern in id_lower
                for pattern in _PERMANENTLY_EXCLUDED_PATTERNS
            )
            if excluded:
                logger.info(
                    "permanently_excluded",
                    table=c.table_id,
                    reason="hardcoded_sensitivity5_substance_abuse",
                )
            else:
                result.append(c)
        return result

    # ── Stage 1: L4 policy resolution ──────────────────────

    async def _resolve_policies(
        self,
        candidates: list[CandidateTable],
        context: SecurityContext,
        request_id: str,
    ) -> PermissionEnvelope:
        """Call the authoritative L4 Policy Resolution Layer.

        L4 handles domain access, clearance gating, and policy resolution
        using Neo4j as the source of truth for table domains and policies.
        """
        table_ids = [c.table_id for c in candidates]

        # Identify sensitivity-5 candidates for explicit multi-role check
        sensitivity5_ids = [
            c.table_id for c in candidates
            if c.sensitivity_level >= _HIGH_SENSITIVITY_THRESHOLD
        ]

        user_ctx = {
            "user_id": context.user_id,
            "department": context.department,
            "unit_id": context.unit_id,
            "provider_id": context.provider_id,
            "facility_id": context.facility_id,
            "clearance_level": context.clearance_level,
            "break_glass": context.break_glass,
            "purpose": context.purpose,
            "sensitivity5_table_ids": sensitivity5_ids,
        }

        # Construct BTGToken for L4 when break_glass is active
        btg_token = None
        if context.break_glass:
            from app.models.l4_models import BTGToken
            btg_token = BTGToken(
                token_id=context.session_id,
                user_id=context.user_id,
                patient_mrn=context.btg_patient_id or None,
                reason="Emergency access",
                expires_at=context.context_expiry.isoformat(),
            )

        return await self._l4.resolve_policies(
            candidate_table_ids=table_ids,
            effective_roles=context.effective_roles,
            user_context=user_ctx,
            request_id=request_id,
            btg_token=btg_token,
        )

    def _apply_policy_decisions(
        self,
        candidates: list[CandidateTable],
        envelope: PermissionEnvelope,
    ) -> list[CandidateTable]:
        """Remove candidates that L4 denied.

        Deny-by-default (spec §13.1): no explicit permission = deny.
        """
        surviving: list[CandidateTable] = []
        denied_fqns: list[str] = []

        for c in candidates:
            perm = envelope.get_table_permission(c.table_id)
            if perm is None:
                # No explicit permission granted = deny by default (spec §13.1)
                logger.debug("deny_by_default", table=c.table_id)
                denied_fqns.append(c.table_id)
                continue
            if perm.decision == TableDecision.DENY:
                logger.debug("l4_denied", table=c.table_id, reason=perm.reason)
                denied_fqns.append(c.table_id)
                continue
            surviving.append(c)

        # Emit per-table denied audit record (spec §16 step 12 — log retrieval metrics)
        if denied_fqns:
            logger.info(
                "rbac_denied_tables",
                denied_count=len(denied_fqns),
                # Emit FQNs for audit trail (NOT sent to client — spec §13.2)
                denied_table_fqns=denied_fqns,
            )

        return surviving
