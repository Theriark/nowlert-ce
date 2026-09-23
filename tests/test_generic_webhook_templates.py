"""Generic webhook backend-owned presentation and transport contract."""

import socket
from pathlib import Path

import pytest

from models import Notification
from outputs.platform import DiscordPlatformAdapter, WebhookPlatformAdapter
from outputs.settings import normalize_output_settings
from storage.delivery import DeliveryResult
from storage.destinations import Destination


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_ADDRESS = "93.184.216.34"

DISCORD_MODERN_SOURCES = (
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
    "supermicro",
    "hpe_ilo",
    "dell_idrac",
    "home_assistant",
    "redfish",
    "nowlert",
    "unknown_product",
)


def public_resolver(host, port, **_kwargs):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (PUBLIC_ADDRESS, port))]


class Response:
    status_code = 204


class HTTPClient:
    def __init__(self):
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append(("POST", url, kwargs))
        return Response()


class RecordingDiscordAdapter:
    def __init__(self):
        self.calls = []

    def deliver(self, destination, secret_value, notification):
        self.calls.append((destination, secret_value, notification))
        return DeliveryResult(True, response_status=204)


def destination(settings=None):
    return Destination(
        id="webhook-destination",
        owner_user_id="owner",
        name="Generic webhook",
        output_type="webhook",
        settings=settings or {},
        shared=False,
        enabled=True,
        secret_configured=True,
        created_at=1,
        updated_at=1,
    )


def notification(source="xo"):
    return Notification(
        source=source,
        category="backup",
        status="success",
        title="Backup completed",
        body="The scheduled backup completed successfully.",
        metadata={"event_id": "xo-42", "severity": "information"},
    )


def test_webhook_editor_exposes_message_style_instead_of_legacy_http_controls():
    script = (ROOT / "src" / "webui" / "app.js").read_text(encoding="utf-8")
    start = script.index("    webhook: {")
    end = script.index("    mqtt: {", start)
    block = script[start:end]

    assert 'key: "message_style"' in block
    assert '["modern", "Modern Card"]' in block
    assert '["classic", "Classic Card"]' in block
    for legacy_key in (
        "method",
        "timeout_seconds",
        "headers",
        "body_template",
        "sign_hmac",
        "allow_private_network",
    ):
        assert f'key: "{legacy_key}"' not in block


def test_webhook_settings_expose_only_message_style_for_new_destinations():
    assert normalize_output_settings("webhook", {}) == {"message_style": "modern"}
    assert normalize_output_settings("webhook", {"message_style": "classic"}) == {
        "message_style": "classic"
    }
    with pytest.raises(ValueError, match="message_style"):
        normalize_output_settings("webhook", {"message_style": "unsupported"})


def test_webhook_preview_builds_backend_owned_modern_and_classic_presentations():
    adapter = WebhookPlatformAdapter(resolver=public_resolver)
    modern = adapter.preview(destination({"message_style": "modern"}), notification())
    classic = adapter.preview(destination({"message_style": "classic"}), notification())

    assert modern.payload["schema"] == "nowlert.event.v1"
    assert modern.payload["presentation"]["style"] == "modern_card"
    assert modern.payload["presentation"]["title"] == "Backup completed"
    assert classic.payload["schema"] == "nowlert.event.v1"
    assert classic.payload["presentation"]["style"] == "classic_card_v1"
    assert classic.payload["presentation"]["description"]
    assert "fields" in classic.payload["presentation"]
    assert "embeds" not in classic.payload


def test_webhook_preview_ignores_legacy_body_template_immediately():
    adapter = WebhookPlatformAdapter(resolver=public_resolver)
    preview = adapter.preview(
        destination(
            {
                "message_style": "modern",
                "body_template": {"content": "legacy custom payload"},
                "method": "PATCH",
                "headers": {"X-Legacy": "true"},
                "timeout_seconds": 29,
                "sign_hmac": True,
            }
        ),
        notification(),
    )

    assert preview.payload["schema"] == "nowlert.event.v1"
    assert preview.payload["presentation"]["style"] == "modern_card"
    assert "content" not in preview.payload
    assert preview.metadata["method"] == "POST"
    assert preview.metadata["signed"] is False


def test_webhook_discord_target_uses_native_discord_message_style():
    adapter = WebhookPlatformAdapter(resolver=public_resolver)
    recorder = RecordingDiscordAdapter()
    adapter.discord = recorder

    modern = adapter.deliver(
        destination({"message_style": "modern"}),
        b"https://discord.com/api/webhooks/123/token",
        notification(),
    )
    classic = adapter.deliver(
        destination({"message_style": "classic"}),
        b"https://discord.com/api/webhooks/123/token",
        notification(),
    )

    assert modern.success is True
    assert classic.success is True
    modern_destination = recorder.calls[0][0]
    classic_destination = recorder.calls[1][0]
    assert modern_destination.output_type == "discord"
    assert modern_destination.settings == {"components_v2": True}
    assert classic_destination.output_type == "discord"
    assert classic_destination.settings == {"components_v2": False}


@pytest.mark.parametrize("source", DISCORD_MODERN_SOURCES)
def test_webhook_discord_modern_preserves_every_source_for_native_delivery(
    monkeypatch,
    source,
):
    adapter = WebhookPlatformAdapter(resolver=public_resolver)
    native_discord = adapter.discord
    calls = []

    assert isinstance(native_discord, DiscordPlatformAdapter)

    def record_delivery(routed_destination, secret_value, routed_notification):
        calls.append((routed_destination, secret_value, routed_notification))
        return DeliveryResult(True, response_status=204)

    monkeypatch.setattr(native_discord, "deliver", record_delivery)
    item = notification(source)

    result = adapter.deliver(
        destination({"message_style": "modern"}),
        b"https://discord.com/api/webhooks/123/token",
        item,
    )

    assert result.success is True
    assert len(calls) == 1
    routed_destination, _secret, routed_notification = calls[0]
    assert routed_destination.output_type == "discord"
    assert routed_destination.settings == {"components_v2": True}
    assert routed_notification is item
    assert routed_notification.source == source


def test_webhook_new_contract_is_fixed_post_json_with_idempotency_header():
    client = HTTPClient()
    adapter = WebhookPlatformAdapter(http_client=client, resolver=public_resolver)

    result = adapter.deliver(
        destination({"message_style": "modern"}),
        b"https://events.example.com/nowlert",
        notification(),
    )

    assert result.success is True
    method, url, kwargs = client.calls[0]
    assert method == "POST"
    assert url == "https://events.example.com/nowlert"
    assert kwargs["timeout"] == 15
    assert kwargs["headers"]["Content-Type"] == "application/json"
    assert kwargs["headers"]["X-Nowlert-Idempotency-Key"] == "xo-42"
    assert kwargs["json"]["presentation"]["style"] == "modern_card"
