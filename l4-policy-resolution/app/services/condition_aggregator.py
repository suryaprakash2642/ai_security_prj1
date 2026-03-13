"""Condition Aggregator.

Takes active policies across tables and columns and flattens their 
conditions (row filters, aggregations, joins) into executable envelopes.
Injects context parameters provided by L1 (SecurityContext).
"""

from __future__ import annotations

import json
import re
from typing import Any
import structlog

from app.models.api_models import JoinRestriction, TablePermission
from app.models.domain_models import ConditionNode, PolicyNode

logger = structlog.get_logger(__name__)


class ConditionAggregator:
    """Combines and parameter-injects conditions."""

    def __init__(self, user_context: dict[str, Any]):
        """Initialize with user context (e.g., {'user_id': '123', 'department': 'Cardiology'})."""
        self.user_context = user_context

    def _resolve_value(self, var: str) -> str:
        """Resolve a single variable name to its safe SQL literal.

        Supports dotted paths like ``user.provider_id`` by walking nested
        dicts/objects in user_context.  The ``user.`` prefix is stripped
        since user_context already represents the user object.
        """
        # Strip leading "user." — user_context IS the user object
        clean_var = var
        if clean_var.startswith("user."):
            clean_var = clean_var[5:]

        # Walk dotted path
        parts = clean_var.split(".")
        val: Any = self.user_context
        for part in parts:
            if isinstance(val, dict):
                val = val.get(part)
            else:
                val = getattr(val, part, None)
            if val is None:
                break

        if val is None:
            logger.warning(f"Missing context variable '{var}' for user_context")
            return "NULL"
        if isinstance(val, (int, float, bool)):
            return str(val)
        safe_str = str(val).replace("'", "''")
        return f"'{safe_str}'"

    def _inject_parameters(self, expression: str) -> str:
        """Replaces parameter placeholders in expressions with actual context values.

        Supports two syntaxes:
          - $param          → looks up ``param`` in user_context
          - {{user.param}}  → looks up ``user.param`` (dotted path) in user_context
        """
        result = expression

        # 1. Handle {{dotted.path}} syntax (e.g. {{user.provider_id}})
        for match in re.finditer(r"\{\{([a-zA-Z0-9_.]+)\}\}", expression):
            var = match.group(1)
            replacement = self._resolve_value(var)
            result = result.replace(match.group(0), replacement)

        # 2. Handle $simple_var syntax (e.g. $user_id)
        for match in re.finditer(r"\$([a-zA-Z0-9_]+)", result):
            var = match.group(1)
            replacement = self._resolve_value(var)
            result = result.replace(match.group(0), replacement)

        return result

    @staticmethod
    def _parse_parameters(condition: ConditionNode) -> dict[str, Any]:
        """Parse the JSON `parameters` string stored on a Neo4j Condition node."""
        if condition.parameters:
            try:
                parsed = json.loads(condition.parameters)
                if isinstance(parsed, dict):
                    return parsed
            except (json.JSONDecodeError, TypeError):
                logger.warning("bad_condition_parameters", condition_id=condition.condition_id,
                               raw=condition.parameters)
        return {}

    def aggregate_table_conditions(self, active_policies: list[PolicyNode], table_perm: TablePermission) -> None:
        """Modifies table_perm in place by appending resolved conditions."""
        
        row_filters = set()
        aggregation_only = False
        denied_in_select: set[str] = set()
        max_rows = None

        for p in active_policies:
            for c in p.conditions:
                if c.condition_type == "ROW_FILTER":
                    injected = self._inject_parameters(c.expression)
                    row_filters.add(f"({injected})")

                elif c.condition_type in ("AGGREGATE_ONLY", "AGGREGATION_ONLY"):
                    # If any policy requires aggregation, the table requires it
                    aggregation_only = True
                    # Extract denied_in_select from condition parameters
                    params = self._parse_parameters(c)
                    for col in params.get("denied_in_select", []):
                        denied_in_select.add(col)

                elif c.condition_type in ("ROW_LIMIT", "MAX_ROWS"):
                    try:
                        # Try numeric expression first, then check parameters
                        params = self._parse_parameters(c)
                        limit_val = params.get("limit") or params.get("max_rows")
                        if limit_val is None:
                            limit_val = int(c.expression)
                        else:
                            limit_val = int(limit_val)
                        if max_rows is None or limit_val < max_rows:
                            max_rows = limit_val
                    except (ValueError, TypeError):
                        pass

        # Apply using AND logic since row filters are cumulative restrictions
        if row_filters:
            table_perm.row_filters = sorted(list(row_filters))

        if aggregation_only:
            table_perm.aggregation_only = True

        if denied_in_select:
            table_perm.denied_in_select = sorted(list(denied_in_select))

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
