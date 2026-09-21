"""Discord Modern image-card coverage for all integrations."""

from __future__ import annotations

from io import BytesIO
import json
import socket

import pytest
from PIL import Image, ImageDraw

from formatters.discord_modern_image import DiscordModernImageRenderer
from formatters.discord_xo_image import XenOrchestraDiscordImageRenderer
from models import Notification
from outputs.discord import DiscordOutput
from outputs.platform import DiscordPlatformAdapter
from storage.destinations import Destination


PUBLIC_ADDRESS = "93.184.216.34"

SOURCES = (
    "zabbix",
    "grafana",
    "portainer",
    "proxmox",
    "qnap",
    "synology",
    "truenas",
    "unifi_network",
    "unifi_protect",
    "unifi_drive",
    "supermicro",
    "hpe_ilo",
    "dell_idrac",
    "home_assistant",
    "redfish",
    "nowlert",
    "unknown_product",
)


def public_resolver(host, port, **_kwargs):
    return [
        (
            socket.AF_INET,
            socket.SOCK_STREAM,
            6,
            "",
            (PUBLIC_ADDRESS, port),
        )
    ]


def destination(modern=True):
    return Destination(
        id="discord-modern",
        owner_user_id="owner",
        name="Discord Modern",
        output_type="discord",
        settings={"components_v2": modern},
        shared=False,
        enabled=True,
        secret_configured=True,
        created_at=1,
        updated_at=1,
    )


def notification(source):
    metadata = {
        "severity": "warning",
        "event_time": "2026-09-21 22:30:00 UTC",
        "host": "LAB-01",
        "hostname": "LAB-01",
        "system": "LAB-01",
        "device": "LAB-01",
        "provider": "Synthetic provider",
        "instance": "LAB-01",
        "node": "NODE-01",
        "nas_name": "NAS-01",
        "controller": "UDM-01",
        "area": "Server room",
        "entity_id": "sensor.lab",
        "rule_name": "Synthetic rule",
        "alert_rule": "Synthetic rule",
        "storage_pool": "pool-01",
        "volume": "volume-01",
        "disk": "disk-01",
        "service": "automation.turn_on",
        "sensor": "Temp 1",
        "message_id": "Synthetic.Message.1",
        "source_ip": "192.0.2.10",
        "recommended_action": "Inspect the affected component.",
    }
    return Notification(
        source=source,
        category="monitoring",
        status="warning",
        title="Synthetic integration event",
        subject="Synthetic integration event",
        body=(
            "Synthetic operational message containing enough context "
            "to exercise the Modern card renderer."
        ),
        start_time="2026-09-21 22:29:00 UTC",
        end_time="2026-09-21 22:30:00 UTC",
        duration="1 min",
        metadata=metadata,
    )


@pytest.mark.parametrize("source", SOURCES)
def test_every_non_xo_modern_source_renders_png_from_classic_content(
    tmp_path,
    source,
):
    output = DiscordOutput()
    output.ICON_DIR = tmp_path
    output.modern_image_renderer.icon_dir = tmp_path
    item = notification(source)
    formatter = output.source_formatters.get(
        source,
        output.default_formatter,
    )

    image = output.render_modern_image(
        item,
        formatter,
    )

    assert image is not None
    assert image.startswith(b"\x89PNG\r\n\x1a\n")
    with Image.open(BytesIO(image)) as rendered:
        assert rendered.width == 1448
        assert rendered.height >= output.modern_image_renderer.MIN_HEIGHT
    assert len(image) < 8 * 1024 * 1024


def test_modern_renderer_uses_classic_embed_as_source_of_truth(tmp_path):
    output = DiscordOutput()
    output.ICON_DIR = tmp_path
    output.modern_image_renderer.icon_dir = tmp_path
    item = notification("grafana")
    formatter = output.source_formatters["grafana"]
    classic = formatter.format(item)

    captured = {}

    def render(_notification, classic_payload):
        captured["classic"] = classic_payload
        return b"\x89PNG\r\n\x1a\nsynthetic"

    output.modern_image_renderer.render = render

    image = output.render_modern_image(
        item,
        formatter,
    )

    assert image.startswith(b"\x89PNG")
    assert captured["classic"] == formatter._sanitize_payload(
        classic
    )
    assert "embeds" in captured["classic"]


def test_modern_readability_baseline_matches_xo_quality(tmp_path):
    renderer = DiscordModernImageRenderer(tmp_path)

    assert renderer.font_section.size >= 35
    assert renderer.font_message.size >= 31
    assert renderer.font_field.size >= 28
    assert renderer.font_value.size >= 30
    assert renderer.font_header_context.size >= 28
    assert renderer.font_summary.size >= 27
    assert renderer.HEADER_ICON_WIDTH >= 150
    assert renderer.HEADER_ICON_HEIGHT >= 112
    assert renderer.MIN_HEIGHT <= 760
    assert renderer.HEADER_LOGO_WIDTHS["qnap"] >= 230
    assert renderer.HEADER_LOGO_WIDTHS["synology"] >= 220
    assert renderer.HEADER_LOGO_WIDTHS["unifi_network"] >= 240


def test_zabbix_profile_groups_fields_and_removes_redundant_alert(tmp_path):
    renderer = DiscordModernImageRenderer(tmp_path)
    fields = [
        {"name": "📊 Alert", "value": "Severity: critical"},
        {"name": "🟩 Problem", "value": "Host: VM-08\nSeverity: High"},
        {
            "name": "Operational Data",
            "value": "replication_lag=187s",
        },
        {"name": "Trigger", "value": "replication_lag > 120"},
        {"name": "Problem ID", "value": "10436555"},
        {"name": "Timing", "value": "Started: 2026-09-21T22:38:30Z"},
        {"name": "Runbook", "value": "DB-RUNBOOK-REPLICATION-01"},
    ]

    sections = renderer._build_sections("zabbix", fields)

    assert [section["title"] for section in sections] == [
        "Problem",
        "Trigger",
        "Response",
    ]
    rendered_names = {
        field["normalized"]
        for section in sections
        for field in section["fields"]
    }
    assert "alert" not in rendered_names
    assert "operational data" in rendered_names
    assert "problem id" in rendered_names
    assert "runbook" in rendered_names


def test_grafana_grouped_alerts_expand_as_full_width_section(tmp_path):
    renderer = DiscordModernImageRenderer(tmp_path)
    fields = [
        {"name": "Alert", "value": "Severity: critical"},
        {"name": "Rule", "value": "Rule: Synthetic Grouped Rule"},
        {"name": "Location", "value": "Dashboard: Shared"},
        {
            "name": "Alerts • 4",
            "value": (
                "Synthetic Cache Saturation — Firing — A=95\n"
                "Synthetic Worker Failure — Firing — B=1\n"
                "Synthetic Queue Depth — Pending — C=30\n"
                "Synthetic API Latency — Firing — D=2.7"
            ),
        },
        {"name": "Timing", "value": "Started: 2026-07-12T11:30:00Z"},
    ]

    sections = renderer._build_sections("grafana", fields)
    grouped = next(
        section
        for section in sections
        if section["title"] == "Alert details"
    )

    assert grouped["full_width"] is True

    image = Image.new("RGB", (renderer.WIDTH, 1))
    draw = ImageDraw.Draw(image)
    layout, height = renderer._section_layout(
        draw,
        sections,
        renderer.WIDTH - renderer.CARD_PADDING * 2,
    )
    grouped_layout = next(
        section
        for section in layout
        if section["title"] == "Alert details"
    )
    assert grouped_layout["width"] == (
        renderer.WIDTH - renderer.CARD_PADDING * 2
    )
    assert grouped_layout["height"] > 160
    assert height > grouped_layout["height"]


def test_unifi_protect_epoch_milliseconds_are_formatted(tmp_path):
    renderer = DiscordModernImageRenderer(tmp_path)
    item = notification("unifi_protect")
    item.metadata["event_time"] = "1767323045000"

    value = renderer._summary_time(item, [])

    assert value == "2026-01-02 03:04:05 UTC"


def test_summary_time_falls_back_to_classic_timing_field(tmp_path):
    renderer = DiscordModernImageRenderer(tmp_path)
    item = Notification(
        source="truenas",
        category="power",
        status="warning",
        title="UPS power alert",
        subject="UPS power alert",
        body="UPS is on battery.",
        metadata={"severity": "warning"},
    )
    fields = [
        {
            "name": "Timing",
            "value": "Started: 2026-07-12T10:09:00Z",
        }
    ]

    value = renderer._summary_time(item, fields)

    assert value == "2026-07-12 10:09:00 UTC"


def test_semantic_event_detail_title_uses_actual_qnap_domain(tmp_path):
    renderer = DiscordModernImageRenderer(tmp_path)
    fields = [
        {"name": "QNAP NAS", "value": "NAS: LAB-QNAP"},
        {
            "name": "Power",
            "value": "UPS: LAB-UPS\nCause: Utility power loss",
        },
    ]

    sections = renderer._build_sections("qnap", fields)

    assert [section["title"] for section in sections] == [
        "QNAP NAS",
        "Power",
    ]


def test_timing_values_are_normalized_for_section_rendering(tmp_path):
    renderer = DiscordModernImageRenderer(tmp_path)

    value = renderer._normalize_timing_block(
        "Started: 2026-07-15T01:30:00Z\n"
        "Resolved: 2026-07-15T01:45:00+00:00\n"
        "Duration: 15 min"
    )

    assert value == (
        "Started: 2026-07-15 01:30:00 UTC\n"
        "Resolved: 2026-07-15 01:45:00 UTC\n"
        "Duration: 15 min"
    )


def test_warning_firing_uses_non_failure_status_icon(tmp_path):
    renderer = DiscordModernImageRenderer(tmp_path)

    status_kind = renderer._status_kind(
        "Firing",
        (244, 193, 49),
    )

    assert status_kind == "skipped"


def test_critical_firing_still_uses_failure_status_icon(tmp_path):
    renderer = DiscordModernImageRenderer(tmp_path)

    status_kind = renderer._status_kind(
        "Firing",
        (255, 64, 72),
    )

    assert status_kind == "failure"


def test_metric_names_do_not_trigger_failure_coloring(tmp_path):
    renderer = DiscordModernImageRenderer(tmp_path)

    assert (
        renderer._line_color(
            "Metric: authentication_failures_total",
            renderer.BRAND_GOLD,
        )
        == renderer.TEXT
    )
    assert (
        renderer._line_color(
            "Error: synthetic checksum error",
            renderer.FAILURE,
        )
        == renderer.FAILURE
    )


def test_event_title_removes_status_emoji_and_suffix(tmp_path):
    renderer = DiscordModernImageRenderer(tmp_path)
    item = notification("zabbix")
    embed = {
        "title": "⚠️ PostgreSQL replication lag exceeds 120 seconds — Updated"
    }

    title = renderer._event_title(
        embed,
        item,
        "Updated",
    )

    assert title == "PostgreSQL replication lag exceeds 120 seconds"


def test_long_sections_grow_instead_of_clipping(tmp_path):
    renderer = DiscordModernImageRenderer(tmp_path)
    fields = [
        {
            "name": "Grouped Alerts • 20",
            "value": "\n".join(
                f"Alert {index}: synthetic grouped detail with a long value"
                for index in range(1, 21)
            ),
        }
    ]
    sections = renderer._build_sections(
        "truenas",
        fields,
    )

    image = Image.new("RGB", (renderer.WIDTH, 1))
    draw = ImageDraw.Draw(image)
    layout, height = renderer._section_layout(
        draw,
        sections,
        renderer.WIDTH - renderer.CARD_PADDING * 2,
    )

    assert len(layout) == 1
    assert layout[0]["height"] > 600
    assert height == layout[0]["height"]


class Response:
    status_code = 200
    text = ""

    def __init__(self, filename):
        self.filename = filename

    def json(self):
        return {
            "attachments": [
                {
                    "id": "2",
                    "filename": self.filename,
                    "content_type": "image/png",
                    "url": (
                        "https://cdn.discordapp.com/"
                        "attachments/1/2/"
                        + self.filename
                    ),
                    "proxy_url": (
                        "https://media.discordapp.net/"
                        "attachments/1/2/"
                        + self.filename
                    ),
                }
            ]
        }


class Client:
    def __init__(self):
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        filename = kwargs["files"]["files[0]"][0]
        return Response(filename)


def test_non_xo_modern_platform_delivery_is_image_only(monkeypatch):
    client = Client()
    adapter = DiscordPlatformAdapter(
        http_client=client,
        resolver=public_resolver,
    )
    item = notification("qnap")
    image = b"\x89PNG\r\n\x1a\nsynthetic"
    monkeypatch.setattr(
        adapter.output,
        "render_modern_image",
        lambda _notification, _formatter=None: image,
    )

    result = adapter.deliver(
        destination(True),
        b"https://discord.com/api/webhooks/123/token",
        item,
    )

    assert result.success is True
    assert len(client.calls) == 1
    url, kwargs = client.calls[0]
    assert url.endswith("?wait=true")
    assert "json" not in kwargs
    filename, content, content_type = (
        kwargs["files"]["files[0]"]
    )
    assert filename == "nowlert-qnap-modern.png"
    assert content == image
    assert content_type == "image/png"
    payload = json.loads(
        kwargs["data"]["payload_json"]
    )
    assert payload["attachments"][0]["filename"] == filename
    assert payload["allowed_mentions"] == {
        "parse": [],
    }


def test_modern_filename_is_source_specific_and_safe():
    assert (
        DiscordOutput.modern_image_filename(
            "dell_idrac"
        )
        == "nowlert-dell_idrac-modern.png"
    )
    assert (
        DiscordOutput.modern_image_filename(
            "unknown product / webhook"
        )
        == "nowlert-unknown-product---webhook-modern.png"
    )


def test_modern_payload_uses_integration_identity():
    payload = DiscordOutput.modern_image_payload(
        "home_assistant",
        "card.png",
    )
    assert payload["attachments"] == [
        {
            "id": 0,
            "filename": "card.png",
            "description": (
                "Home Assistant notification"
            ),
        }
    ]



def test_xo_readability_baseline_is_immediately_legible(tmp_path):
    renderer = XenOrchestraDiscordImageRenderer(tmp_path)

    assert renderer.font_detail.size >= 29
    assert renderer.font_body.size >= 30
    assert renderer.font_label.size >= 29
    assert renderer.font_small.size >= 25
    assert renderer.font_vm.size >= 30
    assert renderer.font_heading.size >= 48
    assert renderer.OUTER_GLOW_GOLD_ALPHA >= 130
    assert renderer.OUTER_GLOW_ACCENT_ALPHA >= 115
    assert renderer.STATUS_GLOW_ALPHA >= 110


def test_footer_position_is_fixed_from_bottom_for_all_modern_cards(tmp_path):
    xo = XenOrchestraDiscordImageRenderer(tmp_path)
    modern = DiscordModernImageRenderer(tmp_path)

    assert xo._footer_y(1400) == 1400 - xo.FOOTER_RESERVE
    assert modern._footer_y(1400) == 1400 - modern.FOOTER_RESERVE


def test_dense_sections_promote_to_full_width_instead_of_shrinking(tmp_path):
    renderer = DiscordModernImageRenderer(tmp_path)
    dense_value = "\n".join(
        f"Field {index}: synthetic operational value {index}"
        for index in range(1, 8)
    )
    sections = [
        {
            "title": "Dense A",
            "fields": [
                {
                    "name": "Dense A",
                    "normalized": "dense a",
                    "value": dense_value,
                }
            ],
            "full_width": False,
        },
        {
            "title": "Dense B",
            "fields": [
                {
                    "name": "Dense B",
                    "normalized": "dense b",
                    "value": dense_value,
                }
            ],
            "full_width": False,
        },
    ]
    draw = ImageDraw.Draw(Image.new("RGB", (renderer.WIDTH, 1)))
    content_width = renderer.WIDTH - renderer.CARD_PADDING * 2

    layout, _height = renderer._section_layout(
        draw,
        sections,
        content_width,
    )

    assert len(layout) == 2
    assert layout[0]["width"] == content_width
    assert layout[1]["width"] == content_width
    assert layout[1]["y"] > layout[0]["y"]


def test_short_sections_can_still_share_a_row(tmp_path):
    renderer = DiscordModernImageRenderer(tmp_path)
    sections = [
        {
            "title": "System",
            "fields": [
                {
                    "name": "System",
                    "normalized": "system",
                    "value": "Host: SRV-01\nState: Healthy",
                }
            ],
            "full_width": False,
        },
        {
            "title": "Hardware Event",
            "fields": [
                {
                    "name": "Hardware Event",
                    "normalized": "hardware event",
                    "value": "Registry: SMC\nMessage ID: Normal",
                }
            ],
            "full_width": False,
        },
    ]
    draw = ImageDraw.Draw(Image.new("RGB", (renderer.WIDTH, 1)))
    content_width = renderer.WIDTH - renderer.CARD_PADDING * 2

    layout, _height = renderer._section_layout(
        draw,
        sections,
        content_width,
    )

    assert len(layout) == 2
    assert layout[0]["y"] == layout[1]["y"]
    assert layout[0]["width"] < content_width
    assert layout[1]["width"] < content_width


def test_long_unbroken_values_wrap_without_truncating(tmp_path):
    renderer = DiscordModernImageRenderer(tmp_path)
    draw = ImageDraw.Draw(Image.new("RGB", (renderer.WIDTH, 1)))
    token = (
        "https://synthetic.example.invalid/redfish/v1/Systems/"
        + "GENERIC-SENSOR-" * 16
    )

    lines = renderer._wrapped_lines(
        draw,
        token,
        320,
        renderer.font_value,
    )

    assert len(lines) > 2
    assert "".join(lines) == token
    assert all(
        draw.textlength(line, font=renderer.font_value) <= 320
        for line in lines
    )


def test_rfc2822_event_time_is_normalized_for_readable_summary(tmp_path):
    renderer = DiscordModernImageRenderer(tmp_path)

    assert renderer._format_time(
        "Fri, 04 Sep 2026 00:20:00 +0100"
    ) == "2026-09-03 23:20:00 UTC"


def test_xo_failure_reason_wraps_beyond_two_lines(tmp_path):
    renderer = XenOrchestraDiscordImageRenderer(tmp_path)
    draw = ImageDraw.Draw(Image.new("RGB", (renderer.WIDTH, 1)))
    reason = (
        "Synthetic backup failure reason with operational context "
        * 14
    )

    lines = renderer._wrapped_text_lines(
        draw,
        reason,
        360,
        renderer.font_reason,
    )

    assert len(lines) > 2
    assert all(
        draw.textlength(line, font=renderer.font_reason) <= 360
        for line in lines
    )


def test_xo_failure_panel_height_grows_for_long_reason(tmp_path):
    renderer = XenOrchestraDiscordImageRenderer(tmp_path)
    item = Notification(
        source="xo",
        vm_details={
            "VM-01": {
                "error": (
                    "Synthetic backup failure reason with detailed "
                    "operational context " * 16
                )
            }
        },
    )
    style = renderer._vm_style(1)

    height = renderer._vm_entry_height(
        item,
        "VM-01",
        include_reason=True,
        vm_count=1,
        entry_width=480,
    )

    assert height > style["reason_height"]
