#!/usr/bin/env python3
"""Validate and materialize a Nowlert release without building or deploying."""

from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import os
import re
import sys
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

EXPECTED_REPOSITORY = "Theriark/nowlert-ce"
EXPECTED_IMAGE_PREFIX = "ghcr.io/theriark/nowlert-ce@sha256:"
EXPECTED_WORKFLOWS = {
    "development": "Development Image",
    "stage": "Promote CE to Stage",
    "production_reference": "Promote CE to Production Reference",
}
PRODREF_APPLICATION_ID = "-Qb71PLUZmBHLJ_Iv68Oo"
PRODREF_SCHEDULE_ID = "JVSEdTk4tt4vKPbG3cKFZ"
PRODREF_QA_HOST = "vm-13"
PRODREF_QA_ROOT = "/var/lib/nowlert-qa/evidence"
PRODREF_SUCCESS_MARKER = "PRODUCTION REFERENCE CE POST-PROMOTION SMOKE PASSED"


def fail(message: str) -> None:
    print(f"::error::{message}", file=sys.stderr)
    raise SystemExit(1)


def api_request(path: str, *, accept: str = "application/vnd.github+json") -> bytes:
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        fail("GITHUB_TOKEN is missing")

    request = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={
            "Accept": accept,
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "nowlert-release-finalization",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        fail(f"GitHub API request failed ({exc.code}) for {path}: {detail}")
    except urllib.error.URLError as exc:
        fail(f"GitHub API request failed for {path}: {exc}")
    raise AssertionError("unreachable")


def get_json(path: str) -> dict[str, Any]:
    return json.loads(api_request(path).decode("utf-8"))


def get_run(repository: str, run_id: int, expected_name: str) -> dict[str, Any]:
    run = get_json(f"/repos/{repository}/actions/runs/{run_id}")
    actual_repository = run.get("repository", {}).get("full_name")
    if actual_repository != repository:
        fail(f"Run {run_id} belongs to {actual_repository!r}, not {repository!r}")
    if run.get("name") != expected_name:
        fail(
            f"Run {run_id} is workflow {run.get('name')!r}; expected {expected_name!r}"
        )
    if run.get("status") != "completed" or run.get("conclusion") != "success":
        fail(
            f"Run {run_id} is not successful: "
            f"status={run.get('status')!r}, conclusion={run.get('conclusion')!r}"
        )
    return run


def get_run_logs(repository: str, run_id: int) -> str:
    payload = api_request(
        f"/repos/{repository}/actions/runs/{run_id}/logs",
        accept="application/vnd.github+json",
    )
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            return "\n".join(
                archive.read(name).decode("utf-8", errors="replace")
                for name in archive.namelist()
                if not name.endswith("/")
            )
    except zipfile.BadZipFile:
        fail(f"Logs for run {run_id} were not returned as a ZIP archive")
    raise AssertionError("unreachable")


def require_in_logs(logs: str, value: str, description: str, run_id: int) -> None:
    if value not in logs:
        fail(f"Run {run_id} logs do not contain {description}: {value}")


def validate_args(args: argparse.Namespace) -> None:
    if not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?", args.version):
        fail("Version must be a semantic version beginning with v, for example v3.0.0")
    if not re.fullmatch(r"[0-9a-f]{40}", args.source_commit):
        fail("Source commit must be a full 40-character lowercase SHA")
    if not re.fullmatch(
        re.escape(EXPECTED_IMAGE_PREFIX) + r"[0-9a-f]{64}", args.final_image
    ):
        fail("Final image must be an immutable nowlert-ce GHCR digest")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.qa_schedule_deployment_id):
        fail("QA schedule deployment ID contains unexpected characters")
    if not args.release_notes.strip():
        fail("Release notes must not be empty")


def validate_runs(args: argparse.Namespace) -> dict[str, dict[str, Any]]:
    runs = {
        "development": get_run(
            args.repository, args.development_run, EXPECTED_WORKFLOWS["development"]
        ),
        "stage": get_run(args.repository, args.stage_run, EXPECTED_WORKFLOWS["stage"]),
        "production_reference": get_run(
            args.repository,
            args.production_reference_run,
            EXPECTED_WORKFLOWS["production_reference"],
        ),
    }

    if runs["development"].get("head_sha") != args.source_commit:
        fail(
            "Development run head SHA does not match the requested source commit: "
            f"{runs['development'].get('head_sha')} != {args.source_commit}"
        )

    development_logs = get_run_logs(args.repository, args.development_run)
    stage_logs = get_run_logs(args.repository, args.stage_run)
    prodref_logs = get_run_logs(args.repository, args.production_reference_run)

    require_in_logs(
        development_logs,
        args.source_commit,
        "the source commit",
        args.development_run,
    )
    require_in_logs(
        development_logs,
        args.final_image,
        "the immutable image digest",
        args.development_run,
    )
    require_in_logs(
        stage_logs,
        args.final_image,
        "the immutable image digest",
        args.stage_run,
    )
    require_in_logs(
        prodref_logs,
        args.final_image,
        "the immutable image digest",
        args.production_reference_run,
    )
    require_in_logs(
        prodref_logs,
        PRODREF_SUCCESS_MARKER,
        "the VM-13 success marker",
        args.production_reference_run,
    )
    require_in_logs(
        prodref_logs,
        args.qa_schedule_deployment_id,
        "the QA schedule deployment ID",
        args.production_reference_run,
    )

    return runs


def write_outputs(args: argparse.Namespace, runs: dict[str, dict[str, Any]]) -> None:
    created_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    manifest = {
        "schema_version": 1,
        "edition": "ce",
        "version": args.version,
        "source_commit": args.source_commit,
        "development_run": str(args.development_run),
        "stage_promotion_run": str(args.stage_run),
        "production_reference_run": str(args.production_reference_run),
        "final_image": args.final_image,
        "production_reference_application_id": PRODREF_APPLICATION_ID,
        "qa_evidence": {
            "host": PRODREF_QA_HOST,
            "root": PRODREF_QA_ROOT,
            "schedule_id": PRODREF_SCHEDULE_ID,
            "schedule_deployment_id": args.qa_schedule_deployment_id,
            "success_marker": PRODREF_SUCCESS_MARKER,
        },
        "workflow_runs": {
            key: {
                "id": str(run["id"]),
                "name": run["name"],
                "html_url": run["html_url"],
                "head_sha": run["head_sha"],
                "run_attempt": run["run_attempt"],
                "conclusion": run["conclusion"],
            }
            for key, run in runs.items()
        },
        "rebuild_during_promotion": False,
        "deployment_during_finalization": False,
        "created_at": created_at,
    }
    Path(args.manifest_path).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    summary = f"""# Nowlert CE {args.version}

{args.release_notes.strip()}

## Immutable release record

- Source commit: `{args.source_commit}`
- Final image: `{args.final_image}`
- Development run: `{args.development_run}`
- Stage promotion run: `{args.stage_run}`
- Production Reference run: `{args.production_reference_run}`
- VM-13 schedule deployment: `{args.qa_schedule_deployment_id}`
- VM-13 success marker: `{PRODREF_SUCCESS_MARKER}`
- Rebuild during promotion: no
- Deployment during release finalisation: no
"""
    Path(args.summary_path).write_text(summary, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", default=EXPECTED_REPOSITORY)
    parser.add_argument("--version", required=True)
    parser.add_argument("--final-image", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--development-run", required=True, type=int)
    parser.add_argument("--stage-run", required=True, type=int)
    parser.add_argument("--production-reference-run", required=True, type=int)
    parser.add_argument("--qa-schedule-deployment-id", required=True)
    parser.add_argument("--release-notes", required=True)
    parser.add_argument("--manifest-path", default="release-manifest.json")
    parser.add_argument("--summary-path", default="release-summary.md")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.repository != EXPECTED_REPOSITORY:
        fail(f"This script is restricted to {EXPECTED_REPOSITORY}")
    validate_args(args)
    runs = validate_runs(args)
    write_outputs(args, runs)
    print(f"Validated Nowlert CE release {args.version}")


if __name__ == "__main__":
    main()
