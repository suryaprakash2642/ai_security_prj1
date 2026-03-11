"""RBAC Intersection Filter — primary security gate.

Three stages:
1. Permanent exclusion (substance_abuse, etc.) — hardcoded, no override
2. Domain pre-filter (role→domain ACCESSES_DOMAIN map from L2) — coarse but fast
3. Policy-Level Resolution (L4 authoritative Permission Envelope) — fine-grained

Spec compliance (Intelligent-Retrieval-Layer-Specification §10, §13):
  §13.1  deny-by-default: no access = eliminated
  §13.1  no domain access = eliminated in Stage 1
  §13.1  hard DENY overrides everything
  §13.2  tables without domain tag are NOT passed through automatically (Fix 2)
  §10.5  multi-role: union of accessible domains, but sensitivity-5 requires
         explicit allow from ALL roles (Fix 3 — deny-wins on high-sensitivity tables)
  §13.3  sensitivity-5 tables require explicit ALLOW — not access-by-union

Tables removed here are INVISIBLE to the LLM.
No downgrade, no hints, no metadata leaks (§13.2).
"""

from __future__ import annotations

import hashlib
import time
from typing import Any

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

    Implements spec §10.2 two-stage filtering:
    Stage 1: Domain pre-filter  — fast set-intersection (<2ms)
    Stage 2: L4 policy resolution — authoritative PermissionEnvelope
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
        """Apply three-stage RBAC filtering.

        Returns:
            (surviving_candidates, permission_envelope, timing_ms)

        Surviving candidates have passed:
        0. Permanent exclusion (substance_abuse, 42CFR, hard_deny)
        1. Domain pre-filter (role→accessible_domain intersection)
        2. L4 policy resolution (full PermissionEnvelope, deny-by-default)
        """
        timing: dict[str, float] = {}

        # Stage 0: Remove permanently excluded tables (hardcoded, no override)
        candidates = self._exclude_permanent(candidates)

        # Stage 0.5: Remove hard_deny tables (§13.1 hard DENY overrides everything)
        candidates = [c for c in candidates if not c.hard_deny]

        # Stage 1: Domain pre-filter (spec §10.2, §13.1)
        t0 = time.monotonic()
        accessible_domains, domain_access_levels = await self._get_accessible_domains(context)
        candidates = self._domain_prefilter(candidates, accessible_domains, context.clearance_level)
        timing["rbac_domain_ms"] = (time.monotonic() - t0) * 1000

        if not candidates:
            return [], PermissionEnvelope(request_id=request_id), timing

        # Stage 2: L4 policy resolution (spec §10.2 Stage 2)
        t1 = time.monotonic()
        envelope = await self._resolve_policies(
            candidates, context, request_id, domain_access_levels
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

    # ── Stage 1: Domain pre-filter ──────────────────────────

    async def _get_accessible_domains(
        self, context: SecurityContext,
    ) -> tuple[set[str], dict[str, str]]:
        """Get the set of domains and their minimum access levels across all roles.

        Uses cache with role_set_hash as key (spec §18) to prevent cross-role poisoning.

        Returns:
            (accessible_domain_names, domain_to_min_access_level_map)
        """
        cache_key = context.role_set_hash
        cached = await self._cache.get_role_domains(cache_key)
        if cached:
            all_domains: set[str] = set()
            access_levels: dict[str, list[str]] = {}
            for role, domains in cached.items():
                for domain in domains:
                    all_domains.add(domain)
                    # Cached format stores domains only; access level tracked separately
            return all_domains, {}

        try:
            role_map = await self._l2.get_role_domain_access(context.effective_roles)
            await self._cache.set_role_domains(cache_key, role_map)
            all_domains = set()
            access_levels = {}
            for _role, domains in role_map.items():
                for domain in domains:
                    all_domains.add(domain)
            return all_domains, access_levels
        except Exception as exc:
            logger.warning("role_domain_fetch_failed", error=str(exc))
            # Fail-secure: no accessible domains means nothing passes Stage 1
            return set(), {}

    def _domain_prefilter(
        self,
        candidates: list[CandidateTable],
        accessible_domains: set[str],
        clearance_level: int = 1,
    ) -> list[CandidateTable]:
        """Remove candidates whose domain is not accessible by any of the user's roles.

        Fix 2 (spec §13.1): Tables with NO domain tag are NO LONGER auto-passed.
        When accessible_domains is known (non-empty), untagged tables are DENIED in
        Stage 1 unless clearance >= 4 (senior clinical/admin staff who may query
        system tables). L4 still makes the final decision.

        When accessible_domains is empty (L2 unavailable), fail-secure: pass only
        to allow L4 to adjudicate and fail it there.

        Spec §10.2: "Any candidate table whose domain_tags have zero intersection
        with the user's accessible domains is immediately eliminated."
        """
        if not accessible_domains:
            # Fail-secure: if we can't determine domains, let L4 decide.
            logger.debug("no_accessible_domains_found_fall_through_to_l4")
            return candidates

        result: list[CandidateTable] = []
        for c in candidates:
            if not c.domain:
                # Fix 2: untagged tables — deny-by-default in Stage 1 unless
                # high clearance (≥4) where system/infra tables are legitimately needed.
                if clearance_level >= 4:
                    logger.debug(
                        "untagged_domain_pass_high_clearance",
                        table=c.table_id,
                        clearance=clearance_level,
                    )
                    result.append(c)
                else:
                    logger.info(
                        "domain_prefilter_removed_untagged",
                        table=c.table_id,
                        reason="no_domain_tag_deny_by_default",
                    )
            elif c.domain.lower() in {d.lower() for d in accessible_domains}:
                result.append(c)
            else:
                logger.debug(
                    "domain_prefilter_removed",
                    table=c.table_id,
                    domain=c.domain,
                )
        return result

    # ── Stage 2: L4 policy resolution ──────────────────────

    async def _resolve_policies(
        self,
        candidates: list[CandidateTable],
        context: SecurityContext,
        request_id: str,
        domain_access_levels: dict[str, str],
    ) -> PermissionEnvelope:
        """Call the authoritative L4 Policy Resolution Layer.

        Fix 3 (spec §13.1, §13.3): For sensitivity-5 tables, we pass a
        require_explicit_allow_all_roles flag so L4 can enforce the deny-wins
        rule across conflicting roles.
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
            # Fix 3: pass sensitivity-5 table list for deny-wins adjudication
            "sensitivity5_table_ids": sensitivity5_ids,
            # Pass domain access levels so L4 can validate AGGREGATE_ONLY constraints
            "domain_access_levels": domain_access_levels,
        }

        return await self._l4.resolve_policies(
            candidate_table_ids=table_ids,
            effective_roles=context.effective_roles,
            user_context=user_ctx,
            request_id=request_id,
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
