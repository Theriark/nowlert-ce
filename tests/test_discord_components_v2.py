"""Focused Discord Components V2 prototype coverage."""

from __future__ import annotations

import json
from urllib.parse import parse_qs, urlsplit

from formatters.discord_hardware import DellIDRACDiscordFormatter
from models import Notification
from outputs.discord import DiscordOutput
import outputs.discord as discord_output_module
from version import VERSION


ALL_DISCORD_SOURCES = (
    "xo",
    "grafana",
    "portainer",
    "proxmox",
    "qnap",
    "synology",
    "truenas",
    "unifi_network",
    "unifi_protect",
    "unifi_drive",
    "zabbix",
    "redfish",
    "supermicro",
    "hpe_ilo",
    "dell_idrac",
    "home_assistant",
    "generic",
)


def integration_notification(source: str) -> Notification:
    item = Notification(
        source="home_lab" if source == "generic" else source,
        title="Synthetic responsive event",
        body="Synthetic responsive operational detail.",
        category="storage",
        status="warning",
        job_name="Synthetic XO backup",
        start_time="2026-07-20T23:31:00+00:00",
        end_time="2026-07-20T23:36:00+00:00",
        duration="5 min",
    )
    item.metadata = {
        "provider": "Generic Webhook",
        "host": "SYNTHETIC-HOST",
        "hostname": "SYNTHETIC-HOST",
        "system": "SYNTHETIC-SYSTEM",
        "nas_name": "SYNTHETIC-NAS",
        "instance": "SYNTHETIC-INSTANCE",
        "device": "SYNTHETIC-DEVICE",
        "area": "Synthetic area",
        "service": "synthetic.service",
        "entity_id": "sensor.synthetic",
        "node": "SYNTHETIC-PVE",
        "controller": "SYNTHETIC-UDM",
        "client_display_name": "SYNTHETIC-CLIENT",
        "wifi_name": "SYNTHETIC-WIFI",
        "trigger_key": "motion",
        "trigger_device": "CAM-SYNTHETIC-01",
        "alarm_name": "Synthetic Protect alarm",
        "backup_task": "Synthetic backup",
        "problem_name": "Synthetic Zabbix problem",
        "alert_name": "Synthetic Grafana alert",
        "alert_count": 1,
        "folder": "Synthetic folder",
        "dashboard": "Synthetic dashboard",
        "panel": "Synthetic panel",
        "operational_data": "Synthetic operational state",
        "event_type": "storage warning",
        "severity": "warning",
        "event_time": "2026-07-20T23:31:00+00:00",
        "state": "warning",
        "message": "Synthetic responsive operational detail.",
        "model": "SYNTHETIC-MODEL",
        "storage_pool": "Synthetic Pool",
        "sensor": "Synthetic sensor",
        "registry": "Synthetic registry",
        "message_id": "Synthetic.Message",
        "origin": "/synthetic/origin",
    }
    return item


def dell_notification() -> Notification:
    return Notification(
        source="dell_idrac",
        title="Power Supply Recovered",
        body="The power supply returned to a healthy state.",
        category="power",
        status="resolved",
        start_time="2026-07-20T23:31:00+00:00",
        metadata={
            "provider": "Dell iDRAC",
            "system": "DELL-SRV-01",
            "severity": "Ok",
            "sensor": "PSU 1",
            "registry": "iDRAC",
            "message_id": "iDRAC.Audit.Power",
            "origin": "/redfish/v1/Chassis/1/Power",
        },
    )


def child_components(payload: dict) -> list[dict]:
    return payload["components"][0]["components"]


def text_content(payload: dict) -> str:
    values = []

    def visit(component):
        if isinstance(component, dict):
            if component.get("type") == 10:
                values.append(component["content"])
            for value in component.values():
                visit(value)
        elif isinstance(component, list):
            for value in component:
                visit(value)

    visit(payload["components"])
    return "\n".join(values)


def flattened_components(payload: dict) -> list[dict]:
    values = []

    def visit(component):
        if isinstance(component, dict):
            if "type" in component:
                values.append(component)
            for value in component.values():
                visit(value)
        elif isinstance(component, list):
            for value in component:
                visit(value)

    visit(payload["components"])
    return values


def test_dell_components_v2_uses_native_responsive_separators():
    formatter = DellIDRACDiscordFormatter()
    payload = formatter.format_components_v2(dell_notification())

    assert set(payload) == {"flags", "components"}
    assert payload["flags"] == 32768
    assert len(payload["components"]) == 1

    container = payload["components"][0]
    assert container["type"] == 17
    assert container["accent_color"] == 0x2ECC71

    children = child_components(payload)
    assert children[0]["type"] == 9
    assert children[0]["accessory"]["type"] == 11
    assert children[0]["accessory"]["media"]["url"].endswith(
        "/dell-idrac.png"
    )

    separators = [child for child in children if child["type"] == 14]
    assert [separator["divider"] for separator in separators] == [
        True,
        False,
        True,
        True,
    ]
    assert all(separator["spacing"] == 1 for separator in separators)

    header_text = children[0]["components"][0]["content"]
    context_text = children[0]["components"][1]["content"]
    assert "DELL-SRV-01 • Power Supply Recovered" in header_text
    assert "Dell iDRAC • ✅ **Resolved** • 🔌 Power" in context_text
    assert "Dell iDRAC" not in header_text
    assert children[1]["type"] == 14
    assert children[1]["divider"] is True
    assert children[2]["content"].startswith("```\n")

    rendered = text_content(payload)
    assert "DELL-SRV-01 • Power Supply Recovered" in rendered
    assert "Dell iDRAC • ✅ **Resolved** • 🔌 Power" in rendered
    assert "The power supply returned to a healthy state." in rendered
    assert "✅ **Severity:** Ok" in rendered
    assert "🔌 **Category:** Power" in rendered
    assert "🕒 **Event time:**" in rendered
    assert "🌡️ **Sensor:** PSU 1" in rendered
    assert "📍 **Origin:** /redfish/v1/Chassis/1/Power" in rendered
    assert f"Theriark • Nowlert v{VERSION}" in rendered
    assert "─" not in rendered
    assert "embeds" not in payload
    assert "attachments" not in payload
    assert len(flattened_components(payload)) <= 40
    assert len(rendered) <= 4000


def test_every_discord_integration_uses_approved_components_v2_contract():
    output = DiscordOutput()

    for source in ALL_DISCORD_SOURCES:
        formatter = (
            output.default_formatter
            if source == "generic"
            else output.source_formatters[source]
        )
        payload = formatter.format_components_v2(
            integration_notification(source)
        )

        assert payload["flags"] == 32768, source
        assert "embeds" not in payload, source
        assert "attachments" not in payload, source
        container = payload["components"][0]
        assert container["type"] == 17, source
        children = container["components"]
        header = children[0]
        assert header["type"] == 9, source
        assert len(header["components"]) == 2, source
        assert header["accessory"]["type"] == 11, source
        assert header["accessory"]["media"]["url"].endswith(".png"), source
        assert children[1] == {
            "type": 14,
            "divider": True,
            "spacing": 1,
        }, source
        assert children[2]["type"] == 10, source
        assert children[2]["content"].startswith("```\n"), source
        separators = [
            component
            for component in children
            if component.get("type") == 14
        ]
        assert [item["divider"] for item in separators] == [
            True,
            False,
            True,
            True,
        ], source
        assert all(item["spacing"] == 1 for item in separators), source
        rendered = text_content(payload)
        assert "**Severity:**" in rendered, source
        assert "**Category:**" in rendered, source
        assert "**Event time:**" in rendered, source
        assert "📋 Event details" in rendered, source
        if source == "xo":
            assert f"Theriark - Nowlert v{VERSION}" in rendered, source
        else:
            assert f"Theriark • Nowlert v{VERSION}" in rendered, source
        assert len(flattened_components(payload)) <= 40, source
        assert len(rendered) <= 4000, source


def _approved_xo_notification(kind: str) -> Notification:
    if kind == "success":
        item = Notification(
            source="xo",
            subject="Backup report for [NON-CRITICAL - 01] Administration",
            category="backup",
            status="success",
            job_name="[NON-CRITICAL - 01] Administration",
            mode="full",
            duration="28 minutes",
            transfer_size="52.06 GiB",
            repository="UNAS-01 | NFS | Non-Critical Backups",
            transfer_speed="33.73 MiB/s",
            start_time="2026-09-21 16:30:22 UTC",
            end_time="2026-09-21 16:58:22 UTC",
            vm_total=3,
            vm_success=3,
            successful_vms=[
                "VM-01 | Admin",
                "VM-06 | XO-02",
                "VM-02 | XO-01",
            ],
        )
        item.vm_details = {
            "VM-01 | Admin": {"size": "45.01 GiB", "speed": "33.73 MiB/s"},
            "VM-06 | XO-02": {"size": "3.42 GiB", "speed": "28.11 MiB/s"},
            "VM-02 | XO-01": {"size": "3.62 GiB", "speed": "22.27 MiB/s"},
        }
        return item

    if kind == "failure":
        item = Notification(
            source="xo",
            subject="Backup report for [CRITICAL - 02] Operation Critical",
            category="backup",
            status="failure",
            job_name="[CRITICAL - 02] Operation Critical",
            mode="full",
            duration="44 minutes",
            transfer_size="49.22 GiB",
            repository="UNAS-01 | NFS | Critical Backups",
            transfer_speed="27.95 MiB/s",
            start_time="2026-09-21 16:14:23 UTC",
            end_time="2026-09-21 16:58:23 UTC",
            vm_total=3,
            vm_success=2,
            vm_failed=1,
            successful_vms=["VM-04 | Docker", "VM-08 | Zabbix"],
            failed_vms=["VM-14 | Windows Server"],
        )
        item.vm_details = {
            "VM-04 | Docker": {"size": "18.33 GiB", "speed": "27.95 MiB/s"},
            "VM-08 | Zabbix": {"size": "7.23 GiB", "speed": "26.99 MiB/s"},
            "VM-14 | Windows Server": {
                "size": "23.66 GiB",
                "speed": "34.25 MiB/s",
                "error": "Body Timeout Error",
            },
        }
        return item

    item = Notification(
        source="xo",
        subject="Backup report for [WEEKLY - 03] Archive Rotation",
        category="backup",
        status="skipped",
        job_name="[WEEKLY - 03] Archive Rotation",
        mode="full",
        duration="21 minutes",
        transfer_size="31.80 GiB",
        repository="UNAS-01 | NFS | Weekly Archives",
        transfer_speed="24.70 MiB/s",
        start_time="2026-09-21 16:37:24 UTC",
        end_time="2026-09-21 16:58:24 UTC",
        vm_total=3,
        vm_success=2,
        vm_skipped=1,
        successful_vms=["VM-03 | Home Assistant", "VM-09 | Management"],
        skipped_vms=["VM-12 | Maintenance Window"],
    )
    item.vm_details = {
        "VM-03 | Home Assistant": {"size": "12.40 GiB", "speed": "24.70 MiB/s"},
        "VM-09 | Management": {"size": "13.90 GiB", "speed": "26.10 MiB/s"},
        "VM-12 | Maintenance Window": {
            "size": "5.50 GiB",
            "error": (
                "Backup policy excluded this VM during its maintenance window"
            ),
        },
    }
    return item


def test_xo_modern_card_matches_approved_success_template():
    payload = DiscordOutput().source_formatters["xo"].format_components_v2(
        _approved_xo_notification("success")
    )
    rendered = text_content(payload)

    assert payload["components"][0]["accent_color"] == 0x57F287
    assert "### 🗄️ Xen Orchestra" in rendered
    assert (
        "### ✅ [NON-CRITICAL - 01] Administration • Backup Successful"
        in rendered
    )
    assert "UNAS-01 | NFS | Non-Critical Backups" in rendered
    assert "Backup report for [NON-CRITICAL - 01] Administration" in rendered
    assert "✅ **Severity:** Success" in rendered
    assert "🔄 **Category:** Backup" in rendered
    assert "🕒 **Event time:** 2026-09-21 16:58:22 UTC" in rendered
    assert "🧰 **Mode:** full" in rendered
    assert "⏱️ **Duration:** 28 min" in rendered
    assert "📦 **Transfer size:** 52.06 GiB" in rendered
    assert "🚀 **Speed:** 33.73 MiB/s" in rendered
    assert "📊 **Result:** ✅ 3 of 3 VMs successful" in rendered
    assert "▶️ **Started:** 2026-09-21 16:30:22 UTC" in rendered
    assert "🏁 **Finished:** 2026-09-21 16:58:22 UTC" in rendered
    assert "✅ **Successful VMs (3)**" in rendered
    for value in (
        "VM-01 | Admin",
        "45.01 GiB",
        "VM-06 | XO-02",
        "3.42 GiB",
        "VM-02 | XO-01",
        "3.62 GiB",
    ):
        assert value in rendered
    assert "Failed VM" not in rendered
    assert "Skipped VM" not in rendered
    assert f"Theriark - Nowlert v{VERSION}" in rendered
    assert "Xen Orchestra Notification" in rendered


def test_xo_modern_card_matches_approved_failure_template():
    payload = DiscordOutput().source_formatters["xo"].format_components_v2(
        _approved_xo_notification("failure")
    )
    rendered = text_content(payload)

    assert payload["components"][0]["accent_color"] == 0xED4245
    assert (
        "### 🚨 [CRITICAL - 02] Operation Critical • Backup Failure"
        in rendered
    )
    assert "🚨 **Severity:** Failure" in rendered
    assert "📊 **Result:** ✅ 2 of 3 VMs successful • ❌ 1 failed" in rendered
    assert "✅ **Successful VMs (2)**" in rendered
    assert "❌ **Failed VM (1)**" in rendered
    for value in (
        "VM-04 | Docker",
        "18.33 GiB",
        "VM-08 | Zabbix",
        "7.23 GiB",
        "VM-14 | Windows Server",
        "23.66 GiB",
        "34.25 MiB/s",
        "Body Timeout Error",
    ):
        assert value in rendered
    assert "Skipped VM" not in rendered


def test_xo_modern_card_matches_approved_skipped_template():
    payload = DiscordOutput().source_formatters["xo"].format_components_v2(
        _approved_xo_notification("skipped")
    )
    rendered = text_content(payload)

    assert payload["components"][0]["accent_color"] == 0x3498DB
    assert (
        "### ℹ️ [WEEKLY - 03] Archive Rotation • Backup Skipped"
        in rendered
    )
    assert "ℹ️ **Severity:** Skipped" in rendered
    assert (
        "📊 **Result:** ✅ 2 of 3 VMs successful • ⚠️ 1 skipped"
        in rendered
    )
    assert "✅ **Successful VMs (2)**" in rendered
    assert "⚠️ **Skipped VM (1)**" in rendered
    for value in (
        "VM-03 | Home Assistant",
        "12.40 GiB",
        "VM-09 | Management",
        "13.90 GiB",
        "VM-12 | Maintenance Window",
        "5.50 GiB",
        "Backup policy excluded this VM during its maintenance window",
    ):
        assert value in rendered
    assert "Failed VM" not in rendered


def test_dell_components_v2_delivery_enables_webhook_components(monkeypatch):
    captured = {}

    class Config:
        def get(self, *keys, default=None):
            if keys[-1:] == ("webhook",):
                return (
                    "https://discord.com/api/webhooks/123/token"
                    "?wait=true"
                )
            return default

    class Response:
        status_code = 204
        text = ""

    def fake_post(url, **kwargs):
        payload = kwargs.get("json")
        if payload is None:
            payload = json.loads(
                kwargs["data"]["payload_json"]
            )

        captured["url"] = url
        captured["payload"] = payload
        captured["timeout"] = kwargs["timeout"]
        return Response()

    monkeypatch.setattr(discord_output_module, "config", Config())
    monkeypatch.setattr(discord_output_module.requests, "post", fake_post)

    assert DiscordOutput().send(dell_notification(), target="alfa")

    query = parse_qs(urlsplit(captured["url"]).query)
    assert query == {"wait": ["true"], "with_components": ["true"]}
    assert captured["payload"]["flags"] == 32768
    assert "components" in captured["payload"]
    assert "embeds" not in captured["payload"]
    attachments = captured["payload"].get("attachments")
    if attachments is not None:
        assert attachments == [
            {"id": 0, "filename": "dell-idrac.png"}
        ]
    assert captured["timeout"] == 15


def test_inherited_components_v2_contract_is_used_for_delivery(monkeypatch):
    captured = {}

    class Config:
        def get(self, *keys, default=None):
            if keys[-1:] == ("webhook",):
                return "https://discord.com/api/webhooks/123/token"
            return default

    class Response:
        status_code = 204
        text = ""

    def fake_post(url, **kwargs):
        payload = kwargs.get("json")
        if payload is None:
            payload = json.loads(
                kwargs["data"]["payload_json"]
            )

        captured["url"] = url
        captured["payload"] = payload
        captured["timeout"] = kwargs["timeout"]
        return Response()

    monkeypatch.setattr(discord_output_module, "config", Config())
    monkeypatch.setattr(discord_output_module.requests, "post", fake_post)

    item = integration_notification("qnap")
    assert DiscordOutput().send(item, target="qnap")

    query = parse_qs(urlsplit(captured["url"]).query)
    assert query == {"with_components": ["true"]}
    assert captured["payload"]["flags"] == 32768
    assert "components" in captured["payload"]
    assert "embeds" not in captured["payload"]
    attachments = captured["payload"].get("attachments")
    if attachments is not None:
        assert attachments == [
            {"id": 0, "filename": "qnap.png"}
        ]
    assert captured["timeout"] == 15


def test_components_v2_context_does_not_change_direct_legacy_formatting():
    formatter = DiscordOutput().source_formatters["qnap"]
    item = integration_notification("qnap")

    responsive = formatter.format_components_v2(item)
    legacy = formatter.format(item)

    assert responsive["flags"] == 32768
    assert "components" in responsive
    assert set(legacy) == {"embeds"}


def test_legacy_discord_payload_does_not_change_webhook_url():
    webhook = "https://discord.com/api/webhooks/123/token?wait=true"

    assert DiscordOutput._delivery_webhook(
        webhook,
        {"embeds": [{"title": "Legacy"}]},
    ) == webhook
