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

Scenarios are local demo helpers: `auto`, `happy`, `failing`, `ambiguous`, and `timeout`. In the UiPath-connected version, the runner uses real Test Manager executions instead of scenario fixtures.

