"""Real Database Executor — connects to Aiven PostgreSQL & MySQL.

Replaces mock_executor for production use. Routes queries to the correct
Aiven database based on target_database, executes real SQL, and returns
results in the same format as execute_mock().
"""

from __future__ import annotations

import ssl
import asyncio
from typing import Any

import asyncpg
import pymysql
import structlog

from app.config import Settings, get_settings
from app.models.api import ColumnMetadata

logger = structlog.get_logger(__name__)

# Map target_database names to (engine, dbname) tuples
DATABASE_MAP: dict[str, tuple[str, str]] = {
    "apollo_analytics":  ("postgresql", "apollo_analytics"),
    "apollo_financial":  ("postgresql", "apollo_financial"),
    "apollohis":         ("mysql",      "ApolloHIS"),
    "apollohr":          ("mysql",      "ApolloHR"),
    # Allow exact-case variants
    "ApolloHIS":         ("mysql",      "ApolloHIS"),
    "ApolloHR":          ("mysql",      "ApolloHR"),
}


def _pg_type_name(oid: int) -> str:
    """Map common PostgreSQL type OIDs to readable names."""
    _PG_TYPES = {
        16: "BOOLEAN", 20: "BIGINT", 21: "SMALLINT", 23: "INTEGER",
        25: "TEXT", 700: "REAL", 701: "DOUBLE", 1043: "VARCHAR",
        1082: "DATE", 1114: "TIMESTAMP", 1184: "TIMESTAMPTZ",
        1700: "NUMERIC", 2950: "UUID", 1042: "CHAR",
    }
    return _PG_TYPES.get(oid, "VARCHAR")


def _mysql_type_name(desc_type: int) -> str:
    """Map pymysql field type constants to readable names."""
    import pymysql.constants.FIELD_TYPE as FT
    _MYSQL_TYPES = {
        FT.TINY: "TINYINT", FT.SHORT: "SMALLINT", FT.LONG: "INTEGER",
        FT.FLOAT: "FLOAT", FT.DOUBLE: "DOUBLE", FT.DECIMAL: "DECIMAL",
        FT.NEWDECIMAL: "DECIMAL", FT.LONGLONG: "BIGINT",
        FT.INT24: "MEDIUMINT", FT.TIMESTAMP: "TIMESTAMP",
        FT.DATE: "DATE", FT.DATETIME: "DATETIME", FT.TIME: "TIME",
        FT.VARCHAR: "VARCHAR", FT.VAR_STRING: "VARCHAR",
        FT.STRING: "CHAR", FT.BLOB: "BLOB", FT.LONG_BLOB: "LONGBLOB",
        FT.MEDIUM_BLOB: "MEDIUMBLOB", FT.TINY_BLOB: "TINYBLOB",
        FT.ENUM: "ENUM", FT.SET: "SET", FT.JSON: "JSON",
    }
    return _MYSQL_TYPES.get(desc_type, "VARCHAR")


async def _execute_postgresql(
    sql: str,
    parameters: dict[str, Any],
    dbname: str,
    max_rows: int,
    timeout_seconds: int,
    settings: Settings,
) -> tuple[list[ColumnMetadata], list[list[Any]], bool]:
    """Execute SQL against PostgreSQL."""
    dsn = (
        f"postgresql://{settings.postgres_user}:{settings.postgres_password}"
        f"@{settings.postgres_host}:{settings.postgres_port}/{dbname}"
    )

    connect_kwargs: dict[str, Any] = {"timeout": timeout_seconds}
    if settings.postgres_sslmode and settings.postgres_sslmode != "disable":
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
        connect_kwargs["ssl"] = ssl_ctx

    conn = await asyncpg.connect(dsn, **connect_kwargs)
    try:
        # Use conn.fetch() directly — no prepared statement issues
        records = await asyncio.wait_for(
            conn.fetch(sql),
            timeout=timeout_seconds,
        )

        # Build column metadata from first record's keys, or empty
        if records:
            col_names = list(records[0].keys())
            # Get type info via describe if possible
            columns = [
                ColumnMetadata(name=name, type="VARCHAR", masked=False)
                for name in col_names
            ]
        else:
            columns = []

        truncated = len(records) > max_rows
        if truncated:
            records = records[:max_rows]

        rows = [list(r.values()) for r in records]

        # Convert non-serialisable types to strings
        for i, row in enumerate(rows):
            for j, val in enumerate(row):
                if val is not None and not isinstance(val, (str, int, float, bool)):
                    rows[i][j] = str(val)

        logger.info("pg_execution_complete", database=dbname,
                     rows=len(rows), truncated=truncated)
        return columns, rows, truncated
    finally:
        await conn.close()


def _execute_mysql_sync(
    sql: str,
    parameters: dict[str, Any],
    dbname: str,
    max_rows: int,
    timeout_seconds: int,
    settings: Settings,
) -> tuple[list[ColumnMetadata], list[list[Any]], bool]:
    """Execute SQL against Aiven MySQL (synchronous — run in executor)."""
    ssl_config = {"ssl": {"ssl_mode": "REQUIRED"}} if settings.mysql_ssl else {}

    conn = pymysql.connect(
        host=settings.mysql_host,
        port=settings.mysql_port,
        user=settings.mysql_user,
        password=settings.mysql_password,
        database=dbname,
        connect_timeout=timeout_seconds,
        read_timeout=timeout_seconds,
        charset="utf8mb4",
        **ssl_config,
    )
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            desc = cursor.description or []

            columns = [
                ColumnMetadata(
                    name=d[0],
                    type=_mysql_type_name(d[1]),
                    masked=False,
                )
                for d in desc
            ]

            # Fetch max_rows + 1 to detect truncation
            records = cursor.fetchmany(max_rows + 1)
            truncated = len(records) > max_rows
            if truncated:
                records = records[:max_rows]

            rows = []
            for rec in records:
                row = []
                for val in rec:
                    if val is not None and not isinstance(val, (str, int, float, bool)):
                        row.append(str(val))
                    else:
                        row.append(val)
                rows.append(row)

        logger.info("mysql_execution_complete", database=dbname,
                     rows=len(rows), truncated=truncated)
        return columns, rows, truncated
    finally:
        conn.close()


def _strip_db_prefix(sql: str, dbname: str) -> str:
    """Strip database name prefix from table references in SQL.

    PostgreSQL doesn't support database.table syntax — tables are accessed
    by schema.table within the connected database. Since we connect directly
    to the target database, strip the prefix so 'apollo_financial.claims'
    becomes just 'claims'.
    """
    import re
    # Match dbname. or dbname.schema. patterns (case-insensitive)
    pattern = re.compile(rf'\b{re.escape(dbname)}\.', re.IGNORECASE)
    return pattern.sub('', sql)


async def execute_real(
    sql: str,
    parameters: dict[str, Any],
    target_database: str,
    max_rows: int,
    timeout_seconds: int,
    settings: Settings | None = None,
) -> tuple[list[ColumnMetadata], list[list[Any]], bool]:
    """Execute SQL against the appropriate Aiven database.

    Returns (columns, rows, truncated) — same signature as execute_mock().
    """
    if settings is None:
        settings = get_settings()

    db_key = target_database.lower().replace("-", "_")
    lookup = DATABASE_MAP.get(db_key) or DATABASE_MAP.get(target_database)

    if not lookup:
        raise ValueError(
            f"Unknown target_database '{target_database}'. "
            f"Valid: {sorted(set(v[1] for v in DATABASE_MAP.values()))}"
        )

    engine, dbname = lookup

    logger.info("real_execution_start", engine=engine, database=dbname,
                sql_preview=sql[:120])

    if engine == "postgresql":
        clean_sql = _strip_db_prefix(sql, dbname)
        return await _execute_postgresql(
            clean_sql, parameters, dbname, max_rows, timeout_seconds, settings,
        )
    elif engine == "mysql":
        # pymysql is synchronous — run in thread executor
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            _execute_mysql_sync,
            sql, parameters, dbname, max_rows, timeout_seconds, settings,
        )
    else:
        raise ValueError(f"Unsupported engine: {engine}")
