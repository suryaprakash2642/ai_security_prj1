"""Policy Orchestrator.

Ties together the entire L4 deterministic rules engine pipeline.
1. Collects policies from Neo4j
2. Resolves conflicts
3. Aggregates conditions
4. Generates NL Rules
5. Signs and issues the Permission Envelope
"""

import hashlib
import hmac
import json
import time
from datetime import UTC, datetime

import structlog

from app.config import get_settings
from app.models.api_models import PermissionEnvelope, PolicyResolveRequest, TablePermission
from app.models.enums import TableDecision
from app.services.condition_aggregator import ConditionAggregator
from app.services.conflict_resolver import ConflictResolver
from app.services.graph_client import GraphClient
from app.services.nl_rule_generator import NLRuleGenerator
from app.services.policy_collector import PolicyCollector

logger = structlog.get_logger(__name__)


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
            "tables": []
        }
        
        # Sort tables and columns explicitly to guarantee stable list ordering for the hash
        for tp in sorted(envelope.table_permissions, key=lambda t: t.table_id):
            tp_dict = {
                "id": tp.table_id,
                "dec": tp.decision.value,
                "cols": [{"n": c.column_name, "v": c.visibility.value} for c in sorted(tp.columns, key=lambda x: x.column_name)],
                "agg": tp.aggregation_only,
                "rows": tp.max_rows
            }
            if tp.row_filters:
                tp_dict["rf"] = sorted(tp.row_filters)
            payload["tables"].append(tp_dict)

        # Sort the JSON explicitly before hashing to ensure determinism
        payload_str = json.dumps(payload, separators=(',', ':'), sort_keys=True)
        
        signature = hmac.new(
            self.settings.envelope_signing_key.encode("utf-8"),
            payload_str.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        
        return signature

    async def resolve(self, request: PolicyResolveRequest) -> PermissionEnvelope:
        """Execute the L4 policy resolution pipeline."""
        start_time = time.perf_counter()
        
        # Initialize output artifact
        envelope = PermissionEnvelope(
            request_id=request.request_id,
            resolved_at=datetime.now(UTC).isoformat() + "Z",
            policy_version=1  # In a real app, from Neo4j schema version
        )

        try:
            # 1. Collect
            table_metadata_map = await self.collector.collect_metadata(
                request.candidate_table_ids, 
                request.effective_roles
            )
            
            aggregator = ConditionAggregator(request.user_context)
            all_active_policies = []

            # 2 & 3. Resolve & Aggregate
            for table_id in request.candidate_table_ids:
                meta = table_metadata_map.get(table_id)
                if not meta:
                    # Should not happen as collector populates dummy entries
                    # but defensively deny.
                    envelope.table_permissions.append(TablePermission(
                        table_id=table_id,
                        decision=TableDecision.DENY,
                        reason="Table omitted from policy collector (internal error)"
                    ))
                    continue

                # Table-Level Resolution
                decision, active_policies, reason = ConflictResolver.resolve_table(meta)
                
                table_perm = TablePermission(
                    table_id=table_id,
                    decision=decision,
                    reason=reason
                )

                if decision == TableDecision.ALLOW:
                    # Column-Level Resolution
                    table_perm.columns = ConflictResolver.resolve_columns(meta, active_policies)
                    
                    # Row-Level & Constraint Aggregation
                    aggregator.aggregate_table_conditions(active_policies, table_perm)
                    
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

            # 5. Cryptographically sign the envelope
            envelope.signature = self._sign_envelope(envelope)

            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.info(
                "policy_resolution_complete",
                request_id=request.request_id,
                allowed_tables=len(envelope.allowed_table_ids),
                denied_tables=len(envelope.denied_table_ids),
                duration_ms=round(elapsed_ms, 2)
            )

        except Exception as e:
            logger.exception("policy_resolution_failed", request_id=request.request_id, error=str(e))
            # Fail closed on exception
            envelope.table_permissions = [
                TablePermission(table_id=tid, decision=TableDecision.DENY, reason="Resolution Exception") 
                for tid in request.candidate_table_ids
            ]
            envelope.signature = self._sign_envelope(envelope)

        return envelope
