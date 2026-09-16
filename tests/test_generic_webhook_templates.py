"""Generic webhook backend-owned presentation and transport contract."""

import socket

import pytest

from models import Notification
from outputs.platform import WebhookPlatformAdapter
from outputs.settings import normalize_output_settings
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
