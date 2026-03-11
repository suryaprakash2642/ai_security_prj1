"""Live database crawl — connects to real databases, extracts schema metadata,
and builds a knowledge graph in Neo4j.

Usage:
    # Crawl all databases and build knowledge graph:
    python -m scripts.live_crawl --graph

    # Crawl specific database(s) and build graph:
    python -m scripts.live_crawl --graph --db tsdb apollo_analytics

    # Crawl only (no graph):
    python -m scripts.live_crawl

    # List available databases:
    python -m scripts.live_crawl --list
"""

from __future__ import annotations

import argparse
import asyncio
import functools
import hashlib
import json
import os
import re
import ssl
import time
import uuid
from pathlib import Path

import structlog
from dotenv import load_dotenv

load_dotenv()

logger = structlog.get_logger(__name__)


# ── Vault / Credential helper (P0-C) ────────────────────────
# Falls back to environment variables when Vault is unavailable.
# To enable Vault: set VAULT_ADDR and VAULT_TOKEN env vars.

def _vault_secret(vault_path: str, key: str, env_fallback: str) -> str:
    """Retrieve a secret from HashiCorp Vault KV v2, falling back to env."""
    vault_addr = os.getenv("VAULT_ADDR", "")
    vault_token = os.getenv("VAULT_TOKEN", "")
    if vault_addr and vault_token:
        try:
            import urllib.request
            req = urllib.request.Request(
                f"{vault_addr}/v1/{vault_path}",
                headers={"X-Vault-Token": vault_token},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                return data["data"]["data"][key]
        except Exception as exc:
            logger.warning("vault_fallback", path=vault_path, key=key, reason=str(exc)[:100])
    return os.getenv(env_fallback, "")


# ── Retry helper (P1-D) ──────────────────────────────────────

def _async_retry(max_attempts: int = 3, base_delay: float = 1.5):
    """Exponential backoff retry decorator for async functions."""
    def decorator(fn):
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return await fn(*args, **kwargs)
                except Exception as exc:
                    if attempt == max_attempts - 1:
                        raise
                    delay = base_delay * (2 ** attempt)
                    logger.warning(
                        "retry_attempt",
                        fn=fn.__name__,
                        attempt=attempt + 1,
                        delay=delay,
                        error=str(exc)[:100],
                    )
                    await asyncio.sleep(delay)
        return wrapper
    return decorator


def _property_hash(props: dict) -> str:
    """Compute a short deterministic hash of a dict for change detection."""
    canonical = json.dumps(props, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]

def _generate_uuid(fqn: str) -> str:
    """Deterministic UUIDv5 from an FQN string for Section 5 node IDs."""
    namespace = uuid.NAMESPACE_URL
    return str(uuid.uuid5(namespace, fqn))


# ── Database connection configs ──────────────────────────────


def _aiven_pg_dsn(dbname: str) -> str:
    """Build PostgreSQL DSN for Aiven Cloud."""
    host = _vault_secret("secret/data/apollo/aiven-pg", "host", "AIVEN_PG_HOST") or os.getenv("POSTGRES_HOST", "")
    port = _vault_secret("secret/data/apollo/aiven-pg", "port", "AIVEN_PG_PORT") or os.getenv("POSTGRES_PORT", "21400")
    user = _vault_secret("secret/data/apollo/aiven-pg", "user", "AIVEN_PG_USER") or os.getenv("POSTGRES_USER", "avnadmin")
    pwd = _vault_secret("secret/data/apollo/aiven-pg", "password", "AIVEN_PG_PASSWORD") or os.getenv("POSTGRES_PASSWORD", "")
    return f"postgresql://{user}:{pwd}@{host}:{port}/{dbname}"


# Keep legacy alias for functions that call _pg_rds_dsn (pgvector storage, etc.)
_pg_rds_dsn = _aiven_pg_dsn


def _aiven_mysql_params(dbname: str) -> dict:
    """Build connection params dict for Aiven MySQL (pymysql)."""
    host = _vault_secret("secret/data/apollo/aiven-mysql", "host", "MYSQL_HOST")
    port = int(_vault_secret("secret/data/apollo/aiven-mysql", "port", "MYSQL_PORT") or "21400")
    user = _vault_secret("secret/data/apollo/aiven-mysql", "user", "MYSQL_USER") or "avnadmin"
    pwd = _vault_secret("secret/data/apollo/aiven-mysql", "password", "MYSQL_PASSWORD")
    return {
        "host": host,
        "port": port,
        "user": user,
        "password": pwd,
        "database": dbname,
        "ssl": {"ssl": True},
        "connect_timeout": 15,
    }


DATABASE_REGISTRY = {
    "apollo_analytics": {
        "engine": "postgresql",
        "host": os.getenv("AIVEN_PG_HOST", os.getenv("POSTGRES_HOST", "")),
        "dsn_fn": lambda: _aiven_pg_dsn("apollo_analytics"),
        "description": "Analytics & Reporting Database (Aiven PostgreSQL)",
        "ssl": "aiven",
    },
    "apollo_financial": {
        "engine": "postgresql",
        "host": os.getenv("AIVEN_PG_HOST", os.getenv("POSTGRES_HOST", "")),
        "dsn_fn": lambda: _aiven_pg_dsn("apollo_financial"),
        "description": "Financial & Procurement Database (Aiven PostgreSQL)",
        "ssl": "aiven",
    },
    "ApolloHR": {
        "engine": "mysql",
        "host": os.getenv("MYSQL_HOST", ""),
        "dsn_fn": lambda: _aiven_mysql_params("ApolloHR"),
        "description": "Human Resources Database (Aiven MySQL)",
        "ssl": None,
    },
    "ApolloHIS": {
        "engine": "mysql",
        "host": os.getenv("MYSQL_HOST", ""),
        "dsn_fn": lambda: _aiven_mysql_params("ApolloHIS"),
        "description": "Hospital Information System (Aiven MySQL)",
        "ssl": None,
    },
}


# ── PostgreSQL live crawler ──────────────────────────────────


async def crawl_postgresql(dsn: str, db_name: str, ssl_ctx=None) -> dict:
    """Crawl a PostgreSQL/Timescale database via information_schema."""
    import asyncpg

    connect_kwargs = {}
    if ssl_ctx:
        connect_kwargs["ssl"] = ssl_ctx

    conn = await asyncio.wait_for(
        asyncpg.connect(dsn, **connect_kwargs),
        timeout=15,
    )

    try:
        logger.info("pg_connected", database=db_name, server_version=str(conn.get_server_version()))

        excluded = (
            "pg_catalog", "information_schema",
            "_timescaledb_catalog", "_timescaledb_config",
            "_timescaledb_internal", "_timescaledb_cache",
        )
        placeholders = ", ".join(f"${i+1}" for i in range(len(excluded)))

        # ── Tables ──
        table_rows = await conn.fetch(f"""
            SELECT t.table_schema, t.table_name
            FROM information_schema.tables t
            WHERE t.table_type = 'BASE TABLE'
              AND t.table_schema NOT IN ({placeholders})
            ORDER BY t.table_schema, t.table_name
        """, *excluded)

        logger.info("tables_discovered", database=db_name, total_tables=len(table_rows))

        tables = {}
        for row in table_rows:
            schema = row["table_schema"]
            table = row["table_name"]
            fqn = f"{db_name}.{schema}.{table}"
            tables[fqn] = {
                "name": table,
                "schema": schema,
                "fqn": fqn,
                "columns": [],
                "pk_columns": [],
                "foreign_keys": [],
                "row_count": 0,
            }

        # ── Columns ──
        col_rows = await conn.fetch(f"""
            SELECT c.table_schema, c.table_name, c.column_name,
                   c.data_type, c.is_nullable, c.ordinal_position
            FROM information_schema.columns c
            JOIN information_schema.tables t
              ON c.table_schema = t.table_schema AND c.table_name = t.table_name
            WHERE t.table_type = 'BASE TABLE'
              AND t.table_schema NOT IN ({placeholders})
            ORDER BY c.table_schema, c.table_name, c.ordinal_position
        """, *excluded)

        for row in col_rows:
            fqn = f"{db_name}.{row['table_schema']}.{row['table_name']}"
            if fqn in tables:
                tables[fqn]["columns"].append({
                    "name": row["column_name"],
                    "data_type": row["data_type"],
                    "is_nullable": row["is_nullable"],
                    "ordinal_position": row["ordinal_position"],
                })

        # ── Primary Keys ──
        pk_rows = await conn.fetch(f"""
            SELECT tc.table_schema, tc.table_name, kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
             AND tc.table_schema = kcu.table_schema
            WHERE tc.constraint_type = 'PRIMARY KEY'
              AND tc.table_schema NOT IN ({placeholders})
        """, *excluded)

        for row in pk_rows:
            fqn = f"{db_name}.{row['table_schema']}.{row['table_name']}"
            if fqn in tables:
                tables[fqn]["pk_columns"].append(row["column_name"])

        # ── Foreign Keys ──
        fk_rows = await conn.fetch(f"""
            SELECT tc.table_schema, tc.table_name, tc.constraint_name,
                   kcu.column_name AS source_column,
                   ccu.table_schema AS target_schema,
                   ccu.table_name AS target_table,
                   ccu.column_name AS target_column
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage ccu
              ON tc.constraint_name = ccu.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_schema NOT IN ({placeholders})
        """, *excluded)

        for row in fk_rows:
            fqn = f"{db_name}.{row['table_schema']}.{row['table_name']}"
            if fqn in tables:
                tables[fqn]["foreign_keys"].append({
                    "constraint_name": row["constraint_name"],
                    "source_column": row["source_column"],
                    "target_schema": row["target_schema"],
                    "target_table": row["target_table"],
                    "target_column": row["target_column"],
                })

        # ── Row counts (approximate via pg_stat) ──
        for fqn, tinfo in tables.items():
            try:
                result = await conn.fetchval(
                    "SELECT reltuples::bigint FROM pg_class "
                    "WHERE relname = $1 AND relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = $2)",
                    tinfo["name"], tinfo["schema"]
                )
                tinfo["row_count"] = max(0, result or 0)
            except Exception:
                tinfo["row_count"] = 0

        # ── Indexes (P2-1) ──
        idx_rows = await conn.fetch(f"""
            SELECT schemaname, tablename, indexname, indexdef
            FROM pg_indexes
            WHERE schemaname NOT IN ({placeholders})
            ORDER BY schemaname, tablename, indexname
        """, *excluded)

        for row in idx_rows:
            fqn = f"{db_name}.{row['schemaname']}.{row['tablename']}"
            if fqn in tables:
                if "indexes" not in tables[fqn]:
                    tables[fqn]["indexes"] = []
                tables[fqn]["indexes"].append({
                    "name": row["indexname"],
                    "definition": row["indexdef"],
                })

        # Ensure all tables have an indexes list
        for tinfo in tables.values():
            tinfo.setdefault("indexes", [])

        # ── Log per-table details ──
        total_columns = 0
        for fqn, tinfo in tables.items():
            col_names = [c["name"] for c in tinfo["columns"]]
            total_columns += len(col_names)
            logger.info(
                "table_metadata",
                database=db_name,
                table=tinfo["name"],
                schema=tinfo["schema"],
                total_columns=len(col_names),
                column_names=col_names,
                primary_keys=tinfo["pk_columns"] or None,
                foreign_keys=len(tinfo["foreign_keys"]),
                indexes=len(tinfo["indexes"]),
                row_count_approx=tinfo["row_count"],
            )
            for col in tinfo["columns"]:
                logger.info(
                    "column_metadata",
                    database=db_name,
                    table=tinfo["name"],
                    column=col["name"],
                    data_type=col["data_type"],
                    is_nullable=col["is_nullable"],
                    ordinal_position=col["ordinal_position"],
                )

        return {
            "tables": tables,
            "total_tables": len(tables),
            "total_columns": total_columns,
            "total_pk": sum(len(t["pk_columns"]) for t in tables.values()),
            "total_fk": sum(len(t["foreign_keys"]) for t in tables.values()),
            "total_indexes": sum(len(t["indexes"]) for t in tables.values()),
            "status": "completed",
        }

    finally:
        await conn.close()


# ── MySQL live crawler ───────────────────────────────────────


def crawl_mysql_sync(conn_params: dict, db_name: str) -> dict:
    """Crawl a MySQL database via information_schema (pymysql, synchronous)."""
    import pymysql

    conn = pymysql.connect(**conn_params)
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    result: dict = {
        "tables": {},
        "total_tables": 0,
        "total_columns": 0,
        "total_pk": 0,
        "total_fk": 0,
        "total_indexes": 0,
        "status": "completed",
    }

    try:
        # ── Discover tables ──
        cursor.execute("""
            SELECT TABLE_SCHEMA, TABLE_NAME
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'BASE TABLE'
            ORDER BY TABLE_SCHEMA, TABLE_NAME
        """, (db_name,))
        raw_tables = cursor.fetchall()

        for tbl in raw_tables:
            schema = tbl["TABLE_SCHEMA"]
            table_name = tbl["TABLE_NAME"]
            fqn = f"{db_name}.{schema}.{table_name}"
            result["tables"][fqn] = {
                "name": table_name,
                "schema": schema,
                "fqn": fqn,
                "columns": [],
                "pk_columns": [],
                "foreign_keys": [],
                "indexes": [],
                "row_count": 0,
            }

        # ── Discover columns ──
        cursor.execute("""
            SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, DATA_TYPE,
                   IS_NULLABLE, ORDINAL_POSITION
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = %s
            ORDER BY TABLE_SCHEMA, TABLE_NAME, ORDINAL_POSITION
        """, (db_name,))
        for col in cursor.fetchall():
            fqn = f"{db_name}.{col['TABLE_SCHEMA']}.{col['TABLE_NAME']}"
            if fqn in result["tables"]:
                result["tables"][fqn]["columns"].append({
                    "name": col["COLUMN_NAME"],
                    "data_type": col["DATA_TYPE"],
                    "is_nullable": col["IS_NULLABLE"] == "YES",
                    "ordinal_position": col["ORDINAL_POSITION"],
                })
                result["total_columns"] += 1

        # ── Discover primary keys ──
        cursor.execute("""
            SELECT tc.TABLE_SCHEMA, tc.TABLE_NAME, kcu.COLUMN_NAME
            FROM information_schema.TABLE_CONSTRAINTS tc
            JOIN information_schema.KEY_COLUMN_USAGE kcu
              ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
              AND tc.TABLE_SCHEMA = kcu.TABLE_SCHEMA
              AND tc.TABLE_NAME = kcu.TABLE_NAME
            WHERE tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
              AND tc.TABLE_SCHEMA = %s
        """, (db_name,))
        for pk in cursor.fetchall():
            fqn = f"{db_name}.{pk['TABLE_SCHEMA']}.{pk['TABLE_NAME']}"
            if fqn in result["tables"]:
                result["tables"][fqn]["pk_columns"].append(pk["COLUMN_NAME"])
                result["total_pk"] += 1

        # ── Discover foreign keys ──
        cursor.execute("""
            SELECT kcu.TABLE_SCHEMA, kcu.TABLE_NAME, kcu.COLUMN_NAME,
                   kcu.REFERENCED_TABLE_SCHEMA, kcu.REFERENCED_TABLE_NAME,
                   kcu.REFERENCED_COLUMN_NAME, kcu.CONSTRAINT_NAME
            FROM information_schema.KEY_COLUMN_USAGE kcu
            WHERE kcu.TABLE_SCHEMA = %s
              AND kcu.REFERENCED_TABLE_NAME IS NOT NULL
        """, (db_name,))
        for fk in cursor.fetchall():
            fqn = f"{db_name}.{fk['TABLE_SCHEMA']}.{fk['TABLE_NAME']}"
            if fqn in result["tables"]:
                result["tables"][fqn]["foreign_keys"].append({
                    "constraint_name": fk["CONSTRAINT_NAME"],
                    "source_column": fk["COLUMN_NAME"],
                    "target_schema": fk["REFERENCED_TABLE_SCHEMA"],
                    "target_table": fk["REFERENCED_TABLE_NAME"],
                    "target_column": fk["REFERENCED_COLUMN_NAME"],
                })
                result["total_fk"] += 1

        # ── Row counts ──
        for fqn, tinfo in result["tables"].items():
            try:
                cursor.execute(
                    f"SELECT COUNT(*) AS cnt FROM `{tinfo['schema']}`.`{tinfo['name']}`"
                )
                row = cursor.fetchone()
                tinfo["row_count"] = row["cnt"] if row else 0
            except Exception:
                tinfo["row_count"] = 0

        # ── Indexes ──
        cursor.execute("""
            SELECT TABLE_SCHEMA, TABLE_NAME, INDEX_NAME, NON_UNIQUE, COLUMN_NAME
            FROM information_schema.STATISTICS
            WHERE TABLE_SCHEMA = %s
            ORDER BY TABLE_SCHEMA, TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX
        """, (db_name,))
        idx_map: dict[str, list] = {}
        for idx in cursor.fetchall():
            fqn = f"{db_name}.{idx['TABLE_SCHEMA']}.{idx['TABLE_NAME']}"
            key = f"{fqn}::{idx['INDEX_NAME']}"
            if key not in idx_map:
                idx_map[key] = {"fqn": fqn, "name": idx["INDEX_NAME"],
                                "unique": idx["NON_UNIQUE"] == 0, "columns": []}
            idx_map[key]["columns"].append(idx["COLUMN_NAME"])

        for info in idx_map.values():
            fqn = info["fqn"]
            if fqn in result["tables"]:
                result["tables"][fqn]["indexes"].append({
                    "name": info["name"],
                    "definition": f"{'UNIQUE ' if info['unique'] else ''}INDEX on ({', '.join(info['columns'])})",
                })
                result["total_indexes"] += 1

        result["total_tables"] = len(result["tables"])

    finally:
        cursor.close()
        conn.close()

    return result


# ── SQL Server live crawler ──────────────────────────────────


def crawl_sqlserver_sync(conn_str: str, db_name: str) -> dict:
    """Crawl a SQL Server database via INFORMATION_SCHEMA (synchronous pyodbc)."""
    import pyodbc

    conn = pyodbc.connect(conn_str, timeout=15)
    cursor = conn.cursor()

    logger.info("sqlserver_connected", database=db_name)

    # ── Tables ──
    cursor.execute("""
        SELECT TABLE_SCHEMA, TABLE_NAME
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_TYPE = 'BASE TABLE'
        ORDER BY TABLE_SCHEMA, TABLE_NAME
    """)
    table_rows = cursor.fetchall()
    logger.info("tables_discovered", database=db_name, total_tables=len(table_rows))

    tables = {}
    for row in table_rows:
        schema, table = row[0], row[1]
        fqn = f"{db_name}.{schema}.{table}"
        tables[fqn] = {
            "name": table,
            "schema": schema,
            "fqn": fqn,
            "columns": [],
            "pk_columns": [],
            "foreign_keys": [],
            "row_count": 0,
        }

    # ── Columns ──
    cursor.execute("""
        SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME,
               DATA_TYPE, IS_NULLABLE, ORDINAL_POSITION
        FROM INFORMATION_SCHEMA.COLUMNS
        ORDER BY TABLE_SCHEMA, TABLE_NAME, ORDINAL_POSITION
    """)
    for row in cursor.fetchall():
        fqn = f"{db_name}.{row[0]}.{row[1]}"
        if fqn in tables:
            tables[fqn]["columns"].append({
                "name": row[2],
                "data_type": row[3],
                "is_nullable": row[4],
                "ordinal_position": row[5],
            })

    # ── Primary Keys ──
    cursor.execute("""
        SELECT tc.TABLE_SCHEMA, tc.TABLE_NAME, ccu.COLUMN_NAME
        FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
        JOIN INFORMATION_SCHEMA.CONSTRAINT_COLUMN_USAGE ccu
          ON tc.CONSTRAINT_NAME = ccu.CONSTRAINT_NAME
        WHERE tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
    """)
    for row in cursor.fetchall():
        fqn = f"{db_name}.{row[0]}.{row[1]}"
        if fqn in tables:
            tables[fqn]["pk_columns"].append(row[2])

    # ── Foreign Keys ──
    cursor.execute("""
        SELECT tc.TABLE_SCHEMA, tc.TABLE_NAME, tc.CONSTRAINT_NAME,
               kcu.COLUMN_NAME AS SOURCE_COLUMN,
               ccu.TABLE_SCHEMA AS TARGET_SCHEMA,
               ccu.TABLE_NAME AS TARGET_TABLE,
               ccu.COLUMN_NAME AS TARGET_COLUMN
        FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
        JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
          ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME AND tc.TABLE_SCHEMA = kcu.TABLE_SCHEMA
        JOIN INFORMATION_SCHEMA.CONSTRAINT_COLUMN_USAGE ccu
          ON tc.CONSTRAINT_NAME = ccu.CONSTRAINT_NAME
        WHERE tc.CONSTRAINT_TYPE = 'FOREIGN KEY'
    """)
    for row in cursor.fetchall():
        fqn = f"{db_name}.{row[0]}.{row[1]}"
        if fqn in tables:
            tables[fqn]["foreign_keys"].append({
                "constraint_name": row[2],
                "source_column": row[3],
                "target_schema": row[4],
                "target_table": row[5],
                "target_column": row[6],
            })

    # ── Row counts ──
    for fqn, tinfo in tables.items():
        try:
            cursor.execute(
                f"SELECT SUM(rows) FROM sys.partitions "
                f"WHERE object_id = OBJECT_ID('{tinfo['schema']}.{tinfo['name']}') AND index_id IN (0, 1)"
            )
            r = cursor.fetchone()
            tinfo["row_count"] = r[0] or 0 if r else 0
        except Exception:
            tinfo["row_count"] = 0

    # ── Indexes (P2-1) ──
    try:
        cursor.execute("""
            SELECT s.name AS schema_name, t.name AS table_name,
                   i.name AS index_name, i.type_desc, i.is_unique
            FROM sys.indexes i
            JOIN sys.tables t ON i.object_id = t.object_id
            JOIN sys.schemas s ON t.schema_id = s.schema_id
            WHERE i.name IS NOT NULL
            ORDER BY s.name, t.name, i.name
        """)
        for row in cursor.fetchall():
            fqn = f"{db_name}.{row[0]}.{row[1]}"
            if fqn in tables:
                if "indexes" not in tables[fqn]:
                    tables[fqn]["indexes"] = []
                tables[fqn]["indexes"].append({
                    "name": row[2],
                    "type": row[3],
                    "is_unique": bool(row[4]),
                })
    except Exception as e:
        logger.warning("sqlserver_index_query_failed", error=str(e)[:100])

    # Ensure all tables have an indexes list
    for tinfo in tables.values():
        tinfo.setdefault("indexes", [])

    conn.close()

    # ── Log per-table details ──
    total_columns = 0
    for fqn, tinfo in tables.items():
        col_names = [c["name"] for c in tinfo["columns"]]
        total_columns += len(col_names)
        logger.info(
            "table_metadata",
            database=db_name,
            table=tinfo["name"],
            schema=tinfo["schema"],
            total_columns=len(col_names),
            column_names=col_names,
            primary_keys=tinfo["pk_columns"] or None,
            foreign_keys=len(tinfo["foreign_keys"]),
            indexes=len(tinfo["indexes"]),
            row_count_approx=tinfo["row_count"],
        )
        for col in tinfo["columns"]:
            logger.info(
                "column_metadata",
                database=db_name,
                table=tinfo["name"],
                column=col["name"],
                data_type=col["data_type"],
                is_nullable=col["is_nullable"],
                ordinal_position=col["ordinal_position"],
            )

    return {
        "tables": tables,
        "total_tables": len(tables),
        "total_columns": total_columns,
        "total_pk": sum(len(t["pk_columns"]) for t in tables.values()),
        "total_fk": sum(len(t["foreign_keys"]) for t in tables.values()),
        "total_indexes": sum(len(t["indexes"]) for t in tables.values()),
        "status": "completed",
    }


# ── Oracle live crawler (P0-A) ─────────────────────────────


def crawl_oracle_sync(conn_str: str, db_name: str) -> dict:
    """Crawl an Oracle database using ALL_TABLES/ALL_TAB_COLUMNS/ALL_CONSTRAINTS."""
    import oracledb  # pip install oracledb

    user, rest = conn_str.split("/", 1)
    pwd, dsn = rest.split("@", 1)
    conn = oracledb.connect(user=user, password=pwd, dsn=dsn)
    cursor = conn.cursor()
    logger.info("oracle_connected", database=db_name)

    # ── Tables (ALL_TABLES visible to this read-only user) ──
    cursor.execute("""
        SELECT owner, table_name
        FROM all_tables
        WHERE owner NOT IN ('SYS','SYSTEM','OUTLN','XDB','DBSNMP','APPQOSSYS',
                            'ORDDATA','MDSYS','CTXSYS','WMSYS','DBSFWUSER',
                            'GGSYS','OJVMSYS','ORDSYS','ORDPLUGINS','SI_INFORMTN_SCHEMA')
        ORDER BY owner, table_name
    """)
    table_rows = cursor.fetchall()
    logger.info("tables_discovered", database=db_name, total_tables=len(table_rows))

    tables: dict = {}
    for owner, table_name in table_rows:
        schema = owner.lower()
        name = table_name.lower()
        fqn = f"{db_name}.{schema}.{name}"
        tables[fqn] = {
            "name": name, "schema": schema, "fqn": fqn,
            "columns": [], "pk_columns": [], "foreign_keys": [],
            "indexes": [], "row_count": 0,
        }

    # ── Columns ──
    cursor.execute("""
        SELECT owner, table_name, column_name, data_type, nullable, column_id
        FROM all_tab_columns
        WHERE owner NOT IN ('SYS','SYSTEM','OUTLN','XDB','DBSNMP','APPQOSSYS',
                            'ORDDATA','MDSYS','CTXSYS','WMSYS','DBSFWUSER',
                            'GGSYS','OJVMSYS','ORDSYS','ORDPLUGINS','SI_INFORMTN_SCHEMA')
        ORDER BY owner, table_name, column_id
    """)
    for owner, tname, cname, dtype, nullable, col_id in cursor.fetchall():
        fqn = f"{db_name}.{owner.lower()}.{tname.lower()}"
        if fqn in tables:
            tables[fqn]["columns"].append({
                "name": cname.lower(), "data_type": dtype.lower(),
                "is_nullable": "YES" if nullable == "Y" else "NO",
                "ordinal_position": col_id,
            })

    # ── Primary Keys ──
    cursor.execute("""
        SELECT c.owner, c.table_name, cols.column_name
        FROM all_constraints c
        JOIN all_cons_columns cols
          ON c.constraint_name = cols.constraint_name AND c.owner = cols.owner
        WHERE c.constraint_type = 'P'
              AND c.owner NOT IN ('SYS','SYSTEM')
    """)
    for owner, tname, colname in cursor.fetchall():
        fqn = f"{db_name}.{owner.lower()}.{tname.lower()}"
        if fqn in tables:
            tables[fqn]["pk_columns"].append(colname.lower())

    # ── Foreign Keys ──
    cursor.execute("""
        SELECT c.owner, c.table_name, c.constraint_name, cc.column_name,
               rc.owner AS r_owner, rc.table_name AS r_table, rcc.column_name AS r_col
        FROM all_constraints c
        JOIN all_cons_columns cc
          ON c.constraint_name = cc.constraint_name AND c.owner = cc.owner
        JOIN all_constraints rc
          ON c.r_constraint_name = rc.constraint_name
        JOIN all_cons_columns rcc
          ON rc.constraint_name = rcc.constraint_name AND rc.owner = rcc.owner
        WHERE c.constraint_type = 'R'
              AND c.owner NOT IN ('SYS','SYSTEM')
    """)
    for row in cursor.fetchall():
        owner, tname, conname, colname, r_owner, r_table, r_col = row
        fqn = f"{db_name}.{owner.lower()}.{tname.lower()}"
        if fqn in tables:
            tables[fqn]["foreign_keys"].append({
                "constraint_name": conname.lower(),
                "source_column": colname.lower(),
                "target_schema": r_owner.lower(),
                "target_table": r_table.lower(),
                "target_column": r_col.lower(),
            })

    # ── Indexes ──
    cursor.execute("""
        SELECT owner, table_name, index_name, uniqueness
        FROM all_indexes
        WHERE owner NOT IN ('SYS','SYSTEM')
    """)
    for owner, tname, iname, uniq in cursor.fetchall():
        fqn = f"{db_name}.{owner.lower()}.{tname.lower()}"
        if fqn in tables:
            tables[fqn]["indexes"].append({
                "name": iname.lower(),
                "is_unique": uniq == "UNIQUE",
            })

    # ── Row counts (approximate via ALL_TABLES.NUM_ROWS) ──
    cursor.execute("""
        SELECT owner, table_name, num_rows FROM all_tables
        WHERE owner NOT IN ('SYS','SYSTEM')
    """)
    for owner, tname, nrows in cursor.fetchall():
        fqn = f"{db_name}.{owner.lower()}.{tname.lower()}"
        if fqn in tables:
            tables[fqn]["row_count"] = nrows or 0

    conn.close()

    total_columns = sum(len(t["columns"]) for t in tables.values())
    return {
        "tables": tables, "total_tables": len(tables),
        "total_columns": total_columns,
        "total_pk": sum(len(t["pk_columns"]) for t in tables.values()),
        "total_fk": sum(len(t["foreign_keys"]) for t in tables.values()),
        "total_indexes": sum(len(t["indexes"]) for t in tables.values()),
        "status": "completed",
    }


# ── MongoDB live crawler (P0-B) ──────────────────────────


async def crawl_mongodb(uri: str, db_name: str) -> dict:
    """Crawl a MongoDB database by sampling documents to infer schema.
    Uses pymongo with Motor for async support. Schema inferred from document samples.
    """
    from pymongo import MongoClient  # pip install pymongo

    client = MongoClient(uri, serverSelectionTimeoutMS=15000)
    db = client[db_name]
    logger.info("mongodb_connected", database=db_name)

    collections = db.list_collection_names()
    logger.info("tables_discovered", database=db_name, total_tables=len(collections))

    tables: dict = {}
    schema_name = "default"

    for coll_name in collections:
        fqn = f"{db_name}.{schema_name}.{coll_name}"
        collection = db[coll_name]

        # Infer schema by sampling up to 200 documents
        sample_docs = list(collection.aggregate([
            {"$sample": {"size": 200}},
            {"$project": {"_id": 0}},
        ]))

        # Gather all unique field names from sampled documents
        field_types: dict[str, set] = {}
        for doc in sample_docs:
            for field, val in doc.items():
                field_types.setdefault(field, set()).add(type(val).__name__)

        columns = [
            {
                "name": fname,
                "data_type": "/".join(sorted(ftypes)),
                "is_nullable": "YES",
                "ordinal_position": idx + 1,
            }
            for idx, (fname, ftypes) in enumerate(sorted(field_types.items()))
        ]

        # Add _id as PK
        pk_columns = ["_id"]
        if "_id" not in field_types:
            columns.insert(0, {"name": "_id", "data_type": "ObjectId", "is_nullable": "NO", "ordinal_position": 0})

        # Indexes from collection.index_information()
        indexes = []
        try:
            for idx_name, idx_info in collection.index_information().items():
                indexes.append({
                    "name": idx_name,
                    "is_unique": idx_info.get("unique", False),
                    "definition": str(idx_info.get("key", "")),
                })
        except Exception:
            pass

        row_count = collection.estimated_document_count()

        tables[fqn] = {
            "name": coll_name, "schema": schema_name, "fqn": fqn,
            "columns": columns, "pk_columns": pk_columns,
            "foreign_keys": [], "indexes": indexes,
            "row_count": row_count,
        }

    client.close()

    total_columns = sum(len(t["columns"]) for t in tables.values())
    return {
        "tables": tables, "total_tables": len(tables),
        "total_columns": total_columns,
        "total_pk": sum(len(t["pk_columns"]) for t in tables.values()),
        "total_fk": 0,  # MongoDB doesn't enforce FK constraints
        "total_indexes": sum(len(t["indexes"]) for t in tables.values()),
        "status": "completed",
    }


# ── Main crawl orchestrator ─────────────────────────────────


async def crawl_one(db_name: str, db_info: dict) -> dict:
    """Crawl a single database."""
    engine = db_info["engine"]
    dsn = db_info["dsn_fn"]()

    logger.info(
        "crawl_starting",
        database=db_name,
        engine=engine,
        host=db_info["host"],
        description=db_info["description"],
    )

    start = time.monotonic()

    try:
        if engine in ("postgresql", "timescale_postgresql"):
            ssl_ctx = None
            ssl_flag = db_info.get("ssl")
            if ssl_flag == "timescale":
                ca_path = Path("certs/timescale-ca.pem")
                if ca_path.exists():
                    ssl_ctx = ssl.create_default_context(cafile=str(ca_path))
            elif ssl_flag == "aiven":
                ssl_ctx = ssl.create_default_context()
                ssl_ctx.check_hostname = False
                ssl_ctx.verify_mode = ssl.CERT_NONE
            result = await crawl_postgresql(dsn, db_name, ssl_ctx)

        elif engine == "mysql":
            # dsn is actually a params dict for pymysql
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, crawl_mysql_sync, dsn, db_name)

        elif engine == "sqlserver":
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, crawl_sqlserver_sync, dsn, db_name)

        elif engine == "oracle":
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, crawl_oracle_sync, dsn, db_name)

        elif engine == "mongodb":
            result = await crawl_mongodb(dsn, db_name)

        else:
            logger.error("unsupported_engine", database=db_name, engine=engine)
            return {"status": "failed", "error": f"unsupported engine: {engine}"}

    except Exception as e:
        elapsed = round(time.monotonic() - start, 2)
        logger.error(
            "crawl_failed",
            database=db_name,
            engine=engine,
            error=f"{type(e).__name__}: {str(e)[:150]}",
            duration_s=elapsed,
        )
        return {"status": "failed", "error": str(e)}

    elapsed = round(time.monotonic() - start, 2)

    logger.info(
        "crawl_complete",
        database=db_name,
        engine=engine,
        status=result["status"],
        tables_found=result["total_tables"],
        columns_found=result["total_columns"],
        primary_keys=result["total_pk"],
        foreign_keys=result["total_fk"],
        duration_s=elapsed,
    )

    return result


# ── Step 4: Auto-Classify Sensitivity ────────────────────────

# PII pattern rules using word-boundary regex (P1-B):
# (regex_pattern, sensitivity_level, pii_type, masking_strategy)
# \b word-boundaries prevent substring false positives (e.g. 'glass_snail' ≠ 'ssn')
PII_RULES: list[tuple[str, int, str, str]] = [
    # Level 5 — Critical identifiers
    (r"\baadhaar\b", 5, "NATIONAL_ID", "HASH"),
    (r"\bssn\b", 5, "SSN", "HASH"),
    (r"\bpan_number\b", 5, "TAX_ID", "HASH"),
    (r"\bpassport\b", 5, "NATIONAL_ID", "HASH"),
    (r"\bcredit_card\b", 5, "FINANCIAL", "HASH"),
    (r"\bbank_account\b", 5, "BANK_ACCOUNT", "HASH"),
    (r"\bifsc\b", 5, "BANK_ACCOUNT", "HASH"),
    # Level 5 — Financial
    (r"\bgross_salary\b", 5, "FINANCIAL", "REDACT"),
    (r"\bnet_salary\b", 5, "FINANCIAL", "REDACT"),
    (r"\bbasic_salary\b", 5, "FINANCIAL", "REDACT"),
    # Level 4 — Strong PII
    (r"\bfull_name\b", 4, "FULL_NAME", "REDACT"),
    (r"\bfirst_name\b", 4, "FULL_NAME", "REDACT"),
    (r"\blast_name\b", 4, "FULL_NAME", "REDACT"),
    (r"\bdate_of_birth\b", 4, "DATE_OF_BIRTH", "GENERALIZE_YEAR"),
    (r"\bdob\b", 4, "DATE_OF_BIRTH", "GENERALIZE_YEAR"),
    (r"\bpersonal_email\b", 4, "EMAIL", "PARTIAL_MASK"),
    (r"\bdiagnosis\b", 4, "MEDICAL", "REDACT"),
    (r"\bblood_type\b", 4, "MEDICAL", "REDACT"),
    (r"\bblood_group\b", 4, "MEDICAL", "REDACT"),
    (r"\ballerg\w*", 4, "MEDICAL", "REDACT"),
    # Level 3 — Moderate PII
    (r"\bemail\b", 3, "EMAIL", "PARTIAL_MASK"),
    (r"\bphone\b", 3, "PHONE", "PARTIAL_MASK"),
    (r"\bmobile\b", 3, "PHONE", "PARTIAL_MASK"),
    (r"\baddress\b", 3, "ADDRESS", "REDACT"),
    (r"\bgender\b", 3, "DEMOGRAPHIC", "GENERALIZE"),
    (r"\breligion\b", 3, "DEMOGRAPHIC", "REDACT"),
    (r"\bmarital\b", 3, "DEMOGRAPHIC", "GENERALIZE"),
    (r"\bemergency_contact\b", 3, "PHONE", "PARTIAL_MASK"),
    # Level 2 — Low PII
    (r"\bcity\b", 2, "ADDRESS", "GENERALIZE"),
    (r"\bstate\b", 2, "ADDRESS", "GENERALIZE"),
    (r"\bpin_code\b", 2, "ADDRESS", "GENERALIZE"),
    (r"\bzip\b", 2, "ADDRESS", "GENERALIZE"),
]

# Tables in clinical/medical schemas get minimum sensitivity 3
CLINICAL_TABLE_PATTERNS = [
    "patient", "encounter", "prescription", "medication", "vital",
    "lab_result", "radiology", "diagnosis", "surgery", "discharge",
    "clinical", "nursing", "icu",
]


def classify_sensitivity(all_results: dict[str, dict]) -> dict:
    """Step 4: Auto-classify PII sensitivity on all columns. Returns classification stats."""
    stats = {"total_pii_columns": 0, "by_level": {}, "by_type": {}}

    for db_name, result in all_results.items():
        if result.get("status") != "completed":
            continue

        for table_fqn, tinfo in result["tables"].items():
            table_lower = tinfo["name"].lower()
            is_clinical_table = any(p in table_lower for p in CLINICAL_TABLE_PATTERNS)

            for col in tinfo["columns"]:
                col_lower = col["name"].lower()
                best_level = 0
                best_pii_type = None
                best_masking = "NONE"

                # Check against PII rules via word-boundary regex (P1-B)
                for pattern, level, pii_type, masking in PII_RULES:
                    if re.search(pattern, col_lower):
                        if level > best_level:
                            best_level = level
                            best_pii_type = pii_type
                            best_masking = masking

                # Clinical table minimum — boost to level 3 and flag as PII
                if is_clinical_table and best_level < 3:
                    best_level = 3
                    if best_pii_type is None:
                        best_pii_type = "CLINICAL_CONTEXT"
                        best_masking = "REVIEW"

                # Set properties
                col["sensitivity_level"] = best_level
                col["is_pii"] = best_pii_type is not None
                col["pii_type"] = best_pii_type
                col["masking_strategy"] = best_masking
                # Flag columns that need human review
                col["needs_review"] = (
                    best_level >= 4
                    or best_pii_type == "CLINICAL_CONTEXT"
                )

                if best_pii_type:
                    stats["total_pii_columns"] += 1
                    stats["by_level"][best_level] = stats["by_level"].get(best_level, 0) + 1
                    stats["by_type"][best_pii_type] = stats["by_type"].get(best_pii_type, 0) + 1

            # Table-level sensitivity = max of its columns
            col_levels = [c.get("sensitivity_level", 0) for c in tinfo["columns"]]
            tinfo["sensitivity_level"] = max(col_levels) if col_levels else 0
            tinfo["has_pii"] = any(c.get("is_pii", False) for c in tinfo["columns"])

    logger.info(
        "sensitivity_classified",
        total_pii_columns=stats["total_pii_columns"],
        by_level=stats["by_level"],
        by_type=stats["by_type"],
    )
    return stats


# ── Step 3: Generate AI Descriptions ─────────────────────────


async def generate_descriptions(all_results: dict[str, dict]) -> dict:
    """Step 3: Use Azure OpenAI GPT-4.1 to generate table descriptions."""
    from openai import AsyncAzureOpenAI

    endpoint = os.getenv("AZURE_AI_ENDPOINT", "")
    api_key = os.getenv("AZURE_AI_API_KEY", "")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1")

    if not endpoint or not api_key:
        logger.warning("description_skip", reason="AZURE_AI_ENDPOINT or AZURE_AI_API_KEY not set")
        return {"tables_described": 0}

    client = AsyncAzureOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version="2024-12-01-preview",
    )

    stats = {"tables_described": 0, "errors": 0}
    sem = asyncio.Semaphore(5)  # Throttle concurrent API calls

    async def _describe_table(db_name, table_fqn, tinfo, engine):
        col_summary = ", ".join(
            f"{c['name']} ({c['data_type']})" for c in tinfo["columns"][:25]
        )
        pii_cols = [c["name"] for c in tinfo["columns"] if c.get("is_pii")]
        pii_note = f" PII columns: {', '.join(pii_cols)}." if pii_cols else ""
        domain = tinfo.get("domain", "general")

        prompt = (
            f"Database: {db_name} (engine: {engine})\n"
            f"Schema: {tinfo['schema']}, Table: {tinfo['name']}\n"
            f"Domain: {domain}\n"
            f"Columns: {col_summary}\n"
            f"Approximate rows: {tinfo['row_count']}\n"
            f"{pii_note}\n\n"
            "Describe what this database table stores in 2–3 sentences, "
            "suitable for a non-technical analyst to understand. "
            "Mention the domain and any notable PII or sensitive data."
        )

        async with sem:
            # P1-D: Retry with exponential backoff before falling back to stub
            @_async_retry(max_attempts=3, base_delay=1.5)
            async def _call_api():
                return await client.chat.completions.create(
                    model=deployment,
                    messages=[
                        {"role": "system", "content": "You are a database documentation assistant. Write concise, clear descriptions."},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=200,
                    temperature=0.3,
                )

            try:
                resp = await _call_api()
                description = resp.choices[0].message.content.strip()
                tinfo["description"] = description
                stats["tables_described"] += 1
                logger.info(
                    "description_generated",
                    database=db_name,
                    table=tinfo["name"],
                    length=len(description),
                )
            except Exception as e:
                stats["errors"] += 1
                tinfo["description"] = f"{tinfo['name']} table in {db_name}"
                logger.warning(
                    "description_error_final",
                    database=db_name,
                    table=tinfo["name"],
                    error=str(e)[:120],
                )

    tasks = []
    for db_name, result in all_results.items():
        if result.get("status") != "completed":
            continue
        engine = result.get("engine", "?")
        for table_fqn, tinfo in result["tables"].items():
            tasks.append(_describe_table(db_name, table_fqn, tinfo, engine))

    if tasks:
        await asyncio.gather(*tasks)

    # Compute description hashes for delta tracking
    for db_name, result in all_results.items():
        if result.get("status") != "completed":
            continue
        for table_fqn, tinfo in result["tables"].items():
            desc = tinfo.get("description", tinfo["name"])
            col_names = ", ".join(c["name"] for c in tinfo["columns"][:20])
            embed_text = f"{tinfo['name']}: {desc} Columns: {col_names}"
            tinfo["description_hash"] = _property_hash({"text": embed_text})

    logger.info("descriptions_complete", **stats)
    await client.close()
    return stats


# ── Step 9: Generate Embeddings (delta-aware) ───────────────


async def generate_embeddings(
    all_results: dict[str, dict],
    existing_desc_hashes: dict[str, str] | None = None,
) -> dict:
    """Step 9: Generate vector embeddings only for changed descriptions.
    Uses AsyncAzureOpenAI. Stores embeddings in PostgreSQL pgvector.
    """
    from openai import AsyncAzureOpenAI

    endpoint = os.getenv("AZURE_AI_ENDPOINT", "")
    api_key = os.getenv("AZURE_AI_API_KEY", "")
    deployment = os.getenv("AZURE_EMBEDDING_DEPLOYMENT", "text-embedding-ada-002")

    if not endpoint or not api_key:
        logger.warning("embedding_skip", reason="AZURE_AI_ENDPOINT or AZURE_AI_API_KEY not set")
        return {"tables_embedded": 0, "skipped_unchanged": 0}

    client = AsyncAzureOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version="2024-12-01-preview",
    )

    existing_hashes = existing_desc_hashes or {}
    stats = {"tables_embedded": 0, "skipped_unchanged": 0, "errors": 0}

    # Collect items that NEED embedding (description changed or new)
    embed_items: list[tuple[str, dict, str]] = []
    for db_name, result in all_results.items():
        if result.get("status") != "completed":
            continue
        for table_fqn, tinfo in result["tables"].items():
            desc = tinfo.get("description", tinfo["name"])
            col_names = ", ".join(c["name"] for c in tinfo["columns"][:20])
            text = f"{tinfo['name']}: {desc} Columns: {col_names}"
            new_hash = tinfo.get("description_hash") or _property_hash({"text": text})

            # Delta check: skip if hash matches existing
            if table_fqn in existing_hashes and existing_hashes[table_fqn] == new_hash:
                stats["skipped_unchanged"] += 1
                continue

            embed_items.append((table_fqn, tinfo, text))

    logger.info(
        "embedding_delta_check",
        total_tables=sum(
            len(r.get("tables", {})) for r in all_results.values()
            if r.get("status") == "completed"
        ),
        need_embedding=len(embed_items),
        skipped_unchanged=stats["skipped_unchanged"],
    )

    # Process in batches of 16
    batch_size = 16
    for i in range(0, len(embed_items), batch_size):
        batch = embed_items[i : i + batch_size]
        texts = [item[2] for item in batch]

        try:
            resp = await client.embeddings.create(
                model=deployment,
                input=texts,
            )
            for j, emb_data in enumerate(resp.data):
                fqn, tinfo, _ = batch[j]
                tinfo["description_embedding"] = emb_data.embedding
                stats["tables_embedded"] += 1

            logger.info(
                "embeddings_batch_complete",
                batch=i // batch_size + 1,
                count=len(batch),
            )
        except Exception as e:
            stats["errors"] += 1
            logger.warning(
                "embedding_batch_error",
                batch=i // batch_size + 1,
                error=str(e)[:120],
            )

    logger.info("embeddings_complete", **stats)
    await client.close()
    return stats


async def _store_embeddings_pgvector(all_results: dict[str, dict]) -> int:
    """Store description embeddings in PostgreSQL (pgvector or JSONB fallback)."""
    import asyncpg

    dsn = _pg_rds_dsn("apollo_analytics")  # Store in analytics DB
    stored = 0

    try:
        conn = await asyncio.wait_for(asyncpg.connect(dsn, ssl="require"), timeout=10)
    except Exception as e:
        logger.warning("pgvector_connect_failed", error=str(e)[:100])
        return 0

    try:
        # Try to enable pgvector, fall back to JSONB
        has_pgvector = False
        try:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            has_pgvector = True
        except Exception:
            logger.info("pgvector_not_available", fallback="JSONB")

        if has_pgvector:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS table_embeddings (
                    fqn TEXT PRIMARY KEY,
                    description_hash TEXT NOT NULL,
                    embedding vector(1536) NOT NULL,
                    description TEXT,
                    updated_at TIMESTAMPTZ DEFAULT now()
                )
            """)
        else:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS table_embeddings (
                    fqn TEXT PRIMARY KEY,
                    description_hash TEXT NOT NULL,
                    embedding JSONB NOT NULL,
                    description TEXT,
                    updated_at TIMESTAMPTZ DEFAULT now()
                )
            """)

        for db_name, result in all_results.items():
            if result.get("status") != "completed":
                continue
            for table_fqn, tinfo in result["tables"].items():
                emb = tinfo.get("description_embedding")
                if not emb:
                    continue

                desc_hash = tinfo.get("description_hash", "")
                desc_text = tinfo.get("description", "")

                if has_pgvector:
                    emb_str = "[" + ",".join(str(v) for v in emb) + "]"
                    await conn.execute(
                        "INSERT INTO table_embeddings (fqn, description_hash, embedding, description, updated_at) "
                        "VALUES ($1, $2, $3::vector, $4, now()) "
                        "ON CONFLICT (fqn) DO UPDATE SET "
                        "  description_hash = EXCLUDED.description_hash, "
                        "  embedding = EXCLUDED.embedding, "
                        "  description = EXCLUDED.description, "
                        "  updated_at = now()",
                        table_fqn, desc_hash, emb_str, desc_text,
                    )
                else:
                    await conn.execute(
                        "INSERT INTO table_embeddings (fqn, description_hash, embedding, description, updated_at) "
                        "VALUES ($1, $2, $3::jsonb, $4, now()) "
                        "ON CONFLICT (fqn) DO UPDATE SET "
                        "  description_hash = EXCLUDED.description_hash, "
                        "  embedding = EXCLUDED.embedding, "
                        "  description = EXCLUDED.description, "
                        "  updated_at = now()",
                        table_fqn, desc_hash, json.dumps(emb), desc_text,
                    )
                stored += 1

        logger.info("pgvector_stored", rows=stored, has_pgvector=has_pgvector)
    finally:
        await conn.close()

    return stored


async def _read_existing_desc_hashes() -> dict[str, str]:
    """Read existing description hashes from pgvector table for delta check."""
    import asyncpg

    dsn = _pg_rds_dsn("apollo_analytics")
    hashes: dict[str, str] = {}

    try:
        conn = await asyncio.wait_for(asyncpg.connect(dsn, ssl="require"), timeout=10)
        try:
            rows = await conn.fetch(
                "SELECT fqn, description_hash FROM table_embeddings"
            )
            hashes = {r["fqn"]: r["description_hash"] for r in rows}
        except Exception:
            pass  # Table doesn't exist yet — first run
        finally:
            await conn.close()
    except Exception:
        pass  # DB not reachable — treat everything as new

    return hashes


# ── Step 6: Assign Domain Tags ───────────────────────────────

# Domain mapping: (table_name_pattern, domain_name)
DOMAIN_RULES: list[tuple[str, str]] = [
    # Clinical / HIS
    ("patient", "clinical"),
    ("encounter", "clinical"),
    ("prescription", "clinical"),
    ("medication", "clinical"),
    ("vital", "clinical"),
    ("lab_result", "clinical"),
    ("radiology", "clinical"),
    ("diagnosis", "clinical"),
    ("surgery", "clinical"),
    ("discharge", "clinical"),
    ("nursing", "clinical"),
    ("ward", "clinical"),
    ("bed", "clinical"),
    # HR
    ("employee", "hr"),
    ("payroll", "hr"),
    ("leave", "hr"),
    ("certification", "hr"),
    ("credential", "hr"),
    ("attendance", "hr"),
    ("benefit", "hr"),
    ("training", "hr"),
    ("department", "hr"),
    ("position", "hr"),
    # Billing / Financial
    ("claim", "billing"),
    ("billing", "billing"),
    ("payment", "billing"),
    ("invoice", "billing"),
    ("payer", "billing"),
    ("insurance", "billing"),
    ("revenue", "billing"),
    # Analytics
    ("report", "analytics"),
    ("dashboard", "analytics"),
    ("metric", "analytics"),
    ("kpi", "analytics"),
    ("statistical", "analytics"),
    # Audit
    ("audit", "audit"),
    ("change_log", "audit"),
    ("access_log", "audit"),
    ("event_log", "audit"),
    ("policy_version", "audit"),
    ("graph_version", "audit"),
    # Security / Admin
    ("role", "security"),
    ("policy", "security"),
    ("permission", "security"),
]


def assign_domains(all_results: dict[str, dict]) -> dict:
    """Step 6: Assign domain tags based on table/schema name patterns.
    Loads rules from config/domain_rules.json if available, falls back to DOMAIN_RULES."""
    # Try loading from config file (P2-3)
    rules = DOMAIN_RULES
    config_path = Path(__file__).resolve().parent.parent / "config" / "domain_rules.json"
    if config_path.exists():
        try:
            with open(config_path) as f:
                cfg = json.load(f)
            rules = [(r["pattern"], r["domain"]) for r in cfg.get("domain_rules", [])]
            logger.info("domain_rules_loaded", source=str(config_path), count=len(rules))
        except Exception as e:
            logger.warning("domain_rules_load_failed", error=str(e)[:80], fallback="hardcoded")

    stats: dict[str, int] = {}  # domain -> count

    for db_name, result in all_results.items():
        if result.get("status") != "completed":
            continue

        for table_fqn, tinfo in result["tables"].items():
            table_lower = tinfo["name"].lower()
            assigned_domain = None

            for pattern, domain in rules:
                if pattern in table_lower:
                    assigned_domain = domain
                    break

            # Fallback: use schema name as domain hint
            if not assigned_domain:
                schema_lower = tinfo["schema"].lower()
                if schema_lower in ("clinical", "billing", "hr", "payroll", "audit"):
                    assigned_domain = schema_lower
                else:
                    assigned_domain = "general"

            tinfo["domain"] = assigned_domain
            stats[assigned_domain] = stats.get(assigned_domain, 0) + 1

    logger.info("domains_assigned", domain_counts=stats)
    return stats


# ── Step 7 & 8: Diff & Apply with Versioning ─────────────────


async def diff_and_apply_graph(
    all_results: dict[str, dict],
    db_registry: dict,
) -> dict:
    """Steps 7+8: Diff crawled data against existing graph, apply changes
    with conditional versioning and soft-delete. Version only bumps when
    property_hash changes. Dropped FKs are deactivated."""
    from neo4j import AsyncGraphDatabase

    uri = os.getenv("NEO4J_URI", "")
    user = os.getenv("NEO4J_USERNAME", "")
    password = os.getenv("NEO4J_PASSWORD", "")
    neo4j_db = os.getenv("NEO4J_DATABASE", "")

    driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
    logger.info("neo4j_connected", uri=uri)

    report = {
        "tables_added": 0, "tables_deactivated": 0, "tables_updated": 0,
        "tables_unchanged": 0,
        "columns_added": 0, "columns_deactivated": 0, "columns_updated": 0,
        "columns_unchanged": 0,
        "domains_created": 0,
        "fk_created": 0, "fk_deactivated": 0,
        "pii_detected": 0,
    }

    try:
        async with driver.session(database=neo4j_db) as session:

            # ── Phase 1: Read existing graph state ──
            logger.info("diff_reading_existing_graph")
            # Setup Constraints & Indexes per Section 5
            # Section 5.1 & 5.3: Unique Constraints
            await session.run("CREATE CONSTRAINT database_id_unique IF NOT EXISTS FOR (d:Database) REQUIRE d.database_id IS UNIQUE")
            await session.run("CREATE CONSTRAINT table_id_unique IF NOT EXISTS FOR (t:Table) REQUIRE t.table_id IS UNIQUE")
            await session.run("CREATE CONSTRAINT policy_id_unique IF NOT EXISTS FOR (p:Policy) REQUIRE p.policy_id IS UNIQUE")
            await session.run("CREATE INDEX IF NOT EXISTS FOR (t:Table) ON (t.name)")
            await session.run("CREATE INDEX IF NOT EXISTS FOR (t:Table) ON (t.sensitivity_level)")
            await session.run("CREATE INDEX IF NOT EXISTS FOR (c:Column) ON (c.name)")
            await session.run("CREATE INDEX IF NOT EXISTS FOR (c:Column) ON (c.sensitivity_level)")
            await session.run("CREATE INDEX IF NOT EXISTS FOR (c:Column) ON (c.pii_type)")

            existing_tables: set[str] = set()
            existing_columns: set[str] = set()
            existing_table_hashes: dict[str, str] = {}
            existing_col_hashes: dict[str, str] = {}

            r = await session.run(
                "MATCH (t:Table) WHERE t.is_active = true "
                "RETURN t.fqn AS fqn, t.property_hash AS hash"
            )
            async for rec in r:
                existing_tables.add(rec["fqn"])
                if rec["hash"]:
                    existing_table_hashes[rec["fqn"]] = rec["hash"]

            r = await session.run(
                "MATCH (c:Column) WHERE c.is_active = true "
                "RETURN c.fqn AS fqn, c.property_hash AS hash"
            )
            async for rec in r:
                existing_columns.add(rec["fqn"])
                if rec["hash"]:
                    existing_col_hashes[rec["fqn"]] = rec["hash"]

            # Phase 1b: Read existing FK edges
            # Key format: "{table_fqn}.{source_column}::{constraint_name}" (P0-D fix)
            existing_fk_keys: set[str] = set()
            r = await session.run(
                "MATCH (src:Column)-[r:FOREIGN_KEY_TO]->(tgt:Column) "
                "WHERE r.is_active <> false "
                "RETURN src.fqn AS src_col_fqn, r.constraint AS constraint"
            )
            async for rec in r:
                # src.fqn is already the full column FQN (table_fqn.column_name)
                existing_fk_keys.add(f"{rec['src_col_fqn']}::{rec['constraint']}")

            logger.info(
                "diff_existing_state",
                existing_tables=len(existing_tables),
                existing_columns=len(existing_columns),
                existing_fks=len(existing_fk_keys),
            )

            # Collect all crawled FQNs + FK keys
            crawled_table_fqns: set[str] = set()
            crawled_col_fqns: set[str] = set()
            crawled_fk_keys: set[str] = set()
            all_domains: set[str] = set()

            for db_name, result in all_results.items():
                if result.get("status") != "completed":
                    continue
                for table_fqn, tinfo in result["tables"].items():
                    crawled_table_fqns.add(table_fqn)
                    if tinfo.get("domain"):
                        all_domains.add(tinfo["domain"])
                    for col in tinfo["columns"]:
                        crawled_col_fqns.add(f"{table_fqn}.{col['name']}")
                    for fk in tinfo["foreign_keys"]:
                        # Key format must match existing_fk_keys: col_fqn::constraint_name (P0-D)
                        src_col_fqn = f"{table_fqn}.{fk['source_column']}"
                        fk_key = f"{src_col_fqn}::{fk['constraint_name']}"
                        crawled_fk_keys.add(fk_key)

            new_tables = crawled_table_fqns - existing_tables
            dropped_tables = existing_tables - crawled_table_fqns
            new_cols = crawled_col_fqns - existing_columns
            dropped_cols = existing_columns - crawled_col_fqns
            dropped_fks = existing_fk_keys - crawled_fk_keys

            logger.info(
                "diff_results",
                new_tables=len(new_tables),
                dropped_tables=len(dropped_tables),
                new_columns=len(new_cols),
                dropped_columns=len(dropped_cols),
                dropped_fks=len(dropped_fks),
            )

            # ── Phase 2: Deactivate dropped items (never hard delete) ──
            if dropped_tables:
                # P1-C: Cascade deactivation — also deactivate child Columns
                await session.run(
                    "UNWIND $fqns AS fqn "
                    "MATCH (t:Table {fqn: fqn}) "
                    "SET t.is_active = false, t.deactivated_at = datetime(), "
                    "    t.version = COALESCE(t.version, 0) + 1 "
                    "WITH t "
                    "OPTIONAL MATCH (t)-[:HAS_COLUMN]->(c:Column) "
                    "WHERE c.is_active = true "
                    "SET c.is_active = false, c.deactivated_at = datetime(), "
                    "    c.version = COALESCE(c.version, 0) + 1",
                    fqns=list(dropped_tables),
                )
                report["tables_deactivated"] = len(dropped_tables)
                logger.info("diff_tables_deactivated", count=len(dropped_tables))

            if dropped_cols:
                await session.run(
                    "UNWIND $fqns AS fqn "
                    "MATCH (c:Column {fqn: fqn}) "
                    "SET c.is_active = false, c.deactivated_at = datetime(), "
                    "    c.version = COALESCE(c.version, 0) + 1",
                    fqns=list(dropped_cols),
                )
                report["columns_deactivated"] = len(dropped_cols)

            # Phase 2b: Deactivate dropped FK edges (P0-2)
            if dropped_fks:
                for fk_key in dropped_fks:
                    src_fqn, constraint = fk_key.split("::", 1)
                    await session.run(
                        "MATCH (src:Column {fqn: $src})-[r:FOREIGN_KEY_TO {constraint: $con}]->() "
                        "SET r.is_active = false, r.deactivated_at = datetime()",
                        src=src_fqn, con=constraint,
                    )
                report["fk_deactivated"] = len(dropped_fks)
                logger.info("diff_fks_deactivated", count=len(dropped_fks))

            # ── Phase 3: Create Domain nodes ──
            for domain_name in all_domains:
                # Find domain info array
                domain_info = {}
                if isinstance(DOMAIN_RULES, dict) and "domain_rules" in DOMAIN_RULES:
                    for rule in DOMAIN_RULES["domain_rules"]:
                        if rule.get("domain") == domain_name:
                            domain_info = rule
                            break
                            
                domain_desc = domain_info.get("description", f"Generic data domain for {domain_name}")
                domain_id = _generate_uuid(domain_name)
                
                # count tables in this domain
                domain_table_count = sum(
                    1 for result in all_results.values() if result.get("status") == "completed"
                    for tinfo in result.get("tables", {}).values() if tinfo.get("domain", "general") == domain_name
                )
                        
                await session.run(
                    "MERGE (d:Domain {name: $name}) "
                    "SET d.domain_id = $domain_id, d.description = $desc, "
                    "    d.table_count = $tc, d.sensitivity_floor = $floor, "
                    "    d.is_active = true",
                    name=domain_name, domain_id=domain_id, desc=domain_desc,
                    tc=domain_table_count, floor=domain_info.get("sensitivity_floor", 1),
                )
                report["domains_created"] += 1

            # ── Phase 4: Upsert Database → Schema → Table → Column ──
            # Uses property_hash for conditional version bumping (P0-1)
            for db_name, result in all_results.items():
                if result.get("status") != "completed":
                    logger.warning("graph_skip_failed_db", database=db_name)
                    continue

                # Map engine to strict Section 5 enum
                engine = db_registry[db_name]["engine"]
                tables = result["tables"]
                
                engine_map = {
                    "postgresql": "POSTGRESQL",
                    "timescale_postgresql": "POSTGRESQL",
                    "sqlserver": "SQLSERVER",
                    "oracle": "ORACLE",
                    "mongodb": "MONGODB"
                }
                engine_enum = engine_map.get(engine.lower(), "POSTGRESQL")

                # Database node (hash-conditional version)
                db_id = _generate_uuid(db_name)
                table_count = len(tables)
                db_hash = _property_hash({"name": db_name, "engine": engine_enum, "tc": table_count})
                await session.run(
                    "MERGE (d:Database {name: $name}) "
                    "SET d.database_id = $db_id, d.engine = $engine, d.source = 'live_crawl', "
                    "    d.host = $host, d.port = $port, d.table_count = $tc, "
                    "    d.description = $desc, "
                    "    d.crawled_at = datetime(), d.is_active = true, "
                    "    d.last_crawled_at = datetime() "
                    "WITH d, d.property_hash AS old_hash "
                    "SET d.property_hash = $hash "
                    "FOREACH (_ IN CASE WHEN old_hash IS NULL OR old_hash <> $hash THEN [1] ELSE [] END | "
                    "  SET d.version = COALESCE(d.version, 0) + 1, d.changed_at = datetime() "
                    ")",
                    name=db_name, db_id=db_id, engine=engine_enum, 
                    host=db_registry[db_name].get("host", ""),
                    port=int(db_registry[db_name].get("port", 5432)),
                    tc=table_count, desc=db_registry[db_name].get("description", ""),
                    hash=db_hash,
                )
                logger.info("graph_node_upserted", type="Database", name=db_name)

                schemas_seen = set()
                for tinfo in tables.values():
                    schemas_seen.add(tinfo["schema"])

                # Schema nodes
                for schema_name in schemas_seen:
                    schema_fqn = f"{db_name}.{schema_name}"
                    schema_id = _generate_uuid(schema_fqn)
                    
                    # Count tables precisely in this schema
                    schema_table_count = sum(1 for t in tables.values() if t["schema"] == schema_name)
                    
                    s_hash = _property_hash({"fqn": schema_fqn, "name": schema_name, "tc": schema_table_count})
                    await session.run(
                        "MERGE (s:Schema {fqn: $fqn}) "
                        "SET s.schema_id = $schema_id, s.name = $name, s.source = 'live_crawl', "
                        "    s.database_id = $db_id, s.table_count = $tc, "
                        "    s.description = $desc, s.is_active = true "
                        "WITH s, s.property_hash AS old_hash "
                        "SET s.property_hash = $hash "
                        "FOREACH (_ IN CASE WHEN old_hash IS NULL OR old_hash <> $hash THEN [1] ELSE [] END | "
                        "  SET s.version = COALESCE(s.version, 0) + 1, s.changed_at = datetime() "
                        ") "
                        "WITH s "
                        "MATCH (d:Database {name: $db_name}) "
                        "MERGE (d)-[:HAS_SCHEMA]->(s)",
                        fqn=schema_fqn, schema_id=schema_id, name=schema_name, 
                        db_id=db_id, db_name=db_name, tc=schema_table_count, 
                        desc=f"Contains {schema_table_count} tables from the {schema_name} schema of {db_name}",
                        hash=s_hash,
                    )

                # Table + Column nodes
                for table_fqn, tinfo in tables.items():
                    schema_fqn = f"{db_name}.{tinfo['schema']}"
                    is_new = table_fqn in new_tables
                    pk_set = set(tinfo["pk_columns"])

                    # Section 5.3 compliance: Ensure sensitivity_level >= 1
                    t_sens = max(tinfo.get("sensitivity_level", 1), 1)
                    
                    # Compute table property hash
                    t_props = {
                        "name": tinfo["name"],
                        "row_count": tinfo["row_count"],
                        "col_count": len(tinfo["columns"]),
                        "sens": t_sens,
                        "has_pii": tinfo.get("has_pii", False),
                        "domain": tinfo.get("domain", "general"),
                        "description": tinfo.get("description"),
                        "pk_cols": pk_set,
                    }
                    t_hash = _property_hash(t_props)
                    old_hash = existing_table_hashes.get(table_fqn)
                    
                    domain_val = tinfo.get("domain", "general")
                    
                    # Compute hipaa category heuristically (Section 5.3)
                    hipaa_cat = "NONE"
                    reg_flags = []
                    if domain_val.lower() == "clinical":
                        reg_flags.append("HIPAA")
                        if tinfo.get("has_pii", False):
                            hipaa_cat = "PHI"
                    
                    await session.run(
                        "MERGE (t:Table {fqn: $fqn}) "
                        "SET t.table_id = $table_id, t.name = $name, t.source = 'live_crawl', "
                        "    t.schema_name = $schema, t.database_id = $db_id, "
                        "    t.record_count = $row_count, t.column_count = $col_count, "
                        "    t.is_active = true, t.last_crawled_at = datetime(), "
                        "    t.sensitivity_level = $sens, t.has_pii = $has_pii, "
                        "    t.domain = $domain, t.domain_tags = [$domain], "
                        "    t.hipaa_category = $hipaa_cat, t.primary_key_columns = $pk_cols, "
                        "    t.regulatory_flags = $reg_flags, "
                        "    t.description = $description, "
                        "    t.crawled_at = datetime() "
                        "WITH t, t.property_hash AS old_hash "
                        "SET t.property_hash = $hash "
                        "FOREACH (_ IN CASE WHEN old_hash IS NULL OR old_hash <> $hash THEN [1] ELSE [] END | "
                        "  SET t.version = COALESCE(t.version, 0) + 1, t.changed_at = datetime() "
                        ") ",
                        fqn=table_fqn, table_id=_generate_uuid(table_fqn), name=tinfo["name"],
                        schema=tinfo["schema"], db_id=db_id,
                        row_count=tinfo["row_count"], col_count=len(tinfo["columns"]),
                        schema_fqn=schema_fqn,
                        sens=t_sens,
                        has_pii=tinfo.get("has_pii", False),
                        domain=domain_val, hipaa_cat=hipaa_cat,
                        reg_flags=reg_flags,
                        pk_cols=list(pk_set), description=tinfo.get("description"),
                        hash=t_hash,
                    )

                    if is_new:
                        report["tables_added"] += 1
                    elif old_hash and old_hash == t_hash:
                        report["tables_unchanged"] += 1
                    else:
                        report["tables_updated"] += 1

                    # Domain relationship
                    domain = tinfo.get("domain", "general")
                    await session.run(
                        "MATCH (t:Table {fqn: $fqn}) "
                        "MATCH (d:Domain {name: $domain}) "
                        "MERGE (t)-[:BELONGS_TO_DOMAIN]->(d)",
                        fqn=table_fqn, domain=domain,
                    )

                    for col in tinfo["columns"]:
                        col_fqn = f"{table_fqn}.{col['name']}"
                        is_pii = col.get("is_pii", False)
                        if is_pii:
                            report["pii_detected"] += 1
                        
                        # Find if this column is an FK in this table
                        is_fk = False
                        fk_target_table = None
                        fk_target_column = None
                        for fk_ref in tinfo["foreign_keys"]:
                            if fk_ref["source_column"] == col["name"]:
                                is_fk = True
                                fk_target_table = fk_ref["target_table"]
                                fk_target_column = fk_ref["target_column"]
                                break

                        # Find if indexed
                        is_indexed = False
                        for idx in tinfo.get("indexes", []):
                            if col["name"] in idx.get("indexdef", "") or col["name"] in idx.get("name", ""):
                                is_indexed = True
                                break

                        # compliance sensitization
                        c_sens = max(col.get("sensitivity_level", 1), 1)

                        # Compute column property hash
                        c_props = {
                            "name": col["name"],
                            "data_type": col["data_type"],
                            "is_pk": col["name"] in pk_set,
                            "is_nullable": col["is_nullable"] in ("YES", True),
                            "ordinal": col["ordinal_position"],
                            "sens": c_sens,
                            "is_pii": is_pii,
                            "pii_type": col.get("pii_type"),
                            "is_fk": is_fk,
                            "is_idx": is_indexed
                        }
                        c_hash = _property_hash(c_props)
                        old_c_hash = existing_col_hashes.get(col_fqn)

                        await session.run(
                            "MERGE (c:Column {fqn: $fqn}) "
                            "SET c.column_id = $col_id, c.name = $name, c.table_id = $table_id, "
                            "    c.data_type = $data_type, "
                            "    c.is_primary_key = $is_pk, c.is_nullable = $is_nullable, "
                            "    c.ordinal_position = $ordinal, c.source = 'live_crawl', "
                            "    c.sensitivity_level = $sens, "
                            "    c.is_pii = $is_pii, c.pii_type = $pii_type, "
                            "    c.masking_strategy = $masking, "
                            "    c.is_foreign_key = $is_fk, c.fk_target_table = $fk_tgt_tab, "
                            "    c.fk_target_column = $fk_tgt_col, c.is_indexed = $is_idx, "
                            "    c.description = $desc, c.sample_values = [], "
                            "    c.is_active = true "
                            "WITH c, c.property_hash AS old_hash "
                            "SET c.property_hash = $hash "
                            "FOREACH (_ IN CASE WHEN old_hash IS NULL OR old_hash <> $hash THEN [1] ELSE [] END | "
                            "  SET c.version = COALESCE(c.version, 0) + 1, c.changed_at = datetime() "
                            ") "
                            "WITH c "
                            "MATCH (t:Table {fqn: $table_fqn}) "
                            "MERGE (t)-[:HAS_COLUMN]->(c)",
                            fqn=col_fqn, col_id=_generate_uuid(col_fqn), name=col["name"],
                            table_id=_generate_uuid(table_fqn), data_type=col["data_type"],
                            is_pk=col["name"] in pk_set,
                            is_nullable=(col["is_nullable"] in ("YES", True)),
                            ordinal=col["ordinal_position"],
                            table_fqn=table_fqn,
                            sens=c_sens,
                            is_pii=is_pii,
                            pii_type=col.get("pii_type", "NONE"),
                            masking=col.get("masking_strategy", "NONE"),
                            desc=f"Physical column {col['name']} in table {tinfo['name']}",
                            is_fk=is_fk, fk_tgt_tab=fk_target_table, fk_tgt_col=fk_target_column,
                            is_idx=is_indexed, hash=c_hash,
                        )

                        if col_fqn in new_cols:
                            report["columns_added"] += 1
                        elif old_c_hash and old_c_hash == c_hash:
                            report["columns_unchanged"] += 1
                        else:
                            report["columns_updated"] += 1

                    # Foreign Key relationships (set is_active=true)
                    for fk in tinfo["foreign_keys"]:
                        src_col_fqn = f"{table_fqn}.{fk['source_column']}"
                        tgt_table_fqn = f"{db_name}.{fk['target_schema']}.{fk['target_table']}"
                        tgt_col_fqn = f"{tgt_table_fqn}.{fk['target_column']}"
                        await session.run(
                            "MATCH (src:Column {fqn: $src_fqn}) "
                            "MATCH (tgt:Column {fqn: $tgt_fqn}) "
                            "MERGE (src)-[r:FOREIGN_KEY_TO {constraint: $constraint}]->(tgt) "
                            "SET r.is_active = true",
                            src_fqn=src_col_fqn, tgt_fqn=tgt_col_fqn,
                            constraint=fk["constraint_name"],
                        )
                        report["fk_created"] += 1

                logger.info(
                    "graph_database_loaded",
                    database=db_name,
                    tables=len(tables),
                    columns=result["total_columns"],
                )

            # ── Final verification ──
            r = await session.run(
                "MATCH (n) WHERE n.source = 'live_crawl' "
                "UNWIND labels(n) AS label "
                "RETURN label, count(*) AS cnt ORDER BY cnt DESC"
            )
            counts = {rec["label"]: rec["cnt"] async for rec in r}

            r = await session.run(
                "MATCH (n)-[r]->(m) "
                "WHERE n.source = 'live_crawl' OR m.source = 'live_crawl' "
                "RETURN type(r) AS rel_type, count(*) AS cnt ORDER BY cnt DESC"
            )
            rel_counts = {rec["rel_type"]: rec["cnt"] async for rec in r}

            logger.info(
                "knowledge_graph_built",
                nodes=counts,
                relationships=rel_counts,
                total_nodes=sum(counts.values()),
                total_relationships=sum(rel_counts.values()),
            )

    finally:
        await driver.close()
        logger.info("neo4j_disconnected")

    return report


# ── Step 10: Crawl Report ────────────────────────────────────────


def print_crawl_report(
    all_results: dict[str, dict],
    pii_stats: dict,
    domain_stats: dict,
    graph_report: dict | None = None,
) -> None:
    """Step 10: Print a human-readable crawl report."""
    print("\n" + "=" * 70)
    print("  CRAWL REPORT")
    print("=" * 70)

    # Per-database summary
    print(f"\n{'Database':<22s} {'Engine':<18s} {'Tables':>7s} {'Columns':>8s} {'FKs':>5s} {'PII Cols':>9s}")
    print("-" * 70)
    total_t = total_c = total_fk = total_pii = 0
    for db_name, result in all_results.items():
        if result.get("status") != "completed":
            print(f"  {db_name:<20s} FAILED")
            continue
        pii_count = sum(
            1 for t in result["tables"].values()
            for col in t["columns"] if col.get("is_pii")
        )
        print(
            f"  {db_name:<20s} {result.get('engine', '?'):<18s}"
            f" {result['total_tables']:>6d} {result['total_columns']:>7d}"
            f" {result['total_fk']:>5d} {pii_count:>8d}"
        )
        total_t += result["total_tables"]
        total_c += result["total_columns"]
        total_fk += result["total_fk"]
        total_pii += pii_count
    print("-" * 70)
    print(f"  {'TOTAL':<20s} {'':<18s} {total_t:>6d} {total_c:>7d} {total_fk:>5d} {total_pii:>8d}")

    # PII classification summary
    print(f"\n  PII Classification:")
    for pii_type, count in sorted(pii_stats.get("by_type", {}).items()):
        print(f"    {pii_type:<20s} {count:>4d} columns")

    # Domain summary
    print(f"\n  Domain Assignment:")
    for domain, count in sorted(domain_stats.items()):
        print(f"    {domain:<20s} {count:>4d} tables")

    # Graph diff (if available)
    if graph_report:
        print(f"\n  Graph Changes:")
        print(f"    Tables added:       {graph_report.get('tables_added', 0)}")
        print(f"    Tables updated:     {graph_report.get('tables_updated', 0)}")
        print(f"    Tables unchanged:   {graph_report.get('tables_unchanged', 0)}")
        print(f"    Tables deactivated: {graph_report.get('tables_deactivated', 0)}")
        print(f"    Columns added:      {graph_report.get('columns_added', 0)}")
        print(f"    Columns updated:    {graph_report.get('columns_updated', 0)}")
        print(f"    Columns unchanged:  {graph_report.get('columns_unchanged', 0)}")
        print(f"    Columns deactivated:{graph_report.get('columns_deactivated', 0)}")
        print(f"    FK relationships:   {graph_report.get('fk_created', 0)}")
        print(f"    FK deactivated:     {graph_report.get('fk_deactivated', 0)}")
        print(f"    Domains created:    {graph_report.get('domains_created', 0)}")
        print(f"    PII columns found:  {graph_report.get('pii_detected', 0)}")

    # ── Human Review Required (P2-2) ──
    review_items: list[str] = []
    for db_name, result in all_results.items():
        if result.get("status") != "completed":
            continue
        for table_fqn, tinfo in result["tables"].items():
            for col in tinfo["columns"]:
                if col.get("needs_review"):
                    reason = []
                    if col.get("sensitivity_level", 0) >= 4:
                        reason.append(f"high sensitivity (level {col['sensitivity_level']})")
                    if col.get("pii_type") == "CLINICAL_CONTEXT":
                        reason.append("clinical auto-boost")
                    review_items.append(
                        f"    {col['name']:<25s} in {tinfo['name']:<20s} — {', '.join(reason)}"
                    )

    if review_items:
        print(f"\n  ⚠ Requires Human Review ({len(review_items)} items):")
        for item in review_items[:30]:  # cap output
            print(item)
        if len(review_items) > 30:
            print(f"    ... and {len(review_items) - 30} more")

    print("\n" + "=" * 70 + "\n")

    logger.info(
        "crawl_report_generated",
        total_tables=total_t,
        total_columns=total_c,
        total_pii=total_pii,
        review_items=len(review_items) if review_items else 0,
        graph_changes=graph_report,
    )


# ── Cypher Seed File Generator ───────────────────────────────


def _esc(val: str) -> str:
    """Escape a string for Cypher string literal."""
    return val.replace("\\", "\\\\").replace('"', '\\"')


def generate_cypher_seeds(
    all_results: dict[str, dict],
    db_registry: dict,
    output_dir: str = "cypher",
) -> list[str]:
    """Generate per-database Cypher seed files from crawled metadata."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    generated_files: list[str] = []

    # Numbering: start at 100 to avoid colliding with hand-crafted seeds
    idx = 100

    for db_name, result in all_results.items():
        if result.get("status") != "completed":
            logger.warning("cypher_skip_failed_db", database=db_name)
            continue

        idx += 1
        tables = result["tables"]
        engine = db_registry[db_name]["engine"]
        desc = db_registry[db_name]["description"]

        lines: list[str] = []
        ln = lines.append

        # ── Header ──
        ln(f"// {'=' * 60}")
        ln(f"// {db_name} — {desc}")
        ln(f"// Auto-generated from live crawl at {time.strftime('%Y-%m-%d %H:%M:%S')}")
        ln(f"// {'=' * 60}")
        ln("")

        # ── Database node ──
        ln("// --- Database ---")
        ln(f'MERGE (db:Database {{name: "{_esc(db_name)}"}})') 
        ln(f'SET db.engine = "{_esc(engine)}", db.is_active = true,') 
        ln(f'    db.created_at = datetime(), db.source = "live_crawl";')
        ln("")

        # ── Collect schemas ──
        schemas = sorted({t["schema"] for t in tables.values()})
        schema_vars = {}
        ln("// --- Schemas ---")
        for i, schema_name in enumerate(schemas):
            var = f"s{i}"
            schema_vars[schema_name] = var
            fqn = f"{db_name}.{schema_name}"
            ln(f'MERGE ({var}:Schema {{fqn: "{_esc(fqn)}"}})') 
            ln(f'SET {var}.name = "{_esc(schema_name)}", {var}.is_active = true;')
        ln("")

        # Schema → Database links
        for schema_name, var in schema_vars.items():
            ln(f'MERGE (db)-[:HAS_SCHEMA]->({var});')
        ln("")

        # ── Tables ──
        table_vars = {}
        ln("// --- Tables ---")
        for t_idx, (table_fqn, tinfo) in enumerate(sorted(tables.items())):
            var = f"t{t_idx}"
            table_vars[table_fqn] = var
            ln(f'MERGE ({var}:Table {{fqn: "{_esc(table_fqn)}"}})') 
            ln(f'SET {var}.name = "{_esc(tinfo["name"])}", {var}.is_active = true,')
            ln(f'    {var}.row_count_approx = {tinfo["row_count"]},')
            sens = tinfo.get('sensitivity_level', 0)
            has_pii = 'true' if tinfo.get('has_pii') else 'false'
            domain = tinfo.get('domain', 'general')
            ln(f'    {var}.sensitivity_level = {sens}, {var}.has_pii = {has_pii},')
            ln(f'    {var}.domain = "{_esc(domain)}", {var}.source = "live_crawl";')
            ln("")

        # Schema → Table links
        ln("// Schema-Table links")
        for table_fqn, tinfo in sorted(tables.items()):
            s_var = schema_vars[tinfo["schema"]]
            t_var = table_vars[table_fqn]
            ln(f'MERGE ({s_var})-[:HAS_TABLE]->({t_var});')
        ln("")

        # ── Columns ──
        col_vars = {}  # col_fqn -> var
        c_idx = 0
        for table_fqn, tinfo in sorted(tables.items()):
            t_var = table_vars[table_fqn]
            pk_set = set(tinfo["pk_columns"])
            ln(f'// --- Columns ({tinfo["name"]}) ---')
            first_col_idx = c_idx

            for col in tinfo["columns"]:
                var = f"c{c_idx}"
                col_fqn = f"{table_fqn}.{col['name']}"
                col_vars[col_fqn] = var
                is_pk = col["name"] in pk_set
                is_nullable = col["is_nullable"] in ("YES", True, "yes")

                ln(f'MERGE ({var}:Column {{fqn: "{_esc(col_fqn)}"}})') 
                parts = [
                    f'{var}.name = "{_esc(col["name"])}"',
                    f'{var}.data_type = "{_esc(col["data_type"])}"',
                ]
                if is_pk:
                    parts.append(f"{var}.is_pk = true")
                parts.append(f"{var}.is_nullable = {'true' if is_nullable else 'false'}")
                parts.append(f'{var}.ordinal_position = {col["ordinal_position"]}')
                # PII properties
                sens = col.get('sensitivity_level', 0)
                if sens > 0:
                    parts.append(f'{var}.sensitivity_level = {sens}')
                if col.get('is_pii'):
                    parts.append(f'{var}.is_pii = true')
                    if col.get('pii_type'):
                        parts.append(f'{var}.pii_type = "{col["pii_type"]}"')
                    if col.get('masking_strategy', 'NONE') != 'NONE':
                        parts.append(f'{var}.masking_strategy = "{col["masking_strategy"]}"')
                parts.append(f'{var}.is_active = true')
                ln(f'SET {", ".join(parts)};')
                ln("")
                c_idx += 1

            # Table → Column links
            ln(f'// Column-Table links ({tinfo["name"]})')
            for ci in range(first_col_idx, c_idx):
                ln(f'MERGE ({t_var})-[:HAS_COLUMN]->(c{ci});')
            ln("")

        # ── Foreign Key relationships ──
        fk_lines = []
        for table_fqn, tinfo in sorted(tables.items()):
            for fk in tinfo["foreign_keys"]:
                src_col_fqn = f"{table_fqn}.{fk['source_column']}"
                tgt_table_fqn = f"{db_name}.{fk['target_schema']}.{fk['target_table']}"
                tgt_col_fqn = f"{tgt_table_fqn}.{fk['target_column']}"
                src_var = col_vars.get(src_col_fqn)
                tgt_var = col_vars.get(tgt_col_fqn)
                if src_var and tgt_var:
                    fk_lines.append(
                        f'MERGE ({src_var})-[:FOREIGN_KEY_TO '
                        f'{{constraint: "{_esc(fk["constraint_name"])}"}}]->({tgt_var});'
                    )

        if fk_lines:
            ln("// --- Foreign Keys ---")
            for fk_line in fk_lines:
                ln(fk_line)
            ln("")

        # ── Domain nodes + BELONGS_TO_DOMAIN ──
        domains_in_db = sorted({t.get("domain", "general") for t in tables.values()})
        if domains_in_db:
            ln("// --- Domains ---")
            for dm in domains_in_db:
                ln(f'MERGE (dom_{dm}:Domain {{name: "{_esc(dm)}"}});')
            ln("")
            ln("// Domain-Table links")
            for table_fqn, tinfo in sorted(tables.items()):
                dm = tinfo.get("domain", "general")
                t_var = table_vars[table_fqn]
                ln(f'MERGE ({t_var})-[:BELONGS_TO_DOMAIN]->(dom_{dm});')
            ln("")

        # ── Write file ──
        filename = f"{idx}_{db_name.lower()}_live_seed.cypher"
        filepath = out_path / filename
        filepath.write_text("\n".join(lines), encoding="utf-8")
        generated_files.append(str(filepath))

        logger.info(
            "cypher_seed_generated",
            database=db_name,
            file=str(filepath),
            tables=len(tables),
            columns=result["total_columns"],
            foreign_keys=len(fk_lines),
            lines=len(lines),
        )

    logger.info(
        "cypher_seeds_complete",
        files_generated=len(generated_files),
        output_dir=str(out_path),
    )
    return generated_files


# ── Main entrypoint ──────────────────────────────────────────


async def main(args: argparse.Namespace) -> None:
    if args.list:
        print("\nAvailable databases for live crawl:")
        print("-" * 75)
        for name, info in DATABASE_REGISTRY.items():
            print(f"  {name:<20s} {info['engine']:<22s} {info['description']}")
        print()
        return

    # Select targets
    if args.db:
        targets = {k: v for k, v in DATABASE_REGISTRY.items() if k in args.db}
        missing = set(args.db) - set(targets.keys())
        if missing:
            print(f"Unknown databases: {missing}")
            print(f"Available: {list(DATABASE_REGISTRY.keys())}")
            return
    else:
        targets = DATABASE_REGISTRY

    logger.info("live_crawl_session_start", databases=list(targets.keys()))

    grand_tables = 0
    grand_columns = 0
    results = {}

    # ── Steps 1-2-5: Crawl all databases ──
    for db_name, db_info in targets.items():
        result = await crawl_one(db_name, db_info)
        results[db_name] = result
        grand_tables += result.get("total_tables", 0)
        grand_columns += result.get("total_columns", 0)

    logger.info(
        "live_crawl_session_complete",
        databases_crawled=len(results),
        total_tables=grand_tables,
        total_columns=grand_columns,
        statuses={k: v.get("status", "unknown") for k, v in results.items()},
    )

    # ── Step 4: Auto-classify PII sensitivity ──
    pii_stats = classify_sensitivity(results)

    # ── Step 6: Assign domain tags ──
    domain_stats = assign_domains(results)

    # ── Step 3: Generate AI descriptions ──
    if args.graph or args.cypher:
        await generate_descriptions(results)

    # ── Generate Cypher seed files (with PII + domain data) ──
    if args.cypher:
        generate_cypher_seeds(results, targets, output_dir="cypher")

    # ── Step 9: Generate embeddings (delta-aware) ──
    if args.graph:
        existing_hashes = await _read_existing_desc_hashes()
        emb_stats = await generate_embeddings(results, existing_hashes)
        logger.info("embedding_stats", **emb_stats)

        # Store embeddings in pgvector
        stored = await _store_embeddings_pgvector(results)
        logger.info("pgvector_stored_count", count=stored)

    # ── Steps 7-8: Diff & apply to Neo4j graph ──
    graph_report = None
    if args.graph:
        logger.info("graph_build_starting", databases=list(results.keys()))
        graph_report = await diff_and_apply_graph(results, targets)

    # ── Step 10: Crawl report ──
    print_crawl_report(results, pii_stats, domain_stats, graph_report)

    if not args.graph and not args.cypher:
        logger.info("hint", message="Use --graph to push to Neo4j, --cypher to generate seed files")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Live crawl databases — full pipeline (crawl → classify → domain → graph)"
    )
    parser.add_argument("--db", nargs="+", help="Specific database(s) to crawl")
    parser.add_argument("--cypher", action="store_true", help="Generate Cypher seed files from crawled data")
    parser.add_argument("--graph", action="store_true", help="Diff & apply to Neo4j knowledge graph")
    parser.add_argument("--list", action="store_true", help="List available databases")
    args = parser.parse_args()
    asyncio.run(main(args))
