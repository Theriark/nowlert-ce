"""Round-49 final Discord Classic family cleanup contract."""

from __future__ import annotations

import json

from models import Notification
from outputs.discord import DiscordOutput


def item(source: str, *, category: str = "event") -> Notification:
    notification = Notification(
        source=source,
        category=category,
        status="warning",
        title=f"Synthetic {source} warning",
        subject=f"Synthetic {source} subject",
        body=f"Synthetic {source} detail.",
        start_time="2026-09-20T07:00:00Z",
        duration="5m",
    )
    notification.metadata = {
        "severity": "warning",
        "event_time": "2026-09-20T07:00:00Z",
        "host": "SYNTHETIC-HOST",
        "system": "SYNTHETIC-SYSTEM",
        "nas_name": "SYNTHETIC-NAS",
        "model": "MODEL-1",
        "storage_pool": "POOL-1",
        "volume": "VOL-1",
        "controller": "controller.example.invalid",
        "client_display_name": "CLIENT-1",
        "client_hostname": "client-1.example.invalid",
        "client_ip": "192.0.2.10",
        "client_mac": "00:00:5e:00:53:10",
        "network_name": "LAN",
        "network_vlan": "101",
        "wifi_name": "WIFI",
        "wifi_band": "5 GHz",
        "wifi_channel": "36",
        "wifi_rssi": "-61 dBm",
        "last_device_name": "AP-1",
        "last_device_model": "Synthetic AP",
        "last_device_ip": "192.0.2.11",
        "last_device_mac": "00:00:5e:00:53:11",
        "trigger_key": "motion",
        "trigger_label": "Motion",
        "trigger_device": "CAMERA-1",
        "trigger_count": 2,
        "alarm_name": "Synthetic motion alarm",
        "configured_source_count": 4,
        "condition_source": "camera",
        "condition_operator": "is",
        "outer_timestamp": "2026-09-20T07:00:02Z",
        "backup_task": "Nightly Backup",
        "alarm_id": "00000000-0000-4000-8000-000000000001",
        "provider": "Synthetic Provider",
        "registry": "SyntheticRegistry",
        "message_id": "Synthetic.Message",
        "event_id": "opaque-event-id",
        "origin": "/redfish/v1/Systems/1",
        "source_ip": "192.0.2.12",
        "area": "Utility room",
        "service": "Environment",
        "event_type": "automation",
        "device": "Utility room sensor",
        "entity_id": "sensor.utility_room_humidity",
        "component": "synthetic.component",
        "endpoint": "192.0.2.13:1234",
        "error_code": "SYNTHETIC_ERROR",
        "retry_seconds": "5",
        "tags": ["internal", "debug"],
        "environment": "development",
    }
    return notification


def fields(embed: dict) -> dict[str, str]:
    return {
        field["name"]: field["value"]
        for field in embed["fields"]
    }


def test_synology_classic_removes_duplicate_alert_rows():
    notification = item("synology", category="storage")
    notification.metadata["storage"] = "POOL-1"
    embed = DiscordOutput().source_formatters["synology"].format(
        notification
    )["embeds"][0]
    values = fields(embed)

    assert values["⚠️ Alert"] == "**Severity:** `warning`"
    assert values["💽 Storage"].splitlines() == [
        "**Storage Pool:** `POOL-1`",
        "**Volume:** `VOL-1`",
    ]
    assert "**Status:**" not in repr(embed)
    assert "**Category:**" not in repr(embed)


def test_truenas_classic_keeps_host_without_duplicate_lifecycle_rows():
    notification = item("truenas", category="power")
    notification.title = "UPS power alert"
    notification.body = "UPS SYNTHETIC-UPS is on battery after utility power loss."
    embed = DiscordOutput().source_formatters["truenas"].format(
        notification
    )["embeds"][0]
    values = fields(embed)

    assert values["⚠️ Alert"] == "**Severity:** `warning`"
    assert values["🗄️ TrueNAS System"] == (
        "**Host:** `SYNTHETIC-HOST`"
    )
    assert "**Status:**" not in values["🔋 Power"]
    assert "**Category:**" not in repr(embed)


def test_unifi_network_classic_removes_duplicate_identity_rows():
    embed = DiscordOutput().source_formatters["unifi_network"].format(
        item("unifi_network", category="network")
    )["embeds"][0]
    values = fields(embed)

    assert values["⚠️ Alert"] == "**Severity:** `warning`"
    assert "Hostname" not in values["💻 Client"]
    assert "00:00:5e:00:53:10" in values["💻 Client"]
    assert "00:00:5e:00:53:11" not in values["📍 Last Access Point"]


def test_unifi_protect_classic_removes_counts_and_webhook_time():
    embed = DiscordOutput().source_formatters["unifi_protect"].format(
        item("unifi_protect", category="security")
    )["embeds"][0]
    rendered = repr(embed)

    assert "**Triggers:**" not in rendered
    assert "Configured Sources" not in rendered
    assert "**Webhook:**" not in rendered
    assert "**Severity:** `warning`" in rendered


def test_unifi_drive_classic_keeps_alarm_id_not_duplicate_name_state():
    embed = DiscordOutput().source_formatters["unifi_drive"].format(
        item("unifi_drive", category="backup")
    )["embeds"][0]
    values = fields(embed)

    assert values["🆔 Alarm"] == (
        "**Alarm ID:** "
        "`00000000-0000-4000-8000-000000000001`"
    )
    assert "Provider" not in repr(embed)
    assert "**Name:**" not in repr(embed)
    assert "**State:**" not in repr(embed)


def test_redfish_vendor_classic_cards_share_compact_hardware_geometry():
    output = DiscordOutput()
    for source, label in (
        ("supermicro", "Supermicro BMC"),
        ("hpe_ilo", "HPE iLO"),
        ("dell_idrac", "Dell iDRAC"),
    ):
        embed = output.source_formatters[source].format(
            item(source, category="hardware")
        )["embeds"][0]
        values = fields(embed)

        assert list(values) == [
            "⚠️ Alert",
            f"🖥️ {label}",
            "🔎 Hardware Event",
            "⏱️ Timing",
        ]
        assert "Provider" not in repr(embed)
        assert "Source IP" not in repr(embed)
        assert "Event ID" not in repr(embed)
        assert "Hardware Origin" not in repr(embed)
        assert "/redfish/" not in repr(embed)


def test_home_assistant_classic_keeps_only_actionable_source_context():
    embed = DiscordOutput().source_formatters["home_assistant"].format(
        item("home_assistant", category="environment")
    )["embeds"][0]
    rendered = repr(embed)

    assert "**Provider:**" not in rendered
    assert "**Event Type:**" not in rendered
    assert "**Tags:**" not in rendered
    assert "**Area:** `Utility room`" in rendered
    assert "**Service:** `Environment`" in rendered
    assert "**Component:** `synthetic.component`" in rendered


def test_generic_fallback_uses_ce_classic_footer_and_compact_sections():
    notification = item("generic", category="event")
    notification.metadata.update(
        provider="generic",
        environment="development",
        action_link="https://example.invalid/event/1",
    )
    embed = DiscordOutput().default_formatter.format(notification)[
        "embeds"
    ][0]
    values = fields(embed)

    assert embed["footer"] == {
        "text": "🦉 Nowlert CE • Classic Card"
    }
    assert list(values) == [
        "⚠️ Alert",
        "📍 Source",
        "🧩 Context",
        "⏱️ Timing",
    ]
    assert "**Severity:** `warning`" in values["⚠️ Alert"]
    assert "**Category:** `event`" in values["⚠️ Alert"]
    assert "**Host:** `SYNTHETIC-HOST`" in values["📍 Source"]
    assert "**Environment:** `development`" in values["🧩 Context"]
    assert embed["url"] == "https://example.invalid/event/1"

    rendered = json.dumps(embed, ensure_ascii=False)
    assert "Theriark • Nowlert" not in rendered
