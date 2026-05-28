# 🚀 Release Sentinel: Judge's Quick Reference

## What is Release Sentinel?

An **agentic release gate** that reviews code changes, predicts risk, selects the right tests, and produces an auditable release verdict—routing ambiguous cases to humans instead of pretending the automation knows everything.

**Key Innovation**: Uses AI agents for risk analysis, test planning, failure triage, and governance. Integrates with UiPath Test Cloud and Action Center.

## 60-Second Demo

```bash
# 1. Install (1 minute)
git clone https://github.com/Ibrahimboutal/Release-Sentinel
cd Release-Sentinel
python -m pip install -e ".[dev]"

# 2. Run a test scenario (30 seconds)
python -m releasesentinel run --scenario failing --pretty

# 3. See the dashboard (30 seconds)
python -m releasesentinel serve --port 8000
# Open: http://localhost:8000/dashboard
```

## Try Different Scenarios

```bash
# Low-risk change (should approve)
python -m releasesentinel run --scenario happy --pretty

# Failed tests (should block)
python -m releasesentinel run --scenario failing --pretty

# Ambiguous failure (should route to human review)
python -m releasesentinel run --scenario ambiguous --pretty

# Test timeout (should flag as timeout)
python -m releasesentinel run --scenario timeout --pretty
```

## View Output Files

After running any scenario, check these files:

- **`artifacts/release_verdict.json`** - Complete verdict with evidence
  ```bash
  jq '.decision' artifacts/release_verdict.json  # See: approve, block, or needs_review
  jq '.risk | {score, level}' artifacts/release_verdict.json  # See risk scoring
  ```

- **`artifacts/run_history.jsonl`** - Audit trail (one JSON object per line)
  ```bash
  tail -5 artifacts/run_history.jsonl  # See recent runs
  ```

## Architecture in 30 Seconds

```
Change Manifest
     ↓
[ChangeImpactAgent] → Risk Score (0-100)
     ↓
[TestPlannerAgent] → Select Test Sets (Smoke/Targeted/Full)
     ↓
[Test Execution] → Run Tests (Local or UiPath)
     ↓
[FailureTriageAgent] → Classify Failures (Bug/Flake/Data/etc)
     ↓
[ReleaseGate] → Decision (Approve/Block/Review)
     ↓
Dashboard + Action Center
```

## Key Features

| Feature | What It Does |
|---------|-------------|
| **Risk Scoring** | Analyzes change (keywords, files, tags) to predict risk 0-100 |
| **Smart Test Selection** | Chooses smoke/targeted/full regression based on risk |
| **Failure Triage** | Classifies failures as product bug vs test flake vs data issue |
| **Human-in-Loop** | Routes ambiguous cases to Action Center, doesn't guess |
| **Auditable** | Every decision backed by evidence and reasoning |
| **UiPath Integration** | Real Test Manager execution + Test Cloud |
| **Local Mode** | Simulated tests for development/demo |

## Files to Look At

### For Understanding the Code
1. **`src/releasesentinel/agents.py`** - Risk analysis, planning, triage logic
2. **`src/releasesentinel/pipeline.py`** - Orchestration
3. **`src/releasesentinel/models.py`** - Data structures (Pydantic)

### For Understanding Output
1. **`docs/ARTIFACTS.md`** - Complete guide to verdict JSON and output formats
2. **`artifacts/release_verdict.json`** - Sample verdict with all fields explained
3. **`artifacts/dashboard-smoke.png`** - Visual dashboard interface

### For Production
1. **`DEPLOYMENT.md`** - Docker, Kubernetes, AWS, GCP examples
2. **`Dockerfile`** - Container definition
3. **`docker-compose.yml`** - One-command deployment

### For Development
1. **`CONTRIBUTING.md`** - How to extend the system
2. **`src/releasesentinel/config.py`** - Configuration validation
3. **`src/releasesentinel/exceptions.py`** - Error handling with remediation

## Quick Statistics

- **3 Agents**: Risk Analysis, Test Planning, Failure Triage
- **2 Runners**: Local (simulator) + UiPath (real Test Manager)
- **4 Test Scenarios**: Approve, Block, Review, Timeout
- **5 Failure Categories**: Product Bug, Test Fragility, Data Issue, Environment, Needs Review
- **46 Tests**: All passing ✅
- **1000+ Lines**: Core agent logic
- **11,000+ Lines**: Documentation

## Environment Variables

```bash
# Local demo (default, no credentials needed)
export RELEASE_SENTINEL_RUNNER='local'

# Cloud mode (requires UiPath credentials)
export RELEASE_SENTINEL_RUNNER='uipath'
export RELEASE_SENTINEL_ORCHESTRATOR_URL='https://cloud.uipath.com/org/tenant/orchestrator_'
export RELEASE_SENTINEL_ORCHESTRATOR_TOKEN='<your-token>'
```

See `DEPLOYMENT.md` for complete reference.

## API Endpoints

Access interactive docs at: http://localhost:8000/docs

Key endpoints:
- `POST /api/analyze-change` - Risk assessment
- `POST /api/select-tests` - Test selection
- `POST /api/triage-results` - Failure classification
- `POST /api/release-verdict` - Final verdict
- `GET /api/latest-verdict` - Last verdict
- `GET /api/run-history` - Audit trail

## Testing

```bash
# Run all 46 tests
PYTEST_DISABLE_PLUGIN_AUTOLOAD='1' python -m pytest -v

# Run specific test
python -m pytest tests/test_agents.py::test_risk_scoring -v

# With coverage
python -m pytest --cov=src/releasesentinel

# All checks (lint, format, test, security)
make check
```

## Docker Deployment

```bash
# One-command deploy
docker-compose up --build

# Then visit: http://localhost:8000/dashboard
```

## Common Questions

**Q: Does this require UiPath?**
A: No! Local mode works entirely without UiPath. Cloud mode optionally integrates with Test Manager.

**Q: How does risk scoring work?**
A: Analyzes requirement text (keyword matching), changed files (routing/eligibility increase risk), and risk tags (customer_impact, compliance). See `agents.py` for scoring tables.

**Q: What if tests fail?**
A: Failure triage classifies as: product bug (fix code), test flake (fix test), data issue (fix test data), environment issue (fix infrastructure), or needs review (escalate to human).

**Q: Can I customize the scoring?**
A: Yes! Edit risk weights in `src/releasesentinel/agents.py`:
- `HIGH_RISK_TERMS` - Keywords that increase risk
- `FILE_RISK_RULES` - File patterns
- `TAG_RISK_RULES` - Tag multipliers

**Q: How do I integrate with my CI/CD?**
A: Use the FastAPI endpoints or CLI. See `DEPLOYMENT.md` for CI/CD examples.

## Improvements Made for Hackathon

✅ Comprehensive CI/CD pipeline with coverage reporting
✅ Production deployment guide (Docker, Kubernetes, AWS, GCP)
✅ Configuration validation with remediation
✅ Custom exceptions with helpful error messages
✅ 24 new tests (46 total, all passing)
✅ 30,000+ words of documentation
✅ Dashboard screenshot and visual examples
✅ Troubleshooting guides and FAQ
✅ Pre-commit hooks for code quality

See `IMPROVEMENTS.md` for full details.

## Next Steps to Evaluate

1. **Run the demo**: `python -m releasesentinel run --scenario failing --pretty`
2. **See the dashboard**: `python -m releasesentinel serve --port 8000`
3. **Check tests**: `make check` or `PYTEST_DISABLE_PLUGIN_AUTOLOAD='1' python -m pytest -v`
4. **Try Docker**: `docker-compose up --build`
5. **Read documentation**: Start with `DEPLOYMENT.md` and `docs/ARTIFACTS.md`
6. **Explore code**: Review `src/releasesentinel/agents.py` for core logic

## Support

- 📖 **[README.md](README.md)** - Full project overview
- 🚀 **[DEPLOYMENT.md](DEPLOYMENT.md)** - Deployment and troubleshooting
- 📊 **[docs/ARTIFACTS.md](docs/ARTIFACTS.md)** - Output format guide
- 🤝 **[CONTRIBUTING.md](CONTRIBUTING.md)** - Development guide
- ⚙️ **[API Documentation](http://localhost:8000/docs)** - Interactive API docs

---

**Built for UiPath AgentHack Track 3 - Test Cloud**

MIT License | Synthetic data for public evaluation
