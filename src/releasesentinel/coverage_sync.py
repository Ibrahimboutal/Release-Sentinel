"""Dynamic coverage mapping via the UiPath Test Manager CLI.

The local ``coverage_map.json`` stays the source of curated capability
metadata. This adapter fetches live Test Manager test sets with ``uip tm`` and
appends any remote test sets that are missing locally. If ``uip`` is absent or
not logged in, the original map is returned unchanged.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
from typing import Any

from .models import CoverageMap, TestCaseRef, TestSetRef

log = logging.getLogger(__name__)


def _infer_execution_type(name: str) -> str:
    lower = name.lower()
    if "smoke" in lower:
        return "smoke"
    if "full" in lower:
        return "full_regression"
    return "targeted_regression"


class CoverageSyncClient:
    """Thin ``uip tm`` adapter for fetching live Test Manager metadata."""

    def __init__(self, project_key: str, timeout_seconds: int = 30) -> None:
        self.project_key = project_key
        self.timeout_seconds = timeout_seconds

    def sync_coverage(self, coverage: CoverageMap) -> CoverageMap:
        live_sets = self._fetch_live_test_sets()
        if not live_sets:
            return coverage

        existing_keys = {test_set.key for test_set in coverage.test_sets}
        new_sets: list[TestSetRef] = []

        for raw in live_sets:
            key = _first(raw, "TestSetKey", "testSetKey", "Key", "key", "Id", "id")
            if not key or key in existing_keys:
                continue

            name = _first(raw, "Name", "name") or key
            new_sets.append(
                TestSetRef(
                    key=key,
                    name=name,
                    execution_type=_infer_execution_type(name),
                    capabilities=["regression_baseline"],
                    test_cases=self._build_test_cases(raw, key),
                )
            )

        if not new_sets:
            log.info("Coverage sync: no new test sets found in Test Manager.")
            return coverage

        log.info("Coverage sync: added %d new test set(s) from Test Manager.", len(new_sets))
        return CoverageMap(
            project_key=coverage.project_key,
            default_folder_key=coverage.default_folder_key,
            test_sets=[*coverage.test_sets, *new_sets],
            capability_risk_weights=coverage.capability_risk_weights,
        )

    def _fetch_live_test_sets(self) -> list[dict[str, Any]]:
        args = [
            "uip",
            "tm",
            "testsets",
            "list",
            "--project-key",
            self.project_key,
            "--output",
            "json",
        ]
        if folder_key := os.getenv("RELEASE_SENTINEL_TEST_MANAGER_FOLDER_KEY", ""):
            args += ["--folder-key", folder_key]
        return self._run_list(args, "Coverage sync skipped")

    def _build_test_cases(self, raw: dict[str, Any], test_set_key: str) -> list[TestCaseRef]:
        cases_raw = raw.get("TestCases") or raw.get("testCases") or self._fetch_test_cases(test_set_key)
        if not cases_raw:
            return [
                TestCaseRef(
                    key=f"{test_set_key}-TC-001",
                    name="Synced Test Manager test set",
                    capability="regression_baseline",
                    automation="",
                )
            ]

        return [
            TestCaseRef(
                key=_first(case, "TestCaseKey", "testCaseKey", "Key", "key", "Id", "id")
                or f"{test_set_key}-{index + 1}",
                name=_first(case, "Name", "name", "TestCaseName", "testCaseName") or "Test case",
                capability="regression_baseline",
                automation=_first(case, "Automation", "automation") or "",
            )
            for index, case in enumerate(cases_raw)
        ]

    def _fetch_test_cases(self, test_set_key: str) -> list[dict[str, Any]]:
        return self._run_list(
            [
                "uip",
                "tm",
                "testsets",
                "list-testcases",
                "--test-set-key",
                test_set_key,
                "--output",
                "json",
            ],
            f"Coverage sync test-case lookup skipped for {test_set_key}",
            log_level=logging.DEBUG,
        )

    def _run_list(
        self,
        args: list[str],
        failure_message: str,
        log_level: int = logging.WARNING,
    ) -> list[dict[str, Any]]:
        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                check=False,
                timeout=self.timeout_seconds,
                shell=os.name == "nt",
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            log.log(log_level, "%s: %s", failure_message, exc)
            return []

        if result.returncode != 0:
            log.log(log_level, "%s: %s", failure_message, (result.stderr or result.stdout)[:200])
            return []

        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            log.log(log_level, "%s: invalid JSON", failure_message)
            return []

        data = payload if isinstance(payload, list) else payload.get("Data", payload)
        return data if isinstance(data, list) else []


def _first(payload: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        if value is not None and value != "":
            return str(value)
    return None
