"""Tests for custom exceptions."""

from releasesentinel.exceptions import (
    ReleaseSentinelError,
    ConfigurationError,
    ManifestError,
    InvalidRunnerError,
    MissingCredentialsError,
    InvalidThresholdError,
    NoTestsSelectedError,
    TestFailureError,
    TestTimeoutError,
    InvalidManifestPathError,
    format_error_for_cli,
)


def test_base_exception_with_message():
    """Test base exception with message."""
    error = ReleaseSentinelError("Something went wrong")
    assert error.message == "Something went wrong"
    assert error.remediation == ""
    assert str(error) == "Something went wrong"


def test_base_exception_with_remediation():
    """Test base exception with message and remediation."""
    error = ReleaseSentinelError(
        "Something went wrong",
        remediation="Try this fix"
    )
    assert error.message == "Something went wrong"
    assert error.remediation == "Try this fix"
    assert "Try this fix" in str(error)


def test_configuration_error():
    """Test configuration error."""
    error = ConfigurationError("Invalid config")
    assert isinstance(error, ReleaseSentinelError)
    assert error.message == "Invalid config"


def test_invalid_runner_error():
    """Test invalid runner error with auto-generated remediation."""
    error = InvalidRunnerError("invalid_mode")
    assert "invalid_mode" in error.message
    assert "local" in error.remediation
    assert "uipath" in error.remediation


def test_missing_credentials_error():
    """Test missing credentials error."""
    error = MissingCredentialsError("uipath")
    assert "uipath" in error.message
    assert "ORCHESTRATOR_URL" in error.remediation
    assert "ORCHESTRATOR_TOKEN" in error.remediation


def test_invalid_threshold_error():
    """Test invalid threshold error."""
    error = InvalidThresholdError("flakiness", 1.5, 0.0, 1.0)
    assert "flakiness" in error.message
    assert "1.5" in error.message
    assert "0.0" in error.remediation
    assert "1.0" in error.remediation


def test_no_tests_selected_error():
    """Test no tests selected error."""
    error = NoTestsSelectedError(75, "Coverage map is empty")
    assert "75" in error.message
    assert "Coverage map is empty" in error.remediation


def test_test_failure_error():
    """Test test failure error."""
    error = TestFailureError("SMOKE", 10, 2, "Assert failed in test")
    assert "SMOKE" in error.message
    assert "10" in error.message
    assert "2" in error.message
    assert "Assert failed in test" in error.remediation


def test_test_timeout_error():
    """Test test timeout error."""
    error = TestTimeoutError("FULL_REGRESSION", 3600)
    assert "FULL_REGRESSION" in error.message
    assert "3600" in error.message
    assert "RELEASE_SENTINEL_RUNNER_TIMEOUT" in error.remediation


def test_invalid_manifest_path_error():
    """Test invalid manifest path error."""
    error = InvalidManifestPathError("/nonexistent/path.json")
    assert "/nonexistent/path.json" in error.message
    assert "manifest" in error.remediation.lower()


def test_format_error_for_cli_no_remediation():
    """Test CLI formatting without remediation."""
    error = ReleaseSentinelError("Test error")
    output = format_error_for_cli(error)
    assert "❌ Error: Test error" in output
    assert "💡 Remediation:" not in output


def test_format_error_for_cli_with_remediation():
    """Test CLI formatting with remediation."""
    error = ReleaseSentinelError("Test error", remediation="Fix this")
    output = format_error_for_cli(error)
    assert "❌ Error: Test error" in output
    assert "💡 Remediation:" in output
    assert "Fix this" in output


def test_format_error_for_cli_multiline_remediation():
    """Test CLI formatting with multiline remediation."""
    remediation = "Step 1: Do this\nStep 2: Do that\nStep 3: Check result"
    error = ReleaseSentinelError("Test error", remediation=remediation)
    output = format_error_for_cli(error)
    assert "Step 1: Do this" in output
    assert "Step 2: Do that" in output
    assert "Step 3: Check result" in output
    # Verify indentation
    lines = output.split("\n")
    remediation_lines = [l for l in lines if "Step" in l]
    for line in remediation_lines:
        assert line.startswith("   ")  # Indented


def test_error_inheritance():
    """Test that custom errors inherit from base correctly."""
    error = InvalidRunnerError("bad")
    assert isinstance(error, ConfigurationError)
    assert isinstance(error, ReleaseSentinelError)
    assert isinstance(error, Exception)
