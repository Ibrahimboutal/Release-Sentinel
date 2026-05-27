from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from .action_center import ActionCenterClient
from .agents import ChangeImpactAgent, FailureTriageAgent, ReleaseGate, TestPlannerAgent
from .coverage_sync import CoverageSyncClient
from .flakiness import FlakinessEngine
from .io import DEFAULT_VERDICT, load_coverage, save_verdict
from .models import ChangeManifest, CoverageMap, ReleaseVerdict
from .runners import Scenario, SimulatedTestRunner, TestRunner, UiPathTestManagerRunner


RunnerMode = Literal["auto", "simulated", "uipath"]


class ReleaseSentinelPipeline:
    def __init__(
        self,
        coverage: CoverageMap | None = None,
        runner: TestRunner | None = None,
        runner_mode: RunnerMode = "auto",
        sync_coverage: bool = False,
        action_center_client: ActionCenterClient | None = None,
        flakiness_engine: FlakinessEngine | None = None,
    ) -> None:
        self.runner_mode = self._resolve_runner_mode(runner_mode)
        self.coverage = coverage or load_coverage()
        if sync_coverage or self.runner_mode == "uipath":
            self.coverage = CoverageSyncClient(self.coverage.project_key).sync_coverage(self.coverage)
        self.runner = runner or self._build_runner(self.runner_mode)
        self.action_center_client = action_center_client or ActionCenterClient()
        self.flakiness_engine = flakiness_engine
        self.change_impact = ChangeImpactAgent()
        self.test_planner = TestPlannerAgent()
        self.failure_triage = FailureTriageAgent()
        self.release_gate = ReleaseGate()

    @staticmethod
    def _resolve_runner_mode(runner_mode: RunnerMode) -> Literal["simulated", "uipath"]:
        selected_mode = runner_mode
        if selected_mode == "auto":
            selected_mode = os.getenv("RELEASE_SENTINEL_RUNNER", "simulated").strip().lower()
        return "uipath" if selected_mode == "uipath" else "simulated"

    def _build_runner(self, runner_mode: Literal["simulated", "uipath"]) -> TestRunner:
        if runner_mode == "uipath":
            return UiPathTestManagerRunner(project_key=self.coverage.project_key)
        return SimulatedTestRunner()

    def analyze_change(self, manifest: ChangeManifest):
        return self.change_impact.analyze(manifest, self.coverage)

    def select_tests(self, manifest: ChangeManifest, risk=None):
        risk = risk or self.analyze_change(manifest)
        return self.test_planner.select(manifest, risk, self.coverage)

    def triage_results(self, manifest: ChangeManifest, executions, flakiness_map: dict[str, float] | None = None):
        return self.failure_triage.triage(manifest, executions, flakiness_map=flakiness_map)

    def run(
        self,
        manifest: ChangeManifest,
        scenario: Scenario = "auto",
        persist: bool = True,
        output_path: Path = DEFAULT_VERDICT,
    ) -> ReleaseVerdict:
        risk = self.analyze_change(manifest)
        plan = self.select_tests(manifest, risk)
        executions = self.runner.run(plan, scenario=scenario)
        flakiness_map = self._build_flakiness_map(plan)
        triage = self.triage_results(manifest, executions, flakiness_map)
        verdict = self.release_gate.decide(manifest, risk, plan, executions, triage)
        if verdict.human_review_status == "pending":
            verdict.action_center_task_id = self.action_center_client.create_review_task(
                verdict.model_dump(mode="json")
            )
        if persist:
            save_verdict(verdict, output_path)
        return verdict

    def _build_flakiness_map(self, plan) -> dict[str, float]:
        if self.runner_mode != "uipath":
            return {}
        engine = self.flakiness_engine or FlakinessEngine(self.coverage.project_key)
        return engine.build_flakiness_map([test_set.key for test_set in plan.selected_test_sets])
