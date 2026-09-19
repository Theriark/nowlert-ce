"""Round-40 Discord Classic Embed v1 port contract."""

from __future__ import annotations

import pytest

from models import Notification
from outputs.platform import DiscordPlatformAdapter
from storage.destinations import Destination


CLASSIC_FOOTER = "🦉 Nowlert CE • Classic Embed"

SOURCE_SIGNATURES = (
    ("xo", "🗃️ Storage"),
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


def test_classic_embed_v1_xo_uses_v1_kpi_and_storage_geometry():
    preview = DiscordPlatformAdapter().preview(
        destination(components_v2=False),
        notification("xo"),
    )
    fields = preview.payload["embeds"][0]["fields"]
    names = [field["name"] for field in fields]

    assert names[:3] == ["⌛ Duration", "💿 Transfer Size", "⚡ Transfer Speed"]
    assert "🗃️ Storage" in names
    assert "🕰️ Timing" in names
    assert "🧾 Job Details" in names


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
