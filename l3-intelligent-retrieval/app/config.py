"""Application configuration — YAML base with environment variable overrides.

Environment variables use the L3_ prefix and uppercase keys:
  L3_EMBEDDING_VOYAGE_API_KEY, L3_REDIS_URL, etc.
"""

from __future__ import annotations

import os
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator


_CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


class AppEnv(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


def _load_yaml(filename: str) -> dict[str, Any]:
    """Load a YAML config file from the config/ directory."""
    path = _CONFIG_DIR / filename
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def _env(key: str, default: Any = None) -> Any:
    """Read L3_-prefixed environment variable."""
    return os.environ.get(f"L3_{key}", default)


def _env_first(keys: list[str], default: Any = None) -> Any:
    """Return first non-empty env var from a list of exact names."""
    for k in keys:
        v = os.environ.get(k)
        if v not in (None, ""):
            return v
    return default


class Settings(BaseModel):
    """Validated application settings."""

    model_config = ConfigDict(extra="ignore")

    # Service
    app_env: AppEnv = AppEnv.DEVELOPMENT
    service_name: str = "l3-intelligent-retrieval"
    service_version: str = "0.1.0"
    api_host: str = "0.0.0.0"
    api_port: int = 8300
    rate_limit_per_minute: int = 300

    # Security
    service_token_secret: str = Field(
        default="dev-l3-secret-must-be-at-least-32-characters-long",
        min_length=32,
    )
    allowed_service_ids: str = "l1-identity,l5-generation,admin-console,test-service"
    context_max_age_seconds: int = 3600
    context_signing_key: str = Field(
        default="dev-context-signing-key-32-chars-min",
        min_length=32,
    )

    # Embedding
    embedding_primary_provider: str = "voyage"
    embedding_fallback_provider: str = "openai"
    embedding_voyage_api_key: str = ""
    embedding_voyage_model: str = "voyage-3-large"
    embedding_openai_api_key: str = ""
    embedding_openai_model: str = "text-embedding-3-large"
    # Azure OpenAI (alternative to standard OpenAI)
    embedding_azure_api_key: str = ""
    embedding_azure_endpoint: str = ""  # e.g. https://<resource>.cognitiveservices.azure.com
    embedding_azure_deployment: str = "text-embedding-ada-002"
    embedding_azure_api_version: str = "2024-02-01"
    embedding_dimensions: int = 1536
    embedding_cache_ttl: int = 900
    embedding_cache_max_entries: int = 10000

    # L2 Knowledge Graph
    l2_base_url: str = "http://localhost:8200"
    l2_timeout: int = 5
    l2_service_id: str = "l3-retrieval"
    l2_service_role: str = "pipeline_reader"

    # L4 Policy Resolution
    l4_base_url: str = "http://localhost:8400"
    l4_timeout: int = 5
    l4_service_id: str = "l3-retrieval"
    l4_service_role: str = "policy_resolver"

    # Redis
    redis_url: str = "redis://localhost:6379/1"
    redis_max_connections: int = 20

    # pgvector
    pgvector_dsn: str = "postgresql+asyncpg://l3:l3pass@localhost:5432/l3_vectors"
    pgvector_ssl: bool = False

    # Metrics
    metrics_enabled: bool = True
    metrics_prefix: str = "l3_retrieval"

    @property
    def is_production(self) -> bool:
        return self.app_env == AppEnv.PRODUCTION

    @property
    def allowed_service_id_set(self) -> set[str]:
        return {s.strip() for s in self.allowed_service_ids.split(",") if s.strip()}

    @field_validator("service_token_secret")
    @classmethod
    def validate_secret(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("service_token_secret must be at least 32 characters")
        return v


def load_settings() -> Settings:
    """Build settings from YAML + environment overrides."""
    raw = _load_yaml("settings.yaml")

    # Flatten nested YAML into Settings fields
    flat: dict[str, Any] = {}

    svc = raw.get("service", {})
    flat["app_env"] = _env("APP_ENV", svc.get("env", "development"))
    flat["service_name"] = svc.get("name", "l3-intelligent-retrieval")
    flat["service_version"] = svc.get("version", "0.1.0")

    api = raw.get("api", {})
    flat["api_host"] = _env("API_HOST", api.get("host", "0.0.0.0"))
    flat["api_port"] = int(_env("API_PORT", api.get("port", 8300)))
    flat["rate_limit_per_minute"] = int(
        _env("RATE_LIMIT", api.get("rate_limit_per_minute", 300))
    )

    sec = raw.get("security", {})
    flat["service_token_secret"] = _env(
        "SERVICE_TOKEN_SECRET", sec.get("service_token_secret", flat.get("service_token_secret"))
    )
    flat["allowed_service_ids"] = _env(
        "ALLOWED_SERVICE_IDS", sec.get("allowed_service_ids", "")
    )
    flat["context_max_age_seconds"] = int(
        _env("CONTEXT_MAX_AGE", sec.get("context_max_age_seconds", 3600))
    )
    flat["context_signing_key"] = _env(
        "CONTEXT_SIGNING_KEY", sec.get("context_signing_key", "dev-context-signing-key-32-chars-min")
    )

    emb = raw.get("embedding", {})
    flat["embedding_primary_provider"] = _env("EMBEDDING_PRIMARY", emb.get("primary_provider", "voyage"))
    flat["embedding_fallback_provider"] = _env("EMBEDDING_FALLBACK", emb.get("fallback_provider", "openai"))
    flat["embedding_voyage_api_key"] = _env(
        "EMBEDDING_VOYAGE_API_KEY",
        _env_first(["VOYAGE_API_KEY", "EMBEDDING_VOYAGE_API_KEY"], emb.get("voyage_api_key", "")),
    )
    flat["embedding_voyage_model"] = emb.get("voyage_model", "voyage-3-large")
    flat["embedding_openai_api_key"] = _env(
        "EMBEDDING_OPENAI_API_KEY",
        _env_first(["OPENAI_API_KEY", "EMBEDDING_OPENAI_API_KEY"], emb.get("openai_api_key", "")),
    )
    flat["embedding_openai_model"] = emb.get("openai_model", "text-embedding-3-large")
    flat["embedding_azure_api_key"] = _env(
        "EMBEDDING_AZURE_API_KEY",
        _env_first(["AZURE_AI_API_KEY", "AZURE_OPENAI_API_KEY"], emb.get("azure_api_key", "")),
    )
    flat["embedding_azure_endpoint"] = _env(
        "EMBEDDING_AZURE_ENDPOINT",
        _env_first(["AZURE_AI_ENDPOINT", "AZURE_OPENAI_ENDPOINT"], emb.get("azure_endpoint", "")),
    )
    flat["embedding_azure_deployment"] = _env(
        "EMBEDDING_AZURE_DEPLOYMENT",
        _env_first(["AZURE_EMBEDDING_DEPLOYMENT"], emb.get("azure_deployment", "text-embedding-ada-002")),
    )
    flat["embedding_azure_api_version"] = _env(
        "EMBEDDING_AZURE_API_VERSION",
        _env_first(["AZURE_OPENAI_API_VERSION"], emb.get("azure_api_version", "2024-02-01")),
    )
    flat["embedding_dimensions"] = int(emb.get("dimensions", 1536))
    flat["embedding_cache_ttl"] = int(emb.get("cache_ttl_seconds", 900))
    flat["embedding_cache_max_entries"] = int(emb.get("cache_max_entries", 10000))

    l2 = raw.get("l2_knowledge_graph", {})
    flat["l2_base_url"] = _env("L2_BASE_URL", l2.get("base_url", "http://localhost:8200"))
    flat["l2_timeout"] = int(l2.get("timeout_seconds", 5))
    flat["l2_service_id"] = l2.get("service_id", "l3-retrieval")

    l4 = raw.get("l4_policy_resolution", {})
    flat["l4_base_url"] = _env("L4_BASE_URL", l4.get("base_url", "http://localhost:8400"))
    flat["l4_timeout"] = int(l4.get("timeout_seconds", 5))

    redis = raw.get("redis", {})
    flat["redis_url"] = _env("REDIS_URL", redis.get("url", "redis://localhost:6379/1"))

    pgv = raw.get("pgvector", {})
    flat["pgvector_dsn"] = _env("PGVECTOR_DSN", pgv.get("dsn", ""))
    flat["pgvector_ssl"] = pgv.get("ssl", False)

    return Settings(**{k: v for k, v in flat.items() if v is not None})


def load_ranking_weights() -> dict[str, Any]:
    """Load ranking weights from YAML."""
    return _load_yaml("ranking_weights.yaml")


def load_abbreviations() -> dict[str, str]:
    """Load healthcare abbreviation map from YAML."""
    raw = _load_yaml("abbreviations.yaml")
    return raw.get("abbreviations", {})


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return load_settings()
