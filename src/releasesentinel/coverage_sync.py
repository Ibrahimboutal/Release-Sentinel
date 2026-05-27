"""Dynamic coverage mapping via UiPath Test Manager CLI.

Shells out to ``uip tm testsets list`` to fetch live test sets from an
authenticated Test Manager session and merges them into the static
CoverageMap loaded from JSON.  Falls back silently to the static map when
``uip`` is not installed or no session is active, so local development
continues to work without cloud access.

Environment variables
---------------------
RELEASE_SENTINEL_RUNNER              Set to ``uipath`` to enable live sync.
RELEASE_SENTINEL_TEST_MANAGER_FOLDER_KEY  Optional folder-key filter.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess

from .models import CoverageMap, TestCaseRef, TestSetRef

log = logging.getLogger(__name__)

# Execution types used in Test Manager (mapped from name heuristics)
_EXEC_TYPE_MAP = {
    "smoke": "smoke",
    "full": "full_regression",
    "regression": "targeted_regression",
}


def _infer_execution_type(name: str) -> str:
    lower = name.lower()
    for keyword, exec_type in _EXEC_TYPE_MAP.items():
        if keyword in lower:
            return exec_type
    return "targeted_regression"


class CoverageSyncClient:
    """Thin ``uip tm`` adapter for fetching live test-set metadata."""

    def __init__(self, project_key: str, timeout_seconds: int = 30) -> None:
        self.project_key = project_key
        self.timeout_seconds = timeout_seconds

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def sync_coverage(self, coverage: CoverageMap) -> CoverageMap:
        """Return an updated CoverageMap that includes live Test Manager test sets.

        Existing local entries are preserved as-is so that hand-crafted
        capability mappings and risk weights are never overwritten by the
        remote data.  New test sets discovered in Test Manager are appended
        with inferred metadata.
        """
        live_sets = self._fetch_live_test_sets()
        if not live_sets:
            return coverage  # fallback: return unchanged map

        existing_keys = {ts.key for ts in coverage.test_sets}
        new_sets: list[TestSetRef] = []

        for raw in live_sets:
            key = str(raw.get("Key") or raw.get("key") or raw.get("Id") or "")
            if not key or key in existing_keys:
                continue  # already mapped locally

            name = str(raw.get("Name") or raw.get("name") or key)
            test_cases = self._build_test_cases(raw, key)
            new_sets.append(
                TestSetRef(
                    key=key,
                    name=name,
                    execution_type=_infer_execution_type(name),
                    capabilities=["regression_baseline"],
                    test_cases=test_cases,
                )
            )

        if not new_sets:
            log.info("Coverage sync: no new test sets found in Test Manager.")
            return coverage

        log.info("Coverage sync: added %d new test set(s) from Test Manager.", len(new_sets))
        merged = CoverageMap(
            project_key=coverage.project_key,
            default_folder_key=coverage.default_folder_key,
            test_sets=coverage.test_sets + new_sets,
            capability_risk_weights=coverage.capability_risk_weights,
        )
        return merged

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_live_test_sets(self) -> list[dict]:
        """Call ``uip tm testsets list`` and return the raw data list."""
        args = [
            "uip", "tm", "testsets", "list",
            "--project-key", self.project_key,
            "--output", "json",
        ]
        folder_key = os.getenv("RELEASE_SENTINEL_TEST_MANAGER_FOLDER_KEY", "")
        if folder_key:
            args += ["--folder-key", folder_key]

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
            log.warning("Coverage sync skipped: %s", exc)
            return []

        if result.returncode != 0:
            log.warning(
                "Coverage sync: uip tm testsets list exited %d – %s",
                result.returncode,
                (result.stderr or result.stdout)[:200],
            )
            return []

        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            log.warning("Coverage sync: could not parse uip output as JSON.")
            return []

        # Orchestrator wraps responses in {"Data": [...]}
        data = payload if isinstance(payload, list) else payload.get("Data", payload)
        return data if isinstance(data, list) else []

    @staticmethod
    def _build_test_cases(raw: dict, set_key: str) -> list[TestCaseRef]:
        """Build minimal TestCaseRef list from raw API data."""
        cases_raw = raw.get("TestCases") or raw.get("testCases") or []
        if not cases_raw:
            # Synthesise a placeholder so the test set is still usable
            return [
                TestCaseRef(
                    key=f"{set_key}-TC-001",
                    name="(synced from Test Manager)",
                    capability="regression_baseline",
                    automation="",
                )
            ]
        return [
            TestCaseRef(
                key=str(tc.get("Key") or tc.get("key") or f"{set_key}-{i}"),
                name=str(tc.get("Name") or tc.get("name") or "Test case"),
                capability="regression_baseline",
                automation=str(tc.get("Automation") or tc.get("automation") or ""),
            )
            for i, tc in enumerate(cases_raw)
        ]
