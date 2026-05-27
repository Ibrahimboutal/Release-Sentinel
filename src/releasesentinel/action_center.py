"""Action Center integration for human-in-the-loop release review tasks.

Calls the UiPath Orchestrator REST API to create a real Task when a verdict
requires human review. Falls back gracefully (logging a warning) when no
Orchestrator credentials are configured, so local development continues
to work without cloud access.

Environment variables
---------------------
RELEASE_SENTINEL_ORCHESTRATOR_URL    Base URL, e.g. https://cloud.uipath.com/org/tenant/orchestrator_
RELEASE_SENTINEL_ORCHESTRATOR_TOKEN  Bearer token (personal access token or client-credentials token)
RELEASE_SENTINEL_TASK_CATALOG        Task catalog name in Action Center (default: ReleaseGateReviews)
"""

from __future__ import annotations

import logging
import os
from typing import Any

log = logging.getLogger(__name__)


class ActionCenterClient:
    """Thin REST adapter for creating Action Center tasks via the Orchestrator API."""

    DEFAULT_CATALOG = "ReleaseGateReviews"

    def __init__(
        self,
        orchestrator_url: str | None = None,
        auth_token: str | None = None,
        task_catalog: str | None = None,
    ) -> None:
        self.orchestrator_url = (
            orchestrator_url
            or os.getenv("RELEASE_SENTINEL_ORCHESTRATOR_URL", "").rstrip("/")
        )
        self.auth_token = auth_token or os.getenv("RELEASE_SENTINEL_ORCHESTRATOR_TOKEN", "")
        self.task_catalog = task_catalog or os.getenv(
            "RELEASE_SENTINEL_TASK_CATALOG", self.DEFAULT_CATALOG
        )

    @property
    def _is_configured(self) -> bool:
        return bool(self.orchestrator_url and self.auth_token)

    def create_review_task(self, verdict_payload: dict[str, Any]) -> str | None:
        """Create a human-review Action Center task for the given verdict.

        Returns the task ID string on success, or None if credentials are not
        configured (graceful fallback for local dev).
        """
        if not self._is_configured:
            log.warning(
                "Action Center not configured. Set RELEASE_SENTINEL_ORCHESTRATOR_URL and "
                "RELEASE_SENTINEL_ORCHESTRATOR_TOKEN to create real tasks. "
                "Skipping task creation."
            )
            return None

        import urllib.request
        import json as _json

        change_id = verdict_payload.get("change_id", "unknown")
        risk_score = verdict_payload.get("risk", {}).get("score", 0)
        risk_level = verdict_payload.get("risk", {}).get("level", "unknown")
        decision = verdict_payload.get("decision", "needs_review")
        triage_summary = verdict_payload.get("triage", {}).get("summary", "")

        payload = {
            "title": f"Release Gate Review: {change_id}",
            "priority": "High",
            "taskCatalogName": self.task_catalog,
            "data": {
                "changeId": change_id,
                "decision": decision,
                "riskScore": risk_score,
                "riskLevel": risk_level,
                "triageSummary": triage_summary,
                "releaseNotes": verdict_payload.get("release_notes", []),
                "nextActions": verdict_payload.get("next_actions", []),
                "executionEvidence": [
                    {"executionId": e.get("execution_id"), "result": e.get("result")}
                    for e in verdict_payload.get("executions", [])
                ],
            },
        }

        url = f"{self.orchestrator_url}/odata/Tasks/UiPath.Server.Configuration.OData.CreateFormTask"
        data = _json.dumps(payload).encode()
        headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json",
            "X-UIPATH-TenantName": os.getenv("RELEASE_SENTINEL_TENANT", ""),
        }

        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = _json.loads(resp.read())
                task_id = str(result.get("Id") or result.get("id") or "")
                log.info("Action Center task created: %s (task_id=%s)", change_id, task_id)
                return task_id
        except Exception as exc:  # noqa: BLE001
            log.error("Failed to create Action Center task for %s: %s", change_id, exc)
            return None
