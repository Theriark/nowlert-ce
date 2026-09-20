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

        assert attachment["title"] == discord_embed["title"][:200]
        assert attachment["color"] == (
            f"#{discord_embed['color'] & 0xFFFFFF:06X}"
        )
        assert attachment["footer"] == CLASSIC_FOOTER
        assert attachment["title_link"] == item.metadata["action_link"]
        assert attachment["mrkdwn_in"] == ["text", "fields"]
        assert len(attachment["fields"]) <= 10
        assert attachment["fields"]

        icon = formatter.PRODUCT_ICONS[expected_icon_source(source)]
        assert attachment["thumb_url"].endswith(f"/{icon}")


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
    assert attachment["footer"] == CLASSIC_FOOTER
    assert attachment["thumb_url"].endswith("/nowlert.png")
    assert "Synthetic presentation warning" in attachment["title"]
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

    assert attachment["thumb_url"].endswith("/nowlert.png")
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
    assert header["accessory"]["image_url"].endswith("/xen-orchestra.png")
    assert header["accessory"]["alt_text"] == "Xen Orchestra"
    rendered = str(attachment["blocks"])
    assert CLASSIC_FOOTER in rendered
    assert "synthetic-job-id" in rendered
    assert "*🆔 Job ID*" not in rendered
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
    links = next(
        field["value"]
        for field in attachment["fields"]
        if field["title"] == "🔗 Links"
    )

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