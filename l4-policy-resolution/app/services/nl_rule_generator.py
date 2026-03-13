"""Natural Language Rule Generator.

Converts strict structured policies (like JSON row filters or MASK rules)
into explicit prompt instructions for the L5 Code Generation layer.
"""

from __future__ import annotations

from app.models.api_models import TablePermission, JoinRestriction
from app.models.enums import ColumnVisibility


class NLRuleGenerator:
    """Translates deterministic rules to natural language for the LLM."""

    @staticmethod
    def generate_global_rules(join_restrictions: list[JoinRestriction]) -> list[str]:
        """Generate rules that apply to the entire query."""
        rules = []
        
        if join_restrictions:
            rules.append("CRITICAL: You are strictly forbidden from joining the following domains together:")
            for j in join_restrictions:
                rules.append(f"  - Do not join tables in domain '{j.source_domain}' with tables in domain '{j.target_domain}'")
                
        return rules

    @staticmethod
    def generate_table_rules(table_perm: TablePermission, table_name: str) -> list[str]:
        """Generate rules specific to a single permitted table."""
        rules = []
        
        if table_perm.row_filters:
            filter_str = " AND ".join(table_perm.row_filters)
            rules.append(f"MANDATORY: When querying table '{table_name}', you MUST include this in the WHERE clause: {filter_str}")
            
        if table_perm.aggregation_only:
            rules.append(f"MANDATORY: Queries against '{table_name}' must be aggregations (e.g. COUNT, SUM). You cannot SELECT individual rows.")
            if table_perm.denied_in_select:
                cols = ", ".join(table_perm.denied_in_select)
                rules.append(f"MANDATORY: You MUST NOT include these columns in SELECT for '{table_name}': {cols}. These are patient identifiers forbidden under aggregation-only policy.")
            
        if table_perm.max_rows:
            rules.append(f"MANDATORY: Queries against '{table_name}' must be limited to a maximum of {table_perm.max_rows} rows.")

        masked_cols = [c for c in table_perm.columns if c.visibility == ColumnVisibility.MASKED]
        if masked_cols:
            rule = f"MANDATORY: The following columns in '{table_name}' must be masked in the SELECT list:"
            for c in masked_cols:
                # Typically, L6 handles the actual rewrite if the LLM fails, 
                # but we instruct the AI to do it right the first time.
                expr = c.masking_expression or f"concat('MASKED-', substr({c.column_name}, -4))"
                rule += f"\n  - {c.column_name}: use expression `{expr}`"
            rules.append(rule)

        return rules
