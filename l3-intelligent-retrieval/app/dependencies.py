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
        )

    async def startup(self) -> None:
        """Connect all infrastructure components."""
        logger.info("container_starting")
        await self.cache.connect()
        await self.embedding_client.connect()
        await self.l2_client.connect()
        await self.l4_client.connect()
        await self.vector_client.connect()
        logger.info("container_started")

    async def shutdown(self) -> None:
        """Gracefully disconnect all infrastructure."""
        logger.info("container_shutting_down")
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
