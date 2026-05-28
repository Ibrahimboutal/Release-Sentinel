from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .io import (
    DATA_DIR,
    DEFAULT_MANIFEST,
    DEFAULT_VERDICT,
    load_coverage,
    load_history,
    load_manifest,
    read_json,
)
from .models import (
    AnalyzeRequest,
    DemoRunRequest,
    SelectTestsRequest,
    TriageRequest,
    VerdictRequest,
)
from .pipeline import ReleaseSentinelPipeline

ROOT = Path(__file__).resolve().parents[2]
WEB_DIR = ROOT / "web"


app = FastAPI(
    title="Release Sentinel",
    version="0.1.0",
    description="Agentic release-risk and Test Cloud orchestration prototype for UiPath AgentHack.",
)
app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(WEB_DIR / "templates"))


def pipeline() -> ReleaseSentinelPipeline:
    return ReleaseSentinelPipeline(coverage=load_coverage())


@app.post("/api/analyze-change")
def analyze_change(request: AnalyzeRequest):
    return pipeline().analyze_change(request.manifest)


@app.post("/api/select-tests")
def select_tests(request: SelectTestsRequest):
    return pipeline().select_tests(request.manifest, request.risk)


@app.post("/api/triage-results")
def triage_results(request: TriageRequest):
    return pipeline().triage_results(request.manifest, request.executions, request.flakiness_map)


@app.post("/api/release-verdict")
def release_verdict(request: VerdictRequest):
    return pipeline().run(request.manifest, scenario=request.scenario, persist=request.persist)


@app.post("/api/demo-run")
def demo_run(request: DemoRunRequest):
    manifest_path = _manifest_path_for_demo(request)
    manifest = load_manifest(manifest_path)
    return ReleaseSentinelPipeline(
        coverage=load_coverage(),
        runner_mode=request.runner,
        sync_coverage=request.sync_coverage,
    ).run(manifest, scenario=request.scenario, persist=True)


@app.get("/api/latest-verdict")
def latest_verdict():
    if not DEFAULT_VERDICT.exists():
        raise HTTPException(status_code=404, detail="No release verdict has been generated yet.")
    return read_json(DEFAULT_VERDICT)


@app.get("/api/run-history")
def run_history(limit: int = 10):
    return {"history": load_history(limit=max(1, min(limit, 50)))}


@app.get("/", response_class=HTMLResponse)
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    verdict = read_json(DEFAULT_VERDICT) if DEFAULT_VERDICT.exists() else None
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {"verdict": verdict, "history": load_history(limit=6)},
    )


def _manifest_path_for_demo(request: DemoRunRequest) -> Path:
    if request.manifest_path:
        candidate = Path(request.manifest_path)
        manifest_path = candidate if candidate.is_absolute() else ROOT / candidate
    elif request.scenario == "happy":
        manifest_path = DATA_DIR / "fixtures" / "low_risk_manifest.json"
    elif request.scenario == "ambiguous":
        manifest_path = DATA_DIR / "fixtures" / "ambiguous_manifest.json"
    else:
        manifest_path = DEFAULT_MANIFEST

    resolved = manifest_path.resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="manifest_path must stay inside the project workspace.") from exc
    if not resolved.exists():
        raise HTTPException(status_code=404, detail=f"Manifest not found: {manifest_path}")
    return resolved
