"""Dependency injection container for the L2 Knowledge Graph layer.

Provides singleton instances of all services, repositories, and infrastructure
components. Wired to FastAPI lifespan for clean startup/shutdown.
"""

from __future__ import annotations

import structlog

from app.config import Settings
from app.repositories.audit_repository import AuditRepository
from app.repositories.graph_read_repo import GraphReadRepository
from app.repositories.graph_write_repo import GraphWriteRepository
from app.repositories.neo4j_manager import Neo4jManager
from app.services.cache import CacheService
from app.services.classification_engine import ClassificationEngine
from app.services.embedding_pipeline import EmbeddingPipeline
from app.services.health_check import HealthCheckService
from app.services.policy_service import PolicyService
from app.services.schema_discovery import SchemaDiscoveryService

logger = structlog.get_logger(__name__)


class Container:
    """Application-level DI container. Initialised once at startup."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

        # Infrastructure
        self.neo4j = Neo4jManager(settings)
        self.audit_repo = AuditRepository(settings)
        self.cache = CacheService(settings)

        # Repositories (depend on neo4j manager)
        self.graph_reader = GraphReadRepository(self.neo4j)
        self.graph_writer = GraphWriteRepository(self.neo4j)

        # Services
        self.policy_service = PolicyService(
            graph_reader=self.graph_reader,
            graph_writer=self.graph_writer,
            audit_repo=self.audit_repo,
            cache=self.cache,
        )
        self.classification_engine = ClassificationEngine(
            graph_reader=self.graph_reader,
            graph_writer=self.graph_writer,
            audit_repo=self.audit_repo,
            cache=self.cache,
        )
        self.schema_discovery = SchemaDiscoveryService(
            graph_writer=self.graph_writer,
            audit_repo=self.audit_repo,
            cache=self.cache,
        )
        self.embedding_pipeline = EmbeddingPipeline(
            settings=settings,
            graph_reader=self.graph_reader,
        )
        self.health_check = HealthCheckService(
            graph_reader=self.graph_reader,
            neo4j=self.neo4j,
            audit_repo=self.audit_repo,
            cache=self.cache,
        )

    async def startup(self) -> None:
        """Connect all infrastructure components."""
        logger.info("container_starting")
        await self.neo4j.connect()
        await self.audit_repo.connect()
        await self.cache.connect()
        await self.embedding_pipeline.connect()
        logger.info("container_started")

    async def shutdown(self) -> None:
        """Gracefully disconnect all infrastructure."""
        logger.info("container_shutting_down")
        await self.embedding_pipeline.close()
        await self.cache.close()
        await self.audit_repo.close()
        await self.neo4j.close()
        logger.info("container_stopped")


# Module-level singleton — set by main.py lifespan
_container: Container | None = None


def set_container(container: Container) -> None:
    global _container
    _container = container


def get_container() -> Container:
    if _container is None:
        raise RuntimeError("Container not initialized — is the app started?")
    return _container
