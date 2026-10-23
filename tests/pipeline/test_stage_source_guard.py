"""Source guard of the Stage promotion workflow.

The guard step is executed as written in the workflow against throw-away local
git repositories. No network connection is opened, so the tests stay silent
inside the network-isolated Stage gate.

Contract: Stage accepts the approved candidate commit when it is the current
development head, or when it is an ancestor of the development head that the
running pipeline was checked out from and every path changed since then is a
workflow file or a flat pipeline test. Everything else fails closed.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "promote-stage.yml"
GUARD_STEP = "Verify CE Stage configuration"
IMAGE = "ghcr.io/theriark/nowlert-ce@sha256:" + "a" * 64


def guard_script() -> str:
    payload = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    for item in payload["jobs"]["promote"]["steps"]:
        if item.get("name") == GUARD_STEP:
            return item["run"]
    raise AssertionError(f"missing step {GUARD_STEP!r}")


def git(cwd: Path, *args: str) -> str:
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.invalid",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.invalid",
    }
    done = subprocess.run(
        ["git", *args], cwd=cwd, env=env, check=True, capture_output=True, text=True
    )
    return done.stdout.strip()


def commit(repo: Path, files: dict[str, str], message: str) -> str:
    for relative, content in files.items():
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", message)
    return git(repo, "rev-parse", "HEAD")


@pytest.fixture()
def repo(tmp_path: Path) -> dict[str, object]:
    """A clone of a bare origin whose development head is the candidate."""
    origin = tmp_path / "origin.git"
    git(tmp_path, "init", "-q", "--bare", "-b", "development", str(origin))
    work = tmp_path / "work"
    git(tmp_path, "clone", "-q", str(origin), str(work))
    git(work, "checkout", "-q", "-b", "development")
    candidate = commit(
        work,
        {
            "src/app.py": "VALUE = 1\n",
            ".github/workflows/promote-stage.yml": "name: a\n",
            "tests/pipeline/test_x.py": "# t\n",
        },
        "candidate",
    )
    git(work, "push", "-q", "origin", "development")
    return {"work": work, "candidate": candidate}


def run_guard(
    repo: dict[str, object], source: str, pipeline_sha: str | None = None
) -> subprocess.CompletedProcess:
    work = Path(str(repo["work"]))
    head = git(work, "rev-parse", "HEAD")
    git(work, "push", "-q", "origin", "development")
    env = {
        **os.environ,
        "DOKPLOY_URL": "https://stage.example.invalid",
        "DOKPLOY_API_KEY": "x",
        "PROMOTION_IMAGE": IMAGE,
        "SOURCE_COMMIT": source,
        "REQUEST_ID": "publishing-test",
        "DEVELOPMENT_RUN_ID": "1",
        "DOCUMENTATION_MANIFEST_SHA256": "b" * 64,
        "RC_TAG": "v27.0.0-rc.7",
        "RELEASE_VERSION": "v27.0.0",
        "GITHUB_REF": "refs/heads/development",
        "GITHUB_SHA": pipeline_sha or head,
    }
    return subprocess.run(
        ["bash", "-c", guard_script()],
        cwd=work,
        env=env,
        capture_output=True,
        text=True,
    )


def test_source_equal_to_development_passes(repo) -> None:
    result = run_guard(repo, str(repo["candidate"]))

    assert result.returncode == 0, result.stdout + result.stderr


def test_pipeline_only_descendant_of_the_candidate_passes(repo) -> None:
    commit(
        Path(str(repo["work"])),
        {
            ".github/workflows/promote-stage.yml": "name: b\n",
            ".github/workflows/new-flow.yaml": "name: c\n",
            "tests/pipeline/test_y.py": "# t2\n",
        },
        "pipeline only",
    )

    result = run_guard(repo, str(repo["candidate"]))

    assert result.returncode == 0, result.stdout + result.stderr
    assert "differs only in workflow and pipeline-test files" in result.stdout


@pytest.mark.parametrize(
    "files",
    [
        {"src/app.py": "VALUE = 2\n"},
        {".github/scripts/helper.py": "# changed\n"},
        {"requirements.txt": "x==1\n"},
        {"docs/readme.md": "doc\n"},
        {"tests/test_app.py": "# application test\n"},
        {"tests/pipeline/sub/test_z.py": "# nested\n"},
        {".github/workflows/promote-stage.yml": "name: b\n", "src/app.py": "VALUE = 3\n"},
    ],
)
def test_change_outside_the_pipeline_paths_fails_closed(repo, files) -> None:
    commit(Path(str(repo["work"])), files, "mixed")

    result = run_guard(repo, str(repo["candidate"]))

    assert result.returncode != 0
    assert "changed outside the pipeline-only paths" in result.stdout


def test_deleted_application_file_fails_closed(repo) -> None:
    work = Path(str(repo["work"]))
    git(work, "rm", "-q", "src/app.py")
    git(work, "commit", "-q", "-m", "remove app")

    result = run_guard(repo, str(repo["candidate"]))

    assert result.returncode != 0
    assert "src/app.py" in result.stdout


def test_source_that_is_not_an_ancestor_fails_closed(repo) -> None:
    work = Path(str(repo["work"]))
    git(work, "checkout", "-q", "-b", "side", str(repo["candidate"]))
    side = commit(work, {"tests/pipeline/test_side.py": "# side\n"}, "side")
    git(work, "push", "-q", "origin", "side")
    git(work, "checkout", "-q", "development")
    commit(work, {"tests/pipeline/test_dev.py": "# dev\n"}, "dev")

    result = run_guard(repo, side)

    assert result.returncode != 0
    assert "is not its ancestor" in result.stdout


def test_pipeline_that_is_not_the_current_development_head_fails_closed(repo) -> None:
    work = Path(str(repo["work"]))
    commit(work, {"tests/pipeline/test_n.py": "# n\n"}, "reviewed pipeline")
    stale = git(work, "rev-parse", "HEAD")
    git(work, "push", "-q", "origin", "development")
    commit(work, {"tests/pipeline/test_m.py": "# m\n"}, "newer pipeline")

    result = run_guard(repo, str(repo["candidate"]), pipeline_sha=stale)

    assert result.returncode != 0
    assert "must run the current development pipeline" in result.stdout


def test_other_authority_checks_remain_in_the_guard() -> None:
    script = guard_script()

    for fragment in (
        "^ghcr\\.io/theriark/nowlert-ce@sha256:[0-9a-f]{64}$",
        "Source commit must be a full lowercase 40-character SHA",
        "documentation_manifest_sha256 must be 64 lowercase hex characters",
        "rc_tag must look like",
        "Stage promotion must be launched from development",
    ):
        assert fragment in script, fragment


def test_sealed_candidate_stays_bound_to_the_original_source() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    assert '[[ "${TAG_TARGET}" == "${SOURCE_COMMIT}" ]]' in text
    assert '"$(jq -r \'.head_sha\' <<<"${RUN}")" == "${SOURCE_COMMIT}"' in text
    assert "ref: ${{ inputs.source_commit }}" in text
    assert "group: nowlert-ce-stage-promotion" in text
    assert "cancel-in-progress: false" in text
