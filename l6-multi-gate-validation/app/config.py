"""Configuration for L6 Multi-Gate Validation Layer."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_port: int = 8600
    log_level: str = "INFO"
    app_env: str = "development"

    # Neo4j for Gate 2 classification lookups
    neo4j_uri: str = "neo4j://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""  # Set via NEO4J_PASSWORD

    # Security
    envelope_signing_key: str = ""  # Set via ENVELOPE_SIGNING_KEY
    service_token_secret: str = ""  # Set via SERVICE_TOKEN_SECRET

    # Validation config
    max_subquery_depth: int = 3
    max_columns_in_select: int = 50
    default_max_rows: int = 1000
    gate_timeout_ms: int = 50
    classification_cache_ttl: int = 600
    enable_parallel_gates: bool = True
    enable_full_sql_logging: bool = False


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
