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
