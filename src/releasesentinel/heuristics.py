"""
Heuristic rules management for risk scoring and failure triage.

Loads configurable heuristic weights and patterns from heuristics.yaml
to allow customization for different enterprise environments without
modifying the core Python source code.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None

log = logging.getLogger(__name__)

# Default heuristics (fallback if YAML file not found)
DEFAULT_HEURISTICS = {
    "high_risk_terms": {
        "eligibility": 18,
        "routing": 16,
        "fraud": 18,
        "payment": 16,
        "settlement": 14,
        "policy": 10,
        "human_review": 12,
        "exception": 10,
        "sla": 8,
        "security": 18,
        "compliance": 16,
    },
    "file_risk_rules": {
        "eligibility": 18,
        "routing": 14,
        "workflow": 12,
        "agent": 12,
        "api": 10,
        "tests": -6,
        "docs": -10,
    },
    "tag_risk_rules": {
        "customer_impact": 18,
        "regulated_decision": 18,
        "human_in_loop": 10,
        "new_logic": 12,
        "minor_copy": -10,
        "test_only": -15,
        "simulate_failure": 0,
        "simulate_ambiguous": 0,
        "simulate_timeout": 0,
    },
    "risk_level_thresholds": {
        "critical": 85,
        "high": 65,
        "medium": 38,
        "low": 0,
    },
    "triage_patterns": {
        "environment_issue": {
            "patterns": ["timeout", "robot unavailable"],
            "confidence": 0.86,
            "recommended_fix": "Check robot capacity, Test Cloud execution folder, and retry once capacity is available.",
        },
        "test_fragility": {
            "patterns": ["selector", "element not found"],
            "confidence": 0.78,
            "recommended_fix": "Regenerate the UI descriptor or use Computer Vision fallback before blocking release.",
        },
        "test_data_issue": {
            "patterns": ["fixture", "test data"],
            "confidence": 0.81,
            "recommended_fix": "Refresh the ClaimsPilot test data queue and rerun the affected test case.",
        },
        "eligibility_routing": {
            "patterns": ["expected route", "eligibility", "policy"],
            "confidence": 0.90,
            "recommended_fix": "Review the eligibility/routing rule change and add an explicit approval for affected claim classes.",
        },
    },
}


class HeuristicsConfig:
    """Manages heuristic rules loaded from YAML configuration."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """
        Initialize heuristics configuration.

        Args:
            config: Dictionary of heuristics. If None, loads from file or uses defaults.
        """
        self._config = config or self._load_config()

    @staticmethod
    def _load_config() -> dict[str, Any]:
        """Load heuristics from YAML file or return defaults."""
        config_path = os.getenv("RELEASE_SENTINEL_HEURISTICS_PATH")

        if not config_path:
            # Try to find heuristics.yaml in the same directory as this module
            module_dir = Path(__file__).parent
            config_path = module_dir / "heuristics.yaml"

        if config_path and Path(config_path).exists():
            try:
                if yaml is None:
                    log.warning(
                        "PyYAML not installed; falling back to default heuristics. "
                        "Install PyYAML to load from %s",
                        config_path,
                    )
                    return DEFAULT_HEURISTICS

                with open(config_path) as f:
                    loaded = yaml.safe_load(f)
                    if loaded:
                        log.info("Loaded heuristics from %s", config_path)
                        return loaded
            except Exception as e:
                log.warning("Failed to load heuristics from %s: %s; using defaults", config_path, e)

        return DEFAULT_HEURISTICS

    @property
    def high_risk_terms(self) -> dict[str, int]:
        """Get high-risk terms and their weights."""
        return self._config.get("high_risk_terms", DEFAULT_HEURISTICS["high_risk_terms"])

    @property
    def file_risk_rules(self) -> dict[str, int]:
        """Get file risk rules."""
        return self._config.get("file_risk_rules", DEFAULT_HEURISTICS["file_risk_rules"])

    @property
    def tag_risk_rules(self) -> dict[str, int]:
        """Get tag risk rules."""
        return self._config.get("tag_risk_rules", DEFAULT_HEURISTICS["tag_risk_rules"])

    @property
    def risk_level_thresholds(self) -> dict[str, int]:
        """Get risk level thresholds."""
        return self._config.get("risk_level_thresholds", DEFAULT_HEURISTICS["risk_level_thresholds"])

    @property
    def triage_patterns(self) -> dict[str, dict[str, Any]]:
        """Get triage patterns."""
        return self._config.get("triage_patterns", DEFAULT_HEURISTICS["triage_patterns"])


# Global heuristics instance
_heuristics: HeuristicsConfig | None = None


def get_heuristics() -> HeuristicsConfig:
    """
    Get or create global heuristics configuration instance.

    Returns:
        Global HeuristicsConfig instance
    """
    global _heuristics
    if _heuristics is None:
        _heuristics = HeuristicsConfig()
    return _heuristics


def reset_heuristics() -> None:
    """Reset global heuristics (useful for testing)."""
    global _heuristics
    _heuristics = None
