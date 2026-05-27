import json
import subprocess

from releasesentinel.coverage_sync import CoverageSyncClient
from releasesentinel.io import load_coverage


def _completed(payload):
    return subprocess.CompletedProcess(args=["uip"], returncode=0, stdout=json.dumps(payload), stderr="")


def test_coverage_sync_appends_missing_test_set(monkeypatch):
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        if args[:4] == ["uip", "tm", "testsets", "list"]:
            return _completed(
                {
                    "Data": [
                        {
                            "TestSetKey": "REL_SENTINEL:99",
                            "Name": "Payments smoke suite",
                            "Id": "set-uuid-99",
                        }
                    ]
                }
            )
        if args[:4] == ["uip", "tm", "testsets", "list-testcases"]:
            return _completed(
                {
                    "Data": [
                        {
                            "TestCaseKey": "REL_SENTINEL:1001",
                            "Name": "Payment approval still routes to finance",
                        }
                    ]
                }
            )
        raise AssertionError(args)

    monkeypatch.setattr("subprocess.run", fake_run)
    coverage = load_coverage()

    synced = CoverageSyncClient(project_key=coverage.project_key).sync_coverage(coverage)

    added = synced.by_key()["REL_SENTINEL:99"]
    assert added.execution_type == "smoke"
    assert added.capabilities == ["regression_baseline"]
    assert added.test_cases[0].key == "REL_SENTINEL:1001"
    assert any("--project-key" in call for call in calls)


def test_coverage_sync_falls_back_when_uip_missing(monkeypatch):
    def fake_run(*args, **kwargs):
        raise FileNotFoundError("uip")

    monkeypatch.setattr("subprocess.run", fake_run)
    coverage = load_coverage()

    synced = CoverageSyncClient(project_key=coverage.project_key).sync_coverage(coverage)

    assert synced == coverage
