"""Embedding Pipeline — generates semantic vectors from graph metadata.

Embeds table descriptions, column descriptions, and composite descriptions.
Stores in pgvector. Only re-embeds when source text changes (hash-based).
Vector DB is fully regenerable from graph metadata.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

import httpx
import numpy as np
import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.repositories.graph_read_repo import GraphReadRepository

logger = structlog.get_logger(__name__)


class EmbeddingPipeline:
    """Generates, stores, and retrieves semantic embeddings from graph metadata."""

    def __init__(self, settings: Settings, graph_reader: GraphReadRepository) -> None:
        self._settings = settings
        self._reader = graph_reader
        self._engine: AsyncEngine | None = None
        self._session_factory: sessionmaker | None = None
        self._http_client: httpx.AsyncClient | None = None

    async def connect(self) -> None:
        import ssl as _ssl
        dsn = self._settings.pg_vector_dsn
        clean_dsn = dsn.split("?")[0] if "?" in dsn else dsn
        is_remote = "localhost" not in clean_dsn and "127.0.0.1" not in clean_dsn
        connect_args: dict[str, Any] = {}
        if is_remote:
            ssl_ctx = _ssl.create_default_context()
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = _ssl.CERT_NONE
            connect_args["ssl"] = ssl_ctx

        self._engine = create_async_engine(
            clean_dsn,
            pool_size=2,
            max_overflow=2,
            connect_args=connect_args,
        )
        self._session_factory = sessionmaker(
            self._engine, class_=AsyncSession, expire_on_commit=False
        )
        self._http_client = httpx.AsyncClient(timeout=30.0)
        await self._ensure_schema()
        logger.info("embedding_pipeline_connected")

    async def _ensure_schema(self) -> None:
        """Ensure schema_embeddings table exists and has required columns.

        The table was originally created by setup_retrieval.py — we just need
        to add the source_hash column if it is absent.  We intentionally skip
        CREATE EXTENSION because pgvector is already installed on Aiven and that
        statement requires superuser, which rolls back the whole transaction.
        """
        async with self._get_session() as session:
            try:
                # Create table if it was somehow dropped (matches setup_retrieval.py DDL).
                await session.execute(text("""
                    CREATE TABLE IF NOT EXISTS schema_embeddings (
                        id              BIGSERIAL PRIMARY KEY,
                        entity_type     VARCHAR(20)  NOT NULL DEFAULT 'table',
                        entity_fqn      VARCHAR(500) NOT NULL,
                        source_text     TEXT         NOT NULL DEFAULT '',
                        is_active       BOOLEAN      NOT NULL DEFAULT true,
                        embedding       vector(1536),
                        created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
                        UNIQUE (entity_fqn, entity_type)
                    )
                """))
                # Add source_hash for idempotent refresh (safe on existing table).
                await session.execute(text(
                    "ALTER TABLE schema_embeddings "
                    "ADD COLUMN IF NOT EXISTS source_hash TEXT NOT NULL DEFAULT ''"
                ))
                await session.commit()
                logger.info("embedding_schema_ready")
            except Exception as exc:
                logger.error("embedding_schema_failed", error=str(exc))
                await session.rollback()
                raise

    async def close(self) -> None:
        if self._engine:
            await self._engine.dispose()
        if self._http_client:
            await self._http_client.aclose()

    def _get_session(self) -> AsyncSession:
        if not self._session_factory:
            raise RuntimeError("Embedding DB not connected")
        return self._session_factory()

    # ── Embedding generation ─────────────────────────────────

    async def embed_all_tables(self) -> dict[str, int]:
        """Embed all active tables. Only re-embeds if source text changed."""
        tables = await self._reader.get_all_active_tables()
        stats = {"processed": 0, "embedded": 0, "skipped": 0}

        for table in tables:
            stats["processed"] += 1

            # Build composite source text
            columns = await self._reader.get_table_columns(table.fqn)
            # Always include column names so semantic similarity reflects the
            # actual schema — descriptions are appended only when present.
            col_parts = []
            for c in columns:
                entry = f"{c.name} ({c.data_type})"
                if c.description:
                    entry += f": {c.description}"
                col_parts.append(entry)
            col_descriptions = ", ".join(col_parts)
            source_text = (
                f"Table: {table.name}\n"
                f"Description: {table.description}\n"
                f"Domain: {table.domain}\n"
                f"Columns: {col_descriptions}"
            )
            source_hash = hashlib.sha256(source_text.encode()).hexdigest()

            # Check if already embedded with same hash
            if await self._has_current_embedding(table.fqn, source_hash):
                stats["skipped"] += 1
                continue

            # Generate embedding
            embedding = await self._generate_embedding(source_text)
            if embedding is None:
                continue

            # Store — use entity_type='table' so L3 vector search finds it.
            await self._store_embedding(
                entity_type="table",
                entity_fqn=table.fqn,
                source_text=source_text,
                source_hash=source_hash,
                embedding=embedding,
            )
            stats["embedded"] += 1

            # Embed every column by name (+ description when available) so that
            # column-name semantic search can boost the correct parent table.
            for col in columns:
                col_text = f"Column {col.name} ({col.data_type}) in {table.name}"
                if col.description:
                    col_text += f": {col.description}"
                col_hash = hashlib.sha256(col_text.encode()).hexdigest()
                col_key = col.fqn if hasattr(col, "fqn") and col.fqn else f"{table.fqn}.{col.name}"
                if not await self._has_current_embedding(col_key, col_hash):
                    col_embedding = await self._generate_embedding(col_text)
                    if col_embedding:
                        await self._store_embedding(
                            entity_type="column",
                            entity_fqn=col_key,
                            source_text=col_text,
                            source_hash=col_hash,
                            embedding=col_embedding,
                        )

        logger.info("embedding_refresh_complete", **stats)
        return stats

    async def search_similar(
        self, query_text: str, limit: int = 10, entity_type: str = "composite"
    ) -> list[dict[str, Any]]:
        """Semantic search over embedded metadata."""
        query_embedding = await self._generate_embedding(query_text)
        if query_embedding is None:
            return []

        embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

        async with self._get_session() as session:
            result = await session.execute(
                text("""
                    SELECT entity_fqn, source_text,
                           1 - (embedding <=> CAST(:query_vec AS vector)) AS similarity
                    FROM schema_embeddings
                    WHERE entity_type = :etype
                      AND is_active = true
                    ORDER BY embedding <=> CAST(:query_vec AS vector)
                    LIMIT :limit
                """),
                {"query_vec": embedding_str, "etype": entity_type, "limit": limit},
            )
            return [
                {"entity_fqn": r[0], "source_text": r[1], "similarity": float(r[2])}
                for r in result.fetchall()
            ]

    # ── Private helpers ──────────────────────────────────────

    async def _generate_embedding(self, text: str) -> list[float] | None:
        """Call the embedding API. Returns None on failure.

        Supports two modes:
        1. Standard OpenAI — when ``embedding_api_key`` is configured.
        2. Azure OpenAI   — when ``AZURE_AI_ENDPOINT`` + ``AZURE_AI_API_KEY``
           environment variables are present and no OpenAI key is configured.
           Uses the ``text-embedding-ada-002`` deployment (1536-dim, matching
           the ``schema_embeddings`` vector column).
        """
        import os

        if not self._http_client:
            return None

        api_key = self._settings.embedding_api_key
        azure_endpoint = os.getenv("AZURE_AI_ENDPOINT", "").rstrip("/")
        azure_api_key = os.getenv("AZURE_AI_API_KEY", "")

        if api_key:
            # Standard OpenAI
            url = f"{self._settings.embedding_api_base}/embeddings"
            headers = {"Authorization": f"Bearer {api_key}"}
            body: dict = {"model": self._settings.embedding_model, "input": text[:8000]}
        elif azure_api_key and azure_endpoint:
            # Azure OpenAI — text-embedding-ada-002 has 1536 dims, matches DB
            url = (
                f"{azure_endpoint}/openai/deployments/"
                "text-embedding-ada-002/embeddings?api-version=2024-02-01"
            )
            headers = {"api-key": azure_api_key}
            body = {"input": text[:8000]}
        else:
            logger.debug("embedding_api_not_configured")
            return None

        try:
            response = await self._http_client.post(url, headers=headers, json=body)
            response.raise_for_status()
            data = response.json()
            return data["data"][0]["embedding"]
        except Exception as exc:
            logger.warning("embedding_generation_failed", error=str(exc))
            return None

    async def _has_current_embedding(self, entity_fqn: str, source_hash: str) -> bool:
        """Check if an embedding with the same source hash already exists."""
        async with self._get_session() as session:
            result = await session.execute(
                text("""
                    SELECT 1 FROM schema_embeddings
                    WHERE entity_fqn = :fqn
                      AND source_hash = :hash
                    LIMIT 1
                """),
                {"fqn": entity_fqn, "hash": source_hash},
            )
            return result.fetchone() is not None

    async def _store_embedding(
        self,
        entity_type: str,
        entity_fqn: str,
        source_text: str,
        source_hash: str,
        embedding: list[float],
    ) -> None:
        """Insert or update embedding in pgvector."""
        embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

        async with self._get_session() as session:
            await session.execute(
                text("""
                    INSERT INTO schema_embeddings
                        (entity_type, entity_fqn, source_text, source_hash,
                         is_active, embedding)
                    VALUES
                        (:etype, :fqn, :source, :hash, true,
                         CAST(:embedding AS vector))
                    ON CONFLICT (entity_fqn, entity_type)
                    DO UPDATE SET
                        source_text = EXCLUDED.source_text,
                        source_hash = EXCLUDED.source_hash,
                        embedding   = EXCLUDED.embedding,
                        is_active   = true,
                        created_at  = NOW()
                """),
                {
                    "etype": entity_type,
                    "fqn": entity_fqn,
                    "source": source_text[:10000],
                    "hash": source_hash,
                    "embedding": embedding_str,
                },
            )
            await session.commit()

    async def rebuild_all(self) -> dict[str, int]:
        """Full rebuild: clear all embeddings and re-embed everything from graph."""
        async with self._get_session() as session:
            await session.execute(
                text("DELETE FROM schema_embeddings WHERE entity_type IN ('table', 'column')")
            )
            await session.commit()

        logger.info("embeddings_cleared_for_rebuild")
        return await self.embed_all_tables()
