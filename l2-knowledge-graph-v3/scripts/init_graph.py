#!/usr/bin/env python3
"""Initialize the L2 Knowledge Graph — run constraints, indexes, seed data, and PG migrations.

Usage:
    python -m scripts.init_graph              # Full init (constraints + seed + migrations)
    python -m scripts.init_graph --seed-only  # Re-run seed data only
    python -m scripts.init_graph --migrate    # Run PG migrations only

Requires Neo4j and PostgreSQL to be running (see docker-compose.yml).
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

import structlog

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.config import get_settings
from app.repositories.neo4j_manager import Neo4jManager
from app.repositories.audit_repository import AuditRepository

logger = structlog.get_logger("init_graph")

CYPHER_DIR = PROJECT_ROOT / "cypher"
MIGRATION_DIR = PROJECT_ROOT / "migrations"


async def run_cypher_file(neo4j: Neo4jManager, filepath: Path) -> int:
    """Execute a .cypher file statement-by-statement. Returns count of statements run."""
    content = filepath.read_text(encoding="utf-8")
    # Split on semicolons, skipping comments and blanks
    statements = [
        s.strip() for s in content.split(";")
        if s.strip() and not s.strip().startswith("//")
    ]
    count = 0
    for stmt in statements:
        if not stmt:
            continue
        try:
            await neo4j.execute_write(stmt)
            count += 1
        except Exception as exc:
            # Constraint-already-exists errors are non-fatal
            err = str(exc)
            if "already exists" in err.lower() or "equivalent" in err.lower():
                logger.debug("statement_skipped_already_exists", stmt=stmt[:80])
            else:
                logger.error("cypher_statement_failed", stmt=stmt[:120], error=err)
                raise
    return count


async def run_sql_file(audit_repo: AuditRepository, filepath: Path) -> None:
    """Execute a .sql migration file.

    asyncpg does not support multiple statements in a single prepared-
    statement call, so we split on ';' and execute each statement
    individually inside one transaction.
    """
    import re
    content = filepath.read_text(encoding="utf-8")
    # Remove SQL comments (-- line comments)
    content = re.sub(r'--[^\n]*', '', content)
    # Split on semicolons and filter out empty/whitespace-only fragments
    statements = [s.strip() for s in content.split(';') if s.strip()]
    async with audit_repo._get_session() as session:
        from sqlalchemy import text
        for stmt in statements:
            await session.execute(text(stmt))
        await session.commit()
    logger.info("sql_migration_applied", file=filepath.name, statements=len(statements))


async def init_constraints(neo4j: Neo4jManager) -> None:
    """Run all Cypher constraint/index files in order."""
    files = sorted(CYPHER_DIR.glob("001_*.cypher"))
    for f in files:
        count = await run_cypher_file(neo4j, f)
        logger.info("constraints_applied", file=f.name, statements=count)


async def init_seed_data(neo4j: Neo4jManager) -> None:
    """Run Cypher seed data files — 002_* base seeds + 008_* compliance patches + 010_* relationships."""
    for pattern in ("002_*.cypher", "008_*.cypher", "010_*.cypher"):
        files = sorted(CYPHER_DIR.glob(pattern))
        for f in files:
            count = await run_cypher_file(neo4j, f)
            logger.info("seed_data_loaded", file=f.name, statements=count)


async def init_migrations(audit_repo: AuditRepository) -> None:
    """Run all SQL migration files in order."""
    files = sorted(MIGRATION_DIR.glob("*.sql"))
    for f in files:
        await run_sql_file(audit_repo, f)


async def verify_graph(neo4j: Neo4jManager) -> dict[str, int]:
    """Quick verification: count nodes by label (all Section 5 types)."""
    query = """
        CALL {
            MATCH (n:Database) RETURN 'Database' AS label, count(n) AS cnt
            UNION ALL
            MATCH (n:Schema) RETURN 'Schema' AS label, count(n) AS cnt
            UNION ALL
            MATCH (n:Table) RETURN 'Table' AS label, count(n) AS cnt
            UNION ALL
            MATCH (n:Column) RETURN 'Column' AS label, count(n) AS cnt
            UNION ALL
            MATCH (n:Domain) RETURN 'Domain' AS label, count(n) AS cnt
            UNION ALL
            MATCH (n:Policy) RETURN 'Policy' AS label, count(n) AS cnt
            UNION ALL
            MATCH (n:Condition) RETURN 'Condition' AS label, count(n) AS cnt
            UNION ALL
            MATCH (n:Regulation) RETURN 'Regulation' AS label, count(n) AS cnt
            UNION ALL
            MATCH (n:Role) RETURN 'Role' AS label, count(n) AS cnt
        }
        RETURN label, cnt
    """
    records = await neo4j.execute_read(query)
    counts = {r["label"]: r["cnt"] for r in records}
    return counts


async def main(args: argparse.Namespace) -> None:
    settings = get_settings()
    neo4j = Neo4jManager(settings)
    audit_repo = AuditRepository(settings)

    try:
        await neo4j.connect()
        logger.info("neo4j_connected", uri=settings.neo4j_uri)

        if not args.migrate_only:
            if not args.seed_only:
                logger.info("applying_constraints_and_indexes")
                await init_constraints(neo4j)

            logger.info("loading_seed_data")
            await init_seed_data(neo4j)

            # Verify
            counts = await verify_graph(neo4j)
            logger.info("graph_verification", **counts)

        if not args.seed_only:
            await audit_repo.connect()
            logger.info("applying_pg_migrations")
            await init_migrations(audit_repo)
            await audit_repo.close()

        logger.info("initialization_complete")

    except Exception as exc:
        logger.error("initialization_failed", error=str(exc))
        raise
    finally:
        await neo4j.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize L2 Knowledge Graph")
    parser.add_argument("--seed-only", action="store_true", help="Only re-run seed data")
    parser.add_argument("--migrate-only", action="store_true", dest="migrate_only",
                        help="Only run PostgreSQL migrations")
    args = parser.parse_args()

    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ]
    )
    asyncio.run(main(args))
