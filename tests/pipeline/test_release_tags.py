"""release_tags.py against throwaway local git repositories (no network)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / ".github" / "scripts" / "release_tags.py"
DIGEST_A = "sha256:" + "a" * 64
DIGEST_B = "sha256:" + "b" * 64
ENV = {
    **os.environ,
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_SYSTEM": os.devnull,
    "GIT_AUTHOR_NAME": "test",
    "GIT_AUTHOR_EMAIL": "test@example.invalid",
    "GIT_COMMITTER_NAME": "test",
    "GIT_COMMITTER_EMAIL": "test@example.invalid",
}


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True, env=ENV
    ).stdout.strip()


def repo(tmp_path: Path) -> tuple[Path, list[str]]:
    git(tmp_path, "init", "-q", "--initial-branch=development")
    commits = []
    for index in range(3):
        (tmp_path / f"f{index}").write_text(str(index), encoding="utf-8")
        git(tmp_path, "add", f"f{index}")
        git(tmp_path, "commit", "-q", "-m", f"c{index}")
        commits.append(git(tmp_path, "rev-parse", "HEAD"))
    return tmp_path, commits


def seal(cwd: Path, tag: str, commit: str, digest: str) -> None:
    message = json.dumps({"sourceCommit": commit, "imageDigest": digest})
    git(cwd, "tag", "-a", tag, "-m", message, commit)


def run(cwd: Path, command: str, commit: str, digest: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), command, "--commit", commit, "--digest", digest],
        cwd=cwd,
        capture_output=True,
        text=True,
        env=ENV,
    )


def choice(cwd: Path, command: str, commit: str, digest: str) -> dict:
    result = run(cwd, command, commit, digest)
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)


def test_first_candidate_is_27_0_0_rc_1(tmp_path: Path) -> None:
    cwd, commits = repo(tmp_path)
    git(cwd, "tag", "-a", "v3.1.6", "-m", "legacy", commits[0])

    assert choice(cwd, "next-rc", commits[2], DIGEST_A) == {
        "rcTag": "v27.0.0-rc.1",
        "version": "27.0.0",
        "number": 1,
        "reuse": False,
    }


def test_next_number_continues_the_unreleased_version(tmp_path: Path) -> None:
    cwd, commits = repo(tmp_path)
    seal(cwd, "v27.0.0-rc.4", commits[0], DIGEST_A)
    seal(cwd, "v27.0.0-rc.23", commits[1], DIGEST_A)

    result = choice(cwd, "next-rc", commits[2], DIGEST_B)
    assert result["rcTag"] == "v27.0.0-rc.24"
    assert result["reuse"] is False


def test_a_candidate_that_seals_the_commit_and_digest_is_reused(tmp_path: Path) -> None:
    cwd, commits = repo(tmp_path)
    seal(cwd, "v27.0.0-rc.1", commits[1], DIGEST_A)
    seal(cwd, "v27.0.0-rc.2", commits[2], DIGEST_A)

    result = choice(cwd, "next-rc", commits[2], DIGEST_A)
    assert result["rcTag"] == "v27.0.0-rc.2"
    assert result["reuse"] is True

    # A rebuilt image of the same commit gets a new number, never the old tag.
    rebuilt = choice(cwd, "next-rc", commits[2], DIGEST_B)
    assert rebuilt["rcTag"] == "v27.0.0-rc.3"
    assert rebuilt["reuse"] is False


def test_lightweight_or_unsealed_tags_are_counted_but_never_reused(tmp_path: Path) -> None:
    cwd, commits = repo(tmp_path)
    git(cwd, "tag", "v27.0.0-rc.5", commits[2])
    git(cwd, "tag", "-a", "v27.0.0-rc.6", "-m", "not json", commits[2])

    result = choice(cwd, "next-rc", commits[2], DIGEST_A)
    assert result["rcTag"] == "v27.0.0-rc.7"
    assert result["reuse"] is False


def test_after_a_release_the_next_minor_starts(tmp_path: Path) -> None:
    cwd, commits = repo(tmp_path)
    seal(cwd, "v27.0.0-rc.2", commits[1], DIGEST_A)
    git(cwd, "tag", "-a", "v27.0.0", "-m", "release", commits[1])

    # Released candidates are never reused, even for the same commit.
    assert choice(cwd, "next-rc", commits[1], DIGEST_A)["rcTag"] == "v27.1.0-rc.1"
    assert choice(cwd, "next-rc", commits[2], DIGEST_B)["rcTag"] == "v27.1.0-rc.1"


def test_stage_candidate_is_the_newest_tag_sealing_commit_and_digest(tmp_path: Path) -> None:
    cwd, commits = repo(tmp_path)
    seal(cwd, "v27.0.0-rc.1", commits[2], DIGEST_A)
    seal(cwd, "v27.0.0-rc.2", commits[2], DIGEST_B)
    seal(cwd, "v27.0.0-rc.3", commits[1], DIGEST_B)

    assert choice(cwd, "stage-candidate", commits[2], DIGEST_B) == {
        "rcTag": "v27.0.0-rc.2",
        "version": "27.0.0",
        "number": 2,
        "stableTag": "v27.0.0",
    }
    assert choice(cwd, "stage-candidate", commits[2], DIGEST_A)["rcTag"] == "v27.0.0-rc.1"


def test_stage_without_a_sealing_candidate_is_refused(tmp_path: Path) -> None:
    cwd, commits = repo(tmp_path)
    seal(cwd, "v27.0.0-rc.1", commits[1], DIGEST_A)

    result = run(cwd, "stage-candidate", commits[2], DIGEST_A)
    assert result.returncode == 1
    assert "No annotated v27 release candidate tag seals stage commit" in result.stderr


def test_malformed_arguments_are_refused(tmp_path: Path) -> None:
    cwd, commits = repo(tmp_path)

    assert run(cwd, "next-rc", "HEAD", DIGEST_A).returncode == 1
    assert run(cwd, "next-rc", commits[0], "sha256:short").returncode == 1
