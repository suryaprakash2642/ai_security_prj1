"""Configuration for L4 Policy Resolution Layer."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment or .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # API
    port: int = 8004
    log_level: str = "INFO"

    # Neo4j
    neo4j_uri: str = "neo4j://localhost:7687"
    neo4j_user: str = "policy_resolver"
    neo4j_password: str = ""  # Set via NEO4J_PASSWORD

    # Security & Signatures
    envelope_ttl_seconds: int = 60
    envelope_signing_key: str = ""  # Set via ENVELOPE_SIGNING_KEY


def get_settings() -> Settings:
    return Settings()
