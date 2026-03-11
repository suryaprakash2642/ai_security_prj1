"""FastAPI application for L6 Multi-Gate Validation Layer."""

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import validate
from app.config import get_settings
from app.models.api import HealthResponse

logger = structlog.get_logger()
settings = get_settings()

app = FastAPI(
    title="Layer 6 — Multi-Gate Validation API",
    description="Zero-Trust NL-to-SQL: deterministic SQL validation through 3 independent gates",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(validate.router, prefix="/api/v1")


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="ok",
        service="l6-multi-gate-validation",
        version="1.0.0",
        dependencies={"neo4j": False},  # Optional — Gate 2 works with cache fallback
    )
