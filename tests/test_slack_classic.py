"""Slack Classic Card presentation parity with Discord Classic v1."""

from __future__ import annotations

from formatters.discord_classic_v1 import render_classic_embed_v1
from formatters.slack import CLASSIC_FOOTER, SlackFormatter
from models import Notification


DEDICATED_SOURCES = (
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
    "home_assistant",
    "redfish",
    "supermicro",
    "hpe_ilo",
    "dell_idrac",
)


def notification(source: str) -> Notification:
    item = Notification(
        source=source,
        category="storage",
        status="warning",
        title="Synthetic presentation warning",
        body="Synthetic presentation event.",
        start_time="2026-07-15T01:15:00Z",
        end_time="2026-07-15T01:20:00Z",
        duration="5 min",
    )
    item.metadata = {
        "host": "synthetic-host",
        "hostname": "synthetic-host",
        "severity": "warning",
        "event_time": "2026-07-15T01:15:00Z",
        "problem_name": "Synthetic Zabbix problem",
        "alert_name": "Synthetic Grafana alert",
        "state": "warning",
        "alert_count": 1,
        "application": "Synthetic application",
        "event_type": "storage warning",
        "message": "Synthetic presentation event.",
        "controller": "synthetic-controller",
        "client_display_name": "synthetic-client",
        "wifi_name": "synthetic-wifi",
        "trigger_key": "motion",
        "trigger_device": "Synthetic camera",
        "system": "synthetic-drive",
        "backup_task": "Synthetic backup",
        "instance": "synthetic-portainer",
        "alert_source": "portainer",
        "node": "synthetic-pve",
        "storage": "synthetic-storage",
        "nas_name": "synthetic-nas",
        "model": "SYNTHETIC-MODEL",
        "storage_pool": "Synthetic Pool",
        "action_link": "https://example.invalid/events/synthetic",
    }
    return item


def expected_icon_source(source: str) -> str:
    if source == "redfish":
        return "nowlert"
    return source if source in SlackFormatter.PRODUCT_ICONS else "nowlert"


def expected_icon_path(formatter: SlackFormatter, source: str) -> str:
    icon_source = expected_icon_source(source)
    return formatter.DISCORD_PRODUCT_ICONS.get(
        icon_source,
        formatter.PRODUCT_ICONS[icon_source],
    )


def test_all_dedicated_slack_sources_use_classic_attachments():
    formatter = SlackFormatter()

    for source in DEDICATED_SOURCES:
        item = notification(source)
        payload = formatter.format(item)

        assert "blocks" not in payload
        assert len(payload["attachments"]) == 1
        attachment = payload["attachments"][0]

        discord_embed = render_classic_embed_v1(
            item,
            {
                "embeds": [
                    {
                        "url": item.metadata["action_link"],
                        "fields": [
                            {
                                "name": "⏱️ Event time",
                                "value": formatter._format_datetime(
                                    item.metadata["event_time"]
                                ),
                            }
                        ],
                    }
                ]
            },
        )["embeds"][0]

        assert attachment["color"] == (
            f"#{discord_embed['color'] & 0xFFFFFF:06X}"
        )
        assert "title" not in attachment
        assert "text" not in attachment
        assert "fields" not in attachment
        assert "thumb_url" not in attachment

        blocks = attachment["blocks"]
        header = blocks[0]
        assert header["type"] == "section"
        assert discord_embed["title"][:200] in header["text"]["text"]
        assert (
            f"<{item.metadata['action_link']}|"
            in header["text"]["text"]
        )
        assert header["accessory"]["type"] == "image"
        assert header["accessory"]["image_url"].endswith(
            f"/{expected_icon_path(formatter, source)}"
        )
        assert len(header.get("fields", [])) <= 10
        assert blocks[-1] == {
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": CLASSIC_FOOTER}],
        }


def test_first_batch_slack_cards_stay_compact_without_show_more_layout():
    formatter = SlackFormatter()

    for source in (
        "zabbix",
        "grafana",
        "portainer",
        "proxmox",
        "qnap",
        "synology",
    ):
        payload = formatter.format(notification(source))
        attachment = payload["attachments"][0]
        blocks = attachment["blocks"]

        assert len(blocks) <= 3, source
        assert blocks[0]["type"] == "section"
        assert blocks[0]["accessory"]["type"] == "image"
        assert blocks[0].get("fields"), source
        assert blocks[-1] == {
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": CLASSIC_FOOTER}],
        }


def test_remaining_dedicated_slack_cards_stay_compact_without_show_more_layout():
    formatter = SlackFormatter()

    for source in (
        "unifi_protect",
        "unifi_drive",
        "home_assistant",
        "redfish",
        "supermicro",
        "hpe_ilo",
        "dell_idrac",
    ):
        payload = formatter.format(notification(source))
        attachment = payload["attachments"][0]
        blocks = attachment["blocks"]

        assert len(blocks) <= 3, source
        assert blocks[0]["type"] == "section"
        assert blocks[0]["accessory"]["type"] == "image"
        assert blocks[0].get("fields"), source
        assert blocks[-1] == {
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": CLASSIC_FOOTER}],
        }


def test_truenas_and_unifi_network_sections_do_not_need_show_more():
    formatter = SlackFormatter()

    unifi = notification("unifi_network")
    unifi.duration = "5m 30s"
    unifi.metadata.update(
        {
            "controller": "synthetic-controller.example.invalid",
            "client_display_name": "SYNTHETIC-CLIENT",
            "client_mac": "00:00:5e:00:53:20",
            "wifi_name": "SYNTHETIC-WIFI",
            "last_device_name": "SYNTHETIC-AP",
            "last_device_model": "Synthetic AP",
            "wifi_rssi": "-60 dBm",
        }
    )
    unifi_blocks = formatter.format(unifi)["attachments"][0]["blocks"]
    unifi_sections = [
        block for block in unifi_blocks
        if block.get("type") == "section"
    ]

    assert len(unifi_sections) >= 2
    assert all(
        len(block.get("fields", [])) <= 2
        for block in unifi_sections
    )
    assert any(
        block.get("fields")
        for block in unifi_sections[1:]
    )
    unifi_rendered = str(unifi_blocks)
    for expected in (
        "SYNTHETIC-CLIENT",
        "SYNTHETIC-WIFI",
        "SYNTHETIC-AP",
        "5m 30s",
    ):
        assert expected in unifi_rendered

    alerts = [
        {
            "event_type": "new",
            "message": "Pool SYNTHETIC-POOL state is DEGRADED.",
            "status": "warning",
        },
        {
            "event_type": "new",
            "message": "Replication task SYNTHETIC-REPLICATION failed.",
            "status": "failure",
        },
        {
            "event_type": "current",
            "message": "Scrub of pool SYNTHETIC-POOL failed.",
            "status": "failure",
        },
        {
            "event_type": "current",
            "message": "SMART warning reported for SYNTHETIC-DISK-01.",
            "status": "warning",
        },
    ]
    truenas = notification("truenas")
    truenas.status = "failure"
    truenas.title = "TrueNAS alerts (4)"
    truenas.body = "4 TrueNAS alerts were reported in one notification."
    truenas.items = alerts
    truenas.metadata.update(
        {
            "host": "SYNTHETIC-TRUENAS",
            "severity": "critical",
            "alert_count": 4,
            "alerts": alerts,
        }
    )

    truenas_blocks = formatter.format(truenas)["attachments"][0]["blocks"]
    body_sections = [
        block for block in truenas_blocks
        if block.get("type") == "section"
        and "accessory" not in block
        and isinstance(block.get("text"), dict)
    ]

    assert body_sections
    assert all(
        block["text"]["text"].count("\n") <= 4
        for block in body_sections
    )
    truenas_rendered = str(truenas_blocks)
    for expected in (
        "Grouped Alerts",
        "SYNTHETIC-POOL",
        "SYNTHETIC-REPLICATION",
        "SYNTHETIC-DISK-01",
    ):
        assert expected in truenas_rendered


def test_slack_generic_fallback_uses_nowlert_classic_card():
    formatter = SlackFormatter()
    item = notification("home_lab")
    item.metadata.update(
        {
            "_input_type": "HTTP",
            "provider": "home_lab",
            "environment": "synthetic",
        }
    )

    payload = formatter.format(item)
    attachment = payload["attachments"][0]
    rendered = str(payload)

    assert "blocks" not in payload
    blocks = attachment["blocks"]
    header = blocks[0]
    assert len(blocks) <= 3
    assert header.get("fields")
    assert blocks[-1] == {
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": CLASSIC_FOOTER}],
    }
    assert header["accessory"]["image_url"].endswith(
        "/discord/nowlert-owl-v3.1.0.png"
    )
    assert "Synthetic presentation warning" in header["text"]["text"]
    assert "Alert" in rendered
    assert "Source" in rendered
    assert "Context" in rendered
    assert "Timing" in rendered


def test_slack_redfish_fallback_keeps_nowlert_branding():
    formatter = SlackFormatter()
    item = notification("redfish")
    item.metadata.update(
        {
            "_input_type": "Redfish",
            "provider": "Redfish",
            "registry": "Synthetic.1.0",
            "message_id": "Synthetic.1.0.Alert",
        }
    )

    attachment = formatter.format(item)["attachments"][0]
    header = attachment["blocks"][0]

    assert header["accessory"]["image_url"].endswith(
        "/discord/nowlert-owl-v3.1.0.png"
    )
    assert "Redfish" in str(attachment)


def test_xo_slack_classic_card_uses_visible_block_icon():
    formatter = SlackFormatter()
    item = notification("xo")
    item.status = "failure"
    item.job_name = "[CRITICAL - 02] Operation Critical"
    item.repository = "UNAS-01 | NFS | Critical Backups"
    item.mode = "full"
    item.transfer_size = "49.22 GiB"
    item.transfer_speed = "27.95 MiB/s"
    item.vm_success = 1
    item.vm_failed = 1
    item.vm_total = 2
    item.successful_vms = ["VM-04 | Docker"]
    item.failed_vms = ["VM-14 | Windows Server"]
    item.vm_details = {
        "VM-04 | Docker": {"size": "18.33 GiB"},
        "VM-14 | Windows Server": {
            "size": "23.66 GiB",
            "error": "Body Timeout Error",
        },
    }
    item.job_id = "synthetic-job-id"

    attachment = formatter.format(item)["attachments"][0]
    header = attachment["blocks"][0]

    assert attachment["fallback"] == (
        "❌ Backup Failed — [CRITICAL - 02] Operation Critical"
    )
    assert attachment["color"] == "#ED4245"
    assert "thumb_url" not in attachment
    assert header["accessory"]["type"] == "image"
    assert header["accessory"]["image_url"].endswith("/discord/xen-orchestra.png")
    assert header["accessory"]["alt_text"] == "Xen Orchestra"
    assert len(header["fields"]) == 4
    rendered = str(attachment["blocks"])
    assert attachment["blocks"][-1] == {
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": CLASSIC_FOOTER}],
    }
    assert "synthetic-job-id" in rendered
    assert "*🆔 Job ID*" in rendered
    assert "Body Timeout Error" in rendered


def test_grafana_slack_classic_links_use_native_slack_mrkdwn():
    formatter = SlackFormatter()
    item = notification("grafana")
    item.metadata.update(
        {
            "dashboard_url": "https://grafana.example.invalid/d/service",
            "panel_url": "https://grafana.example.invalid/d/service?viewPanel=7",
            "rule_url": "https://grafana.example.invalid/alerting/rules/api-latency",
            "silence_url": "https://grafana.example.invalid/alerting/silence/new",
        }
    )

    attachment = formatter.format(item)["attachments"][0]
    links = str(attachment["blocks"])

    assert (
        "<https://grafana.example.invalid/d/service|Dashboard>"
        in links
    )
    assert (
        "<https://grafana.example.invalid/d/service?viewPanel=7|Panel>"
        in links
    )
    assert (
        "<https://grafana.example.invalid/alerting/rules/api-latency|Rule>"
        in links
    )
    assert (
        "<https://grafana.example.invalid/alerting/silence/new|Silence>"
        in links
    )
    assert "[Dashboard](" not in links
    assert "[Panel](" not in links
    assert "[Rule](" not in links
    assert "[Silence](" not in links


def test_slack_classic_link_translation_keeps_unsafe_urls_literal():
    formatter = SlackFormatter()

    rendered = formatter._slack_classic_mrkdwn(
        "[Safe](https://example.invalid/view) · "
        "[Unsafe](javascript:alert(1))"
    )

    assert "<https://example.invalid/view|Safe>" in rendered
    assert "[Unsafe](javascript:alert(1))" in rendered