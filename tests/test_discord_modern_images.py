"""Discord Modern image-card coverage for all integrations."""

from __future__ import annotations

from io import BytesIO
import json
import socket

import pytest
from PIL import Image

from models import Notification
from outputs.discord import DiscordOutput
from outputs.platform import DiscordPlatformAdapter
from storage.destinations import Destination


PUBLIC_ADDRESS = "93.184.216.34"

SOURCES = (
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
    return [
        (
            socket.AF_INET,
            socket.SOCK_STREAM,
            6,
            "",
            (PUBLIC_ADDRESS, port),
        )
    ]


def destination(modern=True):
    return Destination(
        id="discord-modern",
        owner_user_id="owner",
        name="Discord Modern",
        output_type="discord",
        settings={"components_v2": modern},
        shared=False,
        enabled=True,
        secret_configured=True,
        created_at=1,
        updated_at=1,
    )


def notification(source):
    metadata = {
        "severity": "warning",
        "event_time": "2026-09-21 22:30:00 UTC",
        "host": "LAB-01",
        "hostname": "LAB-01",
        "system": "LAB-01",
        "device": "LAB-01",
        "provider": "Synthetic provider",
        "instance": "LAB-01",
        "node": "NODE-01",
        "nas_name": "NAS-01",
        "controller": "UDM-01",
        "area": "Server room",
        "entity_id": "sensor.lab",
        "rule_name": "Synthetic rule",
        "alert_rule": "Synthetic rule",
        "storage_pool": "pool-01",
        "volume": "volume-01",
        "disk": "disk-01",
        "service": "automation.turn_on",
        "sensor": "Temp 1",
        "message_id": "Synthetic.Message.1",
        "source_ip": "192.0.2.10",
        "recommended_action": "Inspect the affected component.",
    }
    return Notification(
        source=source,
        category="monitoring",
        status="warning",
        title="Synthetic integration event",
        subject="Synthetic integration event",
        body=(
            "Synthetic operational message containing enough context "
            "to exercise the Modern card renderer."
        ),
        start_time="2026-09-21 22:29:00 UTC",
        end_time="2026-09-21 22:30:00 UTC",
        duration="1 min",
        metadata=metadata,
    )


@pytest.mark.parametrize("source", SOURCES)
def test_every_non_xo_modern_source_renders_png_from_classic_content(
    tmp_path,
    source,
):
    output = DiscordOutput()
    output.ICON_DIR = tmp_path
    output.modern_image_renderer.icon_dir = tmp_path
    item = notification(source)
    formatter = output.source_formatters.get(
        source,
        output.default_formatter,
    )

    image = output.render_modern_image(
        item,
        formatter,
    )

    assert image is not None
    assert image.startswith(b"\x89PNG\r\n\x1a\n")
    with Image.open(BytesIO(image)) as rendered:
        assert rendered.width == 1448
        assert rendered.height >= 900
    assert len(image) < 8 * 1024 * 1024


def test_modern_renderer_uses_classic_embed_as_source_of_truth(tmp_path):
    output = DiscordOutput()
    output.ICON_DIR = tmp_path
    output.modern_image_renderer.icon_dir = tmp_path
    item = notification("grafana")
    formatter = output.source_formatters["grafana"]
    classic = formatter.format(item)

    captured = {}

    def render(_notification, classic_payload):
        captured["classic"] = classic_payload
        return b"\x89PNG\r\n\x1a\nsynthetic"

    output.modern_image_renderer.render = render

    image = output.render_modern_image(
        item,
        formatter,
    )

    assert image.startswith(b"\x89PNG")
    assert captured["classic"] == formatter._sanitize_payload(
        classic
    )
    assert "embeds" in captured["classic"]


class Response:
    status_code = 200
    text = ""

    def __init__(self, filename):
        self.filename = filename

    def json(self):
        return {
            "attachments": [
                {
                    "id": "2",
                    "filename": self.filename,
                    "content_type": "image/png",
                    "url": (
                        "https://cdn.discordapp.com/"
                        "attachments/1/2/"
                        + self.filename
                    ),
                    "proxy_url": (
                        "https://media.discordapp.net/"
                        "attachments/1/2/"
                        + self.filename
                    ),
                }
            ]
        }


class Client:
    def __init__(self):
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        filename = kwargs["files"]["files[0]"][0]
        return Response(filename)


def test_non_xo_modern_platform_delivery_is_image_only(monkeypatch):
    client = Client()
    adapter = DiscordPlatformAdapter(
        http_client=client,
        resolver=public_resolver,
    )
    item = notification("qnap")
    image = b"\x89PNG\r\n\x1a\nsynthetic"
    monkeypatch.setattr(
        adapter.output,
        "render_modern_image",
        lambda _notification, _formatter=None: image,
    )

    result = adapter.deliver(
        destination(True),
        b"https://discord.com/api/webhooks/123/token",
        item,
    )

    assert result.success is True
    assert len(client.calls) == 1
    url, kwargs = client.calls[0]
    assert url.endswith("?wait=true")
    assert "json" not in kwargs
    filename, content, content_type = (
        kwargs["files"]["files[0]"]
    )
    assert filename == "nowlert-qnap-modern.png"
    assert content == image
    assert content_type == "image/png"
    payload = json.loads(
        kwargs["data"]["payload_json"]
    )
    assert payload["attachments"][0]["filename"] == filename
    assert payload["allowed_mentions"] == {
        "parse": [],
    }


def test_modern_filename_is_source_specific_and_safe():
    assert (
        DiscordOutput.modern_image_filename(
            "dell_idrac"
        )
        == "nowlert-dell_idrac-modern.png"
    )
    assert (
        DiscordOutput.modern_image_filename(
            "unknown product / webhook"
        )
        == "nowlert-unknown-product---webhook-modern.png"
    )


def test_modern_payload_uses_integration_identity():
    payload = DiscordOutput.modern_image_payload(
        "home_assistant",
        "card.png",
    )
    assert payload["attachments"] == [
        {
            "id": 0,
            "filename": "card.png",
            "description": (
                "Home Assistant notification"
            ),
        }
    ]
