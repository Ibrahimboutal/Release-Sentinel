"""Action Center integration for human-in-the-loop release review tasks.

Calls the UiPath Orchestrator REST API to create a real form task when a
verdict requires human review. Missing credentials or API failures return
``None`` so local development and CI keep working without cloud access.

Environment variables:

- ``RELEASE_SENTINEL_ORCHESTRATOR_URL``: Orchestrator base URL, for example
  ``https://cloud.uipath.com/org/tenant/orchestrator_``.
- ``RELEASE_SENTINEL_ORCHESTRATOR_TOKEN``: bearer token.
- ``RELEASE_SENTINEL_TASK_CATALOG``: task catalog name, default
  ``ReleaseGateReviews``.
- ``RELEASE_SENTINEL_TENANT``: optional tenant header for older setups.
- ``RELEASE_SENTINEL_FOLDER_ID``: optional folder/organization unit header.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any

log = logging.getLogger(__name__)


class ActionCenterClient:
    """Thin REST adapter for creating UiPath Action Center form tasks."""

    DEFAULT_CATALOG = "ReleaseGateReviews"
    CREATE_FORM_TASK_PATH = "/forms/TaskForms/CreateFormTask"

    def __init__(
        self,
        orchestrator_url: str | None = None,
        auth_token: str | None = None,
        task_catalog: str | None = None,
    ) -> None:
        self.orchestrator_url = (
            orchestrator_url or os.getenv("RELEASE_SENTINEL_ORCHESTRATOR_URL", "")
        ).rstrip("/")
        self.auth_token = auth_token or os.getenv("RELEASE_SENTINEL_ORCHESTRATOR_TOKEN", "")
        self.task_catalog = task_catalog or os.getenv(
            "RELEASE_SENTINEL_TASK_CATALOG", self.DEFAULT_CATALOG
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.orchestrator_url and self.auth_token)

    def create_review_task(self, verdict_payload: dict[str, Any]) -> str | None:
        """Create an Action Center form task and return its task ID."""

        if not self.is_configured:
            log.warning(
                "Action Center not configured. Set RELEASE_SENTINEL_ORCHESTRATOR_URL "
                "and RELEASE_SENTINEL_ORCHESTRATOR_TOKEN to create real review tasks."
            )
            return None

        compact = _compact_verdict(verdict_payload)
        payload = self._build_payload(compact)
        request = urllib.request.Request(
            f"{self.orchestrator_url}{self.CREATE_FORM_TASK_PATH}",
            data=json.dumps(payload).encode("utf-8"),
            headers=self._headers(),
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                result = json.loads(response.read())
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            log.warning("Failed to create Action Center task for %s: %s", compact["change_id"], exc)
            return None

        task_id = _extract_task_id(result)
        log.info("Action Center task created for %s: %s", compact["change_id"], task_id)
        return task_id

    def _headers(self) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json",
        }
        if tenant := os.getenv("RELEASE_SENTINEL_TENANT", ""):
            headers["X-UIPATH-TenantName"] = tenant
        if folder_id := os.getenv("RELEASE_SENTINEL_FOLDER_ID", ""):
            headers["X-UIPATH-OrganizationUnitId"] = folder_id
        return headers

    def _build_payload(self, compact_verdict: dict[str, Any]) -> dict[str, Any]:
        risk = compact_verdict.get("risk", {})
        triage = compact_verdict.get("triage", {})
        return {
            "title": f"Release Gate Review: {compact_verdict['change_id']}",
            "priority": "High",
            "taskCatalogName": self.task_catalog,
            "data": {
                "changeId": compact_verdict["change_id"],
                "decision": compact_verdict.get("decision", "needs_review"),
                "riskScore": risk.get("score"),
                "riskLevel": risk.get("level"),
                "triageSummary": triage.get("summary", ""),
                "failures": triage.get("failures", []),
                "releaseNotes": compact_verdict.get("release_notes", []),
                "nextActions": compact_verdict.get("next_actions", []),
                "executionEvidence": compact_verdict.get("executions", []),
            },
        }


def _extract_task_id(result: dict[str, Any]) -> str | None:
    data = result.get("Data", result)
    task_id = data.get("Id") or data.get("id") or data.get("TaskId") or data.get("taskId")
    return str(task_id) if task_id else None


def _compact_verdict(verdict_payload: dict[str, Any]) -> dict[str, Any]:
    executions = [
        {
            "execution_id": execution.get("execution_id"),
            "test_set_key": execution.get("test_set_key"),
            "status": execution.get("status"),
            "result": execution.get("result"),
        }
        for execution in verdict_payload.get("executions", [])
    ]

    triage = verdict_payload.get("triage", {})
    failures = [
        {
            "test_case_key": failure.get("test_case_key"),
            "test_case_name": failure.get("test_case_name"),
            "category": failure.get("category"),
            "confidence": failure.get("confidence"),
            "recommended_fix": failure.get("recommended_fix"),
        }
        for failure in triage.get("failures", [])
    ][:10]

    return {
        "change_id": verdict_payload.get("change_id", "unknown"),
        "decision": verdict_payload.get("decision"),
        "risk": verdict_payload.get("risk", {}),
        "triage": {**triage, "failures": failures},
        "release_notes": verdict_payload.get("release_notes", []),
        "next_actions": verdict_payload.get("next_actions", []),
        "executions": executions,
    }
