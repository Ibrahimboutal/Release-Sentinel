from __future__ import annotations

import json
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from .models import ChangeManifest, CoverageMap, ReleaseVerdict

T = TypeVar("T", bound=BaseModel)


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
ARTIFACT_DIR = ROOT / "artifacts"
DEFAULT_MANIFEST = DATA_DIR / "change_manifest.json"
DEFAULT_COVERAGE = DATA_DIR / "coverage_map.json"
DEFAULT_VERDICT = ARTIFACT_DIR / "release_verdict.json"
DEFAULT_HISTORY = ARTIFACT_DIR / "run_history.jsonl"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")


def load_manifest(path: Path = DEFAULT_MANIFEST) -> ChangeManifest:
    return ChangeManifest.model_validate(read_json(path))


def load_coverage(path: Path = DEFAULT_COVERAGE) -> CoverageMap:
    return CoverageMap.model_validate(read_json(path))


def save_verdict(verdict: ReleaseVerdict, path: Path = DEFAULT_VERDICT) -> None:
    payload = verdict.model_dump(mode="json")
    write_json(path, payload)
    append_history(verdict)


def append_history(verdict: ReleaseVerdict, path: Path = DEFAULT_HISTORY) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8") if not path.exists() else None
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record(verdict), default=str) + "\n")


def history_record(verdict: ReleaseVerdict) -> dict:
    return {
        "change_id": verdict.change_id,
        "generated_at": verdict.generated_at.isoformat(),
        "decision": verdict.decision.value,
        "risk_score": verdict.risk.score,
        "risk_level": verdict.risk.level.value,
        "selected_test_sets": [test_set.key for test_set in verdict.plan.selected_test_sets],
        "execution_ids": [execution.execution_id for execution in verdict.executions],
        "failure_count": len(verdict.triage.failures),
        "human_review_status": verdict.human_review_status,
        "action_center_task_id": verdict.action_center_task_id,
    }


def load_history(path: Path = DEFAULT_HISTORY, limit: int = 10) -> list[dict]:
    if not path.exists():
        return []
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records[-limit:][::-1]
