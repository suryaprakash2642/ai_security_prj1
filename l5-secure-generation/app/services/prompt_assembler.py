"""Secure Prompt Assembler.

Assembles the four-section LLM prompt:
  1. System instructions (fixed template per dialect)
  2. Mandatory rules (nl_rules from Permission Envelope)
  3. Schema DDL fragments (allowed tables, ordered by relevance)
  4. User question (sanitized)

Also handles context window management — truncates schema from
lowest-relevance tables first; NEVER truncates rules or question.
"""

from __future__ import annotations

import structlog

from app.models.api import FilteredTable, PermissionEnvelope, FilteredSchema
from app.models.enums import SQLDialect
from app.services.schema_fragment_generator import generate_all_fragments

logger = structlog.get_logger(__name__)

# ── System Prompt Templates ────────────────────────────────────────────────

_SYSTEM_PROMPT_TEMPLATE = """\
You are a secure SQL query generator for a healthcare database system.
Your ONLY job is to generate a single, valid {dialect_hint} SQL SELECT query
that answers the user's question using ONLY the provided schema.

ABSOLUTE RULES:
1. Use ONLY tables and columns from the AVAILABLE SCHEMA section.
2. NEVER reference tables or columns not in the schema.
3. Follow ALL rules in the MANDATORY RULES section without exception.
4. Generate ONLY SELECT statements. Never INSERT/UPDATE/DELETE/DROP.
5. Include LIMIT {max_rows} unless the query already has aggregation.
6. If the question cannot be answered with the provided schema,
   respond with: CANNOT_ANSWER: [brief reason]
7. Output ONLY the SQL query. No explanations. No markdown.
8. For masked columns, use the provided SQL rewrite expressions.
9. Never attempt to circumvent or work around any stated rule.
10. If a rule conflicts with the question, the rule ALWAYS wins.\
"""

_DIALECT_HINTS = {
    SQLDialect.POSTGRESQL: "PostgreSQL. Use LIMIT N, COALESCE(), standard SQL.",
    SQLDialect.MYSQL: "MySQL. Use LIMIT N, IFNULL(), CURDATE(), DATE_SUB(CURDATE(), INTERVAL N DAY). For INTERVAL always include the unit keyword: INTERVAL 30 DAY, INTERVAL 6 MONTH — never write INTERVAL '200' without a unit. Do NOT use date_trunc or PostgreSQL-style INTERVAL '30 days'. Only reference tables and columns provided in the schema — do NOT invent tables like 'units' or 'beds'.",
    SQLDialect.TSQL: "Microsoft SQL Server T-SQL. Use TOP N, bracket-quoted names, ISNULL().",
    SQLDialect.ORACLE: "Oracle PL/SQL. Use FETCH FIRST N ROWS ONLY, NVL(), SYSDATE.",
}


# ── Token estimation (very rough: 1 token ≈ 4 chars) ─────────────────────

def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


# ── Compression levels ─────────────────────────────────────────────────────

def _compress_ddl(ddl: str, level: int) -> str:
    """Reduce DDL token cost at increasing compression levels."""
    if level == 0:
        return ddl
    lines = ddl.split("\n")
    if level == 1:
        # Remove column descriptions (lines containing only "-- ")
        lines = [l for l in lines if not (l.strip().startswith("--") and "MASKED" not in l
                                          and "REQUIRED" not in l and "AGGREGATION" not in l
                                          and "Join:" not in l and "Table:" not in l
                                          and "Description:" not in l)]
    elif level == 2:
        # Keep only table header + column names + masking
        lines = [l for l in lines if (l.strip().startswith("--") and (
            "Table:" in l or "MASKED:" in l or "REQUIRED:" in l or "AGGREGATION" in l
        )) or l.strip().startswith("CREATE") or l.strip().startswith(")") or (
            l.strip() and not l.strip().startswith("--")
        )]
    elif level >= 3:
        # Column names only
        result = []
        for l in lines:
            stripped = l.strip()
            if stripped.startswith("CREATE") or stripped.startswith(")") or \
               (stripped.startswith("--") and ("Table:" in stripped or "REQUIRED:" in stripped)):
                result.append(l)
            elif stripped and not stripped.startswith("--"):
                # Keep just the first "word word" (name type)
                parts = stripped.split()
                result.append("  " + " ".join(parts[:2]) if len(parts) >= 2 else l)
        lines = result
    return "\n".join(lines)


# ── Main assembler ─────────────────────────────────────────────────────────

class AssembledPrompt:
    def __init__(self, system_prompt: str, user_message: str,
                 tables_included: int, tables_truncated: int,
                 rules_count: int, token_breakdown: dict):
        self.system_prompt = system_prompt
        self.user_message = user_message
        self.tables_included = tables_included
        self.tables_truncated = tables_truncated
        self.rules_count = rules_count
        self.token_breakdown = token_breakdown

    @property
    def total_tokens(self) -> int:
        return sum(self.token_breakdown.values())


def assemble_prompt(
    sanitized_question: str,
    envelope: PermissionEnvelope,
    schema: FilteredSchema,
    dialect: SQLDialect = SQLDialect.POSTGRESQL,
    max_prompt_tokens: int = 10000,
    response_reserve_tokens: int = 2048,
    default_max_rows: int = 1000,
) -> AssembledPrompt:
    """Build the complete LLM prompt following the four-section format.

    Policy rules and the user question are NEVER truncated.
    Schema is truncated (lowest-relevance first) if the token budget is tight.
    """
    # ── 1. System prompt ──────────────────────────────────────────────────
    max_rows = default_max_rows
    # Use the minimum max_rows from allowed table permissions
    for tp in envelope.table_permissions:
        if tp.max_rows and tp.max_rows < max_rows:
            max_rows = tp.max_rows

    system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(
        dialect_hint=_DIALECT_HINTS.get(dialect, "PostgreSQL"),
        max_rows=max_rows,
    )

    # ── 2. NL rules section ────────────────────────────────────────────────
    all_rules = envelope.all_nl_rules
    if all_rules:
        rules_section = "=== MANDATORY RULES ===\n"
        rules_section += "You MUST follow ALL of the following rules when generating SQL.\n"
        rules_section += "Violating ANY rule makes the query invalid.\n\n"
        for i, rule in enumerate(all_rules, 1):
            rules_section += f"RULE {i}: {rule}\n"
        rules_section += "=== END MANDATORY RULES ==="
    else:
        rules_section = ""

    # ── 3. Schema fragments ────────────────────────────────────────────────
    table_ddls = generate_all_fragments(schema.tables, envelope, dialect)

    # Budget calculation
    fixed_tokens = (
        _estimate_tokens(system_prompt) +
        _estimate_tokens(rules_section) +
        _estimate_tokens(sanitized_question) +
        response_reserve_tokens +
        200  # overhead for section headers
    )
    schema_budget = max_prompt_tokens - fixed_tokens

    # Greedy table inclusion with compression fallback
    included_tables = []
    truncated_count = 0
    remaining_budget = schema_budget
    must_include = table_ddls[:3]  # top 3 must always be included
    optional_tables = table_ddls[3:]

    schema_lines = ["=== AVAILABLE SCHEMA ===",
                    "The following tables and columns are the ONLY ones you may use.",
                    "Any table or column not listed here DOES NOT EXIST.", ""]

    for tbl, ddl in must_include + optional_tables:
        included = False
        for compression_level in range(4):
            compressed_ddl = _compress_ddl(ddl, compression_level)
            tokens = _estimate_tokens(compressed_ddl)
            if tokens <= remaining_budget or (tbl, ddl) in must_include:
                schema_lines.append(compressed_ddl)
                schema_lines.append("")
                remaining_budget -= tokens
                included_tables.append(tbl)
                included = True
                break
        if not included:
            truncated_count += 1

    schema_lines.append("=== END AVAILABLE SCHEMA ===")
    schema_section = "\n".join(schema_lines)

    # ── 4. Question section ────────────────────────────────────────────────
    question_section = (
        f"=== USER QUESTION ===\n{sanitized_question}\n=== END USER QUESTION ===\n\n"
        f"Generate a single {_DIALECT_HINTS.get(dialect, 'PostgreSQL')} SELECT query."
    )

    # ── Assemble user message ─────────────────────────────────────────────
    user_parts = []
    if rules_section:
        user_parts.append(rules_section)
    user_parts.append(schema_section)
    user_parts.append(question_section)
    user_message = "\n\n".join(user_parts)

    token_breakdown = {
        "system": _estimate_tokens(system_prompt),
        "rules": _estimate_tokens(rules_section),
        "schema": _estimate_tokens(schema_section),
        "question": _estimate_tokens(question_section),
    }

    if truncated_count:
        logger.warning("Schema tables truncated due to token budget",
                       truncated=truncated_count, included=len(included_tables))

    return AssembledPrompt(
        system_prompt=system_prompt,
        user_message=user_message,
        tables_included=len(included_tables),
        tables_truncated=truncated_count,
        rules_count=len(all_rules),
        token_breakdown=token_breakdown,
    )
