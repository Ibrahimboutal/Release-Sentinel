"""Historical test-case flakiness engine.

Fetches past execution logs from UiPath Test Manager via ``uip tm`` and
computes a per-test-case flakiness index: the fraction of recent runs that look
environmental, inconclusive, cancelled, selector-related, or timed out.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
from collections import defaultdict
from typing import Any

log = logging.getLogger(__name__)

DEFAULT_FLAKINESS_THRESHOLD = 0.35
DEFAULT_FLAKINESS_LOOKBACK = 10
FLAKY_RESULTS = {"inconclusive", "cancelled"}
FLAKY_MESSAGES = ("timeout", "robot unavailable", "selector", "element not found")


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
        self.threshold = threshold if threshold is not None else _float_env(
            "RELEASE_SENTINEL_FLAKINESS_THRESHOLD", DEFAULT_FLAKINESS_THRESHOLD
        )
        self.lookback = lookback if lookback is not None else _int_env(
            "RELEASE_SENTINEL_FLAKINESS_LOOKBACK", DEFAULT_FLAKINESS_LOOKBACK
        )
        self.timeout_seconds = timeout_seconds

    def build_flakiness_map(self, test_set_keys: list[str]) -> dict[str, float]:
        """Return ``test_case_key -> flakiness_index`` for selected test sets."""

        test_set_ids = self._fetch_test_set_ids()
        total: dict[str, int] = defaultdict(int)
        flaky: dict[str, int] = defaultdict(int)

        for test_set_key in test_set_keys:
            test_set_id = test_set_ids.get(test_set_key) or _uuid_like(test_set_key)
            if not test_set_id:
                log.debug("Flakiness skipped for %s: no Test Manager Id found.", test_set_key)
                continue

            for execution_id in self._fetch_recent_execution_ids(test_set_id):
                for log_entry in self._fetch_case_logs(execution_id):
                    test_case_key = _test_case_key(log_entry)
                    total[test_case_key] += 1
                    if _is_flaky_result(_result(log_entry), _message(log_entry)):
                        flaky[test_case_key] += 1

        flakiness_map: dict[str, float] = {}
        for test_case_key, runs in total.items():
            index = round(flaky[test_case_key] / runs, 3) if runs else 0.0
            flakiness_map[test_case_key] = index
            if index >= self.threshold:
                log.info(
                    "Flakiness detected: %s index=%.2f (%d/%d flaky runs)",
                    test_case_key,
                    index,
                    flaky[test_case_key],
                    runs,
                )
        return flakiness_map

    def is_flaky(self, test_case_key: str, flakiness_map: dict[str, float]) -> bool:
        return flakiness_map.get(test_case_key, 0.0) >= self.threshold

    def _fetch_test_set_ids(self) -> dict[str, str]:
        payload = self._uip(["tm", "testsets", "list", "--project-key", self.project_key])
        if payload is None:
            return {}
        items = payload if isinstance(payload, list) else payload.get("Data", [])
        return {
            str(item.get("TestSetKey") or item.get("testSetKey")): str(item.get("Id") or item.get("id"))
            for item in items
            if (item.get("TestSetKey") or item.get("testSetKey")) and (item.get("Id") or item.get("id"))
        }

    def _fetch_recent_execution_ids(self, test_set_id: str) -> list[str]:
        payload = self._uip(
            [
                "tm",
                "executions",
                "list",
                "--project-key",
                self.project_key,
                "--test-set-id",
                test_set_id,
                "--top",
                str(self.lookback),
            ]
        )
        if payload is None:
            return []

        items = payload if isinstance(payload, list) else payload.get("Data", [])
        items = sorted(
            items,
            key=lambda item: item.get("StartTime") or item.get("startTime") or item.get("Name") or "",
            reverse=True,
        )[: self.lookback]
        return [
            str(item.get("Id") or item.get("id") or item.get("ExecutionId") or item.get("executionId"))
            for item in items
            if item.get("Id") or item.get("id") or item.get("ExecutionId") or item.get("executionId")
        ]

    def _fetch_case_logs(self, execution_id: str) -> list[dict[str, Any]]:
        payload = self._uip(
            [
                "tm",
                "executions",
                "testcaselogs",
                "list",
                "--execution-id",
                execution_id,
                "--project-key",
                self.project_key,
            ]
        )
        if payload is None:
            return []
        data = payload if isinstance(payload, list) else payload.get("Data", [])
        return data if isinstance(data, list) else []

    def _uip(self, args: list[str]) -> list[dict[str, Any]] | dict[str, Any] | None:
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
            log.debug("uip %s exited %d: %s", " ".join(args[:3]), result.returncode, result.stderr[:160])
            return None

        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return None


def _is_flaky_result(result: str, message: str) -> bool:
    return result in FLAKY_RESULTS or any(keyword in message.lower() for keyword in FLAKY_MESSAGES)


def _test_case_key(log_entry: dict[str, Any]) -> str:
    return str(
        log_entry.get("TestCaseKey")
        or log_entry.get("testCaseKey")
        or log_entry.get("TestCaseId")
        or log_entry.get("TestCaseName")
        or log_entry.get("testCaseName")
        or log_entry.get("Id")
        or "unknown"
    )


def _result(log_entry: dict[str, Any]) -> str:
    return str(log_entry.get("Result") or log_entry.get("result") or "").lower()


def _message(log_entry: dict[str, Any]) -> str:
    return str(log_entry.get("Message") or log_entry.get("message") or "")


def _float_env(name: str, default: float) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except ValueError:
        return default
    return max(0.0, min(1.0, value))


def _int_env(name: str, default: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        return default
    return max(1, value)


def _uuid_like(value: str) -> str | None:
    return value if len(value) >= 32 and "-" in value else None
