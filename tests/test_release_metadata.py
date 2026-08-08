"""Release metadata invariants for Nowlert v3.1.0."""

import json
from pathlib import Path

from version import EDITION, EDITION_SLUG, REPOSITORY, VERSION


ROOT = Path(__file__).resolve().parents[1]


def test_application_version_and_repository_are_current():
    assert VERSION == "3.1.0"
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

    assert "stable-v3.1.0-F4C542" in readme
    assert "| **Current Stable Release** | **v3.1.0** |" in readme
    assert "| **Next Planned Release** | **v3.x** |" in readme
    assert "https://github.com/Theriark/nowlert-ce/releases" in readme


def test_changelog_preserves_history_and_adds_v310():
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    assert "## 3.1.0 - 2026-08-08" in changelog
    assert "## 3.0.0 - 2026-07-29" in changelog
    assert "## 2.5.5 - 2026-07-27" in changelog
    assert changelog.index("## Unreleased") < changelog.index("## 3.1.0")
    assert changelog.index("## 3.1.0") < changelog.index("## 3.0.0")
    assert changelog.index("## 3.0.0") < changelog.index("## 2.5.5")


def test_v300_release_documents_remain_historical():
    notes = ROOT / "docs" / "releases" / "v3.0.0.md"
    checklist = ROOT / "docs" / "v3.0.0-acceptance-checklist.md"
    docker_hub = (ROOT / "DOCKERHUB_README.md").read_text(
        encoding="utf-8"
    )

    assert notes.read_text(encoding="utf-8").startswith(
        "# Nowlert v3.0.0 release notes"
    )
    assert checklist.read_text(encoding="utf-8").startswith(
        "# Nowlert v3.0.0 acceptance checklist"
    )
    assert "current stable release is **v3.1.0**" in docker_hub
    assert "theriark/nowlert-ce:3.1.0" in docker_hub


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
    compose = (ROOT / "compose.production.yaml").read_text(
        encoding="utf-8"
    )

    assert "NOWLERT_IMAGE=theriark/nowlert-ce:3.1.0" in environment
    assert "theriark/nowlert-ce:3.1.0" in compose
    assert "NOWLERT_IMAGE" in compose
    assert "NOWLERT_EXTERNAL_BACKUP_DIR" in compose
    assert "/nowlert/external-backups" in compose


def test_release_notes_cover_cutover_rollback_and_schema():
    notes = (ROOT / "docs" / "releases" / "v3.0.0.md").read_text(
        encoding="utf-8"
    )

    for heading in (
        "## Upgrade",
        "## Repository and registry cutover",
        "## Runtime contract and rollback",
        "## Database and configuration",
        "## Acceptance",
    ):
        assert heading in notes

    assert "schema 9" in notes
    assert "platform_database_v1" in notes
    assert "Theriark/nowlert-ce" in notes
    assert "theriark/nowlert-ce:3.0.0" in notes
    assert "ghcr.io/theriark/nowlert-ce" in notes


def test_release_workflow_is_guarded_and_uses_nowlert_images():
    release = (
        ROOT / ".github" / "workflows" / "docker-release.yml"
    ).read_text(encoding="utf-8")

    assert "Verify release repository identity" in release
    assert '${GITHUB_REPOSITORY,,}' in release
    assert '"theriark/nowlert-ce"' in release
    assert (
        "theriark/nowlert-ce:${{ steps.version.outputs.version }}"
        in release
    )
    assert (
        "ghcr.io/theriark/nowlert-ce:${{ steps.version.outputs.version }}"
        in release
    )
    assert 'RELEASE_TITLE="Nowlert ${TAG}"' in release

    assert "            fortpt/nowlert:" not in release
    assert "            ghcr.io/fortpt/nowlert:" not in release


def test_release_workflows_use_current_action_majors():
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )
    release = (
        ROOT / ".github" / "workflows" / "docker-release.yml"
    ).read_text(encoding="utf-8")

    for value in (
        "actions/checkout@v7",
        "actions/setup-python@v7",
    ):
        assert value in ci
        assert value in release

    assert "actions/setup-node@v7" in ci
    assert "docker/login-action@v4" in release
    assert "docker/setup-buildx-action@v4" in release
    assert "docker/build-push-action@v7" in release


def test_development_workflow_targets_only_ce():
    workflow = (
        ROOT / ".github" / "workflows" / "docker-development.yml"
    ).read_text(encoding="utf-8")

    assert "IMAGE: ghcr.io/theriark/nowlert-ce" in workflow
    assert "environment: development" in workflow
    assert "DOKPLOY_CE_DEVELOPMENT_APPLICATION_ID" in workflow
    assert "DOKPLOY_EE_DEVELOPMENT_APPLICATION_ID" not in workflow
