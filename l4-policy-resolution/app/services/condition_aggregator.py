"""Condition Aggregator.

Takes active policies across tables and columns and flattens their 
conditions (row filters, aggregations, joins) into executable envelopes.
Injects context parameters provided by L1 (SecurityContext).
"""

from __future__ import annotations

import re
from typing import Any
import structlog

from app.models.api_models import JoinRestriction, TablePermission
from app.models.domain_models import PolicyNode

logger = structlog.get_logger(__name__)


class ConditionAggregator:
    """Combines and parameter-injects conditions."""

    def __init__(self, user_context: dict[str, Any]):
        """Initialize with user context (e.g., {'user_id': '123', 'department': 'Cardiology'})."""
        self.user_context = user_context

    def _inject_parameters(self, expression: str) -> str:
        """Replaces $param syntax in expressions with actual context values.
        
        Example: "provider_id = $user_id" -> "provider_id = '123'"
        """
        result = expression
        # Find all $vars in the string
        variables = re.findall(r"\$([a-zA-Z0-9_]+)", expression)
        
        for var in variables:
            val = self.user_context.get(var)
            if val is None:
                # If a policy requires a variable the context lacks, we fail closed by
                # emitting a condition that is impossible, rather than aborting entirely.
                logger.warning(f"Missing context variable '{var}' for expression: {expression}")
                replacement = "NULL" # Fallback to prevent syntax errors that bypass security
            else:
                # Safe injection for standard types
                if isinstance(val, (int, float, bool)):
                    replacement = str(val)
                else:
                    # Very basic escaping to prevent SQL injection in the parameters themselves
                    safe_str = str(val).replace("'", "''")
                    replacement = f"'{safe_str}'"
            
            result = result.replace(f"${var}", replacement)
            
        return result

    def aggregate_table_conditions(self, active_policies: list[PolicyNode], table_perm: TablePermission) -> None:
        """Modifies table_perm in place by appending resolved conditions."""
        
        row_filters = set()
        aggregation_only = False
        max_rows = None

        for p in active_policies:
            for c in p.conditions:
                if c.condition_type == "ROW_FILTER":
                    injected = self._inject_parameters(c.expression)
                    row_filters.add(f"({injected})")
                
                elif c.condition_type == "AGGREGATE_ONLY":
                    # If any policy requires aggregation, the table requires it
                    aggregation_only = True
                    
                elif c.condition_type == "ROW_LIMIT":
                    try:
                        limit_val = int(c.expression)
                        if max_rows is None or limit_val < max_rows:
                            max_rows = limit_val
                    except ValueError:
                        pass

        # Apply using AND logic since row filters are cumulative restrictions
        if row_filters:
            table_perm.row_filters = sorted(list(row_filters))
        
        if aggregation_only:
            table_perm.aggregation_only = True
            
        if max_rows is not None:
            table_perm.max_rows = max_rows

    def extract_join_restrictions(self, active_policies: list[PolicyNode]) -> list[JoinRestriction]:
        """Extract join restrictions from active policies across the whole request."""
        restrictions = []
        for p in active_policies:
            for c in p.conditions:
                if c.condition_type == "JOIN_RESTRICTION":
                    # Expression format expected: "from_domain|to_domain"
                    parts = c.expression.split("|")
                    if len(parts) == 2:
                        restrictions.append(JoinRestriction(
                            source_domain=parts[0].strip(),
                            target_domain=parts[1].strip(),
                            policy_id=p.policy_id,
                            restriction_type="DENY"
                        ))
        return restrictions
