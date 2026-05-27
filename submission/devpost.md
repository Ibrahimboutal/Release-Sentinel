# Release Sentinel

## Track

Track 3: UiPath Test Cloud

## Inspiration

Enterprise teams are adopting AI agents and automations faster than their testing processes can keep up. The hard question is not only "did the tests pass?" It is "which tests should run for this change, what did the failures mean, and who should approve release when the answer is uncertain?"

Release Sentinel answers that question with an agentic release gate built around UiPath Test Cloud.

## What It Does

Release Sentinel reviews a change manifest, predicts risk, maps impacted capabilities to Test Cloud test sets, runs the selected checks, triages failures, and produces an auditable release verdict. If the result is ambiguous or low-confidence, it routes the decision to a human reviewer instead of pretending the automation knows everything.

The demo uses a synthetic insurance workflow called ClaimsPilot. A change to claim eligibility and routing is analyzed, matched to targeted Test Cloud regression coverage, executed, triaged, and summarized in a dashboard.

## How We Built It

- Python coded agent/service for analysis, test selection, triage, and release gating.
- UiPath Test Cloud/Test Manager as the test execution and evidence layer.
- UiPath CLI `uip tm` adapter for launching test sets and collecting results.
- API Workflow-friendly endpoints for deterministic agent tools.
- Action Center review pattern for uncertain verdicts.
- Local deterministic runner for repeatable demos and CI.

## UiPath Components Used

- UiPath Automation Cloud
- UiPath Test Cloud/Test Manager
- UiPath CLI and UiPath for Coding Agents
- API Workflows
- Agent Builder or coded agent deployment
- Action Center for human-in-the-loop review

## What Makes It Different

Release Sentinel does not run every test blindly. It uses risk and coverage to choose the right level of validation, then explains the decision with evidence. It can approve low-risk changes quickly, block product bugs, and route ambiguous cases to people.

## Next Steps

- Connect the demo runner to a live UiPath Labs Test Manager project.
- Add Action Center task creation from the verdict payload.
- Expand the coverage map from static JSON to Test Manager metadata.
- Add historical flakiness and change-impact learning.

## Submission Links & Checklist

- **Demo Video**: `[Insert Link to Demo Video (Max 5 mins)]`
- **Presentation Slide Deck**: `[Insert Shared Link to release-sentinel-agenthack.pptx (Ensure public viewing permissions)]`
- **GitHub Repository**: `[Insert Link to Public GitHub Repo]`

### Hackathon Checklist & Recommendations:
- [ ] **Run on the Cloud for Video**: Configure `RELEASE_SENTINEL_RUNNER=uipath` and `RELEASE_SENTINEL_TEST_MANAGER_FOLDER_KEY` in the UiPath Labs environment before recording.
- [ ] **Presentation Deck Sharing**: Upload `release-sentinel-agenthack.pptx` (located at `outputs/manual-release-sentinel/presentations/release-sentinel/output/release-sentinel-agenthack.pptx`) to Google Drive/OneDrive, set permissions to "Anyone with the link can view", and paste the link above.
- [ ] **Product Feedback Prize**: Complete the optional feedback form on Devpost for a chance to win the $1,500 prize.

