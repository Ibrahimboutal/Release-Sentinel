"""Historical test-case flakiness engine.

Fetches past execution logs from UiPath Test Manager via ``uip tm`` and
computes a per-test-case *flakiness index* — the fraction of recent runs
that ended in an inconclusive or environment-related failure.

A flaky test case has a high index; a reliable one has an index near zero.
The index is used by ``FailureTriageAgent`` to downgrade ``product_bug``
classifications to ``test_fragility`` when a test is historically unreliable,
preventing flaky tests from blocking real releases.

Falls back to an empty map (all zeros) when ``uip`` is not available or
no session is active, so local development always works.

Environment variables
---------------------
RELEASE_SENTINEL_FLAKINESS_THRESHOLD  Float 0-1, default 0.35.
RELEASE_SENTINEL_FLAKINESS_LOOKBACK   Number of past executions to inspect, default 10.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
from collections import defaultdict

log = logging.getLogger(__name__)

_DEFAULT_THRESHOLD = 0.35
_DEFAULT_LOOKBACK = 10

# Results that indicate environment/infra issues rather than product bugs
_FLAKY_RESULTS = {"inconclusive", "cancelled"}
_FLAKY_MESSAGES = ("timeout", "robot unavailable", "selector", "element not found")


def _is_flaky_result(result: str, message: str) -> bool:
    if result in _FLAKY_RESULTS:
        return True
    msg = message.lower()
    return any(kw in msg for kw in _FLAKY_MESSAGES)


class FlakinessEngine:
    """Compute per-test-case flakiness indices using past Test Manager runs."""

    def __init__(
        self,
        project_key: str,
        threshold: float | None = None,
        lookback: int | None = None,
        timeout_seconds: int = 30,
    ) -> None:
        self.project_key = project_key
        self.threshold = threshold if threshold is not None else float(
            os.getenv("RELEASE_SENTINEL_FLAKINESS_THRESHOLD", str(_DEFAULT_THRESHOLD))
        )
        self.lookback = lookback if lookback is not None else int(
            os.getenv("RELEASE_SENTINEL_FLAKINESS_LOOKBACK", str(_DEFAULT_LOOKBACK))
        )
        self.timeout_seconds = timeout_seconds

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build_flakiness_map(self, test_set_keys: list[str]) -> dict[str, float]:
        """Return a dict mapping test_case_key → flakiness_index (0.0 – 1.0).

        Fetches the last ``self.lookback`` executions for each test set and
        tallies flaky results per test case.
        """
        # total_runs[tc_key], flaky_runs[tc_key]
        total: dict[str, int] = defaultdict(int)
        flaky: dict[str, int] = defaultdict(int)

        for ts_key in test_set_keys:
            execution_ids = self._fetch_recent_execution_ids(ts_key)
            for exec_id in execution_ids:
                logs = self._fetch_case_logs(exec_id)
                for log_entry in logs:
                    tc_key = str(
                        log_entry.get("TestCaseKey")
                        or log_entry.get("testCaseKey")
                        or log_entry.get("TestCaseId")
                        or "unknown"
                    )
                    result = str(log_entry.get("Result") or log_entry.get("result") or "").lower()
                    message = str(log_entry.get("Message") or log_entry.get("message") or "")
                    total[tc_key] += 1
                    if _is_flaky_result(result, message):
                        flaky[tc_key] += 1

        flakiness_map: dict[str, float] = {}
        for tc_key, runs in total.items():
            index = round(flaky[tc_key] / runs, 3) if runs else 0.0
            flakiness_map[tc_key] = index
            if index >= self.threshold:
                log.info(
                    "Flakiness detected: %s index=%.2f (%d/%d flaky runs)",
                    tc_key, index, flaky[tc_key], runs,
                )

        return flakiness_map

    def is_flaky(self, test_case_key: str, flakiness_map: dict[str, float]) -> bool:
        """Return True if the test case exceeds the configured threshold."""
        return flakiness_map.get(test_case_key, 0.0) >= self.threshold

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _uip(self, args: list[str]) -> list | dict | None:
        """Run a ``uip`` sub-command and return parsed JSON, or None on failure."""
        try:
            result = subprocess.run(
                ["uip", *args, "--output", "json"],
                capture_output=True,
                text=True,
                check=False,
                timeout=self.timeout_seconds,
                shell=os.name == "nt",
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            log.debug("Flakiness engine skipped (%s): %s", args[:3], exc)
            return None

        if result.returncode != 0:
            log.debug(
                "uip %s exited %d: %s",
                " ".join(args[:3]), result.returncode,
                (result.stderr or result.stdout)[:120],
            )
            return None

        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return None

    def _fetch_recent_execution_ids(self, test_set_key: str) -> list[str]:
        """Return the most recent N execution IDs for a test set."""
        payload = self._uip([
            "tm", "executions", "list",
            "--test-set-key", test_set_key,
            "--project-key", self.project_key,
        ])
        if payload is None:
            return []

        items = payload if isinstance(payload, list) else payload.get("Data", [])
        # Sort descending by date if available, then take the last N
        items = sorted(
            items,
            key=lambda x: x.get("StartTime") or x.get("startTime") or "",
            reverse=True,
        )[: self.lookback]

        return [
            str(item.get("Id") or item.get("id") or item.get("ExecutionId") or "")
            for item in items
            if item.get("Id") or item.get("id") or item.get("ExecutionId")
        ]

    def _fetch_case_logs(self, execution_id: str) -> list[dict]:
        """Return test-case log entries for a given execution ID."""
        payload = self._uip([
            "tm", "executions", "testcaselogs", "list",
            "--execution-id", execution_id,
            "--project-key", self.project_key,
        ])
        if payload is None:
            return []
        return payload if isinstance(payload, list) else payload.get("Data", [])
