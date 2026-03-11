#!/usr/bin/env python3
"""Manual schema crawl trigger.

Usage:
    python -m scripts.run_crawl \\
        --database apollo_his \\
        --engine sqlserver \\
        --connection "mssql+aioodbc://readonly:pass@host/apollo_his?driver=ODBC+Driver+18" \\
        --schemas clinical billing pharmacy

    python -m scripts.run_crawl \\
        --database apollo_his \\
        --engine postgresql \\
        --connection "postgresql+asyncpg://readonly:pass@host/apollo_his"
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

import structlog

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.config import get_settings
from app.dependencies import Container
from app.models.enums import DatabaseEngine

logger = structlog.get_logger("run_crawl")


async def main(args: argparse.Namespace) -> None:
    settings = get_settings()
    container = Container(settings)

    try:
        await container.startup()

        engine = DatabaseEngine(args.engine)
        schemas = args.schemas or None

        logger.info(
            "crawl_starting",
            database=args.database,
            engine=engine.value,
            schemas=schemas,
        )

        summary = await container.schema_discovery.crawl(
            database_name=args.database,
            engine=engine,
            connection_string=args.connection,
            schemas=schemas,
            crawled_by="manual_crawl_cli",
        )

        # Print results
        print("\n" + "=" * 60)
        print("CRAWL SUMMARY")
        print("=" * 60)
        print(json.dumps(summary.model_dump(), indent=2, default=str))
        print("=" * 60)

        if args.classify:
            logger.info("running_auto_classification")
            cls_summary = await container.classification_engine.classify_columns(
                classifier_id="manual_crawl_cli"
            )
            print("\nCLASSIFICATION SUMMARY")
            print("=" * 60)
            print(json.dumps(cls_summary.model_dump(), indent=2, default=str))

        if args.embed:
            logger.info("refreshing_embeddings")
            stats = await container.embedding_pipeline.embed_all_tables()
            print("\nEMBEDDING STATS")
            print("=" * 60)
            print(json.dumps(stats, indent=2))

    except Exception as exc:
        logger.error("crawl_failed", error=str(exc))
        raise
    finally:
        await container.shutdown()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run schema discovery crawl")
    parser.add_argument("--database", required=True, help="Database name")
    parser.add_argument("--engine", required=True,
                        choices=["sqlserver", "postgresql", "oracle", "mongodb"],
                        help="Database engine type")
    parser.add_argument("--connection", required=True, help="Connection string (read-only)")
    parser.add_argument("--schemas", nargs="*", help="Specific schemas to crawl")
    parser.add_argument("--classify", action="store_true",
                        help="Run auto-classification after crawl")
    parser.add_argument("--embed", action="store_true",
                        help="Refresh embeddings after crawl")
    args = parser.parse_args()

    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ]
    )
    asyncio.run(main(args))
