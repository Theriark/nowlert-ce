"""Modern fallback cards show Severity and Category once (NCE-115).

Slack Modern Cards reuse the Discord Modern image, so these checks cover both.
"""

from __future__ import annotations

import pytest

from formatters.discord_classic_v1 import render_classic_embed_v1
from formatters.discord_modern_image import (
    GenericFallbackDiscordModernImageRenderer,
    RedfishDiscordModernImageRenderer,
)
from formatters.modern_sections import without_repeated_classification
from models import Notification
from outputs.discord import DiscordOutput


def _http_fallback() -> Notification:
    return Notification(
        source="unknown_product",
        category="event",
        status="warning",
        title="Synthetic HTTP event",
        subject="Synthetic HTTP event",
        body="Synthetic HTTP fallback message.",
        start_time="2026-10-22 08:00:00 UTC",
        metadata={
            "_input_type": "http",
            "provider": "Synthetic Provider",
            "host": "host-01",
            "severity": "warning",
        },
    )


def _redfish_fallback() -> Notification:
    return Notification(
        source="redfish",
        category="hardware",
        status="warning",
        title="Synthetic Redfish event",
        subject="Synthetic Redfish event",
        body="Synthetic Redfish fallback message.",
        start_time="2026-10-22 08:00:00 UTC",
        metadata={
            "_input_type": "redfish",
            "provider": "Synthetic BMC",
            "system": "system-01",
            "severity": "warning",
            "registry": "Synthetic.1.0",
            "message_id": "Synthetic.1.0.Message",
            "event_id": "42",
            "origin": "/redfish/v1/Systems/1",
        },
    )


def _classic_payload(item: Notification) -> dict:
    return render_classic_embed_v1(item, {})


def _field_names(payload: dict) -> list[str]:
    return [field["name"] for field in payload["embeds"][0]["fields"]]


def _modern_sections(renderer, item: Notification):
    """Sections the Modern builder produces for the payload the card receives."""

    payload = without_repeated_classification(_classic_payload(item))
    fields = renderer._fields(renderer._embed(payload))
    return renderer._build_sections(item.source, fields)


def _section_field_names(sections) -> list[str]:
    return [
        field["normalized"]
        for section in sections
        for field in section["fields"]
    ]


def _all_text(sections) -> str:
    return "\n".join(
        field["value"] for section in sections for field in section["fields"]
    )


def test_classic_cards_keep_their_alert_group_unchanged():
    for item in (_http_fallback(), _redfish_fallback()):
        payload = _classic_payload(item)
        before = _field_names(payload)
        stripped = without_repeated_classification(payload)

        alert = next(
            f for f in payload["embeds"][0]["fields"] if f["name"].endswith("Alert")
        )
        assert "Severity" in alert["value"]
        assert "Category" in alert["value"]
        # The helper copies; the Classic payload itself is never modified.
        assert _field_names(payload) == before
        assert not any(name.endswith("Alert") for name in _field_names(stripped))


def test_http_fallback_omits_additional_details_panel(tmp_path):
    renderer = GenericFallbackDiscordModernImageRenderer(tmp_path)

    sections = _modern_sections(renderer, _http_fallback())

    assert "Additional details" not in [section["title"] for section in sections]
    assert "alert" not in _section_field_names(sections)
    text = _all_text(sections).casefold()
    assert "severity:" not in text
    assert "category:" not in text
    # The source context is still shown.
    assert "provider" in text


def test_redfish_keeps_event_metadata_without_alert_classification(tmp_path):
    renderer = RedfishDiscordModernImageRenderer(tmp_path)

    sections = _modern_sections(renderer, _redfish_fallback())

    names = _section_field_names(sections)
    assert "alert" not in names
    assert "event" in names
    text = _all_text(sections)
    assert "Synthetic.1.0.Message" in text
    assert "severity:" not in text.casefold()
    assert "category:" not in text.casefold()


def test_alert_group_with_real_extra_details_is_unchanged():
    payload = {
        "embeds": [
            {
                "fields": [
                    {"name": "🚨 Alert", "value": "**Severity:** `warning`\n**Alert ID:** `a-1`"},
                    {"name": "🧪 Custom", "value": "**Detail:** `kept`"},
                ]
            }
        ]
    }

    assert without_repeated_classification(payload) is payload


def test_non_alert_fields_are_never_dropped():
    payload = {
        "embeds": [
            {
                "fields": [
                    {"name": "🚨 Alert", "value": "**Severity:** `warning`\n**Category:** `event`"},
                    {"name": "🧪 Custom", "value": "**Severity:** `kept`"},
                ]
            }
        ]
    }

    assert _field_names(without_repeated_classification(payload)) == ["🧪 Custom"]


def test_malformed_payloads_pass_through():
    for payload in ({}, {"embeds": []}, {"embeds": [{}]}, {"embeds": [{"fields": "x"}]}):
        assert without_repeated_classification(payload) is payload


@pytest.mark.parametrize("source", ["unknown_product", "redfish"])
def test_discord_and_slack_modern_render_receives_deduped_payload(
    tmp_path, monkeypatch, source
):
    """Slack Modern reuses render_modern_image, so this covers both."""

    output = DiscordOutput()
    output.ICON_DIR = tmp_path
    item = _redfish_fallback() if source == "redfish" else _http_fallback()
    renderer = (
        output.redfish_modern_image_renderer
        if source == "redfish"
        else output.generic_fallback_modern_image_renderer
    )
    seen = {}

    def capture(notification, classic_payload):
        seen["fields"] = _field_names(classic_payload)
        return b"png"

    monkeypatch.setattr(renderer, "render", capture)

    assert output.render_modern_image(item) == b"png"
    assert not any(name.endswith("Alert") for name in seen["fields"])
    assert any("Source" in name for name in seen["fields"])
