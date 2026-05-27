import json
import subprocess

from releasesentinel.agents import FailureTriageAgent
from releasesentinel.flakiness import FlakinessEngine
from releasesentinel.io import load_manifest
from releasesentinel.models import TriageCategory


def _completed(payload):
    return subprocess.CompletedProcess(args=["uip"], returncode=0, stdout=json.dumps(payload), stderr="")


def test_flakiness_engine_uses_test_set_id_and_calculates_index(monkeypatch):
    seen_commands = []

    def fake_run(args, **kwargs):
        seen_commands.append(args)
        if args[1:4] == ["tm", "testsets", "list"]:
            return _completed({"Data": [{"TestSetKey": "ELIGIBILITY_TARGETED", "Id": "set-uuid-1"}]})
        if args[1:4] == ["tm", "executions", "list"]:
            assert "--test-set-id" in args
            assert "set-uuid-1" in args
            return _completed({"Data": [{"Id": "exec-1"}, {"Id": "exec-2"}]})
        if args[1:5] == ["tm", "executions", "testcaselogs", "list"]:
            execution_id = args[args.index("--execution-id") + 1]
            result = "Inconclusive" if execution_id == "exec-1" else "Passed"
            message = "robot unavailable" if execution_id == "exec-1" else "ok"
            return _completed(
                {
                    "Data": [
                        {
                            "TestCaseKey": "TC-ELIGIBILITY-101",
                            "Result": result,
                            "Message": message,
                        }
                    ]
                }
            )
        raise AssertionError(args)

    monkeypatch.setattr("subprocess.run", fake_run)

    flakiness = FlakinessEngine(project_key="REL_SENTINEL", threshold=0.35, lookback=2)
    result = flakiness.build_flakiness_map(["ELIGIBILITY_TARGETED"])

    assert result["TC-ELIGIBILITY-101"] == 0.5
    assert any("set-uuid-1" in command for command in seen_commands)


def test_triage_downgrades_product_bug_when_test_is_historically_flaky():
    manifest = load_manifest()
    agent = FailureTriageAgent(flakiness_threshold=0.35)

    triage = agent._triage_log(
        "Eligibility assertion failed: expected route adjuster_review but received straight_through.",
        "TC-ELIGIBILITY-101",
        "Injury claim requires adjuster review",
        manifest,
        flakiness_index=0.7,
    )

    assert triage.category == TriageCategory.test_fragility
    assert "Historical flakiness index" in triage.evidence[1]
