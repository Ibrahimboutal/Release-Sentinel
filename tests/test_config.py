"""Tests for configuration validation."""

import os
import pytest

from releasesentinel.config import Settings, RunnerMode, get_settings, reset_settings


def test_settings_default_values():
    """Test default configuration values."""
    settings = Settings()
    assert settings.runner == RunnerMode.local
    assert settings.flakiness_threshold == 0.35
    assert settings.risk_smoke_threshold == 25
    assert settings.risk_targeted_threshold == 50
    assert settings.risk_critical_threshold == 75
    assert settings.task_catalog == "ReleaseGateReviews"


def test_settings_runner_validation():
    """Test runner mode validation."""
    settings = Settings(runner="local")
    assert settings.runner == RunnerMode.local

    settings = Settings(runner="uipath")
    assert settings.runner == RunnerMode.uipath

    with pytest.raises(ValueError):
        Settings(runner="invalid_runner")


def test_settings_flakiness_threshold_validation():
    """Test flakiness threshold validation."""
    # Valid values
    Settings(flakiness_threshold=0.0)
    Settings(flakiness_threshold=0.5)
    Settings(flakiness_threshold=1.0)

    # Invalid values
    with pytest.raises(ValueError):
        Settings(flakiness_threshold=-0.1)

    with pytest.raises(ValueError):
        Settings(flakiness_threshold=1.1)


def test_settings_risk_threshold_validation():
    """Test risk threshold validation."""
    # Valid values
    Settings(risk_smoke_threshold=0)
    Settings(risk_smoke_threshold=50)
    Settings(risk_smoke_threshold=100)

    # Invalid values
    with pytest.raises(ValueError):
        Settings(risk_smoke_threshold=-1)

    with pytest.raises(ValueError):
        Settings(risk_smoke_threshold=101)


def test_cloud_integration_validation():
    """Test cloud integration validation."""
    # Local runner - no validation needed
    settings = Settings(runner="local")
    errors = settings.validate_cloud_integration()
    assert len(errors) == 0

    # UiPath runner without credentials
    settings = Settings(runner="uipath")
    errors = settings.validate_cloud_integration()
    assert len(errors) == 2  # Missing URL and token

    # UiPath runner with credentials
    settings = Settings(
        runner="uipath",
        orchestrator_url="https://cloud.uipath.com/org/tenant/orchestrator_",
        orchestrator_token="token"
    )
    errors = settings.validate_cloud_integration()
    assert len(errors) == 0


def test_sync_coverage_validation():
    """Test sync_coverage validation."""
    # Local runner can't sync coverage
    settings = Settings(runner="local", sync_coverage=True)
    errors = settings.validate_cloud_integration()
    assert any("sync_coverage" in e for e in errors)

    # UiPath runner can sync coverage
    settings = Settings(
        runner="uipath",
        orchestrator_url="https://test",
        orchestrator_token="token",
        sync_coverage=True
    )
    errors = settings.validate_cloud_integration()
    assert len(errors) == 0


def test_from_env_defaults():
    """Test loading from environment with defaults."""
    # Clear any existing env vars
    env_vars = {
        "RELEASE_SENTINEL_RUNNER",
        "RELEASE_SENTINEL_ORCHESTRATOR_URL",
        "RELEASE_SENTINEL_ORCHESTRATOR_TOKEN",
        "RELEASE_SENTINEL_FLAKINESS_THRESHOLD",
    }
    for var in env_vars:
        os.environ.pop(var, None)

    reset_settings()
    settings = Settings.from_env()

    assert settings.runner == RunnerMode.local
    assert settings.flakiness_threshold == 0.35
    assert settings.orchestrator_url is None
    assert settings.orchestrator_token is None


def test_from_env_custom_values(monkeypatch):
    """Test loading custom values from environment."""
    monkeypatch.setenv("RELEASE_SENTINEL_RUNNER", "local")
    monkeypatch.setenv("RELEASE_SENTINEL_FLAKINESS_THRESHOLD", "0.5")
    monkeypatch.setenv("RELEASE_SENTINEL_RISK_SMOKE_THRESHOLD", "30")

    settings = Settings.from_env()

    assert settings.runner == RunnerMode.local
    assert settings.flakiness_threshold == 0.5
    assert settings.risk_smoke_threshold == 30


def test_from_env_invalid_values(monkeypatch):
    """Test that invalid environment values raise errors."""
    monkeypatch.setenv("RELEASE_SENTINEL_FLAKINESS_THRESHOLD", "invalid")

    with pytest.raises(ValueError, match="Invalid flakiness threshold"):
        Settings.from_env()

    monkeypatch.setenv("RELEASE_SENTINEL_FLAKINESS_THRESHOLD", "0.5")
    monkeypatch.setenv("RELEASE_SENTINEL_RISK_SMOKE_THRESHOLD", "invalid")

    with pytest.raises(ValueError, match="Invalid risk smoke threshold"):
        Settings.from_env()


def test_global_settings():
    """Test global settings singleton."""
    reset_settings()

    settings1 = get_settings()
    settings2 = get_settings()

    # Should be same instance
    assert settings1 is settings2

    reset_settings()
    settings3 = get_settings()

    # After reset, should be different instance
    assert settings1 is not settings3
