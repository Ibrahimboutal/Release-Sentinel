from __future__ import annotations

import os
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Protocol
from uuid import uuid4

from .models import TestCaseLog, TestExecution, TestPlan


Scenario = Literal["auto", "happy", "failing", "ambiguous", "timeout"]


class TestRunner(Protocol):
    def run(self, plan: TestPlan, scenario: Scenario = "auto") -> list[TestExecution]:
        ...


class SimulatedTestRunner:
    """Deterministic Test Cloud stand-in for local demos and CI."""

    def run(self, plan: TestPlan, scenario: Scenario = "auto") -> list[TestExecution]:
        scenario = self._resolve_scenario(plan, scenario)
        executions: list[TestExecution] = []
        for test_set in plan.selected_test_sets:
            logs: list[TestCaseLog] = []
            for index, test_case in enumerate(test_set.test_cases):
                logs.append(self._log_for_case(test_case.key, test_case.name, scenario, index))

            status = "timed_out" if any(log.status == "timed_out" for log in logs) else "finished"
            result = "failed" if any(log.result == "failed" for log in logs) else "passed"
            if status == "timed_out":
                result = "inconclusive"

            executions.append(
                TestExecution(
                    execution_id=f"tm-sim-{uuid4().hex[:8]}",
                    test_set_key=test_set.key,
                    test_set_name=test_set.name,
                    source="simulated",
                    status=status,
                    result=result,
                    finished_at=datetime.now(timezone.utc),
                    logs=logs,
                    raw={"scenario": scenario, "note": "Local deterministic stand-in for UiPath Test Manager."},
                )
            )
        return executions

    @staticmethod
    def _resolve_scenario(plan: TestPlan, scenario: Scenario) -> Scenario:
        if scenario != "auto":
            return scenario
        keys = " ".join(reason.lower() for reason in plan.rationale)
        if "critical" in keys:
            return "ambiguous"
        if "high" in keys or "targeted" in keys:
            return "failing"
        return "happy"

    @staticmethod
    def _log_for_case(key: str, name: str, scenario: Scenario, index: int) -> TestCaseLog:
        if scenario == "happy":
            return TestCaseLog(
                test_case_key=key,
                test_case_name=name,
                status="finished",
                result="passed",
                duration_seconds=22 + index * 3,
                message="All assertions passed.",
                assertions=["route is stable", "audit event emitted"],
            )

        if scenario == "timeout" and index == 0:
            return TestCaseLog(
                test_case_key=key,
                test_case_name=name,
                status="timed_out",
                result="inconclusive",
                duration_seconds=900,
                message="Execution timeout: robot unavailable in selected Test Cloud folder.",
            )

        if scenario == "ambiguous" and index == 0:
            return TestCaseLog(
                test_case_key=key,
                test_case_name=name,
                status="finished",
                result="failed",
                duration_seconds=55,
                message="Unexpected API response with no structured assertion message.",
                assertions=["response payload should include routing decision"],
            )

        if scenario == "failing" and ("ELIGIBILITY" in key or index == 1):
            return TestCaseLog(
                test_case_key=key,
                test_case_name=name,
                status="finished",
                result="failed",
                duration_seconds=49,
                message="Eligibility assertion failed: expected route adjuster_review but received straight_through.",
                assertions=["expected route adjuster_review", "human review required for injury claim"],
                attachments=[f"artifacts/screenshots/{key}.png"],
            )

        return TestCaseLog(
            test_case_key=key,
            test_case_name=name,
            status="finished",
            result="passed",
            duration_seconds=26 + index * 4,
            message="All assertions passed.",
            assertions=["claim persisted", "audit event emitted"],
        )


class UiPathTestManagerRunner:
    """Thin CLI adapter for UiPath Test Manager.

    This runner deliberately shells out to `uip tm` so the same implementation
    works with UiPath for Coding Agents and CI. It is not used in automated
    local tests because it requires a logged-in Automation Cloud session.
    """

    def __init__(self, project_key: str, timeout_seconds: int = 1200):
        self.project_key = project_key
        self.timeout_seconds = timeout_seconds

    def run(self, plan: TestPlan, scenario: Scenario = "auto") -> list[TestExecution]:
        executions: list[TestExecution] = []
        for test_set in plan.selected_test_sets:
            launch = self._uip(["tm", "testsets", "run", "--test-set-key", test_set.key])
            execution_id = self._extract_execution_id(launch)
            wait = self._uip(["tm", "wait", "--execution-id", execution_id, "--timeout", str(self.timeout_seconds)], allow_failure=True)
            report = self._uip(["tm", "report", "get", "--execution-id", execution_id, "--project-key", self.project_key], allow_failure=True)
            logs = self._uip(
                [
                    "tm",
                    "executions",
                    "testcaselogs",
                    "list",
                    "--execution-id",
                    execution_id,
                    "--project-key",
                    self.project_key,
                ],
                allow_failure=True,
            )
            executions.append(self._to_execution(test_set.key, test_set.name, execution_id, wait, report, logs))
        return executions

    def _uip(self, args: list[str], allow_failure: bool = False) -> dict:
        completed = subprocess.run(
            ["uip", *args, "--output", "json"],
            capture_output=True,
            text=True,
            check=False,
            shell=os.name == "nt",
        )
        if completed.returncode != 0 and not allow_failure:
            raise RuntimeError(completed.stderr or completed.stdout or f"uip exited {completed.returncode}")
        try:
            return json.loads(completed.stdout)
        except json.JSONDecodeError:
            return {
                "returncode": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            }

    @staticmethod
    def _extract_execution_id(payload: dict) -> str:
        data = payload.get("Data", payload)
        for key in ("ExecutionId", "executionId", "Id", "id"):
            if key in data:
                return str(data[key])
        raise RuntimeError(f"Could not extract ExecutionId from uip output: {payload}")

    @staticmethod
    def _to_execution(test_set_key: str, test_set_name: str, execution_id: str, wait: dict, report: dict, logs_payload: dict) -> TestExecution:
        logs_data = logs_payload.get("Data", [])
        logs = [
            TestCaseLog(
                id=str(item.get("Id", f"log-{uuid4().hex[:8]}")),
                test_case_key=str(item.get("TestCaseKey", item.get("TestCaseId", "unknown"))),
                test_case_name=str(item.get("TestCaseName", "UiPath Test Manager test case")),
                status="finished",
                result=str(item.get("Result", "inconclusive")).lower(),
                message=str(item.get("Message", "")),
            )
            for item in logs_data
        ]
        report_data = report.get("Data", report)
        failed = any(log.result == "failed" for log in logs) or int(report_data.get("Failed", 0) or 0) > 0
        timed_out = wait.get("returncode") == 2
        return TestExecution(
            execution_id=execution_id,
            test_set_key=test_set_key,
            test_set_name=test_set_name,
            source="uipath_test_manager",
            status="timed_out" if timed_out else "finished",
            result="inconclusive" if timed_out else "failed" if failed else "passed",
            finished_at=datetime.now(timezone.utc),
            logs=logs,
            raw={"wait": wait, "report": report, "logs": logs_payload},
        )

