"""Platform output settings, previews, transports, and service boundaries."""

from __future__ import annotations

import json
import socket

import pytest
import requests

from api.security import hash_password
from models import Notification
from outputs.platform import (
    DiscordPlatformAdapter,
    OutputPreview,
    PlatformOutputAdapter,
    PlatformOutputRegistry,
    SlackPlatformAdapter,
    TeamsPlatformAdapter,
    WebhookPlatformAdapter,
)
from outputs.service import PlatformOutputService
from outputs.settings import normalize_output_settings
from storage.audit_events import AuditEventStore
from storage.database import Database
from storage.delivery import DeliveryHistoryStore, DeliveryResult, PlatformDeliveryService
from storage.destinations import Destination, DestinationStore
from storage.routes import RouteStore
from storage.secrets import SecretStore
from storage.users import UserStore


PUBLIC_ADDRESS = "93.184.216.34"


def public_resolver(host, port, **_kwargs):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (PUBLIC_ADDRESS, port))]


def private_resolver(host, port, **_kwargs):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", port))]


class Response:
    def __init__(self, status_code):
        self.status_code = status_code
        self.text = "must never be persisted"


class HTTPClient:
    def __init__(self, statuses=(204,)):
        self.statuses = list(statuses)
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append(("POST", url, kwargs))
        return Response(self.statuses.pop(0))

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return Response(self.statuses.pop(0))


def destination(output_type, settings=None):
    return Destination(
        id=f"{output_type}-destination",
        owner_user_id="owner",
        name=output_type.title(),
        output_type=output_type,
        settings=settings or {},
        shared=False,
        enabled=True,
        secret_configured=True,
        created_at=1,
        updated_at=1,
    )


def notification():
    return Notification(
        source="grafana",
        category="alert",
        status="firing",
        title="Database latency",
        body="token=private-token latency is high",
        start_time="2026-07-21T22:00:00+00:00",
        metadata={
            "event_id": "grafana-42",
            "host": "vm-09",
            "severity": "critical",
            "action_link": "https://monitoring.example.com/alerts/42",
            "api_key": "private-api-key",
        },
    )


CLASSIC_PARITY_SOURCES = (
    "xo",
    "zabbix",
    "grafana",
    "prometheus",
    "portainer",
    "proxmox",
    "qnap",
    "synology",
    "truenas",
    "unifi_network",
    "unifi_protect",
    "unifi_drive",
    "redfish",
    "supermicro",
    "hpe_ilo",
    "dell_idrac",
    "home_assistant",
    "unknown_product",
)


def notification_for_source(source: str) -> Notification:
    item = notification()
    item.source = source
    item.category = {
        "xo": "backup",
        "zabbix": "monitoring",
        "grafana": "monitoring",
        "prometheus": "monitoring",
        "portainer": "containers",
        "proxmox": "storage",
        "qnap": "storage",
        "synology": "storage",
        "truenas": "storage",
        "unifi_network": "network",
        "unifi_protect": "security",
        "unifi_drive": "backup",
        "redfish": "hardware",
        "supermicro": "hardware",
        "hpe_ilo": "hardware",
        "dell_idrac": "hardware",
        "home_assistant": "automation",
        "unknown_product": "event",
    }[source]
    item.status = "warning"
    item.title = f"Synthetic {source} event"
    item.subject = f"Synthetic {source} subject"
    item.body = f"Synthetic {source} operational detail."
    item.job_name = "Synthetic backup job"
    item.job_id = "JOB-WEBHOOK"
    item.run_id = "RUN-WEBHOOK"
    item.mode = "full"
    item.repository = "SYNTHETIC-REPOSITORY"
    item.transfer_size = "52.06 GiB"
    item.transfer_speed = "33.73 MiB/s"
    item.end_time = "2026-07-21T22:05:00+00:00"
    item.duration = "5 min"
    item.vm_total = 3
    item.vm_success = 2
    item.vm_failed = 1
    item.successful_vms = ["VM-OK-1", "VM-OK-2"]
    item.failed_vms = ["VM-FAILED"]
    item.errors = ["Synthetic failure"]
    item.vm_details = {
        "VM-OK-1": {"size": "18 GiB", "speed": "30 MiB/s"},
        "VM-OK-2": {"size": "12 GiB", "speed": "29 MiB/s"},
        "VM-FAILED": {"error": "Synthetic timeout"},
    }
    item.metadata.update(
        {
            "_input_type": "HTTP",
            "provider": {
                "supermicro": "Supermicro BMC",
                "hpe_ilo": "HPE iLO",
                "dell_idrac": "Dell iDRAC",
                "home_assistant": "Home Assistant",
                "unknown_product": "Synthetic Generic Provider",
            }.get(source, source),
            "hostname": "SYNTHETIC-HOST",
            "system": "SYNTHETIC-SYSTEM",
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
            "storage_pool": "SYNTHETIC-POOL",
            "controller": "SYNTHETIC-CONTROLLER",
            "client_display_name": "SYNTHETIC-CLIENT",
            "client_ip": "192.0.2.40",
            "client_mac": "00:11:22:33:44:55",
            "network_name": "SYNTHETIC-LAN",
            "network_vlan": "20",
            "wifi_name": "SYNTHETIC-WIFI",
            "wifi_band": "5 GHz",
            "wifi_channel": "44",
            "wifi_rssi": "-51 dBm",
            "last_device_name": "SYNTHETIC-AP",
            "last_device_model": "Synthetic AP",
            "trigger_key": "motion",
            "trigger_label": "Motion",
            "trigger_device": "SYNTHETIC-CAMERA",
            "alarm_name": "Synthetic alarm",
            "condition_source": "camera",
            "condition_operator": "is",
            "event_link": "https://example.test/event/webhook",
            "backup_task": "Synthetic backup",
            "area": "Synthetic area",
            "service": "synthetic.service",
            "entity_id": "sensor.synthetic",
            "device": "Synthetic Device",
            "component": "synthetic_component",
            "endpoint": "/api/synthetic",
            "error_code": "SYNTHETIC",
            "retry_seconds": "30",
            "tags": ["development", "synthetic"],
            "sensor": "Synthetic sensor",
            "registry": "Synthetic.Registry",
            "message_id": "Synthetic.Message",
            "origin": "/redfish/v1/Systems/1",
            "problem_name": "Synthetic Zabbix problem",
            "operational_data": "Synthetic operational state",
            "problem_id": "4001",
            "fields": {
                "trigger expression": "last(/host/key)>40",
                "event tags": "env:development",
                "runbook": "https://example.test/runbook",
                "original problem id": "4001",
            },
        }
    )
    return item


def prometheus_notification() -> Notification:
    return Notification(
        source="prometheus",
        category="monitoring",
        status="failure",
        title="HighRequestLatency",
        body="95th percentile latency exceeded two seconds.",
        start_time="2026-09-23T02:00:00Z",
        metadata={
            "state": "firing",
            "severity": "critical",
            "instance": "api-01:9090",
            "service": "checkout",
            "job": "api-server",
            "namespace": "production",
            "receiver": "nowlert-critical",
            "labels": {"environment": "production"},
            "external_url": "https://alertmanager.example.test",
            "generator_url": "https://prometheus.example.test/graph",
            "runbook_url": "https://runbook.example.test/prometheus",
        },
    )


def neutral_classic_from_embed(embed: dict) -> dict:
    result = {
        "style": "classic_card_v1",
        "title": embed.get("title", ""),
        "description": embed.get("description", ""),
        "color": embed.get("color"),
        "fields": [
            {
                "title": field.get("name", ""),
                "value": field.get("value", ""),
                "inline": bool(field.get("inline", False)),
            }
            for field in embed.get("fields", [])
        ],
    }
    footer = embed.get("footer")
    if isinstance(footer, dict) and footer.get("text"):
        result["footer"] = footer["text"]
    for key in ("timestamp", "url"):
        if embed.get(key):
            result[key] = embed[key]
    return result


def fast_hash(password: str) -> str:
    return hash_password(password, salt=b"\x05" * 16, iterations=1_000)


@pytest.fixture
def platform(tmp_path):
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    users = UserStore(database, password_hasher=fast_hash)
    admin = users.bootstrap_admin("administrator", "correct horse battery staple")
    owner = users.create("owner-user", "owner secure password")
    another = users.create("another-user", "another secure password")
    audit = AuditEventStore(database)
    secrets = SecretStore(database)
    destinations = DestinationStore(database, audit=audit)
    routes = RouteStore(database, audit=audit)
    history = DeliveryHistoryStore(database)
    return {
        "database": database,
        "admin": admin,
        "owner": owner,
        "another": another,
        "audit": audit,
        "secrets": secrets,
        "destinations": destinations,
        "routes": routes,
        "history": history,
    }


def test_registry_exposes_supported_platform_output_types():
    registry = PlatformOutputRegistry()
    assert set(registry.delivery_adapters()) == {
        "discord",
        "teams",
        "slack",
        "webhook",
    }
    assert PlatformOutputRegistry([]).delivery_adapters() == {}


def test_teams_message_style_defaults_to_modern_and_accepts_classic():
    assert normalize_output_settings("teams", {}) == {
        "message_style": "modern"
    }
    assert normalize_output_settings(
        "teams",
        {"message_style": "modern"},
    ) == {"message_style": "modern"}
    assert normalize_output_settings(
        "teams",
        {"message_style": "classic"},
    ) == {"message_style": "classic"}


def test_slack_message_style_defaults_to_classic_and_accepts_modern():
    assert normalize_output_settings("slack", {}) == {
        "message_style": "classic",
        "include_metadata": True,
    }
    assert normalize_output_settings(
        "slack",
        {
            "message_style": "modern",
            "include_metadata": False,
        },
    ) == {
        "message_style": "modern",
        "include_metadata": False,
    }


def _teams_modern_image_payload():
    return {
        "type": "message",
        "attachments": [
            {
                "contentType": (
                    "application/vnd.microsoft.card.adaptive"
                ),
                "content": {
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "body": [
                        {
                            "type": "Image",
                            "url": (
                                "https://nowlert.example.test/api/health"
                                "?teams_modern_card="
                                + ("a" * 48)
                                + ".png"
                            ),
                        }
                    ],
                },
            }
        ],
    }


def _enable_teams_modern_image(monkeypatch, adapter):
    monkeypatch.setattr(
        adapter.output,
        "modern_image_payload",
        lambda _notification: _teams_modern_image_payload(),
    )


def test_teams_message_style_rejects_unknown_values():
    with pytest.raises(ValueError, match="teams message_style"):
        normalize_output_settings(
            "teams",
            {"message_style": "legacy"},
        )


def test_teams_default_and_explicit_modern_xo_use_existing_formatter(
    monkeypatch,
):
    item = notification_for_source("xo")
    adapter = TeamsPlatformAdapter(resolver=public_resolver)
    _enable_teams_modern_image(monkeypatch, adapter)

    default_preview = adapter.preview(
        destination("teams"),
        item,
    )
    explicit_preview = adapter.preview(
        destination("teams", {"message_style": "modern"}),
        item,
    )

    assert default_preview.metadata["message_style"] == "modern"
    assert default_preview.metadata["rendered_style"] == "modern"
    assert default_preview.metadata["modern_image"] is True
    assert default_preview.metadata["formatter"] == (
        "DiscordModernImageRenderer"
    )
    assert "teams_modern_card=" in json.dumps(default_preview.payload)
    assert explicit_preview.payload == default_preview.payload


@pytest.mark.parametrize("source", CLASSIC_PARITY_SOURCES)
def test_teams_classic_uses_classic_renderer_for_every_supported_source(source):
    item = notification_for_source(source)
    preview = TeamsPlatformAdapter(
        resolver=public_resolver
    ).preview(
        destination("teams", {"message_style": "classic"}),
        item,
    )

    assert preview.metadata["message_style"] == "classic"
    assert preview.metadata["rendered_style"] == "classic"
    expected_formatter = (
        "TeamsClassicXenOrchestraFormatter"
        if source == "xo"
        else "TeamsClassicFormatter"
    )
    assert preview.metadata["formatter"] == expected_formatter
    assert "🦉 Nowlert CE • Classic Card" in json.dumps(
        preview.payload,
        ensure_ascii=False,
    )
    assert (
        preview.metadata["payload_bytes"]
        <= preview.metadata["payload_limit_bytes"]
    )


def test_teams_classic_redfish_fallback_uses_nowlert_icon():
    item = notification_for_source("redfish")
    preview = TeamsPlatformAdapter(
        resolver=public_resolver
    ).preview(
        destination("teams", {"message_style": "classic"}),
        item,
    )

    encoded = json.dumps(preview.payload)
    assert "/nowlert.png" in encoded
    assert "/redfish.png" not in encoded


def test_teams_classic_non_xo_uses_approved_plain_text_style():
    preview = TeamsPlatformAdapter(
        resolver=public_resolver
    ).preview(
        destination("teams", {"message_style": "classic"}),
        notification_for_source("grafana"),
    )

    encoded = json.dumps(preview.payload, ensure_ascii=False)
    assert "`" not in encoded
    assert "📣 Alert" in encoded
    assert "📂 Rule" in encoded


def test_teams_classic_xo_is_sanitized_and_bounded():
    item = notification_for_source("xo")
    item.failed_vms = ["VM-FAILED"]
    item.vm_details = {
        "VM-FAILED": {
            "error": "Bearer private-token",
            "size": "22 GiB",
        }
    }
    item.status = "failure"
    item.vm_failed = 1

    preview = TeamsPlatformAdapter(
        resolver=public_resolver
    ).preview(
        destination("teams", {"message_style": "classic"}),
        item,
    )
    encoded = json.dumps(preview.payload)

    assert "private-token" not in encoded
    assert "<redacted>" in encoded
    assert (
        preview.metadata["payload_bytes"]
        <= preview.metadata["payload_limit_bytes"]
    )




def destination_test_notification(output_type: str) -> Notification:
    name = f"CE Development - {output_type.title()}"
    return Notification(
        source="nowlert",
        category="event",
        status="information",
        title=f"{name} test delivery",
        body=(
            "This is a safe Nowlert test for the "
            f"{output_type} destination \"{name}\"."
        ),
        metadata={
            "provider": "Nowlert",
            "severity": "information",
            "host": name,
            "component": "Destination test",
            "format": "event-api-v1",
        },
    )


def test_send_test_discord_modern_and_classic_use_nowlert_identity():
    item = destination_test_notification("discord")
    adapter = DiscordPlatformAdapter(resolver=public_resolver)

    modern = adapter.preview(
        destination("discord", {"components_v2": True}),
        item,
    )
    classic = adapter.preview(
        destination("discord", {"components_v2": False}),
        item,
    )

    assert "nowlert-owl" in json.dumps(modern.payload).casefold()
    assert classic.payload["embeds"][0]["thumbnail"]["url"].endswith(
        "discord/nowlert-owl-v3.1.0.png"
    )
    assert "CE Development - Discord test delivery" in json.dumps(
        classic.payload
    )


def test_prometheus_discord_classic_uses_compact_xo_style_geometry():
    item = prometheus_notification()
    preview = DiscordPlatformAdapter(
        resolver=public_resolver
    ).preview(
        destination("discord", {"components_v2": False}),
        item,
    )

    embed = preview.payload["embeds"][0]
    fields = embed["fields"]

    assert embed["title"] == "🚨 HighRequestLatency — Firing"
    assert embed["description"] == (
        "95th percentile latency exceeded two seconds."
    )
    assert "url" not in embed
    assert embed["thumbnail"] == {
        "url": "nowlert-asset://prometheus.png"
    }
    assert embed["footer"] == {
        "text": "🦉 Nowlert CE • Classic Card"
    }

    assert [field["name"] for field in fields[:3]] == [
        "🚨 Severity",
        "🎯 Target",
        "📥 Receiver",
    ]
    assert all(field["inline"] is True for field in fields[:3])
    assert fields[0]["value"] == "`Critical`"
    assert fields[1]["value"] == "`api-01:9090`"
    assert fields[2]["value"] == "`nowlert-critical`"

    names = [field["name"] for field in fields]
    assert names == [
        "🚨 Severity",
        "🎯 Target",
        "📥 Receiver",
        "📈 Prometheus",
        "🏷️ Labels",
        "⏱️ Timing",
        "🔗 Links",
    ]
    prometheus = fields[3]["value"]
    assert "**Service:** `checkout`" in prometheus
    assert "**Job:** `api-server`" in prometheus
    assert "**Namespace:** `production`" in prometheus
    assert "**Started:** `2026-09-23T02:00:00Z`" in fields[5]["value"]


def test_prometheus_discord_classic_grouped_alerts_stay_compact():
    item = prometheus_notification()
    item.metadata["alert_count"] = 2
    item.metadata["group_members"] = [
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

    embed = DiscordPlatformAdapter(
        resolver=public_resolver
    ).preview(
        destination("discord", {"components_v2": False}),
        item,
    ).payload["embeds"][0]
    grouped = next(
        field for field in embed["fields"]
        if field["name"] == "👥 Alerts · 2"
    )

    assert (
        "**ApiErrorRateHigh** · Firing · Critical · api-02:9090"
        in grouped["value"]
    )
    assert (
        "**QueueDepthHigh** · Firing · Warning · worker-02:9090"
        in grouped["value"]
    )


def test_prometheus_discord_classic_resolved_keeps_started_and_resolved():
    item = prometheus_notification()
    item.status = "success"
    item.metadata["state"] = "resolved"
    item.end_time = "2026-09-23T02:05:00Z"

    embed = DiscordPlatformAdapter(
        resolver=public_resolver
    ).preview(
        destination("discord", {"components_v2": False}),
        item,
    ).payload["embeds"][0]

    assert embed["title"] == "✅ HighRequestLatency — Resolved"
    assert embed["color"] == 0x2ECC71
    timing = next(
        field for field in embed["fields"]
        if field["name"] == "⏱️ Timing"
    )
    assert "**Started:** `2026-09-23T02:00:00Z`" in timing["value"]
    assert "**Resolved:** `2026-09-23T02:05:00Z`" in timing["value"]


def test_prometheus_modern_seed_contract_is_unchanged_by_classic_layout():
    item = prometheus_notification()
    formatter = DiscordPlatformAdapter(
        resolver=public_resolver
    ).output.source_formatters["prometheus"]
    embed = formatter.format(item)["embeds"][0]

    assert [field["name"] for field in embed["fields"]] == [
        "🚨 Alert",
        "🎯 Target",
        "📈 Prometheus",
        "🏷️ Labels",
        "⏱️ Timing",
        "🔗 Links",
    ]
    assert embed["thumbnail"]["url"].endswith(
        "/discord/prometheus.png"
    )
    assert embed["url"] == "https://prometheus.example.test/graph"


def test_prometheus_webhook_classic_keeps_existing_neutral_contract():
    preview = WebhookPlatformAdapter(
        resolver=public_resolver
    ).preview(
        destination("webhook", {"message_style": "classic"}),
        prometheus_notification(),
    )
    names = [
        field["title"]
        for field in preview.payload["presentation"]["fields"]
    ]

    assert names == [
        "🚨 Alert",
        "🎯 Target",
        "📈 Prometheus",
        "🏷️ Labels",
        "⏱️ Timing",
        "🔗 Links",
    ]
    assert preview.payload["presentation"]["style"] == "classic_card_v1"


def test_prometheus_teams_modern_reuses_standardized_discord_image(
    monkeypatch,
):
    item = prometheus_notification()
    adapter = TeamsPlatformAdapter(resolver=public_resolver)
    calls = []

    def render(value, formatter=None):
        calls.append((value, formatter))
        return b"synthetic-prometheus-modern-png"

    monkeypatch.setattr(
        adapter.output.discord_modern_output,
        "render_modern_image",
        render,
    )
    monkeypatch.setattr(
        "outputs.teams.publish_teams_modern_image",
        lambda _configuration, _image: _slack_modern_image_payload_url(),
    )

    preview = adapter.preview(
        destination("teams", {"message_style": "modern"}),
        item,
    )

    assert calls == [(item, None)]
    assert preview.metadata["modern_image"] is True
    assert preview.metadata["formatter"] == "DiscordModernImageRenderer"
    encoded = json.dumps(preview.payload)
    assert _slack_modern_image_payload_url() in encoded


def test_send_test_teams_modern_and_classic_use_nowlert_identity(
    monkeypatch,
):
    item = destination_test_notification("teams")
    adapter = TeamsPlatformAdapter(resolver=public_resolver)
    _enable_teams_modern_image(monkeypatch, adapter)

    modern = adapter.preview(
        destination("teams", {"message_style": "modern"}),
        item,
    )
    classic = adapter.preview(
        destination("teams", {"message_style": "classic"}),
        item,
    )

    assert "teams_modern_card=" in json.dumps(modern.payload)
    assert modern.metadata["formatter"] == "DiscordModernImageRenderer"
    assert "/nowlert.png" in json.dumps(classic.payload)
    assert "xen-orchestra.png" not in json.dumps(classic.payload)
    assert "Destination test" in json.dumps(classic.payload)


def test_send_test_slack_uses_nowlert_identity():
    item = destination_test_notification("slack")
    preview = SlackPlatformAdapter(resolver=public_resolver).preview(
        destination("slack"),
        item,
    )

    encoded = json.dumps(preview.payload)
    assert "nowlert" in encoded.casefold()
    assert "CE Development - Slack test delivery" in encoded


def test_send_test_generic_webhook_respects_modern_and_classic():
    item = destination_test_notification("webhook")
    adapter = WebhookPlatformAdapter(resolver=public_resolver)

    modern = adapter.preview(
        destination("webhook", {"message_style": "modern"}),
        item,
    )
    classic = adapter.preview(
        destination("webhook", {"message_style": "classic"}),
        item,
    )

    assert modern.payload["presentation"]["style"] == "modern_card"
    assert classic.payload["presentation"]["style"] == "classic_card_v1"
    assert modern.payload["presentation"]["title"] == item.title
    assert item.title in classic.payload["presentation"]["title"]
    assert item.body in classic.payload["presentation"]["description"]


def test_message_style_override_supports_teams_without_mutating_destination():
    original = destination(
        "teams",
        {"message_style": "modern"},
    )
    styled = PlatformOutputService._with_message_style(
        original,
        "classic",
    )

    assert original.settings == {"message_style": "modern"}
    assert styled.settings == {"message_style": "classic"}


def test_message_style_override_supports_slack_without_mutating_destination():
    original = destination(
        "slack",
        {
            "message_style": "classic",
            "include_metadata": True,
        },
    )
    styled = PlatformOutputService._with_message_style(
        original,
        "modern",
    )

    assert original.settings == {
        "message_style": "classic",
        "include_metadata": True,
    }
    assert styled.settings == {
        "message_style": "modern",
        "include_metadata": True,
    }


def test_discord_and_teams_previews_reuse_source_specific_formatters(
    monkeypatch,
):
    item = notification()
    discord = DiscordPlatformAdapter(resolver=public_resolver).preview(
        destination("discord", {"components_v2": False}),
        item,
    )
    teams_adapter = TeamsPlatformAdapter(resolver=public_resolver)
    _enable_teams_modern_image(monkeypatch, teams_adapter)
    teams = teams_adapter.preview(
        destination("teams"),
        item,
    )

    assert discord.metadata["formatter"] == "GrafanaDiscordFormatter"
    assert teams.metadata["formatter"] == "DiscordModernImageRenderer"
    assert teams.metadata["modern_image"] is True
    assert teams.metadata["payload_bytes"] <= teams.metadata["payload_limit_bytes"]
    assert "private-token" not in json.dumps(discord.payload)
    assert "private-token" not in json.dumps(teams.payload)


def _slack_modern_image_payload_url():
    return (
        "https://nowlert.example.test/api/health?"
        "teams_modern_card="
        + ("a" * 48)
        + ".png"
    )


def _enable_slack_modern_image(monkeypatch, adapter):
    calls = []

    def render(item, formatter=None):
        calls.append((item, formatter))
        return b"synthetic-modern-png"

    monkeypatch.setattr(
        adapter.discord_modern_output,
        "render_modern_image",
        render,
    )
    monkeypatch.setattr(
        "outputs.platform.publish_modern_card_image",
        lambda _configuration, _image: _slack_modern_image_payload_url(),
    )
    return calls


def test_prometheus_slack_modern_reuses_standardized_discord_image(
    monkeypatch,
):
    adapter = SlackPlatformAdapter(resolver=public_resolver)
    item = prometheus_notification()
    calls = _enable_slack_modern_image(monkeypatch, adapter)

    preview = adapter.preview(
        destination("slack", {"message_style": "modern"}),
        item,
    )

    assert calls == [(item, None)]
    assert preview.metadata["modern_image"] is True
    assert preview.metadata["formatter"] == "DiscordModernImageRenderer"
    assert preview.payload["blocks"][0] == {
        "type": "image",
        "image_url": _slack_modern_image_payload_url(),
        "alt_text": "prometheus: HighRequestLatency",
    }


def test_slack_modern_preview_reuses_exact_discord_modern_renderer(
    monkeypatch,
):
    adapter = SlackPlatformAdapter(resolver=public_resolver)
    item = notification_for_source("grafana")
    calls = _enable_slack_modern_image(monkeypatch, adapter)

    preview = adapter.preview(
        destination(
            "slack",
            {
                "message_style": "modern",
                "include_metadata": True,
            },
        ),
        item,
    )

    assert calls == [(item, None)]
    assert preview.metadata["message_style"] == "modern"
    assert preview.metadata["rendered_style"] == "modern"
    assert preview.metadata["modern_image"] is True
    assert preview.metadata["formatter"] == "DiscordModernImageRenderer"
    assert preview.payload["blocks"] == [
        {
            "type": "image",
            "image_url": _slack_modern_image_payload_url(),
            "alt_text": "grafana: Synthetic grafana event",
        }
    ]
    assert preview.payload["text"] == "grafana: Synthetic grafana event"
    assert "attachments" not in preview.payload


@pytest.mark.parametrize("source", CLASSIC_PARITY_SOURCES)
def test_slack_modern_preserves_every_source_for_shared_renderer(
    monkeypatch,
    source,
):
    adapter = SlackPlatformAdapter(resolver=public_resolver)
    item = notification_for_source(source)
    calls = _enable_slack_modern_image(monkeypatch, adapter)

    preview = adapter.preview(
        destination("slack", {"message_style": "modern"}),
        item,
    )

    assert calls == [(item, None)]
    assert preview.metadata["modern_image"] is True
    assert preview.payload["blocks"][0]["type"] == "image"


def test_slack_classic_never_invokes_modern_renderer(monkeypatch):
    adapter = SlackPlatformAdapter(resolver=public_resolver)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("Classic must not render a Modern image")

    monkeypatch.setattr(
        adapter.discord_modern_output,
        "render_modern_image",
        forbidden,
    )

    preview = adapter.preview(
        destination(
            "slack",
            {
                "message_style": "classic",
                "include_metadata": True,
            },
        ),
        notification(),
    )

    assert preview.metadata["message_style"] == "classic"
    assert preview.metadata["modern_image"] is False
    assert "attachments" in preview.payload
    assert "blocks" not in preview.payload


def test_slack_modern_fails_closed_without_public_image(monkeypatch):
    client = HTTPClient((200,))
    adapter = SlackPlatformAdapter(
        http_client=client,
        resolver=public_resolver,
    )
    monkeypatch.setattr(
        adapter.discord_modern_output,
        "render_modern_image",
        lambda *_args, **_kwargs: b"synthetic-modern-png",
    )
    monkeypatch.setattr(
        "outputs.platform.publish_modern_card_image",
        lambda _configuration, _image: None,
    )

    target = destination("slack", {"message_style": "modern"})
    preview = adapter.preview(target, notification())
    result = adapter.deliver(
        target,
        b"https://hooks.slack.com/services/T/B/value",
        notification(),
    )

    assert preview.metadata["error_code"] == (
        "slack_modern_image_unavailable"
    )
    assert result.success is False
    assert result.error_code == "slack_modern_image_unavailable"
    assert client.calls == []


def test_slack_preview_is_classic_sanitized_and_has_safe_action():
    preview = SlackPlatformAdapter(resolver=public_resolver).preview(
        destination("slack"),
        notification(),
    )
    encoded = json.dumps(preview.payload)
    attachment = preview.payload["attachments"][0]

    assert "blocks" not in preview.payload
    assert attachment["color"].startswith("#")
    assert "title" not in attachment
    assert "fields" not in attachment
    assert "thumb_url" not in attachment

    header = attachment["blocks"][0]
    assert (
        "<https://monitoring.example.com/alerts/42|"
        in header["text"]["text"]
    )
    assert header["accessory"]["image_url"].endswith(
        "/discord/grafana.png"
    )
    assert attachment["blocks"][-1] == {
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": "🦉 Nowlert CE • Classic Card",
            }
        ],
    }
    assert "private-token" not in encoded


def test_webhook_preview_uses_stable_secret_safe_envelope_and_ignores_legacy_templates():
    adapter = WebhookPlatformAdapter(resolver=public_resolver)
    default = adapter.preview(destination("webhook"), notification())
    legacy = adapter.preview(
        destination(
            "webhook",
            {
                "body_template": {
                    "summary": "${source}:${title}",
                    "host": "${host}",
                    "id": "${event_id}",
                }
            },
        ),
        notification(),
    )

    assert default.payload["schema"] == "nowlert.event.v1"
    assert default.payload["metadata"]["api_key"] == "<redacted>"
    assert legacy.payload["schema"] == "nowlert.event.v1"
    assert legacy.payload["metadata"]["api_key"] == "<redacted>"
    assert legacy.payload["presentation"]["style"] == "modern_card"
    assert "summary" not in legacy.payload


@pytest.mark.parametrize(
    "source",
    tuple(source for source in CLASSIC_PARITY_SOURCES if source != "prometheus"),
)
def test_webhook_classic_preview_matches_approved_discord_classic_geometry(source):
    item = notification_for_source(source)
    webhook_adapter = WebhookPlatformAdapter(resolver=public_resolver)
    discord_adapter = DiscordPlatformAdapter(resolver=public_resolver)

    webhook_preview = webhook_adapter.preview(
        destination("webhook", {"message_style": "classic"}),
        item,
    )
    discord_preview = discord_adapter.preview(
        destination("discord", {"components_v2": False}),
        item,
    )

    embed = discord_preview.payload["embeds"][0]
    presentation = webhook_preview.payload["presentation"]

    assert webhook_preview.payload["schema"] == "nowlert.event.v1"
    assert presentation == neutral_classic_from_embed(embed), source
    assert "embeds" not in webhook_preview.payload
    assert "attachments" not in webhook_preview.payload


def test_webhook_classic_grafana_contains_source_specific_sections():
    preview = WebhookPlatformAdapter(resolver=public_resolver).preview(
        destination("webhook", {"message_style": "classic"}),
        notification_for_source("grafana"),
    )
    names = [
        field["title"]
        for field in preview.payload["presentation"]["fields"]
    ]

    assert preview.payload["presentation"]["style"] == "classic_card_v1"
    assert "📣 Alert" in names
    assert "📂 Rule" in names
    assert "⏱️ Timing" in names
    assert names != ["severity", "status", "source", "category"]


@pytest.mark.parametrize(
    ("source", "identity"),
    (
        ("supermicro", "🖥️ Supermicro BMC"),
        ("hpe_ilo", "🖥️ HPE iLO"),
        ("dell_idrac", "🖥️ Dell iDRAC"),
    ),
)
def test_webhook_classic_hardware_reuses_discord_hardware_sections(
    source,
    identity,
):
    preview = WebhookPlatformAdapter(resolver=public_resolver).preview(
        destination("webhook", {"message_style": "classic"}),
        notification_for_source(source),
    )
    names = [
        field["title"]
        for field in preview.payload["presentation"]["fields"]
    ]

    assert identity in names
    assert "🔎 Hardware Event" in names


def test_prometheus_webhook_modern_uses_standardized_card_hierarchy():
    preview = WebhookPlatformAdapter(resolver=public_resolver).preview(
        destination("webhook", {"message_style": "modern"}),
        prometheus_notification(),
    )

    presentation = preview.payload["presentation"]
    assert presentation["style"] == "modern_card"
    assert presentation["visual_system"] == "nowlert_standard_v1"
    assert presentation["integration"] == "Prometheus"
    assert presentation["accent"] == "#E74C3C"
    assert presentation["badge"] == {
        "label": "Firing",
        "tone": "failure",
        "icon": "status",
    }
    assert [item["label"] for item in presentation["summary"]] == [
        "Severity",
        "Category",
        "Event time",
    ]
    assert presentation["summary"][0]["value"] == "critical"
    assert presentation["summary"][1]["value"] == "monitoring"
    assert presentation["summary"][2]["value"] == "2026-09-23T02:00:00Z"

    section_titles = [section["title"] for section in presentation["sections"]]
    assert section_titles == [
        "Target",
        "Prometheus",
        "Timing & Links",
        "Event Details",
    ]

    rendered = json.dumps(presentation, ensure_ascii=False)
    for value in (
        "api-01:9090",
        "checkout",
        "api-server",
        "production",
        "nowlert-critical",
        "environment",
        "Alertmanager",
        "Prometheus",
        "Runbook",
        "95th percentile latency exceeded two seconds.",
    ):
        assert value in rendered
    assert presentation["footer"] == "Nowlert CE • Modern Card"


@pytest.mark.parametrize(
    ("state", "status", "severity", "expected_tone", "expected_accent"),
    (
        ("firing", "failure", "critical", "failure", "#E74C3C"),
        ("firing", "warning", "warning", "warning", "#F39C12"),
        ("resolved", "success", "critical", "success", "#2ECC71"),
    ),
)
def test_prometheus_webhook_modern_lifecycle_matches_standard_card(
    state,
    status,
    severity,
    expected_tone,
    expected_accent,
):
    item = prometheus_notification()
    item.metadata["state"] = state
    item.metadata["severity"] = severity
    item.status = status
    if state == "resolved":
        item.end_time = "2026-09-23T02:05:00Z"

    presentation = WebhookPlatformAdapter(
        resolver=public_resolver
    ).preview(
        destination("webhook", {"message_style": "modern"}),
        item,
    ).payload["presentation"]

    assert presentation["badge"]["label"] == state.title()
    assert presentation["badge"]["tone"] == expected_tone
    assert presentation["accent"] == expected_accent
    assert presentation["summary"][2]["value"] == (
        item.end_time if state == "resolved" else item.start_time
    )


def test_webhook_modern_presentation_contract_is_unchanged():
    preview = WebhookPlatformAdapter(resolver=public_resolver).preview(
        destination("webhook", {"message_style": "modern"}),
        notification(),
    )

    assert preview.payload["presentation"] == {
        "style": "modern_card",
        "title": "Database latency",
        "message": "token=<redacted> latency is high",
        "facts": [
            {"label": "Severity", "value": "critical"},
            {"label": "Status", "value": "firing"},
            {"label": "Source", "value": "grafana"},
            {"label": "Category", "value": "alert"},
        ],
    }


def test_classic_card_conversion_rejects_missing_embed():
    with pytest.raises(ValueError, match="Classic preview"):
        WebhookPlatformAdapter._classic_card_from_discord_payload({})


def test_classic_card_conversion_omits_missing_optional_members_and_defaults_inline():
    converted = WebhookPlatformAdapter._classic_card_from_discord_payload(
        {
            "embeds": [
                {
                    "title": "Synthetic",
                    "description": "Synthetic detail",
                    "color": 123,
                    "fields": [{"name": "Field", "value": "Value"}],
                }
            ]
        }
    )

    assert converted == {
        "style": "classic_card_v1",
        "title": "Synthetic",
        "description": "Synthetic detail",
        "color": 123,
        "fields": [
            {"title": "Field", "value": "Value", "inline": False}
        ],
    }


def test_webhook_classic_presentation_remains_secret_safe():
    item = notification()
    item.body = "Bearer private-token must be scrubbed"
    item.metadata["api_key"] = "private-api-key"

    preview = WebhookPlatformAdapter(resolver=public_resolver).preview(
        destination("webhook", {"message_style": "classic"}),
        item,
    )
    encoded = json.dumps(preview.payload, sort_keys=True)

    assert "private-token" not in encoded
    assert "private-api-key" not in encoded
    assert "<redacted>" in encoded


def test_webhook_classic_unknown_source_uses_generic_fallback():
    preview = WebhookPlatformAdapter(resolver=public_resolver).preview(
        destination("webhook", {"message_style": "classic"}),
        notification_for_source("unknown_product"),
    )
    names = [
        field["title"]
        for field in preview.payload["presentation"]["fields"]
    ]

    assert "📍 Source" in names
    assert preview.payload["presentation"]["footer"] == (
        "🦉 Nowlert CE • Classic Card"
    )



def test_http_delivery_maps_retryable_and_terminal_status_without_response_body():
    client = HTTPClient((429, 400))
    adapter = SlackPlatformAdapter(http_client=client, resolver=public_resolver)
    target = destination("slack")
    secret = b"https://hooks.slack.com/services/T/B/value"

    retryable = adapter.deliver(target, secret, notification())
    terminal = adapter.deliver(target, secret, notification())

    assert (retryable.retryable, retryable.error_code, retryable.response_status) == (
        True,
        "rate_limited",
        429,
    )
    assert (terminal.retryable, terminal.error_code, terminal.response_status) == (
        False,
        "upstream_rejected",
        400,
    )
    assert "must never" not in repr(retryable) + repr(terminal)


def test_webhook_delivery_ignores_legacy_transport_secrets_and_keeps_idempotency():
    client = HTTPClient((202,))
    adapter = WebhookPlatformAdapter(http_client=client, resolver=public_resolver)
    target = destination(
        "webhook",
        {
            "method": "PUT",
            "headers": {"X-Site": "lab"},
            "sign_hmac": True,
        },
    )
    secret = json.dumps(
        {
            "url": "https://events.example.com/nowlert",
            "hmac_secret": "private-signing-key",
            "headers": {"Authorization": "Bearer private-access-token"},
        }
    ).encode()
    result = adapter.deliver(target, secret, notification())
    method, _url, kwargs = client.calls[0]

    assert result.success is True
    assert method == "POST"
    assert kwargs["headers"]["Content-Type"] == "application/json"
    assert kwargs["headers"]["X-Nowlert-Idempotency-Key"] == "grafana-42"
    assert "X-Site" not in kwargs["headers"]
    assert "X-Nowlert-Signature" not in kwargs["headers"]
    encoded = json.dumps(kwargs, sort_keys=True)
    assert "private-signing-key" not in encoded
    assert "private-access-token" not in encoded


def test_outbound_http_rejects_private_resolution_by_default():
    adapter = WebhookPlatformAdapter(http_client=HTTPClient(), resolver=private_resolver)
    result = adapter.deliver(
        destination("webhook"),
        b"https://internal.example.com/events",
        notification(),
    )
    assert result == DeliveryResult(False, error_code="invalid_destination")


def test_removed_destination_types_are_rejected():
    for removed in ("mqtt", "ntfy"):
        with pytest.raises(ValueError, match="unsupported destination output type"):
            normalize_output_settings(removed, {})


def test_destination_settings_reject_unknown_unsafe_and_unbounded_values(platform):
    owner = platform["owner"]
    destinations = platform["destinations"]
    with pytest.raises(ValueError, match="unsupported destination setting"):
        destinations.create(
            owner.actor,
            owner.id,
            "Unknown",
            "slack",
            settings={"channel": "secret"},
        )
    with pytest.raises(ValueError, match="must be an object"):
        platform["destinations"].create(
            owner.actor,
            owner.id,
            "Invalid settings",
            "slack",
            settings=["invalid"],
        )


def test_only_administrators_can_enable_private_network_destinations(platform):
    owner = platform["owner"]
    admin = platform["admin"]
    with pytest.raises(PermissionError, match="administrators"):
        platform["destinations"].create(
            owner.actor,
            owner.id,
            "Private webhook",
            "webhook",
            settings={"allow_private_network": True},
        )
    created = platform["destinations"].create(
        admin.actor,
        admin.id,
        "Administrator webhook",
        "webhook",
        settings={"allow_private_network": True},
    )
    assert created.settings["allow_private_network"] is True


class StubAdapter(PlatformOutputAdapter):
    output_type = "webhook"

    def __init__(self):
        self.secrets = []

    def preview(self, destination, notification):
        return OutputPreview("webhook", "application/json", {"title": notification.title}, {})

    def deliver(self, destination, secret_value, notification):
        self.secrets.append(secret_value)
        return DeliveryResult(True, response_status=204)


def test_preview_and_test_delivery_enforce_ownership_and_resolve_shared_secret(platform):
    admin = platform["admin"]
    owner = platform["owner"]
    another = platform["another"]
    secret = platform["secrets"].create(
        admin.actor,
        admin.id,
        "Shared transport",
        "webhook",
        "shared-private-value",
    )
    shared = platform["destinations"].create(
        admin.actor,
        admin.id,
        "Shared webhook",
        "webhook",
        secret_id=secret.id,
        shared=True,
    )
    private = platform["destinations"].create(
        owner.actor,
        owner.id,
        "Private webhook",
        "webhook",
    )
    adapter = StubAdapter()
    service = PlatformOutputService(
        platform["destinations"],
        platform["secrets"],
        PlatformOutputRegistry([adapter]),
        audit=platform["audit"],
    )

    preview = service.preview(another.actor, shared.id, notification())
    result = service.test_delivery(another.actor, shared.id, notification())

    assert preview.payload == {"title": "Database latency"}
    assert result.success is True
    assert adapter.secrets == [b"shared-private-value"]
    with pytest.raises(PermissionError):
        service.preview(another.actor, private.id, notification())
    assert service.test_delivery(
        another.actor,
        private.id,
        notification(),
    ).error_code == "destination_unavailable"
    audit_json = json.dumps(
        [event.details for event in platform["audit"].list_visible(another.actor)]
    )
    assert "shared-private-value" not in audit_json
    assert b"shared-private-value" not in platform["database"].path.read_bytes()


def test_real_webhook_adapter_integrates_with_owned_routes_retries_and_history(platform):
    owner = platform["owner"]
    secret = platform["secrets"].create(
        owner.actor,
        owner.id,
        "Webhook URL",
        "webhook",
        "https://events.example.com/notify",
    )
    target = platform["destinations"].create(
        owner.actor,
        owner.id,
        "Outbound webhook",
        "webhook",
        secret_id=secret.id,
    )
    platform["routes"].create(
        owner.actor,
        owner.id,
        "Grafana webhook",
        "grafana",
        target.id,
    )
    client = HTTPClient((503, 202))
    adapter = WebhookPlatformAdapter(http_client=client, resolver=public_resolver)
    service = PlatformDeliveryService(
        platform["routes"],
        platform["destinations"],
        platform["secrets"],
        platform["history"],
        {"webhook": adapter},
        maximum_attempts=2,
        retry_delays=(0, 0),
    )

    summary = service.deliver(owner.actor, notification())
    attempts = sorted(
        platform["history"].list_visible(owner.actor),
        key=lambda item: item.attempt_number,
    )

    assert summary.delivered == 1
    assert summary.attempts == 2
    assert [item.outcome for item in attempts] == ["retry_scheduled", "delivered"]
    raw = platform["database"].path.read_bytes()
    assert b"events.example.com" not in raw
    assert b"must never be persisted" not in raw


class StyleCaptureAdapter(PlatformOutputAdapter):
    def __init__(self, output_type):
        self.output_type = output_type
        self.preview_settings = []
        self.delivery_settings = []
        self.delivery_notifications = []

    def preview(self, destination, notification):
        self.preview_settings.append(dict(destination.settings))
        return OutputPreview(
            self.output_type,
            "application/json",
            {"title": notification.title},
            {},
        )

    def deliver(self, destination, secret_value, notification):
        self.delivery_settings.append(dict(destination.settings))
        self.delivery_notifications.append(notification)
        return DeliveryResult(True, response_status=204)


@pytest.mark.parametrize(
    ("output_type", "stored_settings", "expected_override"),
    [
        ("discord", {"components_v2": True}, {"components_v2": False}),
        ("webhook", {"message_style": "modern"}, {"message_style": "classic"}),
    ],
)
def test_preview_message_style_override_is_temporary(
    platform,
    output_type,
    stored_settings,
    expected_override,
):
    admin = platform["admin"]
    target = platform["destinations"].create(
        admin.actor,
        admin.id,
        f"{output_type} preview target",
        output_type,
        settings=stored_settings,
    )
    adapter = StyleCaptureAdapter(output_type)
    service = PlatformOutputService(
        platform["destinations"],
        platform["secrets"],
        PlatformOutputRegistry([adapter]),
        audit=platform["audit"],
    )

    service.preview(
        admin.actor,
        target.id,
        notification(),
        message_style="classic",
    )
    result = service.test_delivery(
        admin.actor,
        target.id,
        notification(),
        message_style="classic",
    )

    assert result.success is True
    assert adapter.preview_settings[-1] == expected_override
    assert adapter.delivery_settings[-1] == expected_override
    assert platform["destinations"].get(admin.actor, target.id).settings == stored_settings


@pytest.mark.parametrize(
    ("output_type", "settings", "label"),
    (
        ("discord", {"components_v2": False}, "Discord"),
        ("teams", {"message_style": "classic"}, "Microsoft Teams"),
        ("slack", {}, "Slack"),
        ("webhook", {"message_style": "classic"}, "Generic webhook"),
    ),
)
def test_destination_card_send_test_is_canonicalized_server_side(
    platform,
    output_type,
    settings,
    label,
):
    admin = platform["admin"]
    name = f"CE Development - {label}"
    target = platform["destinations"].create(
        admin.actor,
        admin.id,
        name,
        output_type,
        settings=settings,
    )
    adapter = StyleCaptureAdapter(output_type)
    service = PlatformOutputService(
        platform["destinations"],
        platform["secrets"],
        PlatformOutputRegistry([adapter]),
        audit=platform["audit"],
    )
    stale_route_sample = Notification(
        source="dell_idrac",
        category="hardware",
        status="information",
        title="Dell iDRAC test alert",
        body=(
            "Safe WebUI test: Dell iDRAC hardware monitoring is routed "
            "to this destination."
        ),
        metadata={
            "provider": "Dell iDRAC",
            "host": target.name,
            "component": "Destination test",
            "severity": "information",
            "synthetic": "true",
        },
    )

    result = service.test_delivery(
        admin.actor,
        target.id,
        stale_route_sample,
    )

    assert result.success is True
    delivered = adapter.delivery_notifications[-1]
    assert delivered.source == "nowlert"
    assert delivered.category == "event"
    assert delivered.status == "information"
    assert delivered.title == f"{name} test delivery"
    assert delivered.body == (
        f'This is a safe Nowlert test for the {label} destination "{name}".'
    )
    assert delivered.metadata["provider"] == "Nowlert"
    assert delivered.metadata["component"] == "Destination test"
    assert delivered.metadata["host"] == name
    assert delivered.metadata["output"] == output_type


def test_manual_preview_test_notification_is_not_canonicalized(platform):
    admin = platform["admin"]
    target = platform["destinations"].create(
        admin.actor,
        admin.id,
        "Discord preview",
        "discord",
        settings={"components_v2": False},
    )
    adapter = StyleCaptureAdapter("discord")
    service = PlatformOutputService(
        platform["destinations"],
        platform["secrets"],
        PlatformOutputRegistry([adapter]),
        audit=platform["audit"],
    )
    custom = Notification(
        source="grafana",
        category="monitoring",
        status="warning",
        title="Manual preview",
        body="Operator-selected preview content.",
        metadata={"host": "webui-safe-preview"},
    )

    result = service.test_delivery(
        admin.actor,
        target.id,
        custom,
    )

    assert result.success is True
    delivered = adapter.delivery_notifications[-1]
    assert delivered.source == "grafana"
    assert delivered.title == "Manual preview"


def test_preview_message_style_override_rejects_unknown_style(platform):
    admin = platform["admin"]
    target = platform["destinations"].create(
        admin.actor,
        admin.id,
        "Discord preview target",
        "discord",
        settings={"components_v2": True},
    )
    service = PlatformOutputService(
        platform["destinations"],
        platform["secrets"],
        PlatformOutputRegistry([StyleCaptureAdapter("discord")]),
        audit=platform["audit"],
    )

    with pytest.raises(ValueError, match="destination cannot preview"):
        service.preview(
            admin.actor,
            target.id,
            notification(),
            message_style="unsafe",
        )