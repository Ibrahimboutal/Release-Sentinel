import json

from releasesentinel.action_center import ActionCenterClient


def test_action_center_returns_none_when_unconfigured(monkeypatch):
    monkeypatch.delenv("RELEASE_SENTINEL_ORCHESTRATOR_URL", raising=False)
    monkeypatch.delenv("RELEASE_SENTINEL_ORCHESTRATOR_TOKEN", raising=False)

    client = ActionCenterClient()

    assert client.create_review_task({"change_id": "chg-1"}) is None


def test_action_center_creates_form_task(monkeypatch):
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"Data": {"Id": "task-123"}}'

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["auth"] = request.get_header("Authorization")
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    client = ActionCenterClient(
        orchestrator_url="https://cloud.uipath.com/org/tenant/orchestrator_",
        auth_token="token",
        task_catalog="ReleaseGateReviews",
    )

    task_id = client.create_review_task(
        {
            "change_id": "chg-review",
            "decision": "needs_review",
            "risk": {"score": 88, "level": "critical"},
            "triage": {"summary": "Review required.", "failures": []},
            "release_notes": ["Critical risk."],
            "next_actions": ["Review in Action Center."],
            "executions": [{"execution_id": "exec-1", "result": "inconclusive"}],
        }
    )

    assert task_id == "task-123"
    assert captured["url"].endswith("/forms/TaskForms/CreateFormTask")
    assert captured["auth"] == "Bearer token"
    assert captured["payload"]["taskCatalogName"] == "ReleaseGateReviews"
    assert captured["payload"]["data"]["changeId"] == "chg-review"
