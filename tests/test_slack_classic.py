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
            "network_name": "SYNTHETIC-NETWORK",
            "network_vlan": "101",
            "wifi_name": "SYNTHETIC-WIFI",
            "wifi_band": "5 GHz",
            "wifi_channel": "36",
            "wifi_rssi": "-61 dBm",
            "last_device_name": "SYNTHETIC-AP",
            "last_device_model": "Synthetic AP",
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
        "SYNTHETIC-NETWORK",
        "SYNTHETIC-WIFI",
        "SYNTHETIC-AP",
        "5m 30s",
        "Channel",
        "36",
        "RSSI",
        "-61 dBm",
    ):
        assert expected in unifi_rendered

    field_items = [
        field
        for block in unifi_sections
        for field in block.get("fields", [])
    ]
    field_by_title = {
        item["text"].split("\n", 1)[0].strip("*"): item["text"]
        for item in field_items
    }

    network_field = field_by_title["📶 Network / Wi-Fi"]
    radio_field = field_by_title["📡 Radio / Signal"]

    assert "Network" in network_field
    assert "VLAN" in network_field
    assert "Wi-Fi" in network_field
    assert "Band" in network_field
    assert "Channel" not in network_field
    assert "RSSI" not in network_field
    assert network_field.count("\n") == 4

    assert "Channel" in radio_field
    assert "RSSI" in radio_field
    assert radio_field.count("\n") == 2

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


def prometheus_notification(state: str = "firing") -> Notification:
    resolved = state == "resolved"
    item = Notification(
        source="prometheus",
        category="monitoring",
        status="success" if resolved else "warning",
        title="HighRequestLatency",
        body=(
            "Request latency returned below the alert threshold."
            if resolved
            else "95th percentile latency exceeded two seconds."
        ),
        start_time="2026-09-23T02:00:00Z",
        end_time="2026-09-23T02:02:00Z" if resolved else "",
    )
    item.metadata = {
        "state": state,
        "severity": "critical" if resolved else "warning",
        "instance": "api-01:9090",
        "service": "checkout",
        "job": "api-server",
        "namespace": "production",
        "receiver": "nowlert-critical",
        "labels": "environment=production",
        "alert_count": 1,
        "group_members": [],
        "external_url": "https://alertmanager.example.invalid",
        "generator_url": "https://prometheus.example.invalid/graph",
        "runbook_url": "https://runbooks.example.invalid/request-latency",
    }
    return item


def test_prometheus_slack_classic_is_unfolded_without_show_more_geometry():
    formatter = SlackFormatter()
    payload = formatter.format(prometheus_notification())
    blocks = payload["attachments"][0]["blocks"]

    sections = [
        block
        for block in blocks
        if block.get("type") == "section"
    ]
    assert sections
    assert sections[0]["accessory"]["image_url"].endswith(
        "/discord/prometheus.png"
    )

    # Slack folds tall field grids behind "Show more". Keep Prometheus
    # Classic split into small two-column field sections instead.
    assert all(
        len(block.get("fields", [])) <= 2
        for block in sections
    )

    text_sections = [
        block["text"]["text"]
        for block in sections
        if isinstance(block.get("text"), dict)
        and "accessory" not in block
    ]
    assert all(
        text.count("\n") <= 4
        for text in text_sections
    )
    assert all(
        len(text) <= 650
        for text in text_sections
    )

    rendered = str(blocks)
    for expected in (
        "HighRequestLatency",
        "Receiver",
        "nowlert-critical",
        "Labels",
        "environment=production",
        "Target",
        "api-01:9090",
        "checkout",
        "api-server",
        "production",
        "Timing",
        "2026-09-23T02:00:00Z",
        "Alertmanager",
        "Prometheus",
        "Runbook",
    ):
        assert expected in rendered


def test_prometheus_slack_classic_grouped_stays_below_attachment_fold():
    formatter = SlackFormatter()

    grouped = prometheus_notification()
    grouped.title = "Prometheus alert group"
    grouped.metadata["alert_count"] = 2
    grouped.metadata["group_members"] = [
        {
            "title": "ApiErrorRateHigh",
            "state": "firing",
            "severity": "critical",
            "target": "api-02:9090",
        },
        {
            "title": "QueueDepthHigh",
            "state": "firing",
            "severity": "warning",
            "target": "worker-02:9090",
        },
    ]

    blocks = formatter.format(grouped)["attachments"][0]["blocks"]

    # Slack folds the entire attachment when this grouped card becomes too
    # tall. Keep the full grouped Prometheus payload in four compact blocks.
    assert len(blocks) == 4
    assert [block["type"] for block in blocks] == [
        "section",
        "section",
        "section",
        "context",
    ]

    header, alerts, target, footer = blocks
    assert header["accessory"]["image_url"].endswith(
        "/discord/prometheus.png"
    )
    assert len(header["fields"]) == 2
    assert len(alerts["fields"]) == 2
    assert len(target["fields"]) == 2

    header_text = str(header["fields"])
    alerts_text = str(alerts["fields"])
    target_text = str(target["fields"])
    footer_text = str(footer["elements"])

    assert "Alert" in header_text
    assert "Prometheus" in header_text
    assert "Labels" in alerts_text
    assert "Alerts · 2" in alerts_text
    assert "ApiErrorRateHigh" in alerts_text
    assert "QueueDepthHigh" in alerts_text
    assert "api-02:9090" in alerts_text
    assert "worker-02:9090" in alerts_text
    assert "Timing" in target_text
    assert "Target" in target_text
    assert "api-01:9090" in target_text
    assert "api-server" in target_text
    assert "production" in target_text
    assert "Links" in footer_text
    assert "Alertmanager" in footer_text
    assert "Prometheus" in footer_text
    assert CLASSIC_FOOTER in footer_text

    target_field = next(
        field
        for field in target["fields"]
        if "Target" in field["text"]
    )
    assert target_field["text"].count("\n") <= 2


def test_prometheus_slack_classic_resolved_stays_fully_expanded():
    formatter = SlackFormatter()
    resolved = prometheus_notification("resolved")
    blocks = formatter.format(resolved)["attachments"][0]["blocks"]

    sections = [
        block
        for block in blocks
        if block.get("type") == "section"
    ]
    assert all(
        len(block.get("fields", [])) <= 2
        for block in sections
    )
    assert all(
        block["text"]["text"].count("\n") <= 4
        and len(block["text"]["text"]) <= 650
        for block in sections
        if isinstance(block.get("text"), dict)
        and "accessory" not in block
    )

    rendered = str(blocks)
    assert "Resolved" in rendered
    assert "2026-09-23T02:02:00Z" in rendered


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