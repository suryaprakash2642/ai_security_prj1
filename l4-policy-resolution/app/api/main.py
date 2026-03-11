"""FastAPI application initialization for Layer 4."""

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import resolve
from app.config import get_settings
from app.services.graph_client import get_graph_client

logger = structlog.get_logger()
settings = get_settings()

app = FastAPI(
    title="Layer 4 Policy Resolution API",
    description="Deterministic rules engine for Zero-Trust NL-to-SQL",
    version="1.0.0",
)

# In production this should be restricted
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize singletons on startup."""
    logger.info("Initializing Neo4j GraphClient", uri=settings.neo4j_uri)
    # This instantiates the global graph client
    get_graph_client()


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    logger.info("Shutting down Neo4j GraphClient")
    client = get_graph_client()
    if client:
        await client.close()


# Include routers
app.include_router(resolve.router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "ok", "service": "l4-policy-resolution"}
