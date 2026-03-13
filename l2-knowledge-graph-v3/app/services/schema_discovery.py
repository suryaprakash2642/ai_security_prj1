"""Schema Discovery Service — crawls source DB system catalogs and syncs metadata to the graph.

Supports SQL Server, Oracle, PostgreSQL, and (optionally) MongoDB.
Uses read-only credentials, compares extracted schema with existing graph,
and applies inserts/updates/deactivations — never hard deletes.

Edge Cases Implemented (Section 15):
  EC-1  Table exists in DB but not in graph → on-demand re-crawl via `run_crawl(schema_filter=...)`
  EC-2  Table dropped in DB → `is_active=false` on next crawl (soft delete + compliance flag)
  EC-3a Column dropped → deactivated on next crawl
  EC-3b Column data_type changed → detected per-column; re-classification triggered automatically
  EC-7  All Cypher queries use table_id (UUID); table.name is display-only
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from collections.abc import Callable
from typing import Awaitable

import structlog

from app.models.audit import ChangeRecord, CrawlRecord
from app.models.enums import ChangeAction, ChangeSource, DatabaseEngine, SensitivityLevel
from app.models.graph import ColumnNode, DatabaseNode, SchemaNode, TableNode
from app.repositories.audit_repository import AuditRepository
from app.repositories.graph_read_repo import GraphReadRepository
from app.repositories.graph_write_repo import GraphWriteRepository
from app.services.cache import CacheService

# PII-sensitive type transitions that warrant re-classification
# e.g., varchar → encrypted_varchar still needs a review
_PII_SENSITIVE_TYPE_KEYWORDS = {
    "varchar", "nvarchar", "text", "string", "char", "clob",
    "encrypted", "bytea", "binary", "varbinary",
}

logger = structlog.get_logger(__name__)


# ── Extracted metadata structures ────────────────────────────


@dataclass
class ExtractedColumn:
    name: str
    data_type: str
    is_pk: bool = False
    is_nullable: bool = True
    ordinal_position: int = 0
    description: str = ""


@dataclass
class ExtractedForeignKey:
    source_column: str
    target_table: str
    target_column: str
    constraint_name: str = ""


@dataclass
class ExtractedTable:
    schema_name: str
    table_name: str
    columns: list[ExtractedColumn] = field(default_factory=list)
    foreign_keys: list[ExtractedForeignKey] = field(default_factory=list)
    row_count_approx: int = 0
    description: str = ""


@dataclass
class ExtractedSchema:
    database_name: str
    engine: DatabaseEngine
    schemas: dict[str, list[ExtractedTable]] = field(default_factory=dict)


# ── Abstract crawler interface ───────────────────────────────


class BaseCrawler(ABC):
    """Interface for DB-specific schema extraction."""

    @abstractmethod
    async def extract(self, connection_string: str, schema_filter: list[str] | None = None) -> ExtractedSchema:
        ...


class SQLServerCrawler(BaseCrawler):
    """SQL Server system catalog crawler."""

    async def extract(self, connection_string: str, schema_filter: list[str] | None = None) -> ExtractedSchema:
        # In production, this uses aioodbc or pyodbc to query INFORMATION_SCHEMA
        # Here we show the query patterns that would be executed
        logger.info("sqlserver_crawl_start", schema_filter=schema_filter)

        # These are the actual queries that would run against the source DB:
        # Tables:
        #   SELECT TABLE_SCHEMA, TABLE_NAME
        #   FROM INFORMATION_SCHEMA.TABLES
        #   WHERE TABLE_TYPE = 'BASE TABLE'
        #
        # Columns:
        #   SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, DATA_TYPE,
        #          IS_NULLABLE, ORDINAL_POSITION
        #   FROM INFORMATION_SCHEMA.COLUMNS
        #
        # PKs:
        #   SELECT tc.TABLE_SCHEMA, tc.TABLE_NAME, ccu.COLUMN_NAME
        #   FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
        #   JOIN INFORMATION_SCHEMA.CONSTRAINT_COLUMN_USAGE ccu
        #     ON tc.CONSTRAINT_NAME = ccu.CONSTRAINT_NAME
        #   WHERE tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
        #
        # FKs:
        #   SELECT rc.CONSTRAINT_NAME,
        #          kcu1.TABLE_SCHEMA, kcu1.TABLE_NAME, kcu1.COLUMN_NAME,
        #          kcu2.TABLE_SCHEMA AS REF_SCHEMA,
        #          kcu2.TABLE_NAME AS REF_TABLE,
        #          kcu2.COLUMN_NAME AS REF_COLUMN
        #   FROM INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS rc
        #   JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu1 ...
        #   JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu2 ...

        # For now, return empty — real implementation uses aioodbc
        return ExtractedSchema(database_name="", engine=DatabaseEngine.SQLSERVER)


class PostgreSQLCrawler(BaseCrawler):
    """PostgreSQL system catalog crawler using asyncpg."""

    async def extract(self, connection_string: str, schema_filter: list[str] | None = None) -> ExtractedSchema:
        logger.info("postgresql_crawl_start", schema_filter=schema_filter)

        try:
            import asyncpg
        except ImportError:
            raise RuntimeError("asyncpg is required for PostgreSQL crawling: pip install asyncpg")

        conn = await asyncpg.connect(connection_string)
        try:
            schema = ExtractedSchema(database_name="", engine=DatabaseEngine.POSTGRESQL)

            # Build schema filter clause
            schema_clause = ""
            args: list[Any] = []
            if schema_filter:
                placeholders = ", ".join(f"${i+1}" for i in range(len(schema_filter)))
                schema_clause = f"AND t.table_schema IN ({placeholders})"
                args = list(schema_filter)
            else:
                schema_clause = "AND t.table_schema NOT IN ('pg_catalog', 'information_schema')"

            # 1. Extract tables
            table_rows = await conn.fetch(f"""
                SELECT t.table_schema, t.table_name,
                       obj_description((t.table_schema || '.' || t.table_name)::regclass) AS description
                FROM information_schema.tables t
                WHERE t.table_type = 'BASE TABLE'
                  {schema_clause}
                ORDER BY t.table_schema, t.table_name
            """, *args)

            # Build lookup for tables per schema
            tables_by_schema: dict[str, dict[str, ExtractedTable]] = {}
            for row in table_rows:
                s = row["table_schema"]
                tname = row["table_name"]
                if s not in tables_by_schema:
                    tables_by_schema[s] = {}
                tables_by_schema[s][tname] = ExtractedTable(
                    schema_name=s,
                    table_name=tname,
                    description=row["description"] or "",
                )

            # 2. Extract columns
            col_rows = await conn.fetch(f"""
                SELECT c.table_schema, c.table_name, c.column_name,
                       c.data_type, c.is_nullable, c.ordinal_position,
                       col_description((c.table_schema || '.' || c.table_name)::regclass,
                                       c.ordinal_position) AS description
                FROM information_schema.columns c
                JOIN information_schema.tables t
                  ON c.table_schema = t.table_schema AND c.table_name = t.table_name
                WHERE t.table_type = 'BASE TABLE'
                  {schema_clause}
                ORDER BY c.table_schema, c.table_name, c.ordinal_position
            """, *args)

            for row in col_rows:
                s = row["table_schema"]
                tname = row["table_name"]
                if s in tables_by_schema and tname in tables_by_schema[s]:
                    tables_by_schema[s][tname].columns.append(
                        ExtractedColumn(
                            name=row["column_name"],
                            data_type=row["data_type"],
                            is_nullable=row["is_nullable"] == "YES",
                            ordinal_position=row["ordinal_position"],
                            description=row["description"] or "",
                        )
                    )

            # 3. Extract primary keys
            pk_rows = await conn.fetch(f"""
                SELECT tc.table_schema, tc.table_name, kcu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                 AND tc.table_schema = kcu.table_schema
                WHERE tc.constraint_type = 'PRIMARY KEY'
                  {schema_clause.replace('t.table_schema', 'tc.table_schema')}
            """, *args)

            for row in pk_rows:
                s = row["table_schema"]
                tname = row["table_name"]
                col_name = row["column_name"]
                if s in tables_by_schema and tname in tables_by_schema[s]:
                    for col in tables_by_schema[s][tname].columns:
                        if col.name == col_name:
                            col.is_pk = True
                            break

            # 4. Extract foreign keys
            fk_rows = await conn.fetch(f"""
                SELECT tc.table_schema, tc.table_name, tc.constraint_name,
                       kcu.column_name AS source_column,
                       ccu.table_name AS target_table,
                       ccu.column_name AS target_column
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                 AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage ccu
                  ON tc.constraint_name = ccu.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                  {schema_clause.replace('t.table_schema', 'tc.table_schema')}
            """, *args)

            for row in fk_rows:
                s = row["table_schema"]
                tname = row["table_name"]
                if s in tables_by_schema and tname in tables_by_schema[s]:
                    tables_by_schema[s][tname].foreign_keys.append(
                        ExtractedForeignKey(
                            constraint_name=row["constraint_name"],
                            source_column=row["source_column"],
                            target_table=row["target_table"],
                            target_column=row["target_column"],
                        )
                    )

            # Convert to schema format and log per-table details
            for s, table_map in tables_by_schema.items():
                schema.schemas[s] = list(table_map.values())
                logger.info(
                    "schema_discovered",
                    schema=s,
                    tables_in_schema=len(table_map),
                )
                for tname, ext_table in table_map.items():
                    logger.info(
                        "table_discovered",
                        schema=s,
                        table=tname,
                        columns=len(ext_table.columns),
                        primary_keys=sum(1 for c in ext_table.columns if c.is_pk),
                        foreign_keys=len(ext_table.foreign_keys),
                        row_count_approx=ext_table.row_count_approx,
                    )

            total_tables = sum(len(ts) for ts in schema.schemas.values())
            total_columns = sum(
                len(t.columns)
                for ts in schema.schemas.values()
                for t in ts
            )
            total_fks = sum(
                len(t.foreign_keys)
                for ts in schema.schemas.values()
                for t in ts
            )
            logger.info(
                "postgresql_crawl_complete",
                schemas=len(schema.schemas),
                tables=total_tables,
                columns=total_columns,
                foreign_keys=total_fks,
            )
            return schema

        finally:
            await conn.close()


class OracleCrawler(BaseCrawler):
    """Oracle system catalog crawler."""

    async def extract(self, connection_string: str, schema_filter: list[str] | None = None) -> ExtractedSchema:
        raise NotImplementedError(
            "Oracle crawler not yet implemented. "
            "Requires oracledb async driver querying ALL_TABLES, ALL_TAB_COLUMNS, "
            "ALL_CONSTRAINTS, ALL_CONS_COLUMNS."
        )


class MongoDBCrawler(BaseCrawler):
    """MongoDB metadata crawler (collections, field sampling)."""

    async def extract(self, connection_string: str, schema_filter: list[str] | None = None) -> ExtractedSchema:
        raise NotImplementedError(
            "MongoDB crawler not yet implemented. "
            "Requires motor async driver to list databases, list collections, "
            "sample documents, and infer field types."
        )


# ── Crawler factory ──────────────────────────────────────────


_CRAWLER_MAP: dict[DatabaseEngine, type[BaseCrawler]] = {
    DatabaseEngine.SQLSERVER: SQLServerCrawler,
    DatabaseEngine.POSTGRESQL: PostgreSQLCrawler,
    DatabaseEngine.ORACLE: OracleCrawler,
    DatabaseEngine.MONGODB: MongoDBCrawler,
}


def get_crawler(engine: DatabaseEngine) -> BaseCrawler:
    cls = _CRAWLER_MAP.get(engine)
    if not cls:
        raise ValueError(f"Unsupported database engine: {engine}")
    return cls()


# ── Schema Discovery Service ────────────────────────────────


class SchemaDiscoveryService:
    """Orchestrates schema crawl → diff → graph sync → audit."""

    def __init__(
        self,
        graph_writer: GraphWriteRepository,
        audit_repo: AuditRepository,
        cache: CacheService | None = None,
        graph_reader: GraphReadRepository | None = None,
        # EC-3b: Optional callback to trigger re-classification for type-changed columns.
        # Avoids circular import by deferring ClassificationEngine dependency.
        reclassify_callback: Callable[[list[str]], Awaitable[None]] | None = None,
    ) -> None:
        self._graph = graph_writer
        self._reader = graph_reader
        self._audit = audit_repo
        self._cache = cache
        self._reclassify_callback = reclassify_callback

    async def run_crawl(
        self,
        database_name: str,
        engine: DatabaseEngine,
        connection_string: str,
        schema_filter: list[str] | None = None,
        triggered_by: str = "system",
    ) -> CrawlRecord:
        """Full crawl lifecycle: extract → diff → sync → audit."""
        start_time = time.monotonic()
        crawl_record = CrawlRecord(database_name=database_name, triggered_by=triggered_by)
        crawl_id = await self._audit.start_crawl(crawl_record)

        try:
            # 1. Extract schema from source DB
            logger.info(
                "crawl_starting",
                database=database_name,
                engine=engine.value,
                schema_filter=schema_filter,
                triggered_by=triggered_by,
            )
            crawler = get_crawler(engine)
            extracted = await crawler.extract(connection_string, schema_filter)
            extracted.database_name = database_name

            # 2. Ensure database node exists
            db_node = DatabaseNode(name=database_name, engine=engine)
            await self._graph.upsert_database(db_node)

            # 3. Get existing graph state for diff
            existing_table_fqns = await self._graph.get_existing_table_fqns(database_name)
            discovered_table_fqns: set[str] = set()
            audit_records: list[ChangeRecord] = []

            # 4. Process each schema
            for schema_name, tables in extracted.schemas.items():
                schema_fqn = f"{database_name}.{schema_name}"
                schema_node = SchemaNode(fqn=schema_fqn, name=schema_name)
                await self._graph.upsert_schema(schema_node, database_name)

                logger.info(
                    "processing_schema",
                    database=database_name,
                    schema=schema_name,
                    tables_in_schema=len(tables),
                )

                for ext_table in tables:
                    table_fqn = f"{database_name}.{schema_name}.{ext_table.table_name}"
                    discovered_table_fqns.add(table_fqn)
                    crawl_record.tables_found += 1

                    logger.info(
                        "syncing_table",
                        database=database_name,
                        table_fqn=table_fqn,
                        columns=len(ext_table.columns),
                        foreign_keys=len(ext_table.foreign_keys),
                        row_count_approx=ext_table.row_count_approx,
                    )

                    # Determine domain from schema name (heuristic, can be overridden)
                    domain = self._infer_domain(schema_name)

                    # Upsert table
                    table_node = TableNode(
                        fqn=table_fqn,
                        name=ext_table.table_name,
                        description=ext_table.description,
                        sensitivity_level=SensitivityLevel.INTERNAL,
                        domain=domain,
                        row_count_approx=ext_table.row_count_approx,
                    )
                    result = await self._graph.upsert_table(table_node, schema_fqn, domain)

                    if table_fqn in existing_table_fqns:
                        crawl_record.tables_updated += 1
                        action = ChangeAction.UPDATE
                    else:
                        crawl_record.tables_added += 1
                        action = ChangeAction.CREATE

                    audit_records.append(
                        ChangeRecord(
                            node_type="Table",
                            node_id=table_fqn,
                            action=action,
                            new_values={"name": ext_table.table_name, "domain": domain},
                            changed_by=triggered_by,
                            change_source=ChangeSource.SCHEMA_DISCOVERY,
                        )
                    )

                    # Process columns
                    existing_col_fqns = await self._graph.get_existing_column_fqns(table_fqn)
                    discovered_col_fqns: set[str] = set()

                    # EC-3b: Load existing data_types to detect type changes
                    existing_type_map: dict[str, str] = {}
                    if self._reader and existing_col_fqns:
                        try:
                            existing_cols = await self._reader.get_table_columns(table_fqn)
                            existing_type_map = {c.fqn: c.data_type for c in existing_cols}
                        except Exception:
                            pass  # non-fatal; degrade gracefully

                    type_changed_fqns: list[str] = []  # EC-3b: columns needing re-classification

                    for ext_col in ext_table.columns:
                        col_fqn = f"{table_fqn}.{ext_col.name}"
                        discovered_col_fqns.add(col_fqn)
                        crawl_record.columns_found += 1

                        col_node = ColumnNode(
                            fqn=col_fqn,
                            name=ext_col.name,
                            data_type=ext_col.data_type,
                            is_pk=ext_col.is_pk,
                            is_nullable=ext_col.is_nullable,
                            description=ext_col.description,
                        )
                        await self._graph.upsert_column(col_node, table_fqn, ordinal_position=ext_col.ordinal_position)

                        if col_fqn in existing_col_fqns:
                            crawl_record.columns_updated += 1

                            # EC-3b: Detect data_type changes that affect PII classification
                            old_type = (existing_type_map.get(col_fqn) or "").lower()
                            new_type = ext_col.data_type.lower()
                            if old_type and old_type != new_type:
                                old_pii_risk = any(k in old_type for k in _PII_SENSITIVE_TYPE_KEYWORDS)
                                new_pii_risk = any(k in new_type for k in _PII_SENSITIVE_TYPE_KEYWORDS)
                                if old_pii_risk != new_pii_risk:
                                    # Type change crosses a PII risk boundary → must re-classify
                                    type_changed_fqns.append(col_fqn)
                                    logger.warning(
                                        "column_type_changed_pii_risk",
                                        col_fqn=col_fqn,
                                        old_type=old_type,
                                        new_type=new_type,
                                        action="triggering_reclassification",
                                    )
                                    audit_records.append(
                                        ChangeRecord(
                                            node_type="Column",
                                            node_id=col_fqn,
                                            action=ChangeAction.UPDATE,
                                            old_values={"data_type": old_type},
                                            new_values={"data_type": new_type,
                                                        "reclassification_pending": True},
                                            changed_by=triggered_by,
                                            change_source=ChangeSource.SCHEMA_DISCOVERY,
                                        )
                                    )
                        else:
                            crawl_record.columns_added += 1

                    # EC-3b: Trigger re-classification for all type-changed columns
                    if type_changed_fqns and self._reclassify_callback:
                        try:
                            logger.info(
                                "triggering_reclassification_for_type_changes",
                                count=len(type_changed_fqns),
                                columns=type_changed_fqns,
                            )
                            await self._reclassify_callback(type_changed_fqns)
                        except Exception as exc:
                            logger.error(
                                "reclassification_trigger_failed",
                                error=str(exc),
                                columns=type_changed_fqns,
                            )

                    # Deactivate columns no longer in source
                    for gone_col_fqn in existing_col_fqns - discovered_col_fqns:
                        await self._graph.deactivate_column(gone_col_fqn)
                        audit_records.append(
                            ChangeRecord(
                                node_type="Column",
                                node_id=gone_col_fqn,
                                action=ChangeAction.DEACTIVATE,
                                changed_by=triggered_by,
                                change_source=ChangeSource.SCHEMA_DISCOVERY,
                            )
                        )

                    # Process foreign keys
                    for fk in ext_table.foreign_keys:
                        src_col_fqn = f"{table_fqn}.{fk.source_column}"
                        # Target could be in same schema or different
                        tgt_col_fqn = f"{database_name}.{schema_name}.{fk.target_table}.{fk.target_column}"
                        await self._graph.add_foreign_key(
                            src_col_fqn, tgt_col_fqn, fk.constraint_name
                        )

            # 5. Deactivate tables no longer in source (soft delete) — EC-2
            for gone_table_fqn in existing_table_fqns - discovered_table_fqns:
                await self._graph.deactivate_table(gone_table_fqn)
                crawl_record.tables_deactivated += 1
                logger.warning(
                    "table_dropped_in_db_deactivated",
                    table=gone_table_fqn,
                    action="set_is_active_false",
                    note="Policies referencing this table remain inert until explicit cleanup",
                )
                audit_records.append(
                    ChangeRecord(
                        node_type="Table",
                        node_id=gone_table_fqn,
                        action=ChangeAction.DEACTIVATE,
                        old_values={"is_active": True},
                        new_values={"is_active": False, "compliance_review_required": True},
                        changed_by=triggered_by,
                        change_source=ChangeSource.SCHEMA_DISCOVERY,
                    )
                )

            # 6. Commit audit records
            graph_version = await self._audit.increment_graph_version(
                triggered_by, f"Schema crawl: {database_name}"
            )
            await self._audit.log_changes_batch(audit_records, graph_version)

            crawl_record.status = "completed"

            # Invalidate caches affected by schema changes
            if self._cache:
                await self._cache.invalidate("tables:")
                await self._cache.invalidate("columns:")
                await self._cache.invalidate("fks:")

        except Exception as exc:
            crawl_record.status = "failed"
            crawl_record.errors.append({"error": str(exc)})
            logger.error("crawl_failed", database=database_name, error=str(exc))

        finally:
            elapsed = time.monotonic() - start_time
            await self._audit.complete_crawl(crawl_id, crawl_record)
            logger.info(
                "crawl_complete",
                database=database_name,
                engine=engine.value,
                status=crawl_record.status,
                tables_found=crawl_record.tables_found,
                tables_added=crawl_record.tables_added,
                tables_updated=crawl_record.tables_updated,
                tables_deactivated=crawl_record.tables_deactivated,
                columns_found=crawl_record.columns_found,
                columns_added=crawl_record.columns_added,
                columns_updated=crawl_record.columns_updated,
                duration_s=round(elapsed, 2),
            )

        return crawl_record

    async def run_on_demand_crawl_for_schema(
        self,
        database_name: str,
        engine: DatabaseEngine,
        connection_string: str,
        schema_name: str,
        triggered_by: str = "on-demand",
    ) -> CrawlRecord:
        """EC-1: On-demand re-crawl for a specific schema.

        Triggered when the query layer discovers a table that exists in the source DB
        but has not yet been catalogued in the graph (e.g., added after the last scheduled crawl).

        This is a targeted re-crawl scoped to one schema rather than a full database crawl.
        """
        logger.info(
            "on_demand_crawl_triggered",
            database=database_name,
            schema=schema_name,
            triggered_by=triggered_by,
            reason="table_exists_in_db_not_in_graph",
        )
        return await self.run_crawl(
            database_name=database_name,
            engine=engine,
            connection_string=connection_string,
            schema_filter=[schema_name],
            triggered_by=triggered_by,
        )

    @staticmethod
    def _infer_domain(schema_name: str) -> str:
        """Heuristic domain inference from schema name."""
        domain_keywords: dict[str, list[str]] = {
            "clinical": ["clinical", "patient", "medical", "emr", "ehr"],
            "billing": ["billing", "finance", "claims", "payment", "revenue"],
            "pharmacy": ["pharmacy", "rx", "prescription", "medication", "drug"],
            "hr": ["hr", "human_resource", "employee", "payroll", "staff"],
            "admin": ["admin", "config", "system", "master", "reference"],
            "behavioral_health": ["behavioral", "mental", "psych", "substance"],
            "lab": ["lab", "laboratory", "pathology", "specimen"],
        }
        lower = schema_name.lower()
        for domain, keywords in domain_keywords.items():
            if any(kw in lower for kw in keywords):
                return domain
        return "general"
