"""Current Nowlert CE v3.1.1 release/documentation contract."""

from pathlib import Path

from version import VERSION


ROOT = Path(__file__).resolve().parents[1]


CURRENT_SCREENSHOTS = (
    "v3.1.1-dashboard.png",
    "v3.1.1-routes.png",
    "v3.1.1-route-editor.png",
    "v3.1.1-users.png",
    "v3.1.1-backups.png",
    "v3.1.1-delivery-history.png",
    "v3.1.1-audit-log.png",
)


def test_v311_release_identity_is_consistent():
    assert VERSION == "3.1.1"

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    dockerhub = (ROOT / "DOCKERHUB_README.md").read_text(encoding="utf-8")
    environment = (ROOT / ".env.example").read_text(encoding="utf-8")
    compose = (ROOT / "compose.production.yaml").read_text(encoding="utf-8")
    release = (ROOT / "docs" / "releases" / "v3.1.1.md").read_text(
        encoding="utf-8"
    )
    checklist = (ROOT / "docs" / "v3.1.1-qa-checklist.md").read_text(
        encoding="utf-8"
    )

    assert "stable-v3.1.1-F4C542" in readme
    assert "**Current Stable Release** | **v3.1.1**" in readme
    assert "current stable release is **v3.1.1**" in dockerhub.casefold()
    assert "theriark/nowlert-ce:3.1.1" in dockerhub
    assert "NOWLERT_IMAGE=theriark/nowlert-ce:3.1.1" in environment
    assert "${NOWLERT_IMAGE:-theriark/nowlert-ce:3.1.1}" in compose
    assert release.startswith("# Nowlert CE v3.1.1 release notes")
    assert checklist.startswith("# Nowlert CE v3.1.1 QA checklist")


def test_v311_current_screenshots_are_packaged_and_referenced():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    webui = (ROOT / "docs" / "webui.md").read_text(encoding="utf-8")
    docs_index = (ROOT / "docs" / "README.md").read_text(encoding="utf-8")

    for filename in CURRENT_SCREENSHOTS:
        path = ROOT / "docs" / "images" / filename
        assert path.is_file(), filename
        assert path.stat().st_size > 0, filename
        assert filename in readme or filename in webui
        assert filename in docs_index


def test_v311_release_notes_cover_cumulative_qa_and_immutable_release():
    release = (ROOT / "docs" / "releases" / "v3.1.1.md").read_text(
        encoding="utf-8"
    )
    checklist = (ROOT / "docs" / "v3.1.1-qa-checklist.md").read_text(
        encoding="utf-8"
    )

    for issue in ("NCE-30", "NCE-31", "NCE-32", "NCE-33", "NCE-34", "NCE-35", "NCE-36", "NCE-37", "NCE-38", "NCE-39"):
        assert issue in release or issue in checklist

    assert "schema **9**" in release
    assert "platform_database_v1" in release
    assert "without rebuild" in release.casefold()
    assert "main == stage == source_commit" in checklist
    assert "alias publication reports `Image rebuild performed: no`" in checklist


def test_v311_deployment_docs_contain_cli_promotion_chain():
    deployment = (ROOT / "docs" / "deployment.md").read_text(encoding="utf-8")

    for workflow in (
        "promote-stage.yml",
        "promote-production-reference.yml",
        "finalize-release.yml",
        "docker-release.yml",
    ):
        assert f"gh workflow run {workflow}" in deployment

    assert "-F force=false" in deployment
    assert "No image rebuild is performed from the release tag." in deployment
    assert "there is no additional CE Dokploy `Production` deployment workflow" in deployment


def test_v311_changelog_entry_precedes_historical_v310():
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    assert "## 3.1.1 - 2026-08-14" in changelog
    assert changelog.index("## 3.1.1 - 2026-08-14") < changelog.index(
        "## 3.1.0 - 2026-08-08"
    )
