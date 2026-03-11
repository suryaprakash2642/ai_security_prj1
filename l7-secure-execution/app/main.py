"""L7 Secure Execution Layer — FastAPI application entry point."""

from __future__ import annotations

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.execute import router as execute_router
from app.config import get_settings

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(20),
)

logger = structlog.get_logger(__name__)

settings = get_settings()

app = FastAPI(
    title="L7 Secure Execution Layer",
    description=(
        "Executes validated SQL against production databases through "
        "restricted read-only connections with resource limits and result sanitization."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(execute_router)


@app.get("/health", tags=["health"])
async def health() -> dict:
    return {
        "status": "ok",
        "service": "l7-secure-execution",
        "version": "1.0.0",
        "mock_execution": settings.mock_execution,
        "environment": settings.app_env,
    }


@app.on_event("startup")
async def on_startup() -> None:
    logger.info(
        "l7_startup",
        env=settings.app_env,
        port=settings.service_port,
        mock=settings.mock_execution,
    )
