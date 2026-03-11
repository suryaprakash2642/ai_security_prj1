"""Vector search client — queries pgvector for semantic table/column matches.

Uses HNSW index for approximate nearest neighbor search.
Connects to the same pgvector database that L2 populates with embeddings.
"""

from __future__ import annotations

from typing import Any

import structlog

from app.config import Settings
from app.models.l2_models import L2VectorSearchResult

logger = structlog.get_logger(__name__)


class VectorSearchClient:
    """Async client for pgvector similarity search."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._engine: Any | None = None

    async def connect(self) -> None:
        """Initialize async SQLAlchemy engine for pgvector."""
        try:
            from sqlalchemy.ext.asyncio import create_async_engine

            kwargs: dict[str, Any] = {
                "pool_size": 5,
                "max_overflow": 10,
                "pool_timeout": 10,
            }
            if self._settings.pgvector_ssl:
                import ssl as _ssl
                ssl_ctx = _ssl.create_default_context()
                ssl_ctx.check_hostname = False
                ssl_ctx.verify_mode = _ssl.CERT_NONE
                kwargs["connect_args"] = {"ssl": ssl_ctx}

            self._engine = create_async_engine(
                self._settings.pgvector_dsn,
                **kwargs,
            )
            logger.info("pgvector_connected")
        except Exception as exc:
            logger.warning("pgvector_connect_failed", error=str(exc))
            self._engine = None

    async def close(self) -> None:
        if self._engine:
            await self._engine.dispose()

    async def search_similar(
        self,
        embedding: list[float],
        top_k: int = 15,
        min_similarity: float = 0.35,
        entity_type: str | None = None,
    ) -> list[L2VectorSearchResult]:
        """Perform cosine similarity search over embedded schema metadata.

        Uses pgvector's <=> operator for cosine distance.
        """
        if not self._engine:
            logger.warning("pgvector_not_available")
            return []

        try:
            from sqlalchemy import text
            from sqlalchemy.ext.asyncio import AsyncSession
            from sqlalchemy.orm import sessionmaker

            SessionLocal = sessionmaker(self._engine, class_=AsyncSession)

            embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

            type_filter = ""
            params: dict[str, Any] = {
                "embedding": embedding_str,
                "top_k": top_k,
                "min_sim": min_similarity,
            }

            if entity_type:
                type_filter = "AND entity_type = :etype"
                params["etype"] = entity_type

            query = text(f"""
                SELECT entity_fqn, source_text, entity_type,
                       1 - (embedding <=> CAST(:embedding AS vector)) AS similarity
                FROM schema_embeddings
                WHERE is_active = true
                  {type_filter}
                  AND 1 - (embedding <=> CAST(:embedding AS vector)) >= :min_sim
                ORDER BY embedding <=> CAST(:embedding AS vector)
                LIMIT :top_k
            """)

            async with SessionLocal() as session:
                result = await session.execute(query, params)
                rows = result.fetchall()

            return [
                L2VectorSearchResult(
                    entity_fqn=r[0],
                    source_text=r[1] or "",
                    entity_type=r[2] or "table",
                    similarity=float(r[3]),
                )
                for r in rows
            ]

        except Exception as exc:
            logger.error("vector_search_failed", error=str(exc))
            return []

    async def health_check(self) -> bool:
        if not self._engine:
            return False
        try:
            from sqlalchemy import text
            from sqlalchemy.ext.asyncio import AsyncSession
            from sqlalchemy.orm import sessionmaker

            SessionLocal = sessionmaker(self._engine, class_=AsyncSession)
            async with SessionLocal() as session:
                result = await session.execute(text("SELECT 1"))
                return result.scalar() == 1
        except Exception:
            return False
