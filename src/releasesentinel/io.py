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
    write_json(path, verdict.model_dump(mode="json"))

