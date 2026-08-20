"""Release metadata invariants for Nowlert CE v3.1.2."""

import json
from pathlib import Path

from version import EDITION, EDITION_SLUG, REPOSITORY, VERSION


ROOT = Path(__file__).resolve().parents[1]


def test_application_version_and_repository_are_current():
    assert VERSION == "3.1.2"
    assert EDITION == "Community Edition"
    assert EDITION_SLUG == "ce"
    assert REPOSITORY == "https://github.com/Theriark/nowlert-ce"


def test_public_enterprise_release_manifest_is_valid():
    manifest = json.loads(
        (ROOT / "release-manifests" / "nowlert-ee.json").read_text(
            encoding="utf-8"
        )
    )

    assert manifest["edition"] == "ee"
    assert manifest["version"] == "3.0.0"
    assert "release_url" in manifest


def test_readme_release_metadata_is_current():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "stable-v3.1.2-F4C542" in readme
    assert "| **Current Stable Release** | **v3.1.2** |" in readme
    assert "https://github.com/Theriark/nowlert-ce/releases" in readme
    assert "stable-v3.1.1-F4C542" not in readme


def test_changelog_preserves_release_history():
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    assert "## 3.1.1 - 2026-08-14" in changelog
    assert "## 3.1.0 - 2026-08-08" in changelog
    assert "## 3.0.0 - 2026-07-29" in changelog
    assert "## 2.5.5 - 2026-07-27" in changelog
    assert changelog.index("## Unreleased") < changelog.index("## 3.1.1")
    assert changelog.index("## 3.1.1") < changelog.index("## 3.1.0")
    assert changelog.index("## 3.1.0") < changelog.index("## 3.0.0")


def test_historical_v300_v310_and_v311_documents_remain_historical():
    v300_notes = ROOT / "docs" / "releases" / "v3.0.0.md"
    v300_checklist = ROOT / "docs" / "v3.0.0-acceptance-checklist.md"
    v310_notes = ROOT / "docs" / "releases" / "v3.1.0.md"
    v311_notes = ROOT / "docs" / "releases" / "v3.1.1.md"
    v311_checklist = ROOT / "docs" / "v3.1.1-qa-checklist.md"
    docker_hub = (ROOT / "DOCKERHUB_README.md").read_text(encoding="utf-8")

    assert v300_notes.read_text(encoding="utf-8").startswith(
        "# Nowlert v3.0.0 release notes"
    )
    assert v300_checklist.read_text(encoding="utf-8").startswith(
        "# Nowlert v3.0.0 acceptance checklist"
    )
    assert v310_notes.read_text(encoding="utf-8").startswith(
        "# Nowlert v3.1.0 release notes"
    )
    assert v311_notes.read_text(encoding="utf-8").startswith(
        "# Nowlert CE v3.1.1 release notes"
    )
    assert v311_checklist.read_text(encoding="utf-8").startswith(
        "# Nowlert CE v3.1.1 QA checklist"
    )
    assert "current stable release is **v3.1.2**" in docker_hub.casefold()
    assert "theriark/nowlert-ce:3.1.2" in docker_hub


def test_historical_v255_release_identity_is_preserved():
    notes = (ROOT / "docs" / "releases" / "v2.5.5.md").read_text(
        encoding="utf-8"
    )

    assert notes.startswith("# Nowlert v2.5.5 release notes")


def test_quick_starts_prepare_platform_state():
    for path in (ROOT / "README.md", ROOT / "DOCKERHUB_README.md"):
        document = path.read_text(encoding="utf-8")

        assert "mkdir -p logs/emails secrets state" in document
        assert "chmod 700 logs logs/emails secrets state" in document


def test_production_defaults_are_versioned_and_compatible():
    environment = (ROOT / ".env.example").read_text(encoding="utf-8")
    compose = (ROOT / "compose.production.yaml").read_text(encoding="utf-8")

    assert "NOWLERT_IMAGE=theriark/nowlert-ce:3.1.2" in environment
    assert "theriark/nowlert-ce:3.1.2" in compose
    assert "NOWLERT_IMAGE" in compose
    assert "NOWLERT_EXTERNAL_BACKUP_DIR" in compose
    assert "/nowlert/external-backups" in compose


def test_release_notes_cover_v312_compatibility_and_rollback():
    notes = (ROOT / "docs" / "releases" / "v3.1.2.md").read_text(
        encoding="utf-8"
    )

    for heading in (
        "## Highlights",
        "## Compatibility",
        "## Upgrade from v3.1.1",
        "## Rollback",
    ):
        assert heading in notes

    assert "schema **9**" in notes
    assert "platform_database_v1" in notes
    assert "without rebuild" in notes.casefold()


def test_release_workflow_is_guarded_and_reuses_approved_image():
    release = (ROOT / ".github" / "workflows" / "docker-release.yml").read_text(
        encoding="utf-8"
    )
    finalization = (
        ROOT / ".github" / "workflows" / "finalize-release.yml"
    ).read_text(encoding="utf-8")
    stage = (ROOT / ".github" / "workflows" / "promote-stage.yml").read_text(
        encoding="utf-8"
    )

    assert "Verify release repository identity" in release
    assert '${GITHUB_REPOSITORY,,}' in release
    assert '"theriark/nowlert-ce"' in release

    assert "final_image:" in release
    assert "docker://ghcr.io/theriark/nowlert-ce:${VERSION}" in release
    assert "docker://docker.io/theriark/nowlert-ce:${VERSION}" in release
    assert "skopeo copy --all --preserve-digests" in release
    assert "docker/build-push-action" not in release

    assert '--title "Nowlert CE ${VERSION}"' in finalization
    assert 'gh release create "${VERSION}"' in finalization
    assert "Release finalization must be launched from main" in finalization
    assert '[[ "${VERSION}" == "v${SOURCE_VERSION}" ]]' in finalization
    assert "Release tag ${VERSION} does not match source version" in finalization
    assert 'docs/releases/${VERSION}.md' in finalization
    assert 'docs/${VERSION}-qa-checklist.md' in finalization

    assert "-F force=false" in stage
    assert "-F force=true" not in stage
    assert "Waiting for stage ref propagation" in stage

    assert "fortpt/nowlert:" not in release
    assert "ghcr.io/fortpt/nowlert:" not in release


def test_release_workflows_use_current_action_majors():
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    release = (ROOT / ".github" / "workflows" / "docker-release.yml").read_text(
        encoding="utf-8"
    )

    assert "actions/checkout@v7" in ci
    assert "actions/setup-python@v7" in ci
    assert "actions/setup-node@v7" in ci

    assert "actions/checkout@v7" in release
    assert "docker/login-action@v4" in release
    assert "docker/setup-buildx-action" not in release
    assert "docker/build-push-action" not in release
    assert "skopeo copy --all --preserve-digests" in release


def test_development_workflow_targets_only_ce():
    workflow = (
        ROOT / ".github" / "workflows" / "docker-development.yml"
    ).read_text(encoding="utf-8")

    assert "IMAGE: ghcr.io/theriark/nowlert-ce" in workflow
    assert "environment: development" in workflow
    assert "DOKPLOY_CE_DEVELOPMENT_APPLICATION_ID" in workflow
    assert "DOKPLOY_EE_DEVELOPMENT_APPLICATION_ID" not in workflow
