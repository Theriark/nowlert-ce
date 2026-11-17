"""Contract of the two one-button release workflows.

Gate 2 approval dispatches promote-stage.yml and Gate 3 approval dispatches
release.yml, both from development with no inputs. The tests only read workflow
text: they open no network connection, so they stay silent inside the
network-isolated Stage gate.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"
BUTTONS = {"promote-stage.yml": "promote", "release.yml": "release"}

# A step that contains one of these changes a tag, a branch, a release, a
# registry tag or a deployment.
WRITES = (
    "repos/${GITHUB_REPOSITORY}/git/tags\"",
    "repos/${GITHUB_REPOSITORY}/git/refs\"",
    "repos/${GITHUB_REPOSITORY}/git/commits\"",
    "--method PATCH",
    "gh release create",
    "skopeo copy",
    "dokploy_release.py deploy",
)
DRY_RUN_GUARD = 'if [[ "${DRY_RUN}" == "true" ]]; then'


def load(name: str) -> tuple[str, dict]:
    text = (WORKFLOWS / name).read_text(encoding="utf-8")
    return text, yaml.safe_load(text)


def triggers(payload: dict) -> dict:
    # PyYAML reads the bare key `on` as the boolean True.
    return payload.get("on", payload.get(True))


def steps(name: str) -> list[dict]:
    _, payload = load(name)
    return payload["jobs"][BUTTONS[name]]["steps"]


def step_index(name: str, title: str) -> int:
    for index, item in enumerate(steps(name)):
        if item.get("name") == title:
            return index
    raise AssertionError(f"missing step {title!r} in {name}")


def step(name: str, title: str) -> dict:
    return steps(name)[step_index(name, title)]


@pytest.mark.parametrize("name", sorted(BUTTONS))
def test_button_is_dispatch_only_with_one_optional_dry_run(name: str) -> None:
    _, payload = load(name)
    on = triggers(payload)

    assert set(on) == {"workflow_dispatch"}
    assert on["workflow_dispatch"]["inputs"] == {
        "dry_run": {
            "description": "Check everything and change nothing",
            "required": False,
            "default": False,
            "type": "boolean",
        }
    }
    # The gate's one-button detector rejects any required input.
    text, _ = load(name)
    assert "required: true" not in text


@pytest.mark.parametrize("name", sorted(BUTTONS))
def test_button_runs_only_from_development(name: str) -> None:
    first_script = next(item["run"] for item in steps(name) if "run" in item)
    assert 'refs/heads/development' in first_script
    assert "exit 1" in first_script


def test_buttons_share_one_serial_group_without_cancelling() -> None:
    groups = set()
    for name in BUTTONS:
        _, payload = load(name)
        assert payload["concurrency"]["cancel-in-progress"] is False, name
        groups.add(payload["concurrency"]["group"])
    assert groups == {"nowlert-ce-stage-promotion"}


def test_permissions_are_least_privilege() -> None:
    _, stage = load("promote-stage.yml")
    _, release = load("release.yml")

    assert stage["permissions"] == {
        "contents": "write",
        "actions": "read",
        "packages": "write",
    }
    assert release["permissions"] == {"contents": "write", "packages": "write"}
    for name in BUTTONS:
        text, _ = load(name)
        assert "id-token: write" not in text, name


@pytest.mark.parametrize("name", sorted(BUTTONS))
def test_github_token_is_scoped_to_the_steps_that_call_gh(name: str) -> None:
    _, payload = load(name)

    assert "GH_TOKEN" not in payload["jobs"][BUTTONS[name]]["env"]
    callers = [
        item for item in steps(name) if re.search(r"\bgh (api|release)\b", item.get("run", ""))
    ]
    assert callers
    for item in callers:
        assert item["env"]["GH_TOKEN"] == "${{ github.token }}", item["name"]
    for item in steps(name):
        if item not in callers:
            assert "GH_TOKEN" not in item.get("env", {}), item["name"]


@pytest.mark.parametrize("name", sorted(BUTTONS))
def test_inputs_reach_scripts_only_through_the_environment(name: str) -> None:
    for item in steps(name):
        script = item.get("run")
        if script is not None:
            assert "${{" not in script, item.get("name")

    _, payload = load(name)
    env = payload["jobs"][BUTTONS[name]]["env"]
    assert env["DRY_RUN"] == "${{ inputs.dry_run && 'true' || 'false' }}"


@pytest.mark.parametrize("name", sorted(BUTTONS))
def test_every_write_is_skipped_by_dry_run(name: str) -> None:
    writers = 0
    for item in steps(name):
        script = item.get("run", "")
        positions = [script.index(marker) for marker in WRITES if marker in script]
        if not positions:
            continue
        writers += 1
        title = item["name"]
        if item.get("if", "").startswith("${{ (steps.deploy.outcome == 'failure'"):
            # The rollback only runs after a real deployment wrote previous_image.
            assert "steps.deploy.outputs.previous_image != ''" in item["if"], title
            continue
        if item.get("if") == "${{ !inputs.dry_run }}":
            continue
        assert DRY_RUN_GUARD in script, title
        guard = script.index(DRY_RUN_GUARD)
        assert guard < min(positions), title
        assert "exit 0" in script[guard : min(positions)] or "continue" in script[
            guard : min(positions)
        ], title
    assert writers >= 4, name


def test_stage_promotion_order_matches_the_release_standard() -> None:
    name = "promote-stage.yml"
    order = [
        step_index(name, title)
        for title in (
            "Read the commit Development runs",
            "Resolve the immutable image digest",
            "Compute the release candidate tag",
            "Run full notification-silent CE Stage gate",
            "Tag the release candidate",
            "Push the immutable candidate image tag",
            "Promote CE to Stage",
            "Run notification-silent CE Stage promotion smoke",
            "Advance Stage source branch",
        )
    ]
    assert order == sorted(order)


def test_stage_promotes_what_development_runs_without_rebuilding() -> None:
    text, _ = load("promote-stage.yml")
    source = step("promote-stage.yml", "Read the commit Development runs")["run"]

    assert "CE_DEVELOPMENT_APPLICATION_ID: ivj7Ixgw2cP29g6riR2AH" in text
    assert "dokploy_release.py current-image" in source
    assert "SHA_TAG_PATTERN='^ghcr\\.io/theriark/nowlert-ce:sha-([0-9a-f]{40})$'" in source
    assert 'git merge-base --is-ancestor "${SOURCE_COMMIT}" refs/remotes/origin/development' in source
    assert 'git merge-base --is-ancestor refs/remotes/origin/stage "${SOURCE_COMMIT}"' in source
    assert "actions/workflows/ci.yml/runs?branch=development&event=push&status=success" in source

    assert "docker/build-push-action" not in text
    assert "docker build " not in text
    assert "release_tags.py next-rc" in text
    assert 'ref: ${{ steps.source.outputs.source_commit }}' in text
    assert "a candidate tag is never moved" in text
    assert '--title "Stage ${SOURCE_COMMIT}"' in text
    assert "Rebuild performed: no" in text


def test_stage_keeps_the_silent_gate_and_markers() -> None:
    text, _ = load("promote-stage.yml")

    for marker in (
        "STAGE CE SILENT FULL GATE PASSED",
        "STAGE CE SILENT PROMOTION SMOKE PASSED",
        "PASS: promotion gate network namespace has no default route",
        "External notification delivery during promotion: disabled",
        '"${UNSHARE_BIN}" --net',
    ):
        assert marker in text, marker

    advance = step("promote-stage.yml", "Advance Stage source branch")["run"]
    assert '[[ "${BEHIND_BY}" == "0" && "${STATUS}" == "ahead" ]]' in advance
    assert "-F force=false" in advance


def test_release_releases_what_stage_runs_and_is_idempotent() -> None:
    text, _ = load("release.yml")
    stage = step("release.yml", "Read what Stage runs")["run"]

    assert 'STAGE_SHA="$(git rev-parse refs/remotes/origin/stage)"' in stage
    assert "DIGEST_PATTERN='^ghcr\\.io/theriark/nowlert-ce@(sha256:[0-9a-f]{64})$'" in stage
    assert "release_tags.py stage-candidate" in stage
    assert "docker/build-push-action" not in text
    assert "dokploy_release.py deploy" not in text

    # Each step accepts what a previous run already created.
    assert "already is ${IMAGE_DIGEST}" in text
    assert "already tags ${STAGE_SHA}" in text
    assert "already exists:" in text
    assert "already contains stage" in text
    assert "a version tag is never moved" in text


def test_release_merges_stage_into_main_with_stage_files() -> None:
    merge = step("release.yml", "Merge stage into main")["run"]

    assert 'git merge-base --is-ancestor "${STAGE_SHA}" "${MAIN_SHA}"' in merge
    assert 'STAGE_TREE="$(git rev-parse "${STAGE_SHA}^{tree}")"' in merge
    assert '-f tree="${STAGE_TREE}"' in merge
    assert '-f "parents[]=${MAIN_SHA}"' in merge
    assert '-f "parents[]=${STAGE_SHA}"' in merge
    assert "git/refs/heads/main" in merge
    assert "-F force=false" in merge
    assert '[[ "${MAIN_TREE}" == "${STAGE_TREE}" ]]' in merge

    text, _ = load("release.yml")
    # main is never merged into development.
    assert "git/refs/heads/development" not in text


def test_release_notes_come_from_pull_requests_since_the_last_release() -> None:
    notes = step("release.yml", "Create the GitHub Release")["run"]

    assert 'releases/latest" --jq \'.tag_name\'' in notes
    assert "releases/generate-notes" in notes
    assert "previous_tag_name=" in notes
    assert "--verify-tag" in notes
