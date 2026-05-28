"""Environment validation and configuration utilities."""

import os
import sys


class EnvironmentValidator:
    """Validates Release Sentinel environment setup."""

    def __init__(self):
        self.warnings: list[str] = []
        self.errors: list[str] = []

    def validate(self) -> bool:
        """Validate environment. Returns True if no fatal errors."""
        self._check_python_version()
        self._check_runner_config()
        self._check_cloud_credentials()
        self._check_dependencies()

        if self.errors:
            self._print_errors()
            return False

        if self.warnings:
            self._print_warnings()

        return True

    def _check_python_version(self) -> None:
        """Check Python 3.11+."""
        if sys.version_info < (3, 11):
            self.errors.append(
                f"Python 3.11+ required (found {sys.version_info.major}.{sys.version_info.minor})"
            )

    def _check_runner_config(self) -> None:
        """Validate runner configuration."""
        runner = os.getenv("RELEASE_SENTINEL_RUNNER", "local").lower()
        if runner not in ("local", "uipath"):
            self.errors.append(
                f"RELEASE_SENTINEL_RUNNER must be 'local' or 'uipath' (got '{runner}')"
            )

        if runner == "uipath":
            if not os.getenv("RELEASE_SENTINEL_TEST_MANAGER_FOLDER_KEY"):
                self.warnings.append(
                    "RELEASE_SENTINEL_TEST_MANAGER_FOLDER_KEY not set; using default Test Manager scope"
                )

    def _check_cloud_credentials(self) -> None:
        """Validate cloud credentials if enabled."""
        orchestrator_url = os.getenv("RELEASE_SENTINEL_ORCHESTRATOR_URL")
        orchestrator_token = os.getenv("RELEASE_SENTINEL_ORCHESTRATOR_TOKEN")

        if orchestrator_url and not orchestrator_token:
            self.errors.append(
                "RELEASE_SENTINEL_ORCHESTRATOR_URL set but RELEASE_SENTINEL_ORCHESTRATOR_TOKEN missing"
            )

        if not orchestrator_url and orchestrator_token:
            self.warnings.append(
                "RELEASE_SENTINEL_ORCHESTRATOR_TOKEN set but RELEASE_SENTINEL_ORCHESTRATOR_URL missing; Action Center disabled"
            )

    def _check_dependencies(self) -> None:
        """Check required dependencies."""
        try:
            import fastapi  # noqa: F401
            import jinja2  # noqa: F401
            import pydantic  # noqa: F401
        except ImportError as e:
            self.errors.append(f"Missing required dependency: {e.name}")

    def _print_errors(self) -> None:
        """Print errors to stderr."""
        print("\n❌ Environment validation failed:", file=sys.stderr)
        for error in self.errors:
            print(f"   • {error}", file=sys.stderr)
        print()

    def _print_warnings(self) -> None:
        """Print warnings to stderr."""
        print("\n⚠️  Environment warnings:", file=sys.stderr)
        for warning in self.warnings:
            print(f"   • {warning}", file=sys.stderr)
        print()


def validate_environment() -> bool:
    """Entry point for environment validation."""
    return EnvironmentValidator().validate()
