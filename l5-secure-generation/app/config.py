"""Configuration for L5 Secure Generation Layer."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # API
    app_port: int = 8500
    log_level: str = "INFO"
    app_env: str = "development"

    # LLM Provider
    llm_provider: str = "azure_openai"

    # Azure OpenAI
    azure_ai_endpoint: str = ""
    azure_ai_api_key: str = ""
    azure_openai_deployment: str = "gpt-4.1"
    azure_openai_fallback_deployment: str = "gpt-4.1-mini"
    azure_openai_api_version: str = "2024-12-01-preview"

    # Anthropic (alternative provider)
    anthropic_api_key: str = ""
    anthropic_primary_model: str = "claude-sonnet-4-6"
    anthropic_fallback_model: str = "claude-haiku-4-5-20251001"

    # Security
    envelope_signing_key: str = "dev-context-signing-key-32-chars-min"
    service_token_secret: str = "dev-secret-change-in-production-min-32-chars-xx"
    allowed_service_ids: str = "l3-retrieval,l4-policy,l6-validation,l8-audit,orchestrator"

    # Generation Config
    default_max_rows: int = 1000
    max_prompt_tokens: int = 10000
    response_reserve_tokens: int = 2048
    injection_risk_threshold: float = 0.7
    llm_timeout_seconds: int = 15
    llm_max_retries: int = 2

    @property
    def allowed_service_ids_list(self) -> list[str]:
        return [s.strip() for s in self.allowed_service_ids.split(",")]


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
