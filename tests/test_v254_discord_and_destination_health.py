"""v2.5.4 Discord attachment and destination-health regressions."""

from __future__ import annotations

import json
import socket
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

from models import Notification
from outputs.platform import DiscordPlatformAdapter
from storage.database import Database
from storage.delivery import DeliveryResult
from storage.destinations import Destination, DestinationStore
from storage.migrations import LATEST_SCHEMA_VERSION
from storage.ownership import Actor


ROOT = Path(__file__).resolve().parents[1]


class DiscordResponse:
    status_code = 200
    text = ""

    def __init__(
        self,
        filename: str,
        *,
        linked: bool = True,
        media_shape: str = "attachment",
        include_top_level_attachment: bool = True,
    ):
        self.filename = filename
        self.linked = linked
        self.media_shape = media_shape
        self.include_top_level_attachment = include_top_level_attachment

    def json(self):
        if not self.linked:
            return {"attachments": [], "components": []}
        url = f"https://cdn.discordapp.com/attachments/1/2/{self.filename}"
        proxy_url = (
            "https://media.discordapp.net/attachments/"
            f"1/2/{self.filename}?width=128&height=128"
        )
        media = {
            "url": f"attachment://{self.filename}",
            "proxy_url": proxy_url,
            "content_type": "image/png",
            "height": 128,
            "width": 128,
        }
        if self.media_shape == "attachment_id":
            media["url"] = proxy_url
            media["attachment_id"] = "2"
        elif self.media_shape == "cdn":
            media["url"] = proxy_url
        attachments = (
            [
                {
                    "id": "2",
                    "filename": self.filename,
                    "content_type": "image/png",
                    "url": url,
                    "proxy_url": proxy_url,
                    "size": 4096,
                    "height": 128,
                    "width": 128,
                }
            ]
            if self.include_top_level_attachment
            else []
        )
        return {
            "attachments": attachments,
            "components": [
                {
                    "type": 17,
                    "components": [
                        {
                            "type": 9,
                            "components": [
                                {"type": 10, "content": "test"}
                            ],
                            "accessory": {
                                "type": 11,
                                "media": media,
                            },
                        }
                    ],
                }
            ],
        }


class DiscordClient:
    def __init__(
        self,
        *,
        linked: bool = True,
        media_shape: str = "attachment",
    ):
        self.linked = linked
        self.media_shape = media_shape
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        filename = kwargs["files"]["files[0]"][0]
        return DiscordResponse(
            filename,
            linked=self.linked,
            media_shape=self.media_shape,
        )


def public_resolver(*_args, **_kwargs):
    return [
        (
            socket.AF_INET,
            socket.SOCK_STREAM,
            socket.IPPROTO_TCP,
            "",
            ("8.8.8.8", 443),
        )
    ]


def discord_destination() -> Destination:
    return Destination(
        id="d" * 32,
        owner_user_id="u" * 32,
        name="XO",
        output_type="discord",
        settings={"components_v2": True},
        shared=True,
        enabled=True,
        secret_configured=True,
        created_at=1,
        updated_at=1,
    )


def xo_notification() -> Notification:
    return Notification(
        source="xo",
        category="virtualization",
        status="information",
        title="Backup successful",
        body="Safe v2.5.4 Discord attachment test",
        metadata={"severity": "information", "host": "VM-09"},
    )


def test_schema_9_adds_destination_test_health_columns(tmp_path):
    database = Database(tmp_path / "state.db")

    assert database.migrate() == 9
    assert LATEST_SCHEMA_VERSION == 9

    with database.connect() as connection:
        columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(destinations)"
            )
        }

    assert {
        "last_test_at",
        "last_test_outcome",
        "last_test_response_status",
        "last_test_error_code",
        "last_test_safe_error",
    } <= columns


def test_destination_test_result_persists_and_reloads(tmp_path):
    database = Database(tmp_path / "state.db")
    database.migrate()
    actor = Actor("a" * 32, "admin")

    with database.transaction() as connection:
        connection.execute(
            """
            INSERT INTO users(
                id, username, username_normalized, password_hash,
                role, enabled, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 1, 1, 1)
            """,
            (actor.user_id, "admin", "admin", "hash", "admin"),
        )

    store = DestinationStore(database, clock=lambda: 1234)
    destination = store.create(
        actor,
        actor.user_id,
        "Discord",
        "discord",
        settings={},
        enabled=True,
    )

    failed = DeliveryResult(
        False,
        response_status=401,
        error_code="upstream_rejected",
        safe_error="destination returned HTTP 401",
    )
    updated = store.record_test_result(actor, destination.id, failed)

    assert updated.last_test_at == 1234
    assert updated.last_test_outcome == "failed"
    assert updated.last_test_response_status == 401
    assert updated.last_test_error_code == "upstream_rejected"
    assert updated.last_test_safe_error == "destination returned HTTP 401"

    passed = store.record_test_result(
        actor,
        destination.id,
        DeliveryResult(True, response_status=200),
    )
    assert passed.last_test_outcome == "success"
    assert passed.last_test_response_status == 200
    assert passed.last_test_error_code == ""
    assert passed.last_test_safe_error == ""


def test_platform_discord_uploads_exact_padded_icon_and_waits():
    client = DiscordClient()
    adapter = DiscordPlatformAdapter(
        http_client=client,
        resolver=public_resolver,
    )
    adapter.output.ICON_DIR = ROOT / "assets" / "icons"

    result = adapter.deliver(
        discord_destination(),
        b"https://discord.com/api/webhooks/1/token",
        xo_notification(),
    )

    assert result.success is True
    assert len(client.calls) == 1
    url, kwargs = client.calls[0]
    query = parse_qs(urlsplit(url).query)
    assert query["with_components"] == ["true"]
    assert query["wait"] == ["true"]

    filename, stream, content_type = kwargs["files"]["files[0]"]
    assert filename == "xen-orchestra.png"
    assert content_type == "image/png"
    assert stream.name.endswith("assets/icons/discord/xen-orchestra.png")

    payload = json.loads(kwargs["data"]["payload_json"])
    assert payload["attachments"] == [
        {"id": 0, "filename": "xen-orchestra.png"}
    ]
    media = adapter.output._thumbnail_media(payload)
    assert media["url"] == "attachment://xen-orchestra.png"


def test_platform_discord_rejects_unverified_attachment():
    client = DiscordClient(linked=False)
    adapter = DiscordPlatformAdapter(
        http_client=client,
        resolver=public_resolver,
    )
    adapter.output.ICON_DIR = ROOT / "assets" / "icons"

    result = adapter.deliver(
        discord_destination(),
        b"https://discord.com/api/webhooks/1/token",
        xo_notification(),
    )

    assert result.success is False
    assert result.response_status == 200
    assert result.error_code == "discord_attachment_unverified"
    assert "did not retain" in result.safe_error


def test_platform_discord_accepts_returned_attachment_reference():
    """Discord may retain attachment:// while adding CDN media metadata."""

    client = DiscordClient(media_shape="attachment")
    adapter = DiscordPlatformAdapter(
        http_client=client,
        resolver=public_resolver,
    )
    adapter.output.ICON_DIR = ROOT / "assets" / "icons"

    result = adapter.deliver(
        discord_destination(),
        b"https://discord.com/api/webhooks/1/token",
        xo_notification(),
    )

    assert result.success is True
    response = DiscordResponse(
        "xen-orchestra.png",
        media_shape="attachment",
    )
    verified, diagnostics = adapter.output._attachment_inspection(
        response,
        "xen-orchestra.png",
    )
    assert verified is True
    assert diagnostics == {
        "response_status": 200,
        "attachments": [
            {
                "id": "2",
                "filename": "xen-orchestra.png",
                "content_type": "image/png",
                "url_present": True,
                "proxy_url_present": True,
            }
        ],
        "component_types": [17, 9, 10, 11],
        "thumbnail_media_keys": [
            "content_type",
            "height",
            "proxy_url",
            "url",
            "width",
        ],
        "media_attachment_id": "",
        "media_url_kind": "attachment",
        "media_proxy_url_kind": "discord_cdn",
    }


def test_platform_discord_accepts_discord_cdn_rewrite():
    client = DiscordClient(media_shape="cdn")
    adapter = DiscordPlatformAdapter(
        http_client=client,
        resolver=public_resolver,
    )
    adapter.output.ICON_DIR = ROOT / "assets" / "icons"

    result = adapter.deliver(
        discord_destination(),
        b"https://discord.com/api/webhooks/1/token",
        xo_notification(),
    )

    assert result.success is True


def test_platform_discord_accepts_components_v2_media_without_attachment_list():
    """Discord can retain an upload only in the unfurled media object."""

    response = DiscordResponse(
        "xen-orchestra.png",
        media_shape="attachment_id",
        include_top_level_attachment=False,
    )

    verified, diagnostics = DiscordPlatformAdapter().output._attachment_inspection(
        response,
        "xen-orchestra.png",
    )

    assert verified is True
    assert diagnostics["attachments"] == []
    assert diagnostics["media_attachment_id"] == "2"
    assert diagnostics["media_url_kind"] == "discord_cdn"
    assert diagnostics["media_proxy_url_kind"] == "discord_cdn"


def test_platform_discord_rejects_components_v2_media_with_wrong_filename():
    response = DiscordResponse(
        "other.png",
        media_shape="attachment_id",
        include_top_level_attachment=False,
    )

    assert DiscordPlatformAdapter().output._attachment_verified(
        response,
        "xen-orchestra.png",
    ) is False


def test_platform_discord_rejects_components_v2_media_with_wrong_attachment_id():
    response = DiscordResponse(
        "xen-orchestra.png",
        media_shape="attachment_id",
        include_top_level_attachment=False,
    )
    message = response.json()
    media = message["components"][0]["components"][0]["accessory"]["media"]
    media["attachment_id"] = "999"
    response.json = lambda: message

    assert DiscordPlatformAdapter().output._attachment_verified(
        response,
        "xen-orchestra.png",
    ) is False


def test_platform_discord_rejects_components_v2_non_png_media():
    response = DiscordResponse(
        "xen-orchestra.png",
        media_shape="attachment_id",
        include_top_level_attachment=False,
    )
    message = response.json()
    media = message["components"][0]["components"][0]["accessory"]["media"]
    media["content_type"] = "text/plain"
    response.json = lambda: message

    assert DiscordPlatformAdapter().output._attachment_verified(
        response,
        "xen-orchestra.png",
    ) is False


def test_platform_discord_rejects_unrelated_media_attachment():
    response = DiscordResponse(
        "xen-orchestra.png",
        media_shape="cdn",
    )
    message = response.json()
    message["components"][0]["components"][0]["accessory"]["media"] = {
        "url": (
            "https://cdn.discordapp.com/attachments/"
            "1/999/other.png"
        ),
        "content_type": "image/png",
    }
    response.json = lambda: message

    assert DiscordPlatformAdapter().output._attachment_verified(
        response,
        "xen-orchestra.png",
    ) is False


def test_platform_discord_rejects_attachment_without_discord_cdn_url():
    response = DiscordResponse(
        "xen-orchestra.png",
        media_shape="attachment_id",
    )
    message = response.json()
    message["attachments"][0]["url"] = (
        "https://example.invalid/xen-orchestra.png"
    )
    message["attachments"][0]["proxy_url"] = ""
    response.json = lambda: message

    assert DiscordPlatformAdapter().output._attachment_verified(
        response,
        "xen-orchestra.png",
    ) is False


def test_webui_uses_persisted_destination_health_for_routing_flow():
    app = (ROOT / "src/webui/app.js").read_text(encoding="utf-8")

    assert "function destinationTestResult(destination)" in app
    assert "destination.last_test_outcome === \"success\"" in app
    assert "Last destination test failed" in app
    assert "renderFlow();" in app
    assert "last_test_safe_error" in app
    assert "destination-test-detail" in app
