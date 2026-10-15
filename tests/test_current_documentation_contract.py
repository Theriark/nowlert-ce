"""Current operator docs agree with migrations and exclude withdrawn captures."""

from pathlib import Path
import re

import pytest

from storage.migrations import LATEST_SCHEMA_VERSION


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_GUIDES = (
    "README.md", "DOCKERHUB_README.md", "docs/platform-state.md",
    "docs/current-configuration-model.md", "docs/webui.md",
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


def test_old_preview_is_identified_as_historical():
    for relative in ("README.md", "DOCKERHUB_README.md", "docs/README.md", "docs/webui.md"):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "Historical v3.1.0" in text
        assert "remains the current visual baseline" not in text


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
