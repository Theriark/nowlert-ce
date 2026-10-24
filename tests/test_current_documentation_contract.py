"""Current operator docs agree with migrations and exclude withdrawn captures."""

from pathlib import Path
import re

import pytest

from storage.migrations import LATEST_SCHEMA_VERSION


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_GUIDES = (
    "README.md", "DOCKERHUB_README.md", "docs/platform-state.md",
    "docs/current-configuration-model.md", "docs/webui.md",
    "docs/database-authoritative-resources.md", "docs/deployment.md",
)
WITHDRAWN_IMAGES = (
    "unifi-setup/protect-alarms.png",
    "email-setup/mailboxes-healthy-redacted.png",
    "email-setup/noip-warning-redacted.png",
    "hardware-setup/portainer-tls-config.png",
    "monitoring-setup/dell-native-delivery.png",
    "home-assistant-setup/enabled-automations.png",
    "home-assistant-setup/native-test.png",
    "home-assistant-setup/transport-response.png",
    "application-setup/checkmk-single-recipient.png",
    "application-setup/metabase-delivery-alert.jpg",
    "truenas-setup/info-alert-service.png",
    "portainer-setup/xen-backup-report-coverage.png",
    "monitoring-setup/portainer-native-delivery-lifecycle.png",
)


@pytest.mark.parametrize("relative", SCHEMA_GUIDES)
def test_current_schema_matches_migrations(relative):
    text = (ROOT / relative).read_text(encoding="utf-8")
    match = re.search(r"Current development uses database schema \*\*(\d+)\*\*", text)
    assert match, f"{relative} must identify the development schema separately from release history"
    assert int(match[1]) == LATEST_SCHEMA_VERSION


def test_current_guides_include_security_step_for_event_tokens():
    for path in (ROOT / "docs/guides").glob("*.md"):
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"Profile\s*→\s*API tokens", text), path
    section = (ROOT / "docs/webui.md").read_text(encoding="utf-8").split("### Event API tokens", 1)[1].split("###", 1)[0]
    assert "Profile menu → Security → API tokens" in section


@pytest.mark.parametrize("relative", (
    "checkmk.md", "github-actions.md", "metabase.md", "radarr.md",
    "semaphore.md", "sonarr.md", "guides/application-notification-setup.md",
))
def test_application_setup_uses_actual_token_navigation(relative):
    text = (ROOT / "docs" / relative).read_text(encoding="utf-8")
    assert "Profile menu → Security → API tokens → New token" in text


@pytest.mark.parametrize("relative", WITHDRAWN_IMAGES)
def test_exposed_captures_are_withdrawn_from_current_checkout(relative):
    assert not (ROOT / "docs/images" / relative).exists()
    for path in [ROOT / "README.md", ROOT / "DOCKERHUB_README.md", *(ROOT / "docs").rglob("*.md")]:
        if "releases" not in path.parts and path.name != "screenshot-privacy.md":
            assert relative not in path.read_text(encoding="utf-8"), path


# The folder keeps the name of the first release candidate; its contents are
# the reviewed screenshot set of the v27.0.0-rc.7 documentation package.
CURRENT_CAPTURE_DIR = "images/v27.0.0-rc.1/"


def test_preview_shows_current_captures_and_history_stays_separate():
    docs_index = (ROOT / "docs/README.md").read_text(encoding="utf-8")
    assert "## Historical screenshots" in docs_index
    assert "Historical v3.1.0" in docs_index
    assert CURRENT_CAPTURE_DIR in docs_index
    for relative in ("README.md", "DOCKERHUB_README.md", "docs/webui.md"):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert CURRENT_CAPTURE_DIR in text, relative
        assert "images/v3.1.0-" not in text, relative
        assert "images/v27.0.0-rc.8/" not in text, relative
        assert "remains the current visual baseline" not in text


# While the disclosure of the Development test-data names (account, owner,
# destination and channel names) is an open point of
# docs/guides/screenshot-privacy.md, the front-page Preview may use only
# captures that show none of them. Each was opened at full size on
# 24 October 2026; extend this list only after the same check.
PREVIEW_CAPTURES = (
    "sign-in-empty-signed-out-390.png",
    "dashboard-live-admin-390.png",
    "routing-flow-live-admin-390.png",
)


@pytest.mark.parametrize("relative", ("README.md", "DOCKERHUB_README.md"))
def test_front_page_preview_uses_only_captures_without_test_data_names(relative):
    text = (ROOT / relative).read_text(encoding="utf-8")
    embedded = set(re.findall(r"images/v27\.0\.0-rc\.1/([\w.-]+\.png)", text))
    assert embedded == set(PREVIEW_CAPTURES), relative
    for name in PREVIEW_CAPTURES:
        assert (ROOT / "docs" / CURRENT_CAPTURE_DIR / name).stat().st_size > 0, name


def test_current_captures_have_index_and_embeds_resolve():
    folder = ROOT / "docs" / CURRENT_CAPTURE_DIR
    index = (folder / "README.md").read_text(encoding="utf-8")
    embedded = set()
    for relative in ("README.md", "docs/webui.md"):
        text = (ROOT / relative).read_text(encoding="utf-8")
        embedded.update(re.findall(r"images/v27\.0\.0-rc\.1/([\w.-]+\.png)", text))
    assert embedded
    for name in sorted(embedded):
        assert (folder / name).is_file(), name
        assert f"`{name}`" in index, name


def test_version_wording_distinguishes_stable_from_candidates():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    dockerhub = (ROOT / "DOCKERHUB_README.md").read_text(encoding="utf-8")
    for text in (readme, dockerhub):
        assert "v3.1.6" in text
        assert "v27.0.0" in text
        assert "fresh v3.1.6\nconfiguration" not in text
        assert "v27.0.0 is the current stable" not in text.casefold()
    assert "not a stable release" in readme
    assert "not stable releases" in dockerhub


def test_current_guides_follow_destination_route_navigation():
    webui = (ROOT / "docs/webui.md").read_text(encoding="utf-8")
    assert "### Sources" not in webui
    assert "### Routes" not in webui
    assert "### Inputs" not in webui
    assert "### Filtering" in webui
    assert "Manage routes" in webui
    for relative in ("centralise-homelab-smtp-alerts.md", "xen-orchestra-to-teams.md"):
        text = (ROOT / "docs/guides" / relative).read_text(encoding="utf-8")
        assert "**Routes**" not in text, relative
        assert "**Manage routes**" in text, relative
    readme = (ROOT / "README.md").read_text(encoding="utf-8").split("## WebUI", 1)[1].split("## ", 1)[0]
    for retired in ("Sources/integration catalogue", "- Routes;", "- Inputs;"):
        assert retired not in readme
