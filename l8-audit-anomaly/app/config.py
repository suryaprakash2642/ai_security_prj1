"""L8 Audit & Anomaly Detection — configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    service_port: int = 8800
    envelope_signing_key: str = "dev-context-signing-key-32-chars-min"
    db_path: str = "audit.db"

    # Anomaly detection thresholds
    volume_anomaly_z_score_high: float = 3.0
    volume_anomaly_z_score_critical: float = 5.0
    temporal_working_hours_start: int = 7
    temporal_working_hours_end: int = 19
    validation_block_threshold: int = 3     # blocks/hour → HIGH alert
    btg_duration_threshold_hours: float = 4.0
    sanitization_event_threshold: int = 10  # events/hour per column → HIGH

    # Alert deduplication
    alert_dedup_window_minutes: int = 15

    # Event deduplication
    dedup_window_minutes: int = 15

    model_config = SettingsConfigDict(env_file=("../.env.local", ".env"), extra="ignore")

    @property
    def is_dev(self) -> bool:
        return self.app_env in ("development", "dev", "test")


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
