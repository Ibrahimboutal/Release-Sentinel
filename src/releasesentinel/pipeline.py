from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from .agents import ChangeImpactAgent, FailureTriageAgent, ReleaseGate, TestPlannerAgent
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
    ) -> None:
        self.coverage = coverage or load_coverage()
        self.runner = runner or self._build_runner(runner_mode)
        self.change_impact = ChangeImpactAgent()
        self.test_planner = TestPlannerAgent()
        self.failure_triage = FailureTriageAgent()
        self.release_gate = ReleaseGate()

    def _build_runner(self, runner_mode: RunnerMode) -> TestRunner:
        selected_mode = runner_mode
        if selected_mode == "auto":
            selected_mode = os.getenv("RELEASE_SENTINEL_RUNNER", "simulated").strip().lower()
        if selected_mode == "uipath":
            folder_key = os.getenv("RELEASE_SENTINEL_TEST_MANAGER_FOLDER_KEY") or self.coverage.default_folder_key
            if not folder_key:
                raise ValueError(
                    "UiPath runner requested but no Test Manager folder key was configured. "
                    "Set RELEASE_SENTINEL_TEST_MANAGER_FOLDER_KEY or coverage.default_folder_key before running in UiPath mode."
                )
            return UiPathTestManagerRunner(project_key=self.coverage.project_key)
        return SimulatedTestRunner()

    def analyze_change(self, manifest: ChangeManifest):
        return self.change_impact.analyze(manifest, self.coverage)

    def select_tests(self, manifest: ChangeManifest, risk=None):
        risk = risk or self.analyze_change(manifest)
        return self.test_planner.select(manifest, risk, self.coverage)

    def triage_results(self, manifest: ChangeManifest, executions):
        return self.failure_triage.triage(manifest, executions)

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
        triage = self.triage_results(manifest, executions)
        verdict = self.release_gate.decide(manifest, risk, plan, executions, triage)
        if persist:
            save_verdict(verdict, output_path)
        return verdict

