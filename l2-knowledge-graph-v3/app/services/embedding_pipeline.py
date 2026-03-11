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
            pool_size=5,
            max_overflow=5,
            connect_args=connect_args,
        )
        self._session_factory = sessionmaker(
            self._engine, class_=AsyncSession, expire_on_commit=False
        )
        self._http_client = httpx.AsyncClient(timeout=30.0)
        logger.info("embedding_pipeline_connected")

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
            col_descriptions = ", ".join(
                f"{c.name} ({c.data_type}): {c.description}" for c in columns if c.description
            )
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

            # Store
            await self._store_embedding(
                entity_type="composite",
                entity_fqn=table.fqn,
                source_text=source_text,
                source_hash=source_hash,
                embedding=embedding,
            )
            stats["embedded"] += 1

            # Also embed individual table description
            if table.description:
                desc_hash = hashlib.sha256(table.description.encode()).hexdigest()
                if not await self._has_current_embedding(f"{table.fqn}:desc", desc_hash):
                    desc_embedding = await self._generate_embedding(table.description)
                    if desc_embedding:
                        await self._store_embedding(
                            entity_type="table",
                            entity_fqn=f"{table.fqn}:desc",
                            source_text=table.description,
                            source_hash=desc_hash,
                            embedding=desc_embedding,
                        )

            # Embed individual column descriptions for column-level retrieval
            for col in columns:
                if col.description:
                    col_text = f"Column {col.name} ({col.data_type}) in {table.name}: {col.description}"
                    col_hash = hashlib.sha256(col_text.encode()).hexdigest()
                    col_key = f"{col.fqn}:col_desc" if hasattr(col, "fqn") else f"{table.fqn}.{col.name}:col_desc"
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
                           1 - (embedding <=> :query_vec::vector) AS similarity
                    FROM embedding_metadata
                    WHERE entity_type = :etype
                    ORDER BY embedding <=> :query_vec::vector
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
        """Call the embedding API. Returns None on failure."""
        if not self._http_client or not self._settings.embedding_api_key:
            logger.debug("embedding_api_not_configured")
            return None

        try:
            response = await self._http_client.post(
                f"{self._settings.embedding_api_base}/embeddings",
                headers={"Authorization": f"Bearer {self._settings.embedding_api_key}"},
                json={
                    "model": self._settings.embedding_model,
                    "input": text[:8000],  # Truncate to avoid token limits
                },
            )
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
                    SELECT 1 FROM embedding_metadata
                    WHERE entity_fqn = :fqn
                      AND source_hash = :hash
                      AND model_version = :model
                    LIMIT 1
                """),
                {
                    "fqn": entity_fqn,
                    "hash": source_hash,
                    "model": self._settings.embedding_model,
                },
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
                    INSERT INTO embedding_metadata
                        (entity_type, entity_fqn, model_name, model_version,
                         source_text, source_hash, embedding)
                    VALUES
                        (:etype, :fqn, :model_name, :model_version,
                         :source, :hash, :embedding::vector)
                    ON CONFLICT (entity_fqn, model_version)
                    DO UPDATE SET
                        source_text = :source,
                        source_hash = :hash,
                        embedding = :embedding::vector,
                        created_at = NOW()
                """),
                {
                    "etype": entity_type,
                    "fqn": entity_fqn,
                    "model_name": self._settings.embedding_model,
                    "model_version": self._settings.embedding_model,
                    "source": source_text[:10000],
                    "hash": source_hash,
                    "embedding": embedding_str,
                },
            )
            await session.commit()

    async def rebuild_all(self) -> dict[str, int]:
        """Full rebuild: clear all embeddings and re-embed everything from graph."""
        async with self._get_session() as session:
            await session.execute(text("DELETE FROM embedding_metadata"))
            await session.commit()

        logger.info("embeddings_cleared_for_rebuild")
        return await self.embed_all_tables()
