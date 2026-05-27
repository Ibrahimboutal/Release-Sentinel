from releasesentinel.io import append_history, load_history
from releasesentinel.io import load_coverage, load_manifest
from releasesentinel.pipeline import ReleaseSentinelPipeline


def test_append_history_writes_compact_recent_record(tmp_path):
    manifest = load_manifest()
    verdict = ReleaseSentinelPipeline(coverage=load_coverage()).run(
        manifest,
        scenario="failing",
        persist=False,
    )
    history_path = tmp_path / "history.jsonl"

    append_history(verdict, history_path)
    records = load_history(history_path, limit=1)

    assert records[0]["change_id"] == manifest.change_id
    assert records[0]["decision"] == "block"
    assert records[0]["risk_score"] == 100
    assert records[0]["selected_test_sets"]
