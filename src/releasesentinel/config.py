"""
Environment configuration validation for Release Sentinel.

This module provides centralized configuration management with validation
for all environment variables and runtime settings.
"""

import os
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class RunnerMode(str, Enum):
    """Supported test runner modes."""

    local = "local"
    uipath = "uipath"


class Settings(BaseModel):
    """Release Sentinel configuration settings."""

    # Runner configuration
    runner: RunnerMode = Field(
        default=RunnerMode.local,
        description="Test execution mode: 'local' or 'uipath'"
    )

    # UiPath cloud integration (optional)
    orchestrator_url: Optional[str] = Field(
        default=None,
        description="UiPath Orchestrator URL (https://cloud.uipath.com/org/tenant/orchestrator_)"
    )

    orchestrator_token: Optional[str] = Field(
        default=None,
        description="UiPath bearer token (do not commit)"
    )

    test_manager_folder_key: Optional[str] = Field(
        default=None,
        description="UiPath Test Manager folder UUID (optional, filters coverage sync)"
    )

    task_catalog: str = Field(
        default="ReleaseGateReviews",
        description="Action Center task catalog name"
    )

    # Scoring thresholds
    flakiness_threshold: float = Field(
        default=0.35,
        ge=0.0,
        le=1.0,
        description="Historical flakiness threshold (0.0-1.0)"
    )

    risk_smoke_threshold: int = Field(
        default=25,
        ge=0,
        le=100,
        description="Risk score for smoke tests only"
    )

    risk_targeted_threshold: int = Field(
        default=50,
        ge=0,
        le=100,
        description="Risk score for targeted regression"
    )

    risk_critical_threshold: int = Field(
        default=75,
        ge=0,
        le=100,
        description="Risk score for full regression"
    )

    # Paths
    manifest_path: str = Field(
        default="data/change_manifest.json",
        description="Path to change manifest JSON"
    )

    verdict_path: str = Field(
        default="artifacts/release_verdict.json",
        description="Path to output verdict JSON"
    )

    coverage_map_path: str = Field(
        default="data/coverage_map.json",
        description="Path to coverage map JSON"
    )

    # Feature flags
    sync_coverage: bool = Field(
        default=False,
        description="Sync coverage from UiPath Test Manager (requires runner=uipath)"
    )

    @field_validator("runner", mode="before")
    @classmethod
    def validate_runner(cls, v):
        """Ensure runner is a valid mode."""
        if isinstance(v, str):
            try:
                return RunnerMode(v.lower())
            except ValueError:
                raise ValueError(f"Invalid runner mode: {v}. Must be 'local' or 'uipath'")
        return v

    @field_validator("flakiness_threshold")
    @classmethod
    def validate_flakiness(cls, v):
        """Ensure flakiness threshold is valid."""
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"Flakiness threshold must be 0.0-1.0, got {v}")
        return v

    @field_validator("risk_smoke_threshold", "risk_targeted_threshold", "risk_critical_threshold")
    @classmethod
    def validate_risk_thresholds(cls, v):
        """Ensure risk thresholds are valid."""
        if not 0 <= v <= 100:
            raise ValueError(f"Risk threshold must be 0-100, got {v}")
        return v

    def validate_cloud_integration(self) -> list[str]:
        """
        Validate cloud integration configuration.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        if self.runner == RunnerMode.uipath:
            if not self.orchestrator_url:
                errors.append("RELEASE_SENTINEL_ORCHESTRATOR_URL required when runner=uipath")
            if not self.orchestrator_token:
                errors.append("RELEASE_SENTINEL_ORCHESTRATOR_TOKEN required when runner=uipath")

        if self.sync_coverage and self.runner != RunnerMode.uipath:
            errors.append("sync_coverage requires runner=uipath")

        return errors

    @classmethod
    def from_env(cls) -> "Settings":
        """
        Load settings from environment variables.

        Raises:
            ValueError: If required variables are missing or invalid
        """
        # Build config dict from environment
        config = {
            "runner": os.getenv("RELEASE_SENTINEL_RUNNER", "local"),
            "orchestrator_url": os.getenv("RELEASE_SENTINEL_ORCHESTRATOR_URL"),
            "orchestrator_token": os.getenv("RELEASE_SENTINEL_ORCHESTRATOR_TOKEN"),
            "test_manager_folder_key": os.getenv("RELEASE_SENTINEL_TEST_MANAGER_FOLDER_KEY"),
            "task_catalog": os.getenv("RELEASE_SENTINEL_TASK_CATALOG", "ReleaseGateReviews"),
            "manifest_path": os.getenv("RELEASE_SENTINEL_MANIFEST_PATH", "data/change_manifest.json"),
            "verdict_path": os.getenv("RELEASE_SENTINEL_VERDICT_PATH", "artifacts/release_verdict.json"),
            "coverage_map_path": os.getenv("RELEASE_SENTINEL_COVERAGE_MAP_PATH", "data/coverage_map.json"),
            "sync_coverage": os.getenv("RELEASE_SENTINEL_SYNC_COVERAGE", "false").lower() == "true",
        }

        # Parse numeric values
        if flair_threshold := os.getenv("RELEASE_SENTINEL_FLAKINESS_THRESHOLD"):
            try:
                config["flakiness_threshold"] = float(flair_threshold)
            except ValueError:
                raise ValueError(f"Invalid flakiness threshold: {flair_threshold}")

        if smoke_threshold := os.getenv("RELEASE_SENTINEL_RISK_SMOKE_THRESHOLD"):
            try:
                config["risk_smoke_threshold"] = int(smoke_threshold)
            except ValueError:
                raise ValueError(f"Invalid risk smoke threshold: {smoke_threshold}")

        if targeted_threshold := os.getenv("RELEASE_SENTINEL_RISK_TARGETED_THRESHOLD"):
            try:
                config["risk_targeted_threshold"] = int(targeted_threshold)
            except ValueError:
                raise ValueError(f"Invalid risk targeted threshold: {targeted_threshold}")

        if critical_threshold := os.getenv("RELEASE_SENTINEL_RISK_CRITICAL_THRESHOLD"):
            try:
                config["risk_critical_threshold"] = int(critical_threshold)
            except ValueError:
                raise ValueError(f"Invalid risk critical threshold: {critical_threshold}")

        # Create settings instance
        settings = cls(**config)

        # Validate cloud integration if needed
        cloud_errors = settings.validate_cloud_integration()
        if cloud_errors:
            raise ValueError("\n".join(cloud_errors))

        return settings


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get or create global settings instance.

    Returns:
        Global Settings instance

    Raises:
        ValueError: If settings validation fails
    """
    global _settings
    if _settings is None:
        _settings = Settings.from_env()
    return _settings


def reset_settings() -> None:
    """Reset global settings (useful for testing)."""
    global _settings
    _settings = None
