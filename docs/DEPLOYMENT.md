# Deployment Guide

Release Sentinel can be deployed locally, via Docker, or to cloud infrastructure. This guide covers setup and common deployment scenarios.

## Prerequisites

- Python 3.11+ (for local/development)
- Docker & Docker Compose (for containerized deployment)
- UiPath CLI and Orchestrator credentials (for cloud Test Manager integration)

## Local Development

### Quick Start

```bash
# Install dependencies
make install

# Run tests
make test

# Start development server
make serve
```

The dashboard will be available at `http://127.0.0.1:8000/dashboard`.

### Environment Variables

| Variable | Default | Required | Notes |
|----------|---------|----------|-------|
| `RELEASE_SENTINEL_RUNNER` | `local` | No | Use `uipath` for cloud execution |
| `RELEASE_SENTINEL_TEST_MANAGER_FOLDER_KEY` | - | No | Folder UUID from UiPath Labs |
| `RELEASE_SENTINEL_ORCHESTRATOR_URL` | - | No | Required for Action Center integration |
| `RELEASE_SENTINEL_ORCHESTRATOR_TOKEN` | - | No | ****** for Orchestrator |
| `RELEASE_SENTINEL_TASK_CATALOG` | `ReleaseGateReviews` | No | Action Center task catalog name |
| `RELEASE_SENTINEL_FLAKINESS_THRESHOLD` | `0.35` | No | Historical flakiness tolerance (0-1) |

## Docker Deployment

### Build and Run

```bash
# Build the Docker image
make docker-build

# Start the container
make docker-up

# Stop the container
make docker-down
```

The dashboard will be available at `http://localhost:8000/dashboard`.

### Custom Docker Configuration

Override environment variables in `docker-compose.yml`:

```yaml
environment:
  - RELEASE_SENTINEL_RUNNER=uipath
  - RELEASE_SENTINEL_TEST_MANAGER_FOLDER_KEY=<your-folder-key>
```

## Cloud Deployment (UiPath)

### 1. Configure UiPath CLI

```powershell
npm install -g @uipath/cli
uip login
uip tools install tm
uip skills install --agent codex --local
```

### 2. Set Environment Variables

```powershell
$env:RELEASE_SENTINEL_RUNNER='uipath'
$env:RELEASE_SENTINEL_TEST_MANAGER_FOLDER_KEY='<folder-uuid>'
$env:RELEASE_SENTINEL_ORCHESTRATOR_URL='https://cloud.uipath.com/org/tenant/orchestrator_'
$env:RELEASE_SENTINEL_ORCHESTRATOR_TOKEN='<bearer-token>'
```

### 3. Run with UiPath Backend

```bash
python -m releasesentinel run --runner uipath --sync-coverage --pretty
```

## API Deployment

Release Sentinel exposes FastAPI endpoints suitable for API Workflows or external automation:

```bash
python -m releasesentinel serve --host 0.0.0.0 --port 8000
```

Available endpoints:
- `POST /api/analyze-change` - Risk analysis
- `POST /api/select-tests` - Test selection
- `POST /api/triage-results` - Failure triage
- `POST /api/release-verdict` - Release decision
- `GET /api/latest-verdict` - Retrieve latest verdict
- `GET /api/run-history` - Audit trail

See `/docs` for interactive OpenAPI documentation.

## Monitoring & Logs

### Local Execution

Run history is stored in `artifacts/run_history.jsonl` (one verdict per line):

```bash
cat artifacts/run_history.jsonl | python -m json.tool
```

### Docker Logs

```bash
docker-compose logs -f release-sentinel
```

### Verdict Inspection

```bash
cat artifacts/release_verdict.json | python -m json.tool
```

## Troubleshooting

### "RELEASE_SENTINEL_TEST_MANAGER_FOLDER_KEY not set"

**Issue**: When using UiPath runner without folder key.

**Solution**: Set the environment variable or accept the warning (uses default Orchestrator scope).

### "UiPath CLI not found"

**Issue**: `uip tm` commands fail.

**Solution**: Install globally:
```bash
npm install -g @uipath/cli
```

### "No release verdict has been generated yet"

**Issue**: Dashboard shows 404 on `/api/latest-verdict`.

**Solution**: Run a test scenario first:
```bash
python -m releasesentinel run --scenario happy --pretty
```

### Tests fail with "No module named pytest"

**Issue**: Dev dependencies not installed.

**Solution**:
```bash
python -m pip install -e ".[dev]"
```

### Docker container exits immediately

**Issue**: Application crashes on startup.

**Solution**: Check logs and environment:
```bash
docker-compose logs release-sentinel
docker-compose up -e RELEASE_SENTINEL_RUNNER=local release-sentinel
```

## Performance Tuning

### Flakiness Threshold

Lower values (0.1-0.3) are stricter about failing flaky tests; higher values (0.5-0.8) tolerate more historical failures:

```bash
export RELEASE_SENTINEL_FLAKINESS_THRESHOLD='0.25'
python -m releasesentinel run --scenario failing
```

### Test Execution Timeout

Increase timeout for slow Test Manager execution (in seconds):

```bash
python -m releasesentinel run --timeout 1800
```

## Next Steps

- Read [ARCHITECTURE.md](./ARCHITECTURE.md) for system design
- Review [API.md](./API.md) for endpoint contracts
- See [UIPATH_SETUP.md](./UIPATH_SETUP.md) for cloud integration details
