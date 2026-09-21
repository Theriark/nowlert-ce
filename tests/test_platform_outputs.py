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


def test_teams_message_style_rejects_unknown_values():
    with pytest.raises(ValueError, match="teams message_style"):
        normalize_output_settings(
            "teams",
            {"message_style": "legacy"},
        )


def test_teams_default_and_explicit_modern_xo_use_existing_formatter():
    item = notification_for_source("xo")
    adapter = TeamsPlatformAdapter(resolver=public_resolver)

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
    assert default_preview.metadata["formatter"] == "TeamsFormatter"
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
    assert preview.metadata["formatter"] == "TeamsClassicFormatter"
    assert "🦉 Nowlert CE • Classic Card" in json.dumps(
        preview.payload,
        ensure_ascii=False,
    )
    assert (
        preview.metadata["payload_bytes"]
        <= preview.metadata["payload_limit_bytes"]
    )


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


def test_send_test_teams_modern_and_classic_use_nowlert_identity():
    item = destination_test_notification("teams")
    adapter = TeamsPlatformAdapter(resolver=public_resolver)

    modern = adapter.preview(
        destination("teams", {"message_style": "modern"}),
        item,
    )
    classic = adapter.preview(
        destination("teams", {"message_style": "classic"}),
        item,
    )

    assert "/nowlert.png" in json.dumps(modern.payload)
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


def test_discord_and_teams_previews_reuse_source_specific_formatters():
    item = notification()
    discord = DiscordPlatformAdapter(resolver=public_resolver).preview(
        destination("discord", {"components_v2": False}),
        item,
    )
    teams = TeamsPlatformAdapter(resolver=public_resolver).preview(
        destination("teams"),
        item,
    )

    assert discord.metadata["formatter"] == "GrafanaDiscordFormatter"
    assert teams.metadata["formatter"] == "GrafanaTeamsFormatter"
    assert teams.metadata["payload_bytes"] <= teams.metadata["payload_limit_bytes"]
    assert "private-token" not in json.dumps(discord.payload)
    assert "private-token" not in json.dumps(teams.payload)


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


@pytest.mark.parametrize("source", CLASSIC_PARITY_SOURCES)
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