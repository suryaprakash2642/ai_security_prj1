"""Policy Service — CRUD operations, simulation engine, and version rollback.

Enforces mandatory dual-representation (nl_description + structured_rule),
hard deny protections, and audit logging for all policy mutations.
"""

from __future__ import annotations

import json
from typing import Any

import structlog

from app.models.api import (
    ConditionResponse,
    PolicyResponse,
    PolicySimulateRequest,
    PolicySimulateResult,
)
from app.models.audit import ChangeRecord, PolicyVersionRecord
from app.models.enums import ChangeAction, ChangeSource, PolicyType
from app.models.graph import PolicyNode
from app.repositories.audit_repository import AuditRepository
from app.repositories.graph_read_repo import GraphReadRepository
from app.repositories.graph_write_repo import GraphWriteRepository
from app.services.cache import CacheService

logger = structlog.get_logger(__name__)


class PolicyService:
    """Policy lifecycle management with simulation and rollback."""

    def __init__(
        self,
        graph_reader: GraphReadRepository,
        graph_writer: GraphWriteRepository,
        audit_repo: AuditRepository,
        cache: CacheService | None = None,
    ) -> None:
        self._reader = graph_reader
        self._writer = graph_writer
        self._audit = audit_repo
        self._cache = cache

    # ── Policy CRUD ──────────────────────────────────────────

    async def create_policy(
        self,
        policy_id: str,
        policy_type: PolicyType,
        nl_description: str,
        structured_rule: dict[str, Any],
        priority: int = 100,
        is_hard_deny: bool = False,
        role_bindings: list[str] | None = None,
        table_bindings: list[str] | None = None,
        column_bindings: list[str] | None = None,
        domain_bindings: list[str] | None = None,
        created_by: str = "system",
    ) -> PolicyResponse:
        """Create a new policy with mandatory dual representation."""
        # Validate mandatory dual representation
        if not nl_description or len(nl_description.strip()) < 10:
            raise ValueError("nl_description is mandatory and must be at least 10 characters")
        if not structured_rule:
            raise ValueError("structured_rule is mandatory")

        # Create policy node
        policy_node = PolicyNode(
            policy_id=policy_id,
            policy_type=policy_type,
            nl_description=nl_description,
            structured_rule=json.dumps(structured_rule),
            priority=priority,
            is_hard_deny=is_hard_deny,
        )
        result = await self._writer.upsert_policy(policy_node)
        version = result.get("version", 1)

        # Bind to roles, tables, columns, domains
        for role in (role_bindings or []):
            await self._writer.bind_policy_to_role(policy_id, role)
        for table in (table_bindings or []):
            await self._writer.bind_policy_to_table(policy_id, table)
        for column in (column_bindings or []):
            await self._writer.bind_policy_to_column(policy_id, column)
        for domain in (domain_bindings or []):
            await self._writer.bind_policy_to_domain(policy_id, domain)

        # Save version snapshot to PostgreSQL
        await self._audit.save_policy_version(
            PolicyVersionRecord(
                policy_id=policy_id,
                version=version,
                policy_type=policy_type.value,
                nl_description=nl_description,
                structured_rule=structured_rule,
                priority=priority,
                is_active=True,
                created_by=created_by,
            )
        )

        # Audit log
        gv = await self._audit.increment_graph_version(
            created_by, f"Policy created: {policy_id}"
        )
        await self._audit.log_change(
            ChangeRecord(
                node_type="Policy",
                node_id=policy_id,
                action=ChangeAction.CREATE,
                new_values={
                    "policy_type": policy_type.value,
                    "priority": priority,
                    "is_hard_deny": is_hard_deny,
                },
                changed_by=created_by,
                change_source=ChangeSource.POLICY_ADMIN,
            ),
            gv,
        )

        # Invalidate relevant caches
        if self._cache:
            await self._cache.invalidate("tables:")
            await self._cache.invalidate("columns:")
            await self._cache.invalidate("masking:")
            await self._cache.invalidate("fks:")

        # Return full policy response
        policies = await self._reader.get_policies_for_table(
            table_bindings[0] if table_bindings else ""
        )
        match = next((p for p in policies if p.policy_id == policy_id), None)
        if match:
            return match

        return PolicyResponse(
            policy_id=policy_id,
            policy_type=policy_type,
            nl_description=nl_description,
            structured_rule=structured_rule,
            priority=priority,
            is_hard_deny=is_hard_deny,
            bound_roles=role_bindings or [],
            target_tables=table_bindings or [],
            target_columns=column_bindings or [],
            target_domains=domain_bindings or [],
        )

    async def deactivate_policy(self, policy_id: str, deactivated_by: str) -> None:
        """Soft-deactivate a policy (never hard-delete)."""
        await self._writer.deactivate_policy(policy_id)

        gv = await self._audit.increment_graph_version(
            deactivated_by, f"Policy deactivated: {policy_id}"
        )
        await self._audit.log_change(
            ChangeRecord(
                node_type="Policy",
                node_id=policy_id,
                action=ChangeAction.DEACTIVATE,
                changed_by=deactivated_by,
                change_source=ChangeSource.POLICY_ADMIN,
            ),
            gv,
        )

        # Invalidate relevant caches
        if self._cache:
            await self._cache.invalidate("tables:")
            await self._cache.invalidate("masking:")

    async def rollback_policy(
        self, policy_id: str, target_version: int, rolled_back_by: str
    ) -> PolicyResponse | None:
        """Restore a policy to a previous version from the version history."""
        snapshot = await self._audit.get_policy_version(policy_id, target_version)
        if not snapshot:
            raise ValueError(f"Version {target_version} not found for policy {policy_id}")

        structured = snapshot["structured_rule"]
        if isinstance(structured, str):
            structured = json.loads(structured)

        # Re-create the policy with historical state
        policy_node = PolicyNode(
            policy_id=policy_id,
            policy_type=PolicyType(snapshot["policy_type"]),
            nl_description=snapshot["nl_description"],
            structured_rule=json.dumps(structured),
            priority=snapshot["priority"],
            is_active=True,
        )
        result = await self._writer.upsert_policy(policy_node)
        new_version = result.get("version", target_version + 1)

        # Save new version snapshot
        await self._audit.save_policy_version(
            PolicyVersionRecord(
                policy_id=policy_id,
                version=new_version,
                policy_type=snapshot["policy_type"],
                nl_description=snapshot["nl_description"],
                structured_rule=structured,
                priority=snapshot["priority"],
                is_active=True,
                created_by=rolled_back_by,
            )
        )

        gv = await self._audit.increment_graph_version(
            rolled_back_by, f"Policy {policy_id} rolled back to v{target_version}"
        )
        await self._audit.log_change(
            ChangeRecord(
                node_type="Policy",
                node_id=policy_id,
                action=ChangeAction.UPDATE,
                old_values={"rollback_from": "current"},
                new_values={"rollback_to": target_version},
                changed_by=rolled_back_by,
                change_source=ChangeSource.ROLLBACK,
            ),
            gv,
        )

        # Invalidate relevant caches
        if self._cache:
            await self._cache.invalidate("tables:")
            await self._cache.invalidate("masking:")

        return PolicyResponse(
            policy_id=policy_id,
            policy_type=PolicyType(snapshot["policy_type"]),
            nl_description=snapshot["nl_description"],
            structured_rule=structured,
            priority=snapshot["priority"],
            version=new_version,
        )

    # ── Policy Simulation ────────────────────────────────────

    async def simulate(self, request: PolicySimulateRequest) -> list[PolicySimulateResult]:
        """Simulate policy evaluation for given roles against specified tables.

        Resolution order:
        1. HARD DENY (substance_abuse_records) → immediate deny, no override
        2. Explicit DENY policies → deny with reason
        3. MASK policies → allow with masked columns
        4. FILTER policies → allow with conditions
        5. ALLOW policies → allow
        6. No matching policy → DENY (deny by default)
        """
        # Get all policies for the given roles (including inherited)
        role_policies = await self._reader.get_policies_for_roles(request.roles)
        hard_deny_tables = await self._reader.get_hard_deny_tables()

        results: list[PolicySimulateResult] = []

        for table_fqn in request.table_fqns:
            # Check 1: Hard deny
            if table_fqn in hard_deny_tables:
                results.append(
                    PolicySimulateResult(
                        table_fqn=table_fqn,
                        effective_policy=PolicyType.DENY,
                        is_hard_deny=True,
                        deny_reason="Table is under HARD DENY protection (e.g., 42 CFR Part 2). No NL-to-SQL access permitted.",
                    )
                )
                continue

            # Get table-specific policies
            table_policies = await self._reader.get_policies_for_table(table_fqn)

            # Merge: role-based + table-based, deduplicate
            seen_ids: set[str] = set()
            applicable: list[PolicyResponse] = []
            for p in role_policies + table_policies:
                if p.policy_id not in seen_ids:
                    seen_ids.add(p.policy_id)
                    # Check if this policy actually applies to this table/domain
                    if self._policy_applies_to_table(p, table_fqn):
                        applicable.append(p)

            # Check if any role in the request is bound to the policies
            applicable = [
                p for p in applicable
                if not p.bound_roles or any(r in request.roles for r in p.bound_roles)
            ]

            # Sort by priority (highest first)
            applicable.sort(key=lambda p: p.priority, reverse=True)

            if not applicable:
                # Deny by default
                results.append(
                    PolicySimulateResult(
                        table_fqn=table_fqn,
                        effective_policy=PolicyType.DENY,
                        deny_reason="No applicable policy found — deny by default",
                    )
                )
                continue

            # Resolve effective policy
            result = self._resolve_policies(table_fqn, applicable)
            results.append(result)

        return results

    @staticmethod
    def _policy_applies_to_table(policy: PolicyResponse, table_fqn: str) -> bool:
        """Check if a policy governs this specific table or its domain."""
        if table_fqn in policy.target_tables:
            return True
        # Check domain match
        parts = table_fqn.split(".")
        if len(parts) >= 3:
            schema_name = parts[1]
            if schema_name in policy.target_domains:
                return True
        # Wildcard domain policies
        if not policy.target_tables and not policy.target_domains:
            return True
        return False

    @staticmethod
    def _resolve_policies(
        table_fqn: str, policies: list[PolicyResponse]
    ) -> PolicySimulateResult:
        """Resolve multiple applicable policies into a single effective decision."""
        # Priority: DENY > MASK > FILTER > ALLOW
        deny_policies = [p for p in policies if p.policy_type == PolicyType.DENY]
        mask_policies = [p for p in policies if p.policy_type == PolicyType.MASK]
        filter_policies = [p for p in policies if p.policy_type == PolicyType.FILTER]
        allow_policies = [p for p in policies if p.policy_type == PolicyType.ALLOW]

        if deny_policies:
            top_deny = deny_policies[0]
            return PolicySimulateResult(
                table_fqn=table_fqn,
                effective_policy=PolicyType.DENY,
                is_hard_deny=top_deny.is_hard_deny,
                applicable_policies=policies,
                deny_reason=top_deny.nl_description,
            )

        masked_columns: list[str] = []
        all_conditions: list[ConditionResponse] = []

        for mp in mask_policies:
            masked_columns.extend(mp.target_columns)
        for fp in filter_policies:
            all_conditions.extend(fp.conditions)

        if mask_policies:
            return PolicySimulateResult(
                table_fqn=table_fqn,
                effective_policy=PolicyType.MASK,
                applicable_policies=policies,
                masked_columns=list(set(masked_columns)),
                conditions=all_conditions,
            )

        if filter_policies:
            return PolicySimulateResult(
                table_fqn=table_fqn,
                effective_policy=PolicyType.FILTER,
                applicable_policies=policies,
                conditions=all_conditions,
            )

        if allow_policies:
            return PolicySimulateResult(
                table_fqn=table_fqn,
                effective_policy=PolicyType.ALLOW,
                applicable_policies=policies,
                conditions=all_conditions,
            )

        # Should not reach here given deny-by-default, but safety net
        return PolicySimulateResult(
            table_fqn=table_fqn,
            effective_policy=PolicyType.DENY,
            applicable_policies=policies,
            deny_reason="No ALLOW policy matched — deny by default",
        )
