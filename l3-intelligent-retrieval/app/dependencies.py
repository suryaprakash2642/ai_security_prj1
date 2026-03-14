"""Dependency injection container for the L3 Intelligent Retrieval Layer.

Provides singleton instances of all services, clients, and infrastructure.
Wired to FastAPI lifespan for clean startup/shutdown.
"""

from __future__ import annotations

import structlog

from app.cache.cache_service import CacheService
from app.clients.embedding_client import EmbeddingClient
from app.clients.l2_client import L2Client
from app.clients.l4_client import L4Client
from app.clients.vector_search import VectorSearchClient
from app.config import Settings
from app.services.column_scoper import ColumnScoper
from app.services.context_assembler import ContextAssembler
from app.services.embedding_engine import EmbeddingEngine
from app.services.intent_classifier import IntentClassifier
from app.services.join_graph import JoinGraphBuilder
from app.services.dialect_detector import DialectDetector
from app.services.query_enrichment import QueryEnrichmentService
from app.services.ranking_engine import RankingEngine
from app.services.rbac_filter import RBACFilter
from app.services.retrieval_pipeline import RetrievalPipeline
from app.services.orchestrator import RetrievalOrchestrator

logger = structlog.get_logger(__name__)


class Container:
    """Application-level DI container. Initialized once at startup."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

        # Infrastructure
        self.cache = CacheService(settings)
        self.embedding_client = EmbeddingClient(settings)
        self.l2_client = L2Client(settings)
        self.l4_client = L4Client(settings)
        self.vector_client = VectorSearchClient(settings)

        # Services
        self.intent_classifier = IntentClassifier()
        self.ranking_engine = RankingEngine()
        self.context_assembler = ContextAssembler()
        self.enrichment_service = QueryEnrichmentService(settings)
        self.dialect_detector = DialectDetector()

        self.embedding_engine = EmbeddingEngine(
            settings=settings,
            embedding_client=self.embedding_client,
            cache=self.cache,
        )

        self.retrieval_pipeline = RetrievalPipeline(
            settings=settings,
            l2_client=self.l2_client,
            vector_client=self.vector_client,
            cache=self.cache,
        )

        self.rbac_filter = RBACFilter(
            l2_client=self.l2_client,
            l4_client=self.l4_client,
            cache=self.cache,
        )

        self.column_scoper = ColumnScoper(
            l2_client=self.l2_client,
            cache=self.cache,
        )

        self.join_graph_builder = JoinGraphBuilder(
            l2_client=self.l2_client,
            cache=self.cache,
        )

        self.orchestrator = RetrievalOrchestrator(
            settings=settings,
            embedding_engine=self.embedding_engine,
            intent_classifier=self.intent_classifier,
            retrieval_pipeline=self.retrieval_pipeline,
            ranking_engine=self.ranking_engine,
            rbac_filter=self.rbac_filter,
            column_scoper=self.column_scoper,
            join_graph_builder=self.join_graph_builder,
            context_assembler=self.context_assembler,
            enrichment_service=self.enrichment_service,
            dialect_detector=self.dialect_detector,
        )

    async def startup(self) -> None:
        """Connect all infrastructure components."""
        logger.info("container_starting")
        await self.cache.connect()
        await self.embedding_client.connect()
        await self.l2_client.connect()
        await self.l4_client.connect()
        await self.vector_client.connect()
        await self.enrichment_service.connect()

        # Load database catalog from L2 graph for dynamic enrichment + dialect detection
        # Retry a few times since L2 may still be starting up
        import asyncio
        catalog_loaded = False
        for attempt in range(5):
            try:
                databases = await self.l2_client.get_all_databases()
                await self.enrichment_service.load_catalog(databases)
                self.dialect_detector.load_catalog(databases)
                logger.info("database_catalog_loaded", count=len(databases))
                catalog_loaded = True
                break
            except Exception as exc:
                if attempt < 4:
                    logger.info("catalog_load_retry", attempt=attempt + 1, error=str(exc))
                    await asyncio.sleep(3)
                else:
                    logger.warning(
                        "database_catalog_load_failed",
                        error=str(exc),
                        note="Enrichment and dialect detection will use defaults",
                    )

        logger.info("container_started")

    async def shutdown(self) -> None:
        """Gracefully disconnect all infrastructure."""
        logger.info("container_shutting_down")
        await self.enrichment_service.close()
        await self.vector_client.close()
        await self.l4_client.close()
        await self.l2_client.close()
        await self.embedding_client.close()
        await self.cache.close()
        logger.info("container_stopped")


# Module-level singleton
_container: Container | None = None


def set_container(container: Container) -> None:
    global _container
    _container = container


def get_container() -> Container:
    if _container is None:
        raise RuntimeError("Container not initialized — is the app started?")
    return _container
