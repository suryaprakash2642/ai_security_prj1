"""L7 Secure Execution Layer — Configuration."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env.local", ".env"), extra="ignore")

    app_env: str = "development"
    service_port: int = 8700
    log_level: str = "INFO"

    # Signing keys
    envelope_signing_key: str = "dev-context-signing-key-32-chars-min"
    service_token_secret: str = "dev-secret-change-in-production-min-32-chars-xx"

    # Resource limits
    query_timeout_seconds: int = 30
    default_max_rows: int = 10_000
    max_query_memory_mb: int = 100
    max_result_size_mb: int = 50
    max_concurrent_per_user: int = 5
    max_concurrent_total: int = 50
    btg_timeout_seconds: int = 60
    btg_max_rows: int = 50_000

    # Circuit breaker
    circuit_breaker_error_threshold: float = 0.5
    circuit_breaker_cooldown_seconds: int = 30

    # Mock execution (dev — no real DB)
    mock_execution: bool = False
    mock_execution_latency_ms: int = 50

    # PostgreSQL
    postgres_host: str = "127.0.0.1"
    postgres_port: int = 15432
    postgres_user: str = "sentinelsql"
    postgres_password: str = "1234"
    postgres_dbname_analytics: str = "apollo_analytics"
    postgres_dbname_financial: str = "apollo_financial"
    postgres_sslmode: str = "disable"

    # MySQL
    mysql_host: str = "127.0.0.1"
    mysql_port: int = 13306
    mysql_user: str = "sentinelsql"
    mysql_password: str = "1234"
    mysql_dbname_his: str = "ApolloHIS"
    mysql_dbname_hr: str = "ApolloHR"
    mysql_ssl: bool = False

    # Optional NL summary
    nl_summary_enabled: bool = False

    # L8 audit endpoint
    l8_audit_url: str = "http://localhost:8800"

    @property
    def is_dev(self) -> bool:
        return self.app_env != "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
