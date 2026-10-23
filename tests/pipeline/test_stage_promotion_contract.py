"""Input and completion-receipt contract of the Stage promotion workflow.

The tests only read workflow text: they open no network connection, so they stay
silent inside the network-isolated Stage gate.
"""

from __future__ import annotations

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

RECEIPT_FIELDS = (
    "schemaVersion",
    "repository",
    "requestId",
    "version",
    "rcTag",
    "rcTagObjectSha",
    "sourceCommit",
    "image",
    "imageDigest",
    "documentationManifestSha256",
    "developmentRunId",
    "rcWorkflowRunId",
    "gateCycle",
    "stagePromotionRunId",
    "stageApplicationId",
    "stageBranchSha",
    "rebuilt",
    "completedAt",
)


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


def test_inputs_reach_scripts_only_through_the_environment() -> None:
    for step in steps():
        script = step.get("run")
        if script is not None:
            assert "${{ inputs." not in script, step.get("name")

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


def test_stage_emits_a_complete_completion_receipt() -> None:
    text, _ = load("promote-stage.yml")

    for field in RECEIPT_FIELDS:
        assert f"{field}:" in text, field
    assert "rebuilt: false" in text
    assert "STAGE_PROMOTION_RECEIPT" in text
    assert "stage-promotion-receipt.json" in text
    assert "actions/upload-artifact@v7" in text
    assert "nowlert-ce-stage-promotion-${{ github.run_id }}" in text
    assert "GITHUB_RUN_ID" in text

    upload = steps()[step_index("Upload Stage completion receipt")]
    assert upload["with"]["if-no-files-found"] == "error"


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
