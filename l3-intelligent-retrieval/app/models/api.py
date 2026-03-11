"""API request and response models for the L3 retrieval endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import RetrievalErrorCode
from app.models.retrieval import RetrievalResult
from app.models.security import SecurityContext


class RetrievalRequest(BaseModel):
    """POST body for /api/v1/retrieval/resolve."""

    model_config = ConfigDict(extra="forbid")

    question: str = Field(
        ..., min_length=3, max_length=2000,
        description="Natural-language question from the user",
    )
    security_context: SecurityContext
    request_id: str = Field(default="", description="Optional caller-supplied correlation ID")
    max_tables: int = Field(default=10, ge=1, le=25)
    include_ddl: bool = Field(default=True)

    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        stripped = v.strip()
        if len(stripped) < 3:
            raise ValueError("Question must be at least 3 characters")
        return stripped


class ExplainRequest(BaseModel):
    """POST body for /api/v1/retrieval/explain (admin-only)."""

    model_config = ConfigDict(extra="forbid")

    question: str = Field(..., min_length=3, max_length=2000)
    security_context: SecurityContext
    request_id: str = ""


class APIResponse(BaseModel):
    """Standard API envelope response."""

    model_config = ConfigDict()

    success: bool = True
    data: Any = None
    error: str | None = None
    error_code: RetrievalErrorCode | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class RetrievalResponse(BaseModel):
    """Typed response for /resolve — wraps RetrievalResult."""

    model_config = ConfigDict()

    success: bool = True
    data: RetrievalResult | None = None
    error: str | None = None
    error_code: RetrievalErrorCode | None = None


class HealthResponse(BaseModel):
    """Response for /health endpoint."""

    model_config = ConfigDict()

    status: str = "ok"
    service: str = "l3-intelligent-retrieval"
    version: str = "0.1.0"
    dependencies: dict[str, bool] = Field(default_factory=dict)


class StatsResponse(BaseModel):
    """Response for /stats endpoint."""

    model_config = ConfigDict()

    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    avg_latency_ms: float = 0.0
    active_cache_keys: int = 0
    uptime_seconds: float = 0.0
