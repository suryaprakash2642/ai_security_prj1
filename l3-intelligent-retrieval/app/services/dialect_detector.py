"""Backend Dialect Detection — determines SQL dialect from table FQNs.

Each table's FQN already encodes its database (e.g. apollo_analytics.public.encounter_summaries).
The database→dialect mapping is loaded from L2 graph metadata at startup.
Detection simply looks up each table's database in that map — no heuristics.
"""

from __future__ import annotations

import re

import structlog

from app.models.l2_models import L2DatabaseInfo
from app.models.retrieval import EnrichedQuery, FilteredTable

logger = structlog.get_logger(__name__)

# Engine strings from L2 → SQL dialect for L5/frontend
_ENGINE_TO_DIALECT: dict[str, str] = {
    "mysql": "mysql",
    "postgresql": "postgresql",
    "sqlserver": "tsql",
    "oracle": "oracle",
    "mongodb": "nosql",
}

# Patterns to detect engine type from a database description string.
# The description field in the graph is more reliable than the engine field
# which can be stale or wrong after migrations / crawls.
_DESC_ENGINE_PATTERNS: list[tuple[str, str]] = [
    (r"\bpostgres(?:ql)?\b", "postgresql"),
    (r"\brds\s+postgres", "postgresql"),
    (r"\bmysql\b", "mysql"),
    (r"\bmariadb\b", "mysql"),
    (r"\bsql\s*server\b", "sqlserver"),
    (r"\btsql\b", "sqlserver"),
    (r"\boracle\b", "oracle"),
    (r"\bmongo(?:db)?\b", "mongodb"),
]


def _engine_from_description(description: str) -> str | None:
    """Try to extract the engine type from a free-text description."""
    if not description:
        return None
    lower = description.lower()
    for pattern, engine in _DESC_ENGINE_PATTERNS:
        if re.search(pattern, lower):
            return engine
    return None


class DialectDetector:
    """Detects SQL dialect purely from each table's database FQN.

    The database→dialect mapping is built dynamically from L2 metadata
    loaded at startup via ``load_catalog()``.
    """

    def __init__(self) -> None:
        self._db_to_dialect: dict[str, str] = {}

    def load_catalog(self, databases: list[L2DatabaseInfo]) -> None:
        """Build database→dialect mapping from L2 metadata.

        Engine is extracted from the description field first (more reliable),
        falling back to the engine field if description doesn't contain
        recognisable engine keywords.
        """
        self._db_to_dialect = {}
        for db in databases:
            # Prefer engine from description — the engine field can be stale
            desc_engine = _engine_from_description(db.description)
            engine = desc_engine or (db.engine or "").lower()
            if not engine:
                logger.warning("no_engine_for_database", database=db.name,
                               hint="Set engine property on Database node in Neo4j")
                continue
            dialect = _ENGINE_TO_DIALECT.get(engine, engine)
            self._db_to_dialect[db.name.lower()] = dialect
        logger.info(
            "dialect_catalog_loaded",
            mappings=self._db_to_dialect,
        )

    def dialect_for_db(self, db_name: str) -> str:
        """Look up dialect for a database name.

        Raises ValueError if the database is not in the catalog.
        """
        key = db_name.lower()
        if key not in self._db_to_dialect:
            raise ValueError(
                f"Unknown database '{db_name}' — no dialect mapping found. "
                f"Known databases: {list(self._db_to_dialect.keys())}. "
                f"Ensure the Database node in Neo4j has a valid engine property."
            )
        return self._db_to_dialect[key]

    def get_database_metadata(
        self, tables: list[FilteredTable],
    ) -> dict[str, str]:
        """Return {db_name: dialect} for all databases represented in tables.

        This is passed to L5 so the LLM can see which dialect each
        database uses without the frontend pre-selecting one.
        """
        metadata: dict[str, str] = {}
        for t in tables:
            db = (t.table_id or "").split(".")[0].lower()
            if db and db not in metadata:
                metadata[db] = self.dialect_for_db(db)
        return metadata

    def stamp_tables(self, tables: list[FilteredTable]) -> None:
        """Set the ``dialect`` field on each table from its FQN."""
        for t in tables:
            db = (t.table_id or "").split(".")[0]
            if db:
                t.dialect = self.dialect_for_db(db)

    def detect(
        self,
        tables: list[FilteredTable],
        enriched: EnrichedQuery | None = None,
    ) -> tuple[str, str]:
        """Detect the primary dialect and target database.

        Stamps every table with its own dialect first, then picks the
        global dialect from the highest-scoring table (since that's the
        table most likely to be queried).

        Returns:
            (dialect, target_database)
        """
        # Stamp each table with its own dialect
        self.stamp_tables(tables)

        # Priority 1: enrichment hint with high confidence
        if enriched and enriched.suggested_dialect and enriched.confidence >= 0.7:
            dialect = enriched.suggested_dialect
            if enriched.database_hints:
                for db in enriched.database_hints:
                    db_lower = db.lower()
                    if self.dialect_for_db(db_lower) == dialect:
                        return dialect, db_lower

        # Priority 2: dialect of the highest-scoring table
        if tables:
            top = tables[0]
            db = (top.table_id or "").split(".")[0].lower()
            dialect = top.dialect or self.dialect_for_db(db)
            logger.debug(
                "dialect_from_top_table",
                table_id=top.table_id,
                db=db,
                dialect=dialect,
                score=top.relevance_score,
            )
            return dialect, db

        raise ValueError(
            "Cannot detect SQL dialect — no tables available in the filtered schema. "
            "Ensure the query matches at least one table in the knowledge graph."
        )
