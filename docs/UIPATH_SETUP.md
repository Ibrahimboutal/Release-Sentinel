# UiPath Automation Cloud Setup

This repo runs locally without credentials. For the hackathon submission, run the UiPath-backed path so the demo shows real Test Cloud execution evidence. Keep the local simulator only for developer fallback.

## 1. Prepare CLI and Coding-Agent Skills

Install the current UiPath CLI and sign in:

```powershell
npm install -g @uipath/cli
uip login
uip login status
uip tools install tm
uip skills install --agent codex --local
```

Notes:

- `uip tm` is the Test Manager tool. The UiPath docs call out that `tm` is the command prefix, not `uip test-manager`.
- `uip tm --help` should be treated as the final command reference for the installed preview version.
- Do not commit `uipath.config.json`, personal access tokens, tenant IDs, or folder credentials.

## 2. Create Test Cloud Assets

Create or reuse a Test Manager project named `Release Sentinel` with project key `REL_SENTINEL`.
Capture the real Test Manager folder key from UiPath Labs and set `RELEASE_SENTINEL_TEST_MANAGER_FOLDER_KEY` when you want coverage sync filtered to one Orchestrator folder.

Map the local coverage file to Test Cloud:

| Local key | Test Manager asset | Purpose |
| --- | --- | --- |
| `SMOKE` | Test set | Always-on release gate baseline |
| `ELIGIBILITY_TARGETED` | Test set | Checks routing and human-review behavior |
| `CLAIMS_TARGETED_REGRESSION` | Test set | Medium/high-risk regression slice |
| `FULL_REGRESSION` | Test set | Critical-risk fallback |

Each local `test_cases[].automation` value is the intended Orchestrator package entry point to link in Test Manager.

## 3. Run Test Sets From UiPath

The expected `uip tm` flow is:

```powershell
uip tm testsets run --test-set-key SMOKE --output json
uip tm wait --execution-id <ExecutionId> --timeout 1200 --output json
uip tm report get --execution-id <ExecutionId> --project-key REL_SENTINEL --output json
uip tm executions testcaselogs list --execution-id <ExecutionId> --project-key REL_SENTINEL --output json
```

Important: the run and wait commands can finish successfully even when tests fail. Release Sentinel reads the report and test case logs before producing a verdict.

## 4. Switch From Local Runner to UiPath Runner

The `UiPathTestManagerRunner` in `src/releasesentinel/runners.py` already wraps the CLI flow. Use it from a small deployment wrapper or API Workflow host:

```python
from releasesentinel.io import load_coverage, load_manifest
from releasesentinel.pipeline import ReleaseSentinelPipeline
from releasesentinel.runners import UiPathTestManagerRunner

coverage = load_coverage()
manifest = load_manifest()
runner = UiPathTestManagerRunner(project_key=coverage.project_key)
verdict = ReleaseSentinelPipeline(coverage=coverage, runner=runner).run(manifest)
```

For a direct submission demo, set `RELEASE_SENTINEL_RUNNER=uipath` and run:

```powershell
python -m releasesentinel run --runner uipath --sync-coverage --pretty
```

## 5. Dynamic Coverage Sync

Release Sentinel can merge live Test Manager test sets into the local coverage map before selecting tests:

```powershell
uip tm testsets list --project-key REL_SENTINEL --folder-key <folder-uuid> --output json
uip tm testsets list-testcases --test-set-key REL_SENTINEL:10 --output json
```

Existing local mappings are preserved. New Test Manager sets are appended as `regression_baseline` coverage so they can be selected by future risk rules.

## 6. Historical Flakiness

In UiPath runner mode, Release Sentinel resolves each selected test set key to its Test Manager UUID, then inspects recent execution logs:

```powershell
uip tm testsets list --project-key REL_SENTINEL --output json
uip tm executions list --project-key REL_SENTINEL --test-set-id <test-set-uuid> --top 10 --output json
uip tm executions testcaselogs list --execution-id <execution-uuid> --project-key REL_SENTINEL --output json
```

Set `RELEASE_SENTINEL_FLAKINESS_THRESHOLD` to tune the downgrade threshold. The default is `0.35`.

## 7. Agent Builder Tools

Expose these as API Workflow tools:

| Tool | Endpoint | Input | Output |
| --- | --- | --- | --- |
| Analyze change | `POST /api/analyze-change` | `ChangeManifest` | `RiskAssessment` |
| Select tests | `POST /api/select-tests` | `ChangeManifest`, optional `RiskAssessment` | `TestPlan` |
| Triage results | `POST /api/triage-results` | `ChangeManifest`, `TestExecution[]` | `TriageReport` |
| Publish verdict | `POST /api/release-verdict` | `ChangeManifest`, optional scenario for demo | `ReleaseVerdict` |

## 8. Human-In-The-Loop Review

Create an Action Center form task when:

- Test execution times out.
- Triage confidence is low.
- Failure category is `needs_human_review`.
- Risk is critical even when tests pass.

Configure:

```powershell
$env:RELEASE_SENTINEL_ORCHESTRATOR_URL='https://cloud.uipath.com/org/tenant/orchestrator_'
$env:RELEASE_SENTINEL_ORCHESTRATOR_TOKEN='<bearer-token>'
$env:RELEASE_SENTINEL_TASK_CATALOG='ReleaseGateReviews'
```

The Action Center payload should include:

- Change ID and title.
- Risk score and top drivers.
- Test execution IDs.
- Failure triage category and recommendation.
- Approve, block, or request-more-tests action.
- Returned Action Center task ID, stored as `action_center_task_id` in the verdict.

## 9. Demo Checklist

- Show Codex or another coding agent using the UiPath skills or repo scripts.
- Show Test Manager test sets and a real execution result.
- Show Release Sentinel consuming the Test Manager execution ID.
- Show a final verdict in the dashboard.
- Show where a human reviewer would approve or block in Action Center.

Official docs used while building this plan:

- https://docs.uipath.com/uipath-cli/standalone/latest/user-guide/uip-test-manager
- https://docs.uipath.com/uipath-cli/standalone/latest/user-guide/uip-test-manager-testsets
- https://docs.uipath.com/uipath-cli/standalone/latest/user-guide/uip-test-manager-executions
- https://docs.uipath.com/uipath-cli/standalone/latest/user-guide/coding-agents
