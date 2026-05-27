# API Reference

Run locally:

```powershell
python -m releasesentinel serve --port 8000
```

Open `http://127.0.0.1:8000/docs` for the generated OpenAPI UI.

## POST /api/analyze-change

Input:

```json
{
  "manifest": {
    "title": "Tighten injury claim routing",
    "requirement": "Claims with injuries must route to adjuster review.",
    "changed_files": ["src/claimspilot/eligibility.py"],
    "affected_capabilities": ["eligibility_routing"],
    "risk_tags": ["customer_impact"]
  }
}
```

Output: `RiskAssessment` with score, level, impacted capabilities, drivers, and confidence.

## POST /api/select-tests

Input: `manifest` plus optional `risk`.

Output: `TestPlan` with selected Test Cloud test sets, rationale, and expected runtime.

## POST /api/triage-results

Input: `manifest` and `executions`.

Input can also include `flakiness_map`, keyed by test case key or test case name.

Output: `TriageReport` with classified failures and human-review flag.

## POST /api/release-verdict

Input:

```json
{
  "manifest": "...",
  "scenario": "failing",
  "persist": true
}
```

Output: full `ReleaseVerdict`.

When the verdict requires human review and Orchestrator credentials are configured, the response includes `action_center_task_id`.

Scenarios are local demo helpers: `auto`, `happy`, `failing`, `ambiguous`, and `timeout`. In the UiPath-connected version, the runner uses real Test Manager executions instead of scenario fixtures.

## POST /api/demo-run

Runs a pre-wired demo scenario, persists `artifacts/release_verdict.json`, appends `artifacts/run_history.jsonl`, and powers the dashboard scenario buttons.

Input:

```json
{
  "scenario": "ambiguous",
  "sync_coverage": false,
  "runner": "auto"
}
```

Optional `manifest_path` may point to a manifest inside this workspace. Scenarios are `happy`, `failing`, `ambiguous`, and `timeout`.

Output: full `ReleaseVerdict`.

## GET /api/latest-verdict

Returns the latest persisted verdict from `artifacts/release_verdict.json`.

## GET /api/run-history

Returns compact recent run records for dashboard history.

Example:

```http
GET /api/run-history?limit=6
```
