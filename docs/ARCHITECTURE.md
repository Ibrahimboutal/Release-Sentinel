# Architecture

Release Sentinel is split into four layers.

## 1. Business Surface

`ClaimsPilot` is a synthetic insurance intake workflow. It routes claims to straight-through processing, adjuster review, SIU review, or manual exception based on policy status, amount, injury, missing documents, repeat claims, and fraud score.

The app is intentionally small. Its job is to give the testing agent a believable enterprise process with regulated decisions and human handoffs.

## 2. Agent Layer

- `ChangeImpactAgent` reads the manifest and scores risk from requirement text, changed files, tags, and covered capabilities.
- `TestPlannerAgent` maps risk and impacted capabilities to Test Cloud test sets.
- `FailureTriageAgent` classifies failed logs as product bugs, test fragility, data issues, environment issues, or human-review cases, and downgrades likely product bugs when historical flakiness exceeds the configured threshold.
- `ReleaseGate` creates an approve, block, or needs-review verdict.

## 3. Execution Layer

- `SimulatedTestRunner` creates deterministic local execution evidence for development and video rehearsals.
- `UiPathTestManagerRunner` shells out to `uip tm` so the same pipeline can launch Test Manager runs, wait for terminal state, fetch reports, and inspect test case logs.
- `CoverageSyncClient` merges live Test Manager test sets into local coverage before analysis in UiPath mode.
- `FlakinessEngine` reads recent Test Manager executions to prevent historically flaky tests from blocking releases as product defects.
- `ActionCenterClient` creates real Action Center form tasks for pending human review.

## 4. Experience Layer

- FastAPI endpoints are shaped for API Workflow tools.
- The dashboard summarizes verdict, risk drivers, selected test sets, execution IDs, triage, and next actions.
- JSON artifacts make the run auditable and easy to attach to Devpost or a change-management record.
