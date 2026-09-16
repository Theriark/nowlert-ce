"""Generic webhook backend-owned presentation and transport contract."""

import socket

import pytest

from models import Notification
from outputs.platform import WebhookPlatformAdapter
from outputs.settings import normalize_output_settings
from storage.delivery import DeliveryResult
from storage.destinations import Destination


PUBLIC_ADDRESS = "93.184.216.34"


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


def notification():
    return Notification(
        source="xo",
        category="backup",
        status="success",
        title="Backup completed",
        body="The scheduled backup completed successfully.",
        metadata={"event_id": "xo-42", "severity": "information"},
    )


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
    assert classic.payload["presentation"]["style"] == "classic_embed"
    assert classic.payload["presentation"]["description"] == (
        "The scheduled backup completed successfully."
    )


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
