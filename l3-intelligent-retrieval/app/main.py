"""Layer 3 — Intelligent Retrieval API

Production-grade FastAPI application serving the Intelligent Retrieval Layer
of the Zero Trust NL-to-SQL pipeline.

Security boundaries:
- Every request requires valid inter-service auth token
- Every retrieval requires valid signed SecurityContext from L1
- Zero-trust: LLM never sees full schema, only policy-intersected subset
- Fail-secure: any dependency failure returns structured error
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.dependencies import Container, set_container
from app.routes import retrieval_routes

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
        "l3_retrieval_started",
        env=settings.app_env.value,
        l2=settings.l2_base_url,
        l4=settings.l4_base_url,
    )

    yield

    await container.shutdown()
    logger.info("l3_retrieval_stopped")


def create_app() -> FastAPI:
    """Factory function to create the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="L3 Intelligent Retrieval Layer",
        description=(
            "Zero-trust schema retrieval service for the NL-to-SQL pipeline. "
            "Returns policy-filtered, token-budgeted schema packages for LLM consumption."
        ),
        version=settings.service_version,
        lifespan=lifespan,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
    )

    # CORS — restrictive
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"] if not settings.is_production else [],
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
        allow_credentials=False,
    )

    # Request logging middleware
    @app.middleware("http")
    async def request_logging(request: Request, call_next):
        start = time.monotonic()
        response = await call_next(request)
        elapsed_ms = (time.monotonic() - start) * 1000
        if request.url.path not in ("/health", "/api/v1/retrieval/health"):
            logger.info(
                "http_request",
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                latency_ms=round(elapsed_ms, 2),
            )
        return response

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_error_handler(request: Request, exc: Exception):
        logger.error("unhandled_error", error=str(exc), path=request.url.path)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Internal server error",
                "error_code": "INTERNAL_ERROR",
            },
        )

    # Routes
    app.include_router(retrieval_routes.router)

    # System endpoints (no auth required)
    @app.get("/health", tags=["system"])
    async def root_health():
        return {"status": "ok", "service": "l3-intelligent-retrieval"}

    # Dev-only: generate a service token for the frontend dashboard
    @app.get("/mock/service-token", tags=["dev"])
    async def mock_service_token():
        if settings.is_production:
            from fastapi import HTTPException as _HTTPException
            raise _HTTPException(status_code=403, detail="Not available in production")
        from app.auth import create_service_token
        token = create_service_token(
            service_id="admin-console",
            role="pipeline_reader",
            secret=settings.service_token_secret,
        )
        return {"token": token}

    return app


# For uvicorn direct run
app = create_app()
