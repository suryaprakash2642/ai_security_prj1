"""FastAPI application for L5 Secure Generation Layer."""

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import generate
from app.config import get_settings
from app.models.api import HealthResponse

logger = structlog.get_logger()
settings = get_settings()

app = FastAPI(
    title="Layer 5 — Secure Generation API",
    description="Zero-Trust NL-to-SQL: LLM query generation under policy constraints",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(generate.router, prefix="/api/v1")


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="ok",
        service="l5-secure-generation",
        version="1.0.0",
        llm_provider=settings.llm_provider,
    )
