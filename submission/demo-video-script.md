# Five-Minute Demo Script

## 0:00-0:30 Problem

"AI agents and automations can change enterprise workflows quickly, but testing needs to know which tests matter, why failures happened, and when a human must approve release. Release Sentinel is an agentic release gate built on UiPath Test Cloud."

Show the repo and ClaimsPilot scenario.

## 0:30-1:15 Change Ingest

Show `data/change_manifest.json`.

Narration:

"This change updates eligibility and routing for injury claims. Release Sentinel reads the requirement, changed files, affected capabilities, and risk tags."

Run:

```powershell
python -m releasesentinel run --scenario failing --pretty
```

## 1:15-2:10 Agent Planning

Show risk score and drivers.

Narration:

"The ChangeImpactAgent scores this as high or critical risk because it touches regulated routing, customer impact, eligibility logic, and human review."

Show selected test sets.

Narration:

"The TestPlannerAgent chooses smoke tests, eligibility targeted checks, and targeted regression. It avoids full regression unless risk or failures justify it."

## 2:10-3:10 Test Cloud Evidence

Show UiPath Test Manager project/test sets and the live execution IDs from UiPath Labs.

Narration:

"These execution IDs come from UiPath Test Manager using `uip tm testsets run`, `uip tm wait`, and `uip tm report get`."

## 3:10-4:10 Failure Triage

Show the failing eligibility test and triage output.

Narration:

"The FailureTriageAgent classifies this as a likely product bug, not a flaky UI selector or stale test data, because the assertion says the claim routed straight-through when adjuster review was expected."

Run ambiguous scenario if showing human review:

```powershell
python -m releasesentinel run --manifest data/fixtures/ambiguous_manifest.json --scenario ambiguous --pretty
```

## 4:10-4:45 Dashboard Verdict

Start:

```powershell
python -m releasesentinel serve --port 8000
```

Show `http://127.0.0.1:8000/dashboard`.

Narration:

"The release verdict is auditable: risk drivers, selected test sets, execution evidence, triage, and next action. Ambiguous cases go to Action Center instead of being silently approved."

## 4:45-5:00 Close

"Release Sentinel helps enterprise teams move faster without surrendering control: agents decide what to test, UiPath Test Cloud executes and stores evidence, and humans stay in charge at the release boundary."

