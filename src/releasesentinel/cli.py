from __future__ import annotations

import argparse
import json
from pathlib import Path

import uvicorn

from .api import app
from .io import (
    DEFAULT_COVERAGE,
    DEFAULT_MANIFEST,
    DEFAULT_VERDICT,
    load_coverage,
    load_manifest,
    save_verdict,
)
from .pipeline import ReleaseSentinelPipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Release Sentinel demo runner")
    subcommands = parser.add_subparsers(dest="command", required=True)

    run = subcommands.add_parser("run", help="Run the release-risk and test-selection pipeline")
    run.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    run.add_argument("--coverage", type=Path, default=DEFAULT_COVERAGE)
    run.add_argument("--output", type=Path, default=DEFAULT_VERDICT)
    run.add_argument("--scenario", choices=["auto", "happy", "failing", "ambiguous", "timeout"], default="auto")
    run.add_argument("--runner", choices=["auto", "simulated", "uipath"], default="auto")
    run.add_argument("--sync-coverage", action="store_true", help="Merge live UiPath Test Manager test sets before analysis")
    run.add_argument("--pretty", action="store_true", help="Print the full verdict JSON")

    serve = subcommands.add_parser("serve", help="Start the local API and dashboard")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)

    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.command == "run":
        manifest = load_manifest(args.manifest)
        coverage = load_coverage(args.coverage)
        verdict = ReleaseSentinelPipeline(
            coverage=coverage,
            runner_mode=args.runner,
            sync_coverage=args.sync_coverage,
        ).run(
            manifest,
            scenario=args.scenario,
            persist=False,
        )
        save_verdict(verdict, args.output)
        if args.pretty:
            print(json.dumps(verdict.model_dump(mode="json"), indent=2))
        else:
            print(f"{verdict.decision.value}: {verdict.release_notes[0]}")
            print(f"wrote {args.output}")
    elif args.command == "serve":
        uvicorn.run(app, host=args.host, port=args.port)
