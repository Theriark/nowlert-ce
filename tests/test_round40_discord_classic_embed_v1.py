"""Round-40 Discord Classic Card v1 port contract."""

from __future__ import annotations

import pytest

from models import Notification
from outputs.discord import DiscordOutput
from outputs.platform import DiscordPlatformAdapter
from storage.destinations import Destination


CLASSIC_FOOTER = "🦉 Nowlert CE • Classic Card"

SOURCE_SIGNATURES = (
    ("xo", "📁 Storage"),
    ("zabbix", "🚨 Problem"),
    ("grafana", "📂 Rule"),
    ("portainer", "📦 Portainer"),
    ("proxmox", "🟧 Proxmox VE"),
    ("qnap", "🗄️ QNAP NAS"),
    ("synology", "🗄️ Synology NAS"),
    ("truenas", "🗄️ TrueNAS System"),
    ("unifi_network", "🎛️ UniFi Controller"),
    ("unifi_protect", "🎯 Trigger"),
    ("unifi_drive", "🗄️ UniFi Drive"),
    ("supermicro", "🖥️ Supermicro BMC"),
    ("hpe_ilo", "🖥️ HPE iLO"),
    ("dell_idrac", "🖥️ Dell iDRAC"),
    ("home_assistant", "🏠 Home Assistant"),
)


def destination(*, components_v2: bool) -> Destination:
    return Destination(
        id="d" * 32,
        owner_user_id="u" * 32,
        name="Discord",
        output_type="discord",
        settings={"components_v2": components_v2},
        shared=True,
        enabled=True,
        secret_configured=True,
        created_at=1,
        updated_at=1,
    )


def notification(source: str) -> Notification:
    category = {
        "xo": "backup",
        "zabbix": "monitoring",
        "grafana": "monitoring",
        "portainer": "containers",
        "proxmox": "storage",
        "qnap": "storage",
        "synology": "storage",
        "truenas": "storage",
        "unifi_network": "network",
        "unifi_protect": "security",
        "unifi_drive": "backup",
        "supermicro": "hardware",
        "hpe_ilo": "hardware",
        "dell_idrac": "hardware",
        "home_assistant": "automation",
    }[source]
    item = Notification(
        source=source,
        category=category,
        status="warning",
        title=f"Synthetic {source} event",
        subject=f"Synthetic {source} subject",
        body=f"Synthetic {source} operational detail.",
        sender="source@example.test",
        job_name="Synthetic backup job",
        job_id="JOB-40",
        run_id="RUN-40",
        mode="full",
        repository="SYNTHETIC-REPOSITORY",
        transfer_size="52.06 GiB",
        transfer_speed="33.73 MiB/s",
        start_time="2026-09-19T03:00:00+00:00",
        end_time="2026-09-19T03:28:00+00:00",
        duration="28 minutes",
        vm_total=3,
        vm_success=2,
        vm_failed=1,
        successful_vms=["VM-OK-1", "VM-OK-2"],
        failed_vms=["VM-FAILED"],
        errors=["Synthetic failure"],
        vm_details={
            "VM-OK-1": {"size": "18 GiB", "speed": "30 MiB/s"},
            "VM-OK-2": {"size": "12 GiB", "speed": "29 MiB/s"},
            "VM-FAILED": {"error": "Synthetic timeout"},
        },
    )
    item.metadata = {
        "_input_type": "http",
        "provider": {
            "supermicro": "Supermicro BMC",
            "hpe_ilo": "HPE iLO",
            "dell_idrac": "Dell iDRAC",
            "home_assistant": "Home Assistant",
        }.get(source, source),
        "host": "SYNTHETIC-HOST",
        "hostname": "SYNTHETIC-HOST",
        "system": "SYNTHETIC-SYSTEM",
        "severity": "warning",
        "state": "warning",
        "event_time": "2026-09-19T03:00:00+00:00",
        "nas_name": "SYNTHETIC-NAS",
        "model": "SYNTHETIC-MODEL",
        "application": "Synthetic App",
        "event_type": "storage warning",
        "message": f"Synthetic {source} operational detail.",
        "alert_name": "Synthetic alert",
        "alert_rule": "Synthetic rule",
        "rule_name": "Synthetic rule",
        "alert_count": 1,
        "folder": "Synthetic folder",
        "organization": "Synthetic org",
        "dashboard": "Synthetic dashboard",
        "panel": "Synthetic panel",
        "datasource": "Synthetic datasource",
        "values": {"value": "42"},
        "labels": {"environment": "development"},
        "instance": "SYNTHETIC-INSTANCE",
        "alert_source": "Synthetic area",
        "authentication_method": "local",
        "username": "synthetic",
        "metric": "synthetic_metric",
        "current_value": "42",
        "threshold": "40",
        "window": "5m",
        "node": "PVE-01",
        "guest": "VM-100",
        "vmid": "100",
        "storage": "local-zfs",
        "used_percent": "71",
        "storage_pool": "POOL-01",
        "controller": "UDM-01",
        "client_display_name": "CLIENT-01",
        "client_hostname": "client-01",
        "client_ip": "192.0.2.40",
        "client_mac": "00:11:22:33:44:55",
        "network_name": "LAN",
        "network_vlan": "20",
        "wifi_name": "WiFi",
        "wifi_band": "5 GHz",
        "wifi_channel": "44",
        "wifi_rssi": "-51 dBm",
        "last_device_name": "AP-01",
        "last_device_model": "U7 Pro",
        "last_device_ip": "192.0.2.41",
        "last_device_mac": "00:11:22:33:44:66",
        "trigger_key": "motion",
        "trigger_label": "Motion",
        "trigger_device": "CAM-01",
        "trigger_count": 1,
        "alarm_name": "Perimeter",
        "configured_source_count": 2,
        "condition_source": "camera",
        "condition_operator": "is",
        "outer_timestamp": "2026-09-19T03:00:02+00:00",
        "event_link": "https://example.test/event/40",
        "backup_task": "Nightly Backup",
        "area": "Server room",
        "service": "automation.synthetic",
        "entity_id": "sensor.synthetic",
        "device": "Synthetic Device",
        "component": "synthetic_component",
        "endpoint": "/api/synthetic",
        "error_code": "SYNTHETIC",
        "retry_seconds": "30",
        "tags": ["development", "synthetic"],
        "sensor": "Synthetic Sensor",
        "registry": "Synthetic.Registry",
        "message_id": "Synthetic.Message",
        "event_id": "EVENT-40",
        "origin": "/redfish/v1/Systems/1",
        "source_ip": "192.0.2.42",
        "problem_name": "Synthetic Zabbix problem",
        "operational_data": "Synthetic operational state",
        "problem_id": "4001",
        "fields": {
            "trigger expression": "last(/host/key)>40",
            "event tags": "env:development",
            "runbook": "https://example.test/runbook",
            "original problem id": "4001",
        },
        "source_fields": {
            "event type": "storage warning",
            "nas name": "SYNTHETIC-NAS",
            "app name": "Synthetic App",
            "disk": "Disk 1",
            "storage pool": "POOL-01",
            "pool status": "Degraded",
        },
    }
    return item


@pytest.mark.parametrize(("source", "signature"), SOURCE_SIGNATURES)
def test_classic_embed_v1_uses_ee_source_layout_without_ai(source: str, signature: str):
    preview = DiscordPlatformAdapter().preview(
        destination(components_v2=False),
        notification(source),
    )

    assert set(preview.payload) == {"embeds"}
    embed = preview.payload["embeds"][0]
    names = [str(field.get("name") or "") for field in embed.get("fields", [])]
    flattened = "\n".join(
        [
            str(embed.get("title") or ""),
            str(embed.get("description") or ""),
            *(str(field.get("name") or "") for field in embed.get("fields", [])),
            *(str(field.get("value") or "") for field in embed.get("fields", [])),
            str((embed.get("footer") or {}).get("text") or ""),
        ]
    )

    assert signature in names, source
    assert embed["footer"] == {"text": CLASSIC_FOOTER}, source
    assert "Nowlert AI" not in flattened, source
    assert "Insight" not in names, source
    assert "Context" not in names, source
    assert "Recommended Action" not in names, source


def test_classic_embed_v1_xo_uses_compact_ce_geometry():
    preview = DiscordPlatformAdapter().preview(
        destination(components_v2=False),
        notification("xo"),
    )
    fields = preview.payload["embeds"][0]["fields"]
    names = [field["name"] for field in fields]
    values = {field["name"]: field["value"] for field in fields}

    assert names == [
        "⏱️ Duration",
        "📦 Transfer Size",
        "🚀 Transfer Speed",
        "📁 Storage",
        "✅ Successful VMs · 2",
        "❌ Failed VMs · 1",
        "🆔 Job ID",
    ]
    assert values["📁 Storage"] == "`SYNTHETIC-REPOSITORY · Full`"
    assert "30 MiB/s" not in values["✅ Successful VMs · 2"]
    assert "29 MiB/s" not in values["✅ Successful VMs · 2"]
    assert "Synthetic timeout" in values["❌ Failed VMs · 1"]
    assert "⏱️ Timing" not in names
    assert "📧 Email" not in names
    assert "✉️ Subject" not in names
    assert "🔢 Job Details" not in names



@pytest.mark.parametrize(
    ("classification", "status", "icon", "label", "color"),
    (
        ("urgent", "critical", "🚨", "Urgent", 0xE74C3C),
        ("warning", "warning", "⚠️", "Warning", 0xF39C12),
        ("information", "information", "ℹ️", "Information", 0x3498DB),
    ),
)
def test_email_classic_card_uses_email_alert_semantics(
    classification,
    status,
    icon,
    label,
    color,
):
    item = Notification(
        source="email",
        category="Nowlert CE Dev",
        status=status,
        title="[NOWLERT-MOCK-GATE] Email Alerts acceptance",
        subject="[NOWLERT-MOCK-GATE] Email Alerts acceptance",
        body=(
            "Email from nowlert.qa@gmail.com to nowlert.qa@gmail.com "
            "matched Nowlert CE Mock Platform."
        ),
        sender="nowlert.qa@gmail.com",
    )
    item.metadata = {
        "_input_type": "email",
        "classification": classification,
        "state": classification,
        "severity": status,
        "group": "Nowlert CE Dev",
        "rule": f"Nowlert CE Mock Platform - {label}",
        "mailbox": "nowlert.qa@gmail.com",
        "recipient": "nowlert.qa@gmail.com",
        "sender": "nowlert.qa@gmail.com",
        "provider": "gmail",
        "message_id": "internal-message-id",
        "internet_message_id": "<internet-message@example.invalid>",
        "provider_deep_link": "https://mail.google.com/mail/u/0/#inbox/example",
    }

    preview = DiscordPlatformAdapter().preview(
        destination(components_v2=False),
        item,
    )

    embed = preview.payload["embeds"][0]
    fields = {field["name"]: field["value"] for field in embed["fields"]}
    flattened = repr(embed)

    assert embed["title"] == (
        f"{icon} [NOWLERT-MOCK-GATE] Email Alerts acceptance — {label}"
    )
    assert embed["color"] == color
    assert embed["footer"] == {"text": "🦉 Nowlert CE • Email Alerts"}
    assert embed["url"] == "https://mail.google.com/mail/u/0/#inbox/example"
    assert f"**Classification:** `{label}`" in fields[f"{icon} Email Alert"]
    assert (
        f"**Rule:** `Nowlert CE Mock Platform - {label}`"
        in fields[f"{icon} Email Alert"]
    )
    assert "**Group:** `Nowlert CE Dev`" in fields[f"{icon} Email Alert"]
    assert "**Sender:** `nowlert.qa@gmail.com`" in fields["✉️ Email"]
    assert "**Mailbox:** `nowlert.qa@gmail.com`" in fields["✉️ Email"]
    assert "**Provider:** `Gmail`" in fields["✉️ Email"]
    assert "**Recipient:**" not in fields["✉️ Email"]
    assert "Failed" not in flattened
    assert "Input" not in flattened
    assert "Message ID" not in flattened
    assert "Category" not in flattened


def test_email_components_v2_remains_on_existing_modern_contract():
    item = Notification(
        source="email",
        category="Nowlert CE Dev",
        status="critical",
        title="Urgent email",
        subject="Urgent email",
        body="Existing modern-card body",
        sender="nowlert.qa@gmail.com",
    )
    item.metadata = {
        "_input_type": "email",
        "classification": "urgent",
        "severity": "critical",
        "provider": "gmail",
        "mailbox": "nowlert.qa@gmail.com",
    }

    preview = DiscordPlatformAdapter().preview(
        destination(components_v2=True),
        item,
    )

    assert preview.payload["flags"] == 32768
    assert "components" in preview.payload
    assert "embeds" not in preview.payload
    assert "Nowlert CE • Email Alerts" not in repr(preview.payload)


def test_components_v2_bypasses_classic_embed_v1():
    preview = DiscordPlatformAdapter().preview(
        destination(components_v2=True),
        notification("dell_idrac"),
    )

    assert preview.payload["flags"] == 32768
    assert "components" in preview.payload
    assert "embeds" not in preview.payload
    rendered = repr(preview.payload)
    assert CLASSIC_FOOTER not in rendered


@pytest.mark.parametrize(("source", "signature"), SOURCE_SIGNATURES)
def test_direct_classic_formatter_uses_v1_contract(source: str, signature: str):
    """Direct formatter calls must not bypass the Classic Card v1 renderer."""

    output = DiscordOutput()
    formatter = output.source_formatters[source]
    payload = formatter.format(notification(source))

    assert set(payload) == {"embeds"}
    embed = payload["embeds"][0]
    names = [str(field.get("name") or "") for field in embed.get("fields", [])]

    assert signature in names, source
    assert embed["footer"] == {"text": CLASSIC_FOOTER}, source


def test_direct_xo_formatter_no_longer_emits_legacy_classic_geometry():
    payload = DiscordOutput().source_formatters["xo"].format(notification("xo"))
    embed = payload["embeds"][0]
    names = [str(field.get("name") or "") for field in embed.get("fields", [])]

    assert "📁 Storage" in names
    assert "📋 Event details" not in names
    assert embed["footer"] == {"text": CLASSIC_FOOTER}


def test_direct_components_v2_still_uses_existing_modern_contract():
    formatter = DiscordOutput().source_formatters["xo"]
    payload = formatter.format_components_v2(notification("xo"))

    assert payload["flags"] == 32768
    assert "components" in payload
    assert "embeds" not in payload
    assert CLASSIC_FOOTER not in repr(payload)


FINAL_EE_REQUIRED_FIELDS = {
    "zabbix": [
        "🚨 Problem",
        "📈 Operational Data",
        "🧪 Trigger",
        "🆔 Problem ID",
        "⏱️ Timing",
        "📘 Runbook",
    ],
    "grafana": [
        "📣 Alert",
        "📂 Rule",
        "📊 Location",
        "🗄️ Datasource",
        "🏷️ Labels",
        "📈 Values",
        "⏱️ Timing",
    ],
    "portainer": [
        "⚠️ Alert",
        "📦 Portainer",
        "🔐 Authentication",
        "📈 Signal",
        "⏱️ Timing",
    ],
    "proxmox": [
        "⚠️ Alert",
        "🟧 Proxmox VE",
        "💾 Storage",
        "⏱️ Timing",
    ],
    "qnap": [
        "⚠️ Alert",
        "🗄️ QNAP NAS",
        "💽 Storage",
        "⏱️ Timing",
    ],
    "synology": [
        "⚠️ Alert",
        "🗄️ Synology NAS",
        "💽 Storage",
        "⏱️ Timing",
    ],
    "truenas": [
        "⚠️ Alert",
        "🗄️ TrueNAS System",
        "💽 Storage",
        "⏱️ Timing",
    ],
    "unifi_network": [
        "⚠️ Alert",
        "🎛️ UniFi Controller",
        "💻 Client",
        "📶 Network / Wi-Fi",
        "📍 Last Access Point",
        "⏱️ Timing",
    ],
    "unifi_protect": [
        "⚠️ Alert",
        "🎯 Trigger",
        "🚨 Alarm Rule",
        "🔎 Condition",
        "⏱️ Timing",
    ],
    "unifi_drive": [
        "⚠️ Alert",
        "🗄️ UniFi Drive",
        "⏱️ Timing",
    ],
    "supermicro": [
        "⚠️ Alert",
        "🖥️ Supermicro BMC",
        "🔎 Hardware Event",
        "⏱️ Timing",
    ],
    "hpe_ilo": [
        "⚠️ Alert",
        "🖥️ HPE iLO",
        "🔎 Hardware Event",
        "⏱️ Timing",
    ],
    "dell_idrac": [
        "⚠️ Alert",
        "🖥️ Dell iDRAC",
        "🔎 Hardware Event",
        "⏱️ Timing",
    ],
    "home_assistant": [
        "⚠️ Alert",
        "🏠 Home Assistant",
        "🎯 Entity / Device",
        "🔎 Source Details",
        "⏱️ Timing",
    ],
}


@pytest.mark.parametrize(("source", "required"), FINAL_EE_REQUIRED_FIELDS.items())
def test_non_xo_classic_templates_match_final_ee_operator_sections(source, required):
    embed = DiscordOutput().source_formatters[source].format(notification(source))["embeds"][0]
    names = [str(field.get("name") or "") for field in embed.get("fields", [])]

    positions = [names.index(name) for name in required]
    assert positions == sorted(positions), source
    assert embed["footer"] == {"text": CLASSIC_FOOTER}, source
    assert all(name not in names for name in ("Body", "Metadata", "Job Details")), source
    assert all(
        marker not in repr(embed)
        for marker in ("Nowlert AI", "Insight", "Context", "Recommended Action")
    ), source
