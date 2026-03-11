"""Mock Query Executor — returns synthetic results in dev/test mode.

In production this is replaced by actual database drivers (asyncpg,
pyodbc, oracledb). The mock parses the SQL AST to infer column names
and returns plausible synthetic rows.
"""

from __future__ import annotations

import asyncio
import random
import re
import time
from typing import Any

import structlog

from app.models.api import ColumnMetadata

logger = structlog.get_logger(__name__)

# Synthetic value generators per inferred column semantic
_SYNTHETIC_VALUES: dict[str, list[Any]] = {
    "mrn":              ["MRN-10001", "MRN-10002", "MRN-10003", "MRN-10004", "MRN-10005"],
    "full_name":        ["J. Patel", "A. Kumar", "R. Singh", "S. Sharma", "P. Iyer"],
    "admission_date":   ["2026-01-15T08:30:00Z", "2026-01-16T14:22:00Z", "2026-02-01T09:00:00Z"],
    "discharge_date":   ["2026-01-18T11:00:00Z", "2026-01-19T16:30:00Z", None],
    "unit_id":          ["3B", "ICU", "CARDIO", "ORTHO", "NEURO"],
    "encounter_id":     ["ENC-0001", "ENC-0002", "ENC-0003", "ENC-0004"],
    "encounter_type":   ["INPATIENT", "OUTPATIENT", "EMERGENCY"],
    "treating_provider_id": ["DR-4521", "DR-3310", "DR-7842"],
    "department":       ["CARDIOLOGY", "ICU", "NEUROLOGY", "ORTHOPEDICS"],
    "claim_id":         ["CLM-AA001", "CLM-AA002", "CLM-BB001"],
    "total_amount":     [12500.00, 8900.50, 34200.00, 7650.75],
    "service_date":     ["2026-01-10", "2026-01-11", "2026-01-14"],
    "count":            [42, 17, 8, 103, 29],
    "count(*)":         [42, 17, 8],
    "admission_id":     ["ADM-001", "ADM-002", "ADM-003"],
    "diagnosis_code":   ["I21.0", "J18.1", "N18.3", "E11.9"],
    "diagnosis_name":   ["STEMI", "Pneumonia", "CKD stage 3", "Type 2 DM"],
}

_DEFAULT_VALS = ["sample_value_1", "sample_value_2", "sample_value_3"]


def _infer_col_type(col_name: str) -> str:
    name = col_name.lower()
    if any(k in name for k in ("date", "time", "at", "on")):
        return "TIMESTAMP"
    if any(k in name for k in ("amount", "total", "cost", "fee", "price")):
        return "NUMERIC"
    if any(k in name for k in ("count", "num", "qty", "total_")):
        return "INTEGER"
    if "id" in name:
        return "VARCHAR"
    return "VARCHAR"


def _extract_columns_from_sql(sql: str) -> list[str]:
    """Best-effort column name extraction from SELECT clause."""
    sql_upper = sql.upper().strip()

    # Handle SELECT *
    if re.match(r"SELECT\s+(\w+\.)?\*", sql_upper):
        return ["id", "name", "value", "created_at"]

    # Extract between SELECT and FROM
    m = re.search(r"SELECT\s+(DISTINCT\s+)?(.+?)\s+FROM\b", sql, re.IGNORECASE | re.DOTALL)
    if not m:
        return ["col1", "col2"]

    col_str = m.group(2)
    # Handle aggregate functions
    col_str = re.sub(r"COUNT\s*\(\s*\*\s*\)", "count(*)", col_str, flags=re.IGNORECASE)
    col_str = re.sub(r"\b(?:COUNT|SUM|AVG|MIN|MAX)\s*\([^)]+\)\s+(?:AS\s+)?(\w+)?",
                     lambda m: m.group(1) or "aggregate", col_str, flags=re.IGNORECASE)

    # Split by comma, clean alias
    cols = []
    for part in col_str.split(","):
        part = part.strip()
        # Handle "table.column" or "table.column AS alias"
        alias_m = re.search(r"\bAS\s+(\w+)\s*$", part, re.IGNORECASE)
        if alias_m:
            cols.append(alias_m.group(1).lower())
        else:
            # Take last dot-separated part
            name = part.split(".")[-1].strip()
            name = re.sub(r"[^a-z0-9_*()]", "", name.lower())
            if name:
                cols.append(name)

    return cols if cols else ["col1", "col2"]


async def execute_mock(
    sql: str,
    parameters: dict[str, Any],
    max_rows: int,
    timeout_seconds: int,
    latency_ms: int = 50,
) -> tuple[list[ColumnMetadata], list[list[Any]], bool]:
    """Simulate database execution and return synthetic results.

    Returns (columns, rows, truncated).
    """
    start = time.monotonic()
    await asyncio.sleep(latency_ms / 1000.0)

    col_names = _extract_columns_from_sql(sql)
    columns = [
        ColumnMetadata(name=c, type=_infer_col_type(c), masked=False)
        for c in col_names
    ]

    # Determine row count — check for LIMIT in SQL
    limit_m = re.search(r"\bLIMIT\s+(\d+)\b", sql, re.IGNORECASE)
    sql_limit = int(limit_m.group(1)) if limit_m else 20
    # Top in T-SQL
    top_m = re.search(r"\bTOP\s+(\d+)\b", sql, re.IGNORECASE)
    if top_m:
        sql_limit = min(sql_limit, int(top_m.group(1)))

    # Simulate 3–10 rows, or up to min(sql_limit, max_rows)
    target_rows = min(random.randint(3, 10), sql_limit, max_rows)

    rows = []
    for _ in range(target_rows):
        row = []
        for col in columns:
            key = col.name.lower()
            pool = _SYNTHETIC_VALUES.get(key, _DEFAULT_VALS)
            row.append(random.choice(pool))
        rows.append(row)

    truncated = target_rows >= max_rows

    elapsed = (time.monotonic() - start) * 1000
    logger.debug("mock_execution_complete", columns=len(columns), rows=len(rows),
                 latency_ms=f"{elapsed:.1f}")

    return columns, rows, truncated
