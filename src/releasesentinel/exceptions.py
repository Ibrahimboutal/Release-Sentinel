"""
Custom exceptions for Release Sentinel.

Provides domain-specific exceptions with clear error messages and remediation steps.
"""


class ReleaseSentinelError(Exception):
    """Base exception for all Release Sentinel errors."""

    def __init__(self, message: str, remediation: str = ""):
        """
        Initialize exception with message and optional remediation.

        Args:
            message: Clear description of what went wrong
            remediation: Suggested fix or troubleshooting steps
        """
        self.message = message
        self.remediation = remediation
        full_message = message
        if remediation:
            full_message = f"{message}\n\nRemediation: {remediation}"
        super().__init__(full_message)


class ConfigurationError(ReleaseSentinelError):
    """Raised when configuration is invalid or incomplete."""

    pass


class ManifestError(ReleaseSentinelError):
    """Raised when change manifest is invalid."""

    pass


class CoverageError(ReleaseSentinelError):
    """Raised when coverage mapping is invalid or unavailable."""

    pass


class TestExecutionError(ReleaseSentinelError):
    """Raised when test execution fails."""

    pass


class TimeoutError(ReleaseSentinelError):
    """Raised when test execution times out."""

    pass


class UiPathError(ReleaseSentinelError):
    """Raised when UiPath integration fails."""

    pass


class ActionCenterError(ReleaseSentinelError):
    """Raised when Action Center task creation fails."""

    pass


class VerdictError(ReleaseSentinelError):
    """Raised when verdict cannot be generated or persisted."""

    pass


class InvalidRunnerError(ConfigurationError):
    """Raised when runner mode is not recognized."""

    def __init__(self, runner: str):
        super().__init__(
            f"Invalid runner mode: '{runner}'",
            remediation="Set RELEASE_SENTINEL_RUNNER to 'local' or 'uipath'"
        )


class MissingCredentialsError(ConfigurationError):
    """Raised when UiPath credentials are missing."""

    def __init__(self, runner: str = "uipath"):
        vars_needed = [
            "RELEASE_SENTINEL_ORCHESTRATOR_URL",
            "RELEASE_SENTINEL_ORCHESTRATOR_TOKEN"
        ]
        super().__init__(
            f"Missing UiPath credentials for '{runner}' runner",
            remediation=f"Set environment variables: {', '.join(vars_needed)}\n"
                       "Get credentials from UiPath Cloud: https://cloud.uipath.com"
        )


class InvalidThresholdError(ConfigurationError):
    """Raised when configuration threshold is out of valid range."""

    def __init__(self, threshold_name: str, value: float, min_val: float, max_val: float):
        super().__init__(
            f"Invalid {threshold_name}: {value}",
            remediation=f"Must be between {min_val} and {max_val}"
        )


class ManifestValidationError(ManifestError):
    """Raised when manifest structure is invalid."""

    def __init__(self, field: str, reason: str):
        super().__init__(
            f"Invalid manifest field '{field}': {reason}",
            remediation=f"See docs/ARTIFACTS.md for manifest schema and examples"
        )


class NoTestsSelectedError(CoverageError):
    """Raised when test selection results in no tests."""

    def __init__(self, risk_score: int, coverage_error: str = ""):
        remediation = (
            "Possible causes:\n"
            "1. Coverage map is empty or invalid\n"
            "2. Risk score doesn't match any test sets\n"
            "3. UiPath Test Manager folder filter is too strict\n"
            "Verify coverage_map.json and risk thresholds in RELEASE_SENTINEL_*"
        )
        if coverage_error:
            remediation = f"{coverage_error}\n\n{remediation}"

        super().__init__(
            f"No tests selected for risk score {risk_score}",
            remediation=remediation
        )


class TestFailureError(TestExecutionError):
    """Raised when tests fail execution."""

    def __init__(self, test_set_key: str, passed: int, failed: int, error_log: str = ""):
        message = f"Test set '{test_set_key}' failed: {passed} passed, {failed} failed"
        remediation = (
            "Review failure triage in release_verdict.json to determine if:\n"
            "1. This is a product bug (fix code and retry)\n"
            "2. This is test fragility (fix test and retry)\n"
            "3. This is a data issue (fix test data and retry)\n"
            "4. This needs human review"
        )
        if error_log:
            remediation = f"Error:\n{error_log}\n\n{remediation}"

        super().__init__(message, remediation)


class TestTimeoutError(TimeoutError):
    """Raised when test execution times out."""

    def __init__(self, test_set_key: str, timeout_seconds: int):
        super().__init__(
            f"Test set '{test_set_key}' timed out after {timeout_seconds} seconds",
            remediation=(
                "Increase timeout: Set RELEASE_SENTINEL_RUNNER_TIMEOUT=<seconds>\n"
                "Or investigate why tests are slow:\n"
                "1. Check UiPath Test Manager execution logs\n"
                "2. Verify network connectivity to test environment\n"
                "3. Review test performance history"
            )
        )


class CliError(ReleaseSentinelError):
    """Raised for command-line interface errors."""

    pass


class InvalidManifestPathError(ManifestError):
    """Raised when manifest file cannot be found."""

    def __init__(self, path: str):
        super().__init__(
            f"Manifest file not found: {path}",
            remediation=(
                "Ensure file exists or set RELEASE_SENTINEL_MANIFEST_PATH\n"
                "Example: python -m releasesentinel run --manifest data/change_manifest.json"
            )
        )


class InvalidCoveragePathError(CoverageError):
    """Raised when coverage file cannot be found."""

    def __init__(self, path: str):
        super().__init__(
            f"Coverage map file not found: {path}",
            remediation=(
                "Ensure file exists or set RELEASE_SENTINEL_COVERAGE_MAP_PATH\n"
                "See docs/ARTIFACTS.md for coverage_map.json structure"
            )
        )


def format_error_for_cli(error: ReleaseSentinelError) -> str:
    """Format error for display in CLI with color codes."""
    lines = [f"❌ Error: {error.message}"]
    if error.remediation:
        lines.append("")
        lines.append("💡 Remediation:")
        for line in error.remediation.split("\n"):
            lines.append(f"   {line}")
    return "\n".join(lines)
