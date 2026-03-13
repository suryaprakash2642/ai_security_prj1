"""Conflict Resolver.

Applies deterministic rules to a collection of policies.
Rules (in order of application):
1. DENY beats ALLOW
2. Higher Priority beats Lower Priority
3. Column-level beats Table-level
4. No explicit ALLOW = DENY (Default Deny)
"""

from __future__ import annotations

import structlog

from app.models.api_models import ColumnDecision, TablePermission
from app.models.domain_models import ColumnMetadata, PolicyNode, TableMetadata
from app.models.enums import ColumnVisibility, TableDecision

logger = structlog.get_logger(__name__)


class ConflictResolver:
    """Deterministically resolves conflicting policies."""

    @staticmethod
    def resolve_table(table_meta: TableMetadata) -> tuple[TableDecision, list[PolicyNode], str]:
        """Resolve access to the table itself.

        Returns (Decision, active_policies, reason).
        """
        if not table_meta.table_policies:
             return TableDecision.DENY, [], "No policies apply to this role for this table"

        # Sort policies by priority DESC
        sorted_pols = sorted(table_meta.table_policies, key=lambda p: p.priority, reverse=True)

        # At the table level, DENY and ALLOW are the only access decisions.
        # FILTER and MASK are condition modifiers that imply table access is
        # granted (with constraints).  They must not shadow an ALLOW that
        # sits at a lower priority.
        #
        # Strategy: scan ALL policies (not just the top tier) for the
        # highest-priority DENY and the highest-priority "grants access"
        # (ALLOW / FILTER / MASK).  DENY beats grant at equal priority.
        _GRANT_EFFECTS = {"ALLOW", "FILTER", "MASK"}

        best_deny_prio = None
        best_grant_prio = None
        for p in sorted_pols:
            eff = p.effect.upper()
            if eff == "DENY" and best_deny_prio is None:
                best_deny_prio = p.priority
            if eff in _GRANT_EFFECTS and best_grant_prio is None:
                best_grant_prio = p.priority

        # If there is a DENY at equal or higher priority than any grant, deny.
        if best_deny_prio is not None:
            if best_grant_prio is None or best_deny_prio >= best_grant_prio:
                active = [p for p in sorted_pols if p.is_deny and p.priority == best_deny_prio]
                return TableDecision.DENY, active, f"Hard DENY applied via top-priority policy ({active[0].policy_id})"

        # If any grant exists, allow.  Collect ALL granting policies so
        # their conditions (row filters, masks, etc.) are applied.
        if best_grant_prio is not None:
            all_grants = [p for p in sorted_pols if p.effect.upper() in _GRANT_EFFECTS]
            leading = next(p for p in sorted_pols if p.effect.upper() in _GRANT_EFFECTS)
            return TableDecision.ALLOW, all_grants, f"ALLOW via policy ({leading.policy_id})"

        return TableDecision.DENY, [], "No valid ALLOW or DENY effect found"

    @staticmethod
    def resolve_columns(table_meta: TableMetadata, table_active_policies: list[PolicyNode]) -> list[ColumnDecision]:
        """Resolve access to specific columns inside an explicitly ALLOWED table."""
        decisions: list[ColumnDecision] = []

        for col_id, col_meta in table_meta.columns.items():
            if not col_meta.policies:
                # Rule 3 fallback: No explicit column policy, fallback to table policy
                # If table is ALLOWED and column has no policy, column is VISIBLE by default
                decisions.append(ColumnDecision(
                    column_name=col_meta.column_name,
                    visibility=ColumnVisibility.VISIBLE,
                    reason="Inherited ALLOW from table"
                ))
                continue

            # Sort column policies
            sorted_pols = sorted(col_meta.policies, key=lambda p: p.priority, reverse=True)
            best_priority = sorted_pols[0].priority
            top_tier = [p for p in sorted_pols if p.priority == best_priority]
            
            has_deny = any(p.is_deny for p in top_tier)
            has_mask = any(p.effect.upper() == "MASK" for p in top_tier)
            has_allow = any(p.is_allow for p in top_tier)

            if has_deny:
                decisions.append(ColumnDecision(
                    column_name=col_meta.column_name,
                    visibility=ColumnVisibility.HIDDEN,
                    reason=f"Column explicitly DENIED via {top_tier[0].policy_id}"
                ))
            elif has_mask:
                mask_pol = next(p for p in top_tier if p.effect.upper() == "MASK")
                expr = None
                for c in mask_pol.conditions:
                    if c.condition_type == "MASKING_RULE":
                        expr = c.expression
                
                decisions.append(ColumnDecision(
                    column_name=col_meta.column_name,
                    visibility=ColumnVisibility.MASKED,
                    masking_expression=expr,
                    reason=f"MASKED via {mask_pol.policy_id}"
                ))
            elif has_allow:
                decisions.append(ColumnDecision(
                    column_name=col_meta.column_name,
                    visibility=ColumnVisibility.VISIBLE,
                    reason=f"Column explicitly ALLOWED via {top_tier[0].policy_id}"
                ))
            else:
                decisions.append(ColumnDecision(
                    column_name=col_meta.column_name,
                    visibility=ColumnVisibility.HIDDEN,
                    reason="Unknown column policy effect"
                ))

        return decisions
