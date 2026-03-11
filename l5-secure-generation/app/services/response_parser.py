"""Response Parser & SQL Extractor.

Extracts clean SQL from LLM responses that may include markdown blocks,
explanatory text, CANNOT_ANSWER declarations, or multiple query variants.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import structlog

logger = structlog.get_logger(__name__)

# Write-operation keywords that must NEVER appear in generated SQL
_WRITE_KEYWORDS = re.compile(
    r"\b(INSERT\s+INTO|UPDATE\s+\w|DELETE\s+FROM|DROP\s+TABLE|ALTER\s+TABLE|"
    r"CREATE\s+TABLE|TRUNCATE\s+TABLE|EXEC\s*\(|EXECUTE\s+IMMEDIATE|"
    r"sp_executesql|GRANT\s+|REVOKE\s+)\b",
    re.IGNORECASE,
)

# System table patterns
_SYSTEM_TABLES = re.compile(
    r"\b(information_schema|sys\.|pg_catalog\.|pg_|dba_|all_tab|user_tables|"
    r"SYSCOLUMNS|SYSOBJECTS|xp_cmdshell)\b",
    re.IGNORECASE,
)

# Markdown SQL fence
_MD_FENCE = re.compile(r"```(?:sql)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)

# Bare SQL start
_SQL_START = re.compile(r"(?:^|\n)((?:WITH|SELECT|(\())\s)", re.IGNORECASE)


@dataclass
class ParseResult:
    sql: str | None
    cannot_answer: bool
    cannot_answer_reason: str | None
    parse_error: str | None

    @property
    def success(self) -> bool:
        return self.sql is not None and not self.cannot_answer


def parse(llm_response: str) -> ParseResult:
    """Extract and validate SQL from LLM response text."""
    text = llm_response.strip()

    # 1. Check for CANNOT_ANSWER
    if text.upper().startswith("CANNOT_ANSWER"):
        reason = text.split(":", 1)[1].strip() if ":" in text else "LLM declined to answer"
        logger.info("LLM returned CANNOT_ANSWER", reason=reason[:100])
        return ParseResult(sql=None, cannot_answer=True,
                           cannot_answer_reason=reason, parse_error=None)

    # Check for other refusal phrases
    refusal_phrases = ["i cannot", "i'm unable", "i am unable", "cannot generate",
                       "i cannot help", "i don't have access"]
    lower_text = text.lower()
    for phrase in refusal_phrases:
        if lower_text.startswith(phrase):
            return ParseResult(sql=None, cannot_answer=True,
                               cannot_answer_reason=text[:200], parse_error=None)

    # 2. Extract from markdown block
    md_match = _MD_FENCE.search(text)
    if md_match:
        sql = md_match.group(1).strip()
    else:
        # 3. Find bare SQL
        sql_match = _SQL_START.search(text)
        if sql_match:
            sql = text[sql_match.start():].strip()
            # Trim post-SQL explanatory text (stop at first empty line after SQL)
            # Keep up to the last semicolon or end of SQL-looking content
            lines = sql.split("\n")
            sql_lines = []
            for line in lines:
                stripped = line.strip()
                # Stop at blank line that follows non-blank content
                if not stripped and sql_lines and sql_lines[-1].strip():
                    # Check if next non-blank line looks like SQL
                    remaining = "\n".join(lines[lines.index(line)+1:]).strip()
                    if not remaining or not _SQL_START.match(remaining):
                        break
                sql_lines.append(line)
            sql = "\n".join(sql_lines).strip()
        else:
            return ParseResult(sql=None, cannot_answer=False,
                               cannot_answer_reason=None,
                               parse_error="No SQL found in LLM response")

    # 4. Normalize: strip trailing semicolons and whitespace
    sql = sql.rstrip(";").strip()

    if not sql:
        return ParseResult(sql=None, cannot_answer=False,
                           cannot_answer_reason=None,
                           parse_error="Empty SQL extracted")

    # 5. Security validation
    if _WRITE_KEYWORDS.search(sql):
        logger.warning("Write operation in LLM output blocked", sql_preview=sql[:100])
        return ParseResult(sql=None, cannot_answer=False,
                           cannot_answer_reason=None,
                           parse_error="Write operation detected in generated SQL")

    if _SYSTEM_TABLES.search(sql):
        logger.warning("System table reference in LLM output blocked", sql_preview=sql[:100])
        return ParseResult(sql=None, cannot_answer=False,
                           cannot_answer_reason=None,
                           parse_error="System table reference detected in generated SQL")

    # 6. Basic structure check
    upper_sql = sql.upper().lstrip()
    if not (upper_sql.startswith("SELECT") or upper_sql.startswith("WITH") or
            upper_sql.startswith("(")):
        return ParseResult(sql=None, cannot_answer=False,
                           cannot_answer_reason=None,
                           parse_error=f"SQL does not start with SELECT/WITH: {sql[:60]}")

    # 7. Normalize whitespace
    sql = re.sub(r"\n{3,}", "\n\n", sql)
    sql = sql.strip()

    logger.debug("SQL extracted successfully", sql_len=len(sql))
    return ParseResult(sql=sql, cannot_answer=False,
                       cannot_answer_reason=None, parse_error=None)
