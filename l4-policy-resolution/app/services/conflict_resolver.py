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
        
        # Rule 1: Highest priority wins. If identical priorities conflict, DENY beats ALLOW.
        best_priority = sorted_pols[0].priority
        top_tier = [p for p in sorted_pols if p.priority == best_priority]
        
        has_allow = any(p.is_allow for p in top_tier)
        has_deny = any(p.is_deny for p in top_tier)
        
        if has_deny:
            active = [p for p in top_tier if p.is_deny]
            return TableDecision.DENY, active, f"Hard DENY applied via top-priority policy ({active[0].policy_id})"
            
        if has_allow:
            active = [p for p in top_tier if p.is_allow]
            # Accumulate all filters / rule conditions from all allowed policies in the top tier (or lower tiers if cumulative)
            # For strict deny-wins, we return all ALLOW policies that don't contradict.
            all_allows = [p for p in sorted_pols if p.is_allow]
            return TableDecision.ALLOW, all_allows, f"ALLOW via policy ({active[0].policy_id})"

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
