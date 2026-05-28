# Contributing to Release Sentinel

Thanks for your interest in Release Sentinel! This guide explains how to set up development environment, run tests, and contribute improvements.

## Development Setup

### 1. Clone and Install

```bash
git clone https://github.com/Ibrahimboutal/Release-Sentinel.git
cd Release-Sentinel
make install
```

### 2. Verify Installation

```bash
make check  # Run tests, linting, and security checks
```

## Running Tests

```bash
# Run all tests
make test

# Run specific test file
python -m pytest tests/test_agents.py -v

# Run with coverage
python -m pytest --cov=src
```

## Code Quality

### Linting & Formatting

```bash
# Check code style
make lint

# Auto-format code
make format
```

We use:
- **black** for code formatting
- **ruff** for linting
- **bandit** for security checks

### Pre-commit Hooks (Optional)

```bash
pip install pre-commit
pre-commit install
```

## Project Structure

```
Release-Sentinel/
├── src/releasesentinel/
│   ├── agents.py          # Risk, planning, triage, release gate
│   ├── runners.py         # Local simulator + UiPath runner
│   ├── action_center.py   # Action Center integration
│   ├── pipeline.py        # Orchestration
│   ├── api.py             # FastAPI endpoints
│   ├── cli.py             # Command-line interface
│   └── models.py          # Pydantic data models
├── tests/                 # pytest test suite
├── web/                   # Dashboard HTML/CSS/JS
├── data/                  # Sample manifests and coverage maps
└── docs/                  # Architecture, setup, API docs
```

## Making Changes

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Your Changes

Keep commits focused and descriptive:

```bash
git add src/releasesentinel/your_file.py
git commit -m "Add feature: clear description of change"
```

### 3. Run Tests

```bash
make check
```

All tests must pass before submitting a PR.

### 4. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Then open a pull request with:
- Clear title describing the change
- Summary of what was added/fixed
- Any breaking changes or new dependencies

## Testing Guidelines

- Add tests for new functionality in `tests/`
- Use descriptive test names: `test_<function>_<scenario>`
- Mock external dependencies (UiPath CLI, Test Manager)
- Aim for >80% code coverage

Example test:

```python
def test_change_impact_agent_high_risk_routing():
    """Verify agent raises risk score for routing changes."""
    manifest = ChangeManifest(
        title="Update routing logic",
        changed_files=["src/routing.py"],
        risk_tags=["customer_impact"]
    )
    agent = ChangeImpactAgent()
    risk = agent.analyze(manifest, coverage=CoverageMap())
    assert risk.score > 50
```

## Documentation

- Update README.md for user-facing changes
- Update ARCHITECTURE.md for system changes
- Add docstrings to new functions/classes
- Reference issues/PRs in commit messages when relevant

## Common Tasks

| Task | Command |
|------|---------|
| Install dependencies | `make install` |
| Run tests | `make test` |
| Check all quality gates | `make check` |
| Format code | `make format` |
| Build Docker image | `make docker-build` |
| Start dev server | `make serve` |
| View all tasks | `make help` |

## Architecture Overview

Release Sentinel follows a 4-layer design:

1. **Business Layer**: ClaimsPilot workflow
2. **Agent Layer**: Risk analysis, test planning, triage, release gating
3. **Execution Layer**: Local simulator, UiPath runner, coverage sync, flakiness scoring
4. **Experience Layer**: FastAPI, dashboard, CLI

New features typically belong in the Agent or Execution layers. See [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) for details.

## Getting Help

- Check [DEPLOYMENT.md](./DEPLOYMENT.md) for setup issues
- Review [API.md](./API.md) for endpoint details
- Open an issue for questions or bugs

## License

Release Sentinel is MIT licensed. By contributing, you agree to license your changes under MIT.

---

Thanks for contributing to Release Sentinel! 🚀
