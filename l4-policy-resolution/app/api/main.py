"""FastAPI application initialization for Layer 4."""

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import resolve
from app.api.routes import admin
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


# Structured error handler for validation errors (400)
@app.exception_handler(422)
async def validation_exception_handler(request: Request, exc):
    """Return structured error for invalid requests per spec Section 13.1."""
    return JSONResponse(
        status_code=400,
        content={
            "error": "INVALID_REQUEST",
            "message": "Missing or malformed candidate_table_ids, effective_roles, or security_context",
            "details": str(exc),
        },
    )


# Include routers
app.include_router(resolve.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """Health check with Neo4j connectivity, signing key status per spec Section 13.2."""
    neo4j_ok = False
    try:
        client = get_graph_client()
        # Quick connectivity test
        async with client._driver.session() as session:
            result = await session.run("RETURN 1 AS n")
            record = await result.single()
            neo4j_ok = record is not None and record["n"] == 1
    except Exception as e:
        logger.warning("health_check_neo4j_failed", error=str(e))

    signing_key_ok = bool(settings.context_signing_key and len(settings.context_signing_key) >= 32)

    status = "ok" if (neo4j_ok and signing_key_ok) else "degraded"

    return {
        "status": status,
        "service": "l4-policy-resolution",
        "neo4j": "connected" if neo4j_ok else "disconnected",
        "signing_key": "configured" if signing_key_ok else "missing",
        "envelope_ttl_seconds": settings.envelope_ttl_seconds,
    }
