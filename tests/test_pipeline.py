from pathlib import Path

from releasesentinel.io import load_coverage, load_manifest
from releasesentinel.models import ReleaseDecision, RiskLevel, TriageCategory
from releasesentinel.pipeline import ReleaseSentinelPipeline


ROOT = Path(__file__).resolve().parents[1]


def test_low_risk_change_runs_smoke_and_approves():
    manifest = load_manifest(ROOT / "data" / "fixtures" / "low_risk_manifest.json")
    pipeline = ReleaseSentinelPipeline(coverage=load_coverage())

    verdict = pipeline.run(manifest, scenario="happy", persist=False)

    assert verdict.risk.level == RiskLevel.low
    assert [test_set.key for test_set in verdict.plan.selected_test_sets] == ["SMOKE"]
    assert verdict.decision == ReleaseDecision.approve


def test_high_risk_change_selects_targeted_regression_and_blocks_on_product_bug():
    manifest = load_manifest(ROOT / "data" / "change_manifest.json")
    pipeline = ReleaseSentinelPipeline(coverage=load_coverage())

    verdict = pipeline.run(manifest, scenario="failing", persist=False)

    keys = {test_set.key for test_set in verdict.plan.selected_test_sets}
    assert "SMOKE" in keys
    assert "ELIGIBILITY_TARGETED" in keys
    assert "CLAIMS_TARGETED_REGRESSION" in keys
    assert verdict.decision == ReleaseDecision.block
    assert any(f.category == TriageCategory.product_bug for f in verdict.triage.failures)


def test_ambiguous_failure_routes_to_human_review():
    manifest = load_manifest(ROOT / "data" / "fixtures" / "ambiguous_manifest.json")
    pipeline = ReleaseSentinelPipeline(coverage=load_coverage())

    verdict = pipeline.run(manifest, scenario="ambiguous", persist=False)

    assert verdict.decision == ReleaseDecision.needs_review
    assert verdict.human_review_status == "pending"
    assert verdict.triage.human_review_required


def test_timeout_never_produces_false_pass():
    manifest = load_manifest(ROOT / "data" / "change_manifest.json")
    pipeline = ReleaseSentinelPipeline(coverage=load_coverage())

    verdict = pipeline.run(manifest, scenario="timeout", persist=False)

    assert verdict.decision == ReleaseDecision.needs_review
    assert any(execution.status == "timed_out" for execution in verdict.executions)

