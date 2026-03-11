"""Layer 2 — Knowledge Graph API

Production-grade FastAPI application serving the Knowledge Graph Layer
of the Zero Trust NL-to-SQL pipeline. This is the metadata brain of the system.

Security boundaries:
- Only authenticated service accounts can access the API
- Read and write accounts are separated
- All queries are parameterized (no raw Cypher from downstream)
- All mutations are audited to PostgreSQL
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.dependencies import Container, set_container
from app.api_audit import APIAccessAuditMiddleware
from app.rate_limit import RateLimitMiddleware
from app.routes import classification_routes, policy_routes, schema_routes
from app.routes import admin_routes

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start up and shut down all infrastructure components."""
    settings = get_settings()
    container = Container(settings)
    set_container(container)
    app.state.container = container

    await container.startup()
    logger.info(
        "l2_knowledge_graph_started",
        env=settings.app_env.value,
        neo4j=settings.neo4j_uri,
    )

    yield

    await container.shutdown()
    logger.info("l2_knowledge_graph_stopped")


def create_app() -> FastAPI:
    """Application factory."""
    settings = get_settings()

    app = FastAPI(
        title="L2 Knowledge Graph API",
        description=(
            "Central security and metadata brain for the Zero Trust NL-to-SQL pipeline. "
            "Stores schema catalog, access policies, data classifications, and role hierarchies. "
            "All access is through parameterized, pre-approved endpoints."
        ),
        version="2.1.0",
        lifespan=lifespan,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
    )

    # CORS — restrictive by default
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"] if not settings.is_production else [],
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
        allow_credentials=False,
    )

    # Rate limiting per service identity
    app.add_middleware(RateLimitMiddleware)

    # API access audit logging to PostgreSQL
    app.add_middleware(APIAccessAuditMiddleware)

    # ── Request logging middleware ─────────────────────────────
    @app.middleware("http")
    async def request_logging(request: Request, call_next):
        start = time.monotonic()
        response = await call_next(request)
        elapsed_ms = (time.monotonic() - start) * 1000
        logger.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            elapsed_ms=round(elapsed_ms, 2),
        )
        return response

    # ── Exception handlers ────────────────────────────────────
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"success": False, "error": exc.detail, "data": None, "meta": {}},
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error("unhandled_exception", path=request.url.path, error=str(exc))
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "Internal server error", "data": None, "meta": {}},
        )

    # ── Routes ────────────────────────────────────────────────
    app.include_router(schema_routes.router)
    app.include_router(policy_routes.router)
    app.include_router(classification_routes.router)
    app.include_router(admin_routes.router)

    # ── Health / readiness ────────────────────────────────────
    @app.get("/health", tags=["system"])
    async def health():
        return {"status": "ok", "service": "l2-knowledge-graph", "version": "2.1.0"}

    @app.get("/ready", tags=["system"])
    async def readiness():
        container = app.state.container
        try:
            alive = await container.neo4j.health_check()
            if not alive:
                return JSONResponse(status_code=503, content={"status": "not_ready", "neo4j": False})
            return {"status": "ready", "neo4j": True}
        except Exception:
            return JSONResponse(status_code=503, content={"status": "not_ready", "neo4j": False})

    return app


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:create_app",
        factory=True,
        host="0.0.0.0",
        port=settings.app_port,
        reload=not settings.is_production,
        log_level=settings.log_level.lower(),
    )
