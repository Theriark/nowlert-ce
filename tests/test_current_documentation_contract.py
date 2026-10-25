"""Current operator docs agree with migrations and exclude withdrawn captures."""

from pathlib import Path
import re

import pytest

from integrations.catalog import integrations
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


# Nowlert CE is a desktop web application: the front-page Preview shows the
# full desktop (1440 px) captures. The product owner decided on 25 October 2026
# (docs/guides/screenshot-privacy.md) that their generic Development test
# labels may appear; each was opened at full size that day. Narrow-window
# captures are secondary examples in docs/webui.md, never the Preview.
PREVIEW_CAPTURES = (
    "dashboard-live-admin-1440.png",
    "routing-flow-live-admin-1440.png",
    "destinations-list-admin-1440.png",
    "sign-in-empty-signed-out-1440.png",
)


@pytest.mark.parametrize("relative", ("README.md", "DOCKERHUB_README.md"))
def test_front_page_preview_uses_only_desktop_captures(relative):
    text = (ROOT / relative).read_text(encoding="utf-8")
    embedded = set(re.findall(r"images/v27\.0\.0-rc\.1/([\w.-]+\.png)", text))
    assert embedded == set(PREVIEW_CAPTURES), relative
    for name in PREVIEW_CAPTURES:
        assert (ROOT / "docs" / CURRENT_CAPTURE_DIR / name).stat().st_size > 0, name
    assert not any(name.endswith(("-390.png", "-768.png")) for name in embedded), relative
    # Each desktop capture stands on its own line at full width, not in a
    # table row of squeezed columns.
    for line in text.splitlines():
        if re.search(r"images/v27\.0\.0-rc\.1/[\w.-]+\.png", line):
            assert line.startswith("![") and line.count("](") == 1, line


def test_narrow_window_captures_are_secondary_and_not_mobile():
    webui = (ROOT / "docs/webui.md").read_text(encoding="utf-8")
    responsive = webui.split("## Narrow browser windows\n", 1)[1].split("\n## ", 1)[0]
    assert "secondary compatibility examples" in responsive
    assert "not the Nowlert Mobile app" in responsive
    before = webui.split("## Narrow browser windows\n", 1)[0]
    assert "-390.png" not in before and "-768.png" not in before


def test_owner_labels_are_described_as_typed_usernames():
    for relative in (
        "README.md",
        "docs/images/v27.0.0-rc.1/README.md",
        "docs/guides/screenshot-privacy.md",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "it is a role name" not in text, relative
        assert "role-named owner label" not in text, relative
        assert "synthetic crew" not in text, relative
        assert "synthetic test accounts" not in text, relative


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


# Absent from the catalogue of the v3.1.6 tag. The Docker Hub page names them
# because its versioned image is 3.1.6 while its list follows current source.
ADDED_AFTER_V316 = (
    "Prometheus", "Checkmk", "Semaphore", "Sonarr", "Radarr", "Metabase", "GitHub Actions",
)


def test_front_page_integration_lists_match_catalogue():
    catalogue = {item["name"] for item in integrations() if item["source"] != "email"}
    readme = (ROOT / "README.md").read_text(encoding="utf-8").split("# 🔌 Supported Integrations", 1)[1]
    table = set(re.findall(r"^\| ([^|]+?) \| `[a-z_]+` \|", readme.split("\n---", 1)[0], re.M))
    assert table == catalogue
    dockerhub = (ROOT / "DOCKERHUB_README.md").read_text(encoding="utf-8")
    section = " ".join(dockerhub.split("## Built-in integrations", 1)[1].split("\n## ", 1)[0].split())
    for name in sorted(catalogue):
        assert name in section, name
    assert f"same {len(catalogue)} integrations" in section
    stable = section.split("The stable `3.1.6` image", 1)[1]
    assert f"includes {len(catalogue) - len(ADDED_AFTER_V316)} of them" in stable
    for name in ADDED_AFTER_V316:
        assert name in stable, name


def _flat(text):
    return " ".join(text.split())


def _names_destination(passage, name):
    # "Email" must name the destination itself, not the Email Alerts input.
    if name == "Email":
        return re.search(rf"\b{name}\b(?! Alerts)", passage) is not None
    return name in passage


def test_integrations_and_inputs_table_matches_catalogue():
    text = (ROOT / "docs/integrations-and-inputs.md").read_text(encoding="utf-8")
    rows = re.findall(r"^\| ([^|]+?) \| `([a-z_]+)` \| ([^|]+?) \| ([^|]+?) \|$", text, re.M)
    expected = [
        (
            item["name"],
            item["source"],
            ", ".join(value["name"] for value in item["inputs"]),
            item["category"].capitalize(),
        )
        for item in integrations()
    ]
    assert sorted(rows) == sorted(expected)
    flat = _flat(text)
    assert "Nowlert v3.1.2" not in text
    assert f"includes {len(expected) - 1 - len(ADDED_AFTER_V316)} of the {len(expected) - 1}" in flat
    for name in ADDED_AFTER_V316:
        assert name in flat.split("The stable `3.1.6` image", 1)[1], name


def test_current_input_lists_name_every_catalogue_input():
    names = {value["name"] for item in integrations() for value in item["inputs"]}
    assert names == {"SMTP", "HTTP", "Redfish", "Email Alerts"}
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    passages = {
        "README.md": readme.split("## Input\n", 1)[1].split("\n## ", 1)[0],
        "DOCKERHUB_README.md": (ROOT / "DOCKERHUB_README.md").read_text(encoding="utf-8")
        .split("Normalized inputs are", 1)[1].split("\n\n", 1)[0],
        "docs/integrations-and-inputs.md": (ROOT / "docs/integrations-and-inputs.md")
        .read_text(encoding="utf-8").split("Inputs are the normalized", 1)[1].split("\n\n", 1)[0],
    }
    for relative, passage in passages.items():
        for name in names:
            assert name in passage, (relative, name)
        assert "3.1.6" in passage or "listener" in passage, relative
    badges = _flat((ROOT / "docs/webui.md").read_text(encoding="utf-8")
                   .split("The normalized input badges are", 1)[1].split(".", 1)[0])
    for name in names:
        assert f"**{name}**" in badges, ("docs/webui.md badges", name)
    index = (ROOT / "docs/README.md").read_text(encoding="utf-8")
    for row in ("[Integrations and inputs]", "[Technical use-case guides]"):
        line = next(line for line in index.splitlines() if line.startswith(f"| {row}"))
        for name in names:
            assert name in line, (row, name)
    roadmap = _flat((ROOT / "docs/roadmap.md").read_text(encoding="utf-8"))
    milestone = roadmap.split("normalized SMTP, HTTP, and Redfish input model", 1)[1].split(";", 1)[0]
    assert "Email Alerts" in milestone and "after v3.1.6" in milestone


# Destination display names of src/outputs/service.py for the current types.
DESTINATION_NAMES = {
    "discord": "Discord", "teams": "Microsoft Teams", "slack": "Slack",
    "webhook": "webhooks", "email": "Email", "nowlert_mobile": "Nowlert Mobile",
}
# Destination types of the v3.1.6 tag (src/outputs/settings.py OUTPUT_TYPES).
V316_ONLY_DESTINATIONS = ("MQTT", "ntfy")


def test_front_page_destinations_match_current_output_types():
    from outputs.settings import OUTPUT_TYPES

    assert set(DESTINATION_NAMES) == OUTPUT_TYPES
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    dockerhub = (ROOT / "DOCKERHUB_README.md").read_text(encoding="utf-8")
    current = {
        "README.md destinations": readme.split("## Destinations\n", 1)[1].split("The stable `3.1.6` image", 1)[0],
        "README.md tagline": readme.split("**Self-hosted", 1)[1].split("**", 1)[0],
        "DOCKERHUB_README.md intro": _flat(dockerhub.split("Current development and the v27.0.0 release candidates also", 1)[1]
                                           .split("The stable `3.1.6` image", 1)[0]).split("deliver to", 1)[1],
    }
    for label, passage in current.items():
        for name in DESTINATION_NAMES.values():
            # The README tagline shortens Microsoft Teams to Teams.
            assert _names_destination(passage, name.removeprefix("Microsoft ")), (label, name)
        for removed in V316_ONLY_DESTINATIONS:
            assert removed not in passage, (label, removed)
    # MQTT and ntfy may appear only in the sentence that qualifies the 3.1.6 image.
    for relative, text in (("README.md", readme), ("DOCKERHUB_README.md", dockerhub),
                           ("docs/platform-outputs.md", (ROOT / "docs/platform-outputs.md").read_text(encoding="utf-8"))):
        for paragraph in text.split("\n\n"):
            if any(name in paragraph for name in V316_ONLY_DESTINATIONS):
                assert "3.1.6" in paragraph and "no longer offered" in paragraph, (relative, paragraph[:80])


def test_readme_integration_table_states_the_316_subset():
    readme = _flat((ROOT / "README.md").read_text(encoding="utf-8").split("# 🔌 Supported Integrations", 1)[1].split("| Integration |", 1)[0])
    catalogue = [item for item in integrations() if item["source"] != "email"]
    assert f"lists the {len(catalogue)} integrations" in readme
    stable = readme.split("The stable `3.1.6` image", 1)[1]
    assert f"includes {len(catalogue) - len(ADDED_AFTER_V316)} of them" in stable
    for name in ADDED_AFTER_V316:
        assert name in stable, name


def test_routing_guide_lists_current_destination_types_and_examples_use_stable_image():
    routing = (ROOT / "docs/platform-routing.md").read_text(encoding="utf-8")
    listed = routing.split("Supported platform destination types are:", 1)[1].split("\n\n", 2)[1]
    for name in DESTINATION_NAMES.values():
        assert _names_destination(listed, name.rstrip("s")), name
    smtp = (ROOT / "docs/smtp-security.md").read_text(encoding="utf-8")
    assert set(re.findall(r"theriark/nowlert-ce:([\w.-]+)", smtp)) == {"3.1.6"}
