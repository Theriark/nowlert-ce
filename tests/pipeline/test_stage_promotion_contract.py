"""Input and completion-receipt contract of the Stage promotion workflow.

The tests only read workflow text: they open no network connection, so they stay
silent inside the network-isolated Stage gate. The source-ancestry tests run the
workflow's own git commands against throwaway local repositories only.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"

# Registered workflow input -> private publisher controller value.
REGISTERED_INPUT_MAPPING = {
    "ce_image": "image",
    "source_commit": "commit",
    "change_reference": "requestId",
    "version": "version",
    "development_run_id": "developmentRun",
    "request_id": "requestId",
    "documentation_manifest_sha256": "documentationManifestSha256",
    "rc_tag": "rcTag",
}

# Receipt object key -> jq expression in the receipt step. Every value is a jq
# variable bound with --arg/--argjson, except the two literals.
EXPECTED_RECEIPT = {
    "schemaVersion": "1",
    "kind": '"nowlert-ce-stage-promotion"',
    "repository": "$repository",
    "requestId": "$requestId",
    "version": "$version",
    "rcTag": "$rcTag",
    "rcTagObjectSha": "$rcTagObjectSha",
    "sourceCommit": "$sourceCommit",
    "image": "$image",
    "imageDigest": "$imageDigest",
    "documentationManifestSha256": "$manifest",
    "developmentRunId": "$developmentRunId",
    "rcWorkflowRunId": "$rcWorkflowRunId",
    "gateCycle": "$gateCycle",
    "stagePromotionRunId": "$stagePromotionRunId",
    "runAttempt": "$runAttempt",
    "stageApplicationId": "$stageApplicationId",
    "stageHealthUrl": "$stageHealthUrl",
    "stageBranchSha": "$stageBranchSha",
    "changeReference": "$changeReference",
    "rebuilt": "false",
    "completedAt": "$completedAt",
}

# jq variable -> shell value it is bound to in the receipt step.
EXPECTED_BINDINGS = {
    "repository": "${GITHUB_REPOSITORY}",
    "requestId": "${REQUEST_ID}",
    "version": "${RELEASE_VERSION}",
    "rcTag": "${RC_TAG}",
    "rcTagObjectSha": "${RC_TAG_OBJECT_SHA}",
    "sourceCommit": "${SOURCE_COMMIT}",
    "image": "${PROMOTION_IMAGE}",
    "imageDigest": "${IMAGE_DIGEST}",
    "manifest": "${DOCUMENTATION_MANIFEST_SHA256}",
    "developmentRunId": "${DEVELOPMENT_RUN_ID}",
    "rcWorkflowRunId": "${RC_WORKFLOW_RUN_ID}",
    "gateCycle": "${GATE_CYCLE}",
    "stagePromotionRunId": "${GITHUB_RUN_ID}",
    "runAttempt": "${GITHUB_RUN_ATTEMPT}",
    "stageApplicationId": "${CE_STAGE_APPLICATION_ID}",
    "stageHealthUrl": "${CE_STAGE_HEALTH_URL}",
    "stageBranchSha": "${STAGE_SHA}",
    "changeReference": "${SAFE_CHANGE_REFERENCE}",
    "completedAt": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
}


def load(name: str) -> tuple[str, dict]:
    text = (WORKFLOWS / name).read_text(encoding="utf-8")
    return text, yaml.safe_load(text)


def triggers(payload: dict) -> dict:
    # PyYAML reads the bare key `on` as the boolean True.
    return payload.get("on", payload.get(True))


def steps() -> list[dict]:
    _, payload = load("promote-stage.yml")
    return payload["jobs"]["promote"]["steps"]


def step_index(name: str) -> int:
    for index, step in enumerate(steps()):
        if step.get("name") == name:
            return index
    raise AssertionError(f"missing step {name!r}")


def step(name: str) -> dict:
    return steps()[step_index(name)]


def receipt_script() -> str:
    return step("Emit verified Stage completion receipt")["run"]


def receipt_bindings(script: str) -> dict[str, str]:
    return dict(re.findall(r'--arg(?:json)?\s+(\w+)\s+"([^"]*)"', script))


def receipt_object(script: str) -> dict[str, str]:
    match = re.search(r"'\{(.*?)\}'", script, re.DOTALL)
    assert match, "receipt jq object not found"
    pairs = re.findall(r"(\w+):\s*([^,\n]+)", match.group(1))
    return {key: value.strip() for key, value in pairs}


def test_stage_workflow_accepts_exactly_the_registered_inputs() -> None:
    _, payload = load("promote-stage.yml")
    inputs = triggers(payload)["workflow_dispatch"]["inputs"]

    assert set(inputs) == set(REGISTERED_INPUT_MAPPING)
    for name, definition in inputs.items():
        assert definition["type"] == "string", name
        assert definition["required"] is True, name

    # The publishing contract names the image input `image`; the registered
    # mapping dispatches `ce_image`. GitHub rejects an undeclared input, so the
    # registered names are authoritative here.
    assert "image" not in inputs


def test_stage_run_name_is_publishing_request_id() -> None:
    _, payload = load("promote-stage.yml")

    assert payload["run-name"] == "publishing:${{ inputs.request_id }}"
    # finalize_release.py matches the workflow name of the Stage run.
    assert payload["name"] == "Promote CE to Stage"


def test_stage_promotion_shares_the_serial_group_without_cancelling() -> None:
    _, stage = load("promote-stage.yml")
    _, rc = load("prepare-rc.yml")

    assert stage["concurrency"]["group"] == rc["concurrency"]["group"]
    assert stage["concurrency"]["group"] == "nowlert-ce-stage-promotion"
    assert stage["concurrency"]["cancel-in-progress"] is False
    assert rc["concurrency"]["cancel-in-progress"] is False


def test_stage_permissions_are_least_privilege() -> None:
    text, payload = load("promote-stage.yml")

    assert payload["permissions"] == {
        "contents": "write",
        "actions": "read",
        "packages": "read",
    }
    assert "id-token: write" not in text


def test_github_token_is_scoped_to_the_steps_that_call_gh() -> None:
    _, payload = load("promote-stage.yml")

    assert "GH_TOKEN" not in payload["jobs"]["promote"]["env"]
    callers = [
        item for item in steps() if re.search(r"\bgh (api|release)\b", item.get("run", ""))
    ]
    assert len(callers) >= 3
    for item in callers:
        assert item["env"]["GH_TOKEN"] == "${{ github.token }}", item["name"]
    for item in steps():
        if item not in callers:
            assert "GH_TOKEN" not in item.get("env", {}), item["name"]


def test_inputs_reach_scripts_only_through_the_environment() -> None:
    for item in steps():
        script = item.get("run")
        if script is not None:
            assert "${{ inputs." not in script, item.get("name")

    _, payload = load("promote-stage.yml")
    env = payload["jobs"]["promote"]["env"]
    for name, value in {
        "PROMOTION_IMAGE": "ce_image",
        "SOURCE_COMMIT": "source_commit",
        "CHANGE_REFERENCE": "change_reference",
        "RELEASE_VERSION": "version",
        "DEVELOPMENT_RUN_ID": "development_run_id",
        "REQUEST_ID": "request_id",
        "DOCUMENTATION_MANIFEST_SHA256": "documentation_manifest_sha256",
        "RC_TAG": "rc_tag",
    }.items():
        assert env[name] == "${{ inputs." + value + " }}", name


def test_stage_verifies_the_sealed_candidate_before_any_write() -> None:
    verify = step_index("Verify the release candidate tag, prerelease and Development run")
    digest = step_index("Verify the immutable image digest")
    gate = step_index("Run full notification-silent CE Stage gate")
    deploy = step_index("Promote CE to Stage")
    smoke = step_index("Run notification-silent CE Stage promotion smoke")
    advance = step_index("Advance Stage source branch")
    receipt = step_index("Emit verified Stage completion receipt")

    assert verify < digest < gate < deploy < smoke < advance < receipt

    text, _ = load("promote-stage.yml")
    for fragment in (
        "git/ref/tags/${RC_TAG}",
        '== "tag"',
        "sourceCommit",
        "imageDigest",
        "developmentRunId",
        "documentationManifestSha256",
        "isPrerelease",
        "${IMAGE_REPOSITORY}@${IMAGE_DIGEST}",
        "imagetools inspect",
    ):
        assert fragment in text, fragment


def test_rc_workflow_run_is_a_prepare_rc_dispatch_on_development() -> None:
    script = step("Verify the release candidate tag, prerelease and Development run")["run"]
    start = script.index('RC_RUN="$(gh api')
    end = script.index('echo "tag_object_sha=')
    block = script[start:end]

    for field, value in (
        ("path", ".github/workflows/prepare-rc.yml"),
        ("event", "workflow_dispatch"),
        ("head_branch", "development"),
        ("status", "completed"),
        ("conclusion", "success"),
    ):
        assert f"jq -r '.{field}' <<<\"${{RC_RUN}}\")\" == \"{value}\"" in block, field

    outputs = script[end:]
    for name in ("tag_object_sha", "rc_workflow_run_id", "gate_cycle", "image_digest"):
        assert f"echo \"{name}=" in outputs, name


def test_stage_promotes_the_existing_digest_without_rebuilding() -> None:
    text, _ = load("promote-stage.yml")

    assert "docker/build-push-action" not in text
    assert "docker build " not in text
    assert "gh api --method POST" not in text  # never mints or moves a tag
    assert "gh release create" not in text
    assert '--image "${PROMOTION_IMAGE}"' in text
    assert '--title "Stage ${SOURCE_COMMIT}"' in text
    assert '--description "nowlert-ce GitHub Actions run ${GITHUB_RUN_ID}"' in text
    assert "Rebuild performed: no" in text


def test_receipt_object_and_bindings_are_exactly_the_contract() -> None:
    script = receipt_script()

    # Removing or renaming a key, or pointing one at the wrong jq variable
    # (for example the manifest binding), changes these dictionaries.
    assert receipt_object(script) == EXPECTED_RECEIPT
    assert receipt_bindings(script) == EXPECTED_BINDINGS

    # The receipt carries no deployment id: deploy does not expose one.
    assert "deploymentId" not in script
    assert "DEPLOYMENT_ID" not in script


def test_receipt_inputs_come_from_the_verified_rc_outputs() -> None:
    env = step("Emit verified Stage completion receipt")["env"]

    assert env["IMAGE_DIGEST"] == "${{ steps.rc.outputs.image_digest }}"
    assert env["RC_TAG_OBJECT_SHA"] == "${{ steps.rc.outputs.tag_object_sha }}"
    assert env["RC_WORKFLOW_RUN_ID"] == "${{ steps.rc.outputs.rc_workflow_run_id }}"
    assert env["GATE_CYCLE"] == "${{ steps.rc.outputs.gate_cycle }}"


def test_receipt_is_uploaded_and_logged() -> None:
    text, _ = load("promote-stage.yml")

    assert "STAGE_PROMOTION_RECEIPT" in text
    assert "stage-promotion-receipt.json" in text
    assert "actions/upload-artifact@v7" in text
    assert "nowlert-ce-stage-promotion-${{ github.run_id }}" in text

    upload = step("Upload Stage completion receipt")
    assert upload["with"]["if-no-files-found"] == "error"
    assert upload["with"]["path"] == "stage-promotion-receipt.json"


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
    # The release finalizer reads the image digest from the Stage run logs.
    assert "Promoting ${PROMOTION_IMAGE}" in text


# --- Source binding: the sealed source must be part of development's history ---
# --- and must never move Stage backwards ---


def configuration_script() -> str:
    return step("Verify CE Stage configuration")["run"]


def ancestry_gate_script() -> str:
    """The workflow's own fetch + source-binding commands, unmodified."""
    script = configuration_script()
    return "set -euo pipefail\n" + script[script.index("git fetch origin") :]


def git(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_SYSTEM": os.devnull,
            "GIT_AUTHOR_NAME": "test",
            "GIT_AUTHOR_EMAIL": "test@example.invalid",
            "GIT_COMMITTER_NAME": "test",
            "GIT_COMMITTER_EMAIL": "test@example.invalid",
        },
    )
    return result.stdout.strip()


def commit(cwd: Path, name: str) -> str:
    (cwd / name).write_text(name, encoding="utf-8")
    git(cwd, "add", name)
    git(cwd, "commit", "-q", "-m", name)
    return git(cwd, "rev-parse", "HEAD")


def history(tmp_path: Path) -> dict[str, str]:
    """Local `origin`: development c1 -> c2 -> c3, stage at c1, plus side commits."""
    origin = tmp_path / "origin"
    origin.mkdir()
    git(origin, "init", "-q", "--initial-branch=development")
    c1 = commit(origin, "c1")
    c2 = commit(origin, "c2")
    c3 = commit(origin, "c3")
    git(origin, "branch", "stage", c1)

    # A commit on a line that left development at c1: it can sit on Stage but is
    # neither ahead of nor behind c2 and c3.
    git(origin, "checkout", "-q", "-b", "diverged", c1)
    d1 = commit(origin, "d1")
    git(origin, "checkout", "-q", "development")

    work = tmp_path / "work"
    work.mkdir()
    git(work, "init", "-q", "--initial-branch=work")
    git(work, "remote", "add", "origin", str(origin))
    git(work, "fetch", "-q", "origin", "development")

    # A commit that exists locally but is not part of development's history.
    git(work, "checkout", "-q", "-b", "side", c1)
    side = commit(work, "side")
    return {
        "c1": c1,
        "c2": c2,
        "c3": c3,
        "d1": d1,
        "side": side,
        "origin": str(origin),
        "work": str(work),
    }


def set_stage(commits: dict[str, str], sha: str) -> None:
    git(Path(commits["origin"]), "branch", "-f", "stage", sha)


def run_gate(commits: dict[str, str], source_commit: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", "-c", ancestry_gate_script()],
        cwd=commits["work"],
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_SYSTEM": os.devnull,
            "SOURCE_COMMIT": source_commit,
        },
    )


def test_stage_source_may_be_an_older_ancestor_of_development(tmp_path: Path) -> None:
    commits = history(tmp_path)

    # The sealed RC predates later development merges (c1 and c2 are behind c3).
    for older in (commits["c1"], commits["c2"]):
        result = run_gate(commits, older)
        assert result.returncode == 0, result.stdout + result.stderr

    # The development head itself is still accepted.
    result = run_gate(commits, commits["c3"])
    assert result.returncode == 0, result.stdout + result.stderr


def test_stage_source_outside_development_history_is_rejected(tmp_path: Path) -> None:
    commits = history(tmp_path)

    result = run_gate(commits, commits["side"])

    assert result.returncode != 0
    assert (
        f"::error::Stage source {commits['side']} is not an ancestor of current "
        f"development {commits['c3']}"
    ) in result.stdout


def test_stage_ahead_of_or_diverged_from_source_is_rejected(tmp_path: Path) -> None:
    commits = history(tmp_path)

    # Stage is already ahead of the sealed source: promoting it would downgrade Stage.
    set_stage(commits, commits["c3"])
    ahead = run_gate(commits, commits["c2"])
    assert ahead.returncode != 0
    assert (
        f"::error::Stage branch {commits['c3']} is not an ancestor of source "
        f"{commits['c2']}"
    ) in ahead.stdout

    # Stage sits on a line that diverged from the source: not a fast-forward either.
    set_stage(commits, commits["d1"])
    diverged = run_gate(commits, commits["c2"])
    assert diverged.returncode != 0
    assert (
        f"::error::Stage branch {commits['d1']} is not an ancestor of source "
        f"{commits['c2']}"
    ) in diverged.stdout


def test_stage_behind_or_equal_to_source_is_accepted(tmp_path: Path) -> None:
    commits = history(tmp_path)

    # Stage is behind the source (c1 < c3): a normal fast-forward promotion.
    set_stage(commits, commits["c1"])
    behind = run_gate(commits, commits["c3"])
    assert behind.returncode == 0, behind.stdout + behind.stderr

    # Stage already is the source (re-promotion of the same candidate).
    set_stage(commits, commits["c2"])
    equal = run_gate(commits, commits["c2"])
    assert equal.returncode == 0, equal.stdout + equal.stderr


def test_stage_source_check_is_ancestry_not_head_equality() -> None:
    script = configuration_script()

    assert (
        'git merge-base --is-ancestor "${SOURCE_COMMIT}" '
        "refs/remotes/origin/development"
    ) in script
    assert '"${SOURCE_COMMIT}" == "${DEVELOPMENT_SHA}"' not in script

    # The check reads the freshly fetched development, after the launch-branch guard.
    assert script.index('"${GITHUB_REF}" == "refs/heads/development"') < script.index(
        "git fetch origin"
    )
    assert script.index("git fetch origin") < script.index("git merge-base --is-ancestor")


def test_stage_guard_rejects_a_stage_ahead_of_the_source_before_any_deploy() -> None:
    script = configuration_script()

    assert "+refs/heads/stage:refs/remotes/origin/stage" in script
    assert (
        'git merge-base --is-ancestor refs/remotes/origin/stage "${SOURCE_COMMIT}"'
    ) in script
    # It runs after the development ancestry check and in the guard step, which
    # precedes every step that writes (image deploy and the stage branch update).
    assert script.index(
        'git merge-base --is-ancestor "${SOURCE_COMMIT}" refs/remotes/origin/development'
    ) < script.index("+refs/heads/stage:refs/remotes/origin/stage")
    assert step_index("Verify CE Stage configuration") < step_index("Promote CE to Stage")


def test_stage_keeps_every_other_source_binding() -> None:
    rc_script = step("Verify the release candidate tag, prerelease and Development run")["run"]

    # RC tag target, sealed digest, and the Development run's head SHA stay exact.
    assert '"${TAG_TARGET}" == "${SOURCE_COMMIT}"' in rc_script
    assert ".sourceCommit == $sourceCommit" in rc_script
    assert ".imageDigest == $imageDigest" in rc_script
    assert "jq -r '.head_sha' <<<\"${RUN}\")\" == \"${SOURCE_COMMIT}\"" in rc_script

    # The image digest is bound to the source through its sha-<SOURCE> tag.
    digest_script = step("Verify the immutable image digest")["run"]
    assert 'SHA_TAG="${IMAGE_REPOSITORY}:sha-${SOURCE_COMMIT}"' in digest_script
    assert '"${TAG_DIGEST}" == "${IMAGE_DIGEST}"' in digest_script

    # The full gate tests the sealed source, not whatever development is now.
    assert step("Checkout candidate source for the full gate")["with"]["ref"] == (
        "${{ inputs.source_commit }}"
    )

    # The stage branch only fast-forwards: history that is not ahead is rejected.
    advance = step("Advance Stage source branch")["run"]
    assert '[[ "${BEHIND_BY}" == "0" && "${STATUS}" == "ahead" ]]' in advance
    assert "-F force=false" in advance
