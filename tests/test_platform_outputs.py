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


def test_slack_preview_is_bounded_sanitized_and_has_safe_action():
    preview = SlackPlatformAdapter(resolver=public_resolver).preview(
        destination("slack"),
        notification(),
    )
    encoded = json.dumps(preview.payload)

    assert preview.payload["text"] == "Database latency"
    assert len(preview.payload["blocks"]) <= 50
    assert "private-token" not in encoded
    assert "https://monitoring.example.com/alerts/42" in encoded


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
