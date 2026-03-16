"""Policy Orchestrator.

Ties together the entire L4 deterministic rules engine pipeline.
1. Collects policies from Neo4j
2. Resolves conflicts (with BTG override)
3. Aggregates conditions
4. Generates NL Rules
5. Signs and issues the Permission Envelope
"""

import hashlib
import hmac
import json
import time
import uuid
from datetime import UTC, datetime, timedelta

import structlog

from app.config import get_settings
from app.models.api_models import (
    BTGToken,
    PermissionEnvelope,
    PolicyResolveRequest,
    TablePermission,
)
from app.models.enums import ColumnVisibility, TableDecision
from app.services.condition_aggregator import ConditionAggregator
from app.services.conflict_resolver import ConflictResolver
from app.services.graph_client import GraphClient
from app.services.nl_rule_generator import NLRuleGenerator
from app.services.policy_collector import PolicyCollector

logger = structlog.get_logger(__name__)

# Resolution statistics (in-memory, per-process)
_stats = {
    "total_requests": 0,
    "total_latency_ms": 0.0,
    "total_policies_evaluated": 0,
    "total_denials": 0,
    "total_allows": 0,
    "btg_activations": 0,
    "errors": 0,
}


def get_stats() -> dict:
    """Return a copy of accumulated resolution statistics."""
    s = dict(_stats)
    if s["total_requests"] > 0:
        s["avg_latency_ms"] = round(s["total_latency_ms"] / s["total_requests"], 2)
    else:
        s["avg_latency_ms"] = 0.0
    return s


def clear_stats() -> None:
    """Reset all stats counters."""
    for k in _stats:
        _stats[k] = 0 if isinstance(_stats[k], int) else 0.0


class PolicyOrchestrator:
    """Manages the full resolution lifecycle for a single request."""

    def __init__(self, graph_client: GraphClient):
        self.collector = PolicyCollector(graph_client)
        self.settings = get_settings()

    def _sign_envelope(self, envelope: PermissionEnvelope) -> str:
        """Create an HMAC-SHA256 signature of the envelope contents."""

        # We sign a deterministic subset of the envelope that L5/L6 must trust
        payload = {
            "request_id": envelope.request_id,
            "resolved_at": envelope.resolved_at,
            "policy_version": envelope.policy_version,
            "tables": [],
        }

        # Sort tables and columns explicitly to guarantee stable list ordering for the hash
        for tp in sorted(envelope.table_permissions, key=lambda t: t.table_id):
            tp_dict = {
                "id": tp.table_id,
                "dec": tp.decision.value,
                "cols": [
                    {"n": c.column_name, "v": c.visibility.value}
                    for c in sorted(tp.columns, key=lambda x: x.column_name)
                ],
                "agg": tp.aggregation_only,
                "rows": tp.max_rows,
            }
            if tp.row_filters:
                tp_dict["rf"] = sorted(tp.row_filters)
            payload["tables"].append(tp_dict)

        # Sort the JSON explicitly before hashing to ensure determinism
        payload_str = json.dumps(payload, separators=(",", ":"), sort_keys=True)

        signature = hmac.new(
            self.settings.context_signing_key.encode("utf-8"),
            payload_str.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return signature

    @staticmethod
    def _is_btg_valid(btg: BTGToken) -> bool:
        """Check if a BTG token is currently valid (not expired)."""
        if not btg or not btg.expires_at:
            return False
        try:
            raw = btg.expires_at.rstrip("Z")
            # If no timezone info, assume UTC
            if "+" not in raw and raw[-1].isdigit():
                raw += "+00:00"
            expires = datetime.fromisoformat(raw)
            return datetime.now(UTC) < expires
        except (ValueError, TypeError):
            return False

    @staticmethod
    def _btg_overrides_table(table_id: str, btg: BTGToken, decision: TableDecision, policies) -> bool:
        """Determine if BTG should override a DENY for this table.

        BTG overrides DENY policies with priority < 200.
        Tables in btg.still_denied are never overridden.
        """
        if decision != TableDecision.DENY:
            return False
        # Check if table is in the BTG exclusion list
        if table_id in btg.still_denied:
            return False
        # Check for hard DENY (priority >= 200, no exception)
        for p in policies:
            if p.is_deny and p.priority >= 200:
                return False
        return True

    async def resolve(
        self, request: PolicyResolveRequest, *, trace: bool = False
    ) -> PermissionEnvelope | dict:
        """Execute the L4 policy resolution pipeline.

        If trace=True, returns a dict with the envelope plus full resolution trace.
        """
        start_time = time.perf_counter()
        now = datetime.now(UTC)
        trace_log: list[dict] = [] if trace else None

        # Initialize output artifact
        envelope = PermissionEnvelope(
            envelope_id=str(uuid.uuid4()),
            request_id=request.request_id,
            user_id=request.user_context.get("user_id", ""),
            effective_roles=sorted(request.effective_roles),
            resolved_at=now.isoformat() + "Z",
            expires_at=(now + timedelta(seconds=self.settings.envelope_ttl_seconds)).isoformat() + "Z",
            policy_version=1,
        )

        # BTG check
        btg = request.btg_token
        btg_active = btg is not None and self._is_btg_valid(btg)
        envelope.btg_active = btg_active
        if btg_active:
            _stats["btg_activations"] += 1

        total_policies_seen = 0

        try:
            # 1. Collect
            table_metadata_map = await self.collector.collect_metadata(
                request.candidate_table_ids,
                request.effective_roles,
            )

            aggregator = ConditionAggregator(request.user_context)
            all_active_policies = []

            # 2 & 3. Resolve & Aggregate
            for table_id in request.candidate_table_ids:
                meta = table_metadata_map.get(table_id)
                if not meta:
                    envelope.table_permissions.append(
                        TablePermission(
                            table_id=table_id,
                            decision=TableDecision.DENY,
                            reason="Table omitted from policy collector (internal error)",
                        )
                    )
                    continue

                total_policies_seen += len(meta.table_policies)

                # Clearance-level gating: user.clearance_level >= table.sensitivity_level
                user_clearance = request.user_context.get("clearance_level", 1)
                table_sensitivity = meta.sensitivity_level
                if user_clearance < table_sensitivity:
                    envelope.table_permissions.append(
                        TablePermission(
                            table_id=table_id,
                            decision=TableDecision.DENY,
                            reason=f"Clearance insufficient (user={user_clearance}, required={table_sensitivity})",
                        )
                    )
                    if trace_log is not None:
                        trace_log.append({
                            "table_id": table_id,
                            "decision": "DENY",
                            "reason": f"Clearance gating: {user_clearance} < {table_sensitivity}",
                        })
                    continue

                # Table-Level Resolution
                decision, active_policies, reason = ConflictResolver.resolve_table(meta)

                # BTG override: if table was denied but BTG is active and can override
                btg_override = False
                if btg_active and self._btg_overrides_table(
                    table_id, btg, decision, meta.table_policies
                ):
                    decision = TableDecision.ALLOW
                    reason = f"BTG override (token={btg.token_id}). Original: {reason}"
                    btg_override = True
                    # Under BTG, use all policies for column resolution
                    active_policies = [p for p in meta.table_policies if p.is_allow] or meta.table_policies

                table_perm = TablePermission(
                    table_id=table_id,
                    decision=decision,
                    reason=reason,
                )

                if trace_log is not None:
                    trace_log.append({
                        "table_id": table_id,
                        "policies_considered": [p.policy_id for p in meta.table_policies],
                        "decision": decision.value,
                        "reason": reason,
                        "btg_override": btg_override,
                    })

                if decision == TableDecision.ALLOW:
                    # Column-Level Resolution
                    table_perm.columns = ConflictResolver.resolve_columns(meta, active_policies)

                    # BTG row filter relaxation (spec §10.5):
                    #   - BTG + patient_mrn → scope to that patient only
                    #   - BTG + no patient_mrn → broader access (no row filters)
                    # This applies to ALL BTG-active tables, not just DENY overrides.
                    if btg_active and btg.patient_mrn:
                        table_perm.row_filters = [f"(patient_id = '{btg.patient_mrn}')"]
                    elif btg_active:
                        # Broader emergency access — no provider/unit/facility scoping
                        table_perm.row_filters = []
                    else:
                        # Normal (non-BTG) row filter aggregation
                        table_col_names = {cm.column_name for cm in meta.columns.values()} if meta else set()
                        aggregator.aggregate_table_conditions(active_policies, table_perm, table_col_names)

                        # Facility-scoped row filter: inject facility_id filter
                        # when the table has a facility_id column and the user
                        # has a facility_id in their context.
                        user_facility = request.user_context.get("facility_id", "")
                        if user_facility and "facility_id" in table_col_names:
                            facility_filter = f"facility_id = '{user_facility}'"
                            if facility_filter not in table_perm.row_filters:
                                table_perm.row_filters.append(facility_filter)

                    # Enforce denied_in_select at the column level: mark those
                    # columns HIDDEN so they never appear in the schema sent to
                    # the LLM.  This is the primary enforcement — NL rules and
                    # L6 gate checks are defence-in-depth only.
                    if table_perm.denied_in_select:
                        denied_set = set(table_perm.denied_in_select)
                        for cd in table_perm.columns:
                            if cd.column_name in denied_set:
                                cd.visibility = ColumnVisibility.HIDDEN
                                cd.reason = "HIDDEN by aggregation_only denied_in_select"

                    # Track policies for global constraints (like Joins)
                    all_active_policies.extend(active_policies)

                envelope.table_permissions.append(table_perm)

            # Global constraints
            envelope.join_restrictions = aggregator.extract_join_restrictions(all_active_policies)

            # 4. Generate Natural Language Rules for the LLM
            envelope.global_nl_rules = NLRuleGenerator.generate_global_rules(envelope.join_restrictions)
            for tp in envelope.table_permissions:
                if tp.decision == TableDecision.ALLOW:
                    tp.nl_rules = NLRuleGenerator.generate_table_rules(tp, tp.table_id)

            # Populate audit counters
            envelope.total_policies_evaluated = total_policies_seen
            envelope.total_tables_allowed = len(envelope.allowed_table_ids)
            envelope.total_tables_denied = len(envelope.denied_table_ids)

            # 5. Cryptographically sign the envelope
            envelope.signature = self._sign_envelope(envelope)

            elapsed_ms = (time.perf_counter() - start_time) * 1000
            envelope.resolution_latency_ms = round(elapsed_ms, 2)

            # Update stats
            _stats["total_requests"] += 1
            _stats["total_latency_ms"] += elapsed_ms
            _stats["total_policies_evaluated"] += total_policies_seen
            _stats["total_allows"] += envelope.total_tables_allowed
            _stats["total_denials"] += envelope.total_tables_denied

            logger.info(
                "policy_resolution_complete",
                request_id=request.request_id,
                allowed_tables=envelope.total_tables_allowed,
                denied_tables=envelope.total_tables_denied,
                btg_active=btg_active,
                duration_ms=round(elapsed_ms, 2),
            )

        except Exception as e:
            logger.exception(
                "policy_resolution_failed",
                request_id=request.request_id,
                error=str(e),
            )
            _stats["errors"] += 1
            # Fail closed on exception
            envelope.table_permissions = [
                TablePermission(
                    table_id=tid,
                    decision=TableDecision.DENY,
                    reason="Resolution Exception",
                )
                for tid in request.candidate_table_ids
            ]
            envelope.total_tables_denied = len(request.candidate_table_ids)
            envelope.total_tables_allowed = 0
            envelope.signature = self._sign_envelope(envelope)
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            envelope.resolution_latency_ms = round(elapsed_ms, 2)

        if trace:
            return {
                "envelope": envelope,
                "trace": trace_log or [],
                "policies_evaluated": total_policies_seen,
            }

        return envelope
