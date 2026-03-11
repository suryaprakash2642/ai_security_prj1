"""Environment-based configuration with optional Vault secret fetching."""

from __future__ import annotations

import os
from enum import Enum
from functools import lru_cache
from typing import Any

import structlog
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

logger = structlog.get_logger(__name__)


class AppEnvironment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """All configuration pulled from env vars. Vault overrides applied at startup."""

    # App
    app_env: AppEnvironment = AppEnvironment.DEVELOPMENT
    app_port: int = 8002
    log_level: str = "INFO"

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_read_user: str = "neo4j"
    neo4j_read_password: str = "changeme"
    neo4j_write_user: str = "neo4j"
    neo4j_write_password: str = "changeme"
    neo4j_database: str = "neo4j"
    neo4j_max_pool_size: int = 50
    neo4j_encrypted: bool = False
    neo4j_ca_cert_path: str = ""  # Path to CA cert for TLS; empty = trust system CAs

    # PostgreSQL audit
    pg_audit_dsn: str = "postgresql+asyncpg://l2_admin:changeme123@localhost:5432/l2_audit"
    pg_audit_ca_cert_path: str = ""
    pg_pool_min: int = 5
    pg_pool_max: int = 20

    # pgvector embeddings
    pg_vector_dsn: str = "postgresql+asyncpg://l2_admin:changeme123@localhost:5432/l2_audit"

    # Redis cache
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_seconds: int = 300

    # Vault
    vault_addr: str = "http://localhost:8200"
    vault_token: str = ""
    vault_secret_path: str = "secret/data/l2-knowledge-graph"
    vault_enabled: bool = False

    # Auth
    service_token_secret: str = Field(
        default="dev-secret-change-in-production-min-32-chars",
        min_length=32,
    )
    allowed_service_ids: str = "l1-identity,l3-retrieval,l4-policy,l6-validation,l8-audit"

    # Embedding
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    embedding_api_key: str = ""
    embedding_api_base: str = "https://api.openai.com/v1"

    # LLM for description generation
    llm_api_key: str = ""
    llm_api_base: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"

    # Rate limiting
    rate_limit_per_minute: int = 600

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    @field_validator("service_token_secret")
    @classmethod
    def validate_token_secret(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("service_token_secret must be at least 32 characters")
        return v

    @property
    def allowed_services(self) -> set[str]:
        return {s.strip() for s in self.allowed_service_ids.split(",") if s.strip()}

    @property
    def is_production(self) -> bool:
        return self.app_env == AppEnvironment.PRODUCTION


def _fetch_vault_secrets(settings: Settings) -> dict[str, Any]:
    """Fetch secrets from HashiCorp Vault. Returns empty dict on failure."""
    if not settings.vault_enabled:
        return {}
    try:
        import hvac

        client = hvac.Client(url=settings.vault_addr, token=settings.vault_token)
        if not client.is_authenticated():
            logger.warning("vault_auth_failed", addr=settings.vault_addr)
            return {}
        resp = client.secrets.kv.v2.read_secret_version(path=settings.vault_secret_path)
        data = resp.get("data", {}).get("data", {})
        logger.info("vault_secrets_loaded", key_count=len(data))
        return data
    except Exception as exc:
        logger.warning("vault_fetch_failed", error=str(exc))
        return {}


def _apply_vault_overrides(settings: Settings) -> Settings:
    """Override settings fields with Vault values if available."""
    secrets = _fetch_vault_secrets(settings)
    if not secrets:
        return settings

    field_map = {
        "neo4j_read_password": "neo4j_read_password",
        "neo4j_write_password": "neo4j_write_password",
        "pg_audit_dsn": "pg_audit_dsn",
        "service_token_secret": "service_token_secret",
        "embedding_api_key": "embedding_api_key",
        "llm_api_key": "llm_api_key",
        "redis_url": "redis_url",
    }
    overrides = {}
    for vault_key, field_name in field_map.items():
        if vault_key in secrets:
            overrides[field_name] = secrets[vault_key]

    if overrides:
        settings = settings.model_copy(update=overrides)
        logger.info("vault_overrides_applied", fields=list(overrides.keys()))
    return settings


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Singleton settings with Vault override."""
    settings = Settings()
    settings = _apply_vault_overrides(settings)

    if settings.is_production and settings.service_token_secret.startswith("dev-"):
        raise RuntimeError("Production requires a proper service_token_secret from Vault")

    return settings
