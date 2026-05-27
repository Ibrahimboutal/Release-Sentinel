from fastapi.testclient import TestClient

from releasesentinel.api import app
from releasesentinel.io import load_manifest


client = TestClient(app)


def test_analyze_endpoint_returns_risk_score():
    manifest = load_manifest()

    response = client.post("/api/analyze-change", json={"manifest": manifest.model_dump(mode="json")})

    assert response.status_code == 200
    assert response.json()["score"] >= 65


def test_release_verdict_endpoint_runs_pipeline():
    manifest = load_manifest()

    response = client.post(
        "/api/release-verdict",
        json={"manifest": manifest.model_dump(mode="json"), "scenario": "failing", "persist": False},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"] == "block"
    assert payload["executions"]


def test_dashboard_renders():
    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "Release Sentinel" in response.text
    assert "Run a release gate scenario" in response.text


def test_demo_run_endpoint_runs_happy_scenario():
    response = client.post("/api/demo-run", json={"scenario": "happy"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"] == "approve"
    assert payload["risk"]["level"] == "low"


def test_demo_run_endpoint_rejects_manifest_outside_workspace():
    response = client.post(
        "/api/demo-run",
        json={"scenario": "happy", "manifest_path": "../outside.json"},
    )

    assert response.status_code == 400


def test_run_history_endpoint_returns_recent_records():
    client.post("/api/demo-run", json={"scenario": "ambiguous"})

    response = client.get("/api/run-history?limit=1")

    assert response.status_code == 200
    history = response.json()["history"]
    assert len(history) == 1
    assert history[0]["decision"] == "needs_review"
