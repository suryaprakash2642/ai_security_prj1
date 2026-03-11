"""Tests for health check service and configuration validation."""

from __future__ import annotations

import pytest

from app.config import Settings
from app.models.enums import SensitivityLevel


class TestConfigValidation:
    def test_valid_settings(self, test_settings):
        assert test_settings.app_env == "development"
        assert len(test_settings.service_token_secret) >= 32

    def test_service_token_secret_minimum_length(self):
        with pytest.raises(Exception):  # ValidationError
            Settings(service_token_secret="short")

    def test_allowed_services_parsing(self, test_settings):
        services = test_settings.allowed_services
        assert "l1-identity" in services
        assert "l3-retrieval" in services
        assert "test-service" in services

    def test_is_production_flag(self):
        settings = Settings(
            app_env="production",
            service_token_secret="prod-secret-must-be-very-long-32-characters-minimum",
        )
        assert settings.is_production is True

    def test_development_not_production(self, test_settings):
        assert test_settings.is_production is False


class TestHealthCheckService:
    """Tests for the HealthCheckService methods."""

    def test_substance_abuse_hard_deny_check_concept(self):
        """Verify the concept: substance_abuse_records must always be HARD DENY."""
        from app.services.classification_engine import ClassificationEngine

        assert ClassificationEngine.is_hard_deny_table("substance_abuse_records") is True
        assert ClassificationEngine.is_hard_deny_table("patients") is False

    def test_sensitivity_level_ordering(self):
        """Verify sensitivity levels are properly ordered for comparisons."""
        assert SensitivityLevel.PUBLIC < SensitivityLevel.INTERNAL
        assert SensitivityLevel.INTERNAL < SensitivityLevel.CONFIDENTIAL
        assert SensitivityLevel.CONFIDENTIAL < SensitivityLevel.RESTRICTED
        assert SensitivityLevel.RESTRICTED < SensitivityLevel.TOP_SECRET
        assert SensitivityLevel.TOP_SECRET == 5


class TestCacheService:
    """Basic cache behavior tests."""

    @pytest.mark.asyncio
    async def test_cache_get_returns_none_by_default(self, mock_cache):
        result = await mock_cache.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_set_is_callable(self, mock_cache):
        await mock_cache.set("key", {"data": "value"})
        mock_cache.set.assert_called_once()
