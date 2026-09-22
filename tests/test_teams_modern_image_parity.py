"""Microsoft Teams Modern image parity with Discord."""

from __future__ import annotations

from io import BytesIO
import json
import socket
from urllib.parse import urlsplit

from PIL import Image

from config import config
from models import Notification
from outputs.platform import TeamsPlatformAdapter
from outputs.teams import TeamsOutput
from outputs.teams_modern_image import (
    TEAMS_MODERN_CARD_MAX_DIMENSION,
    TEAMS_MODERN_CARD_ROUTE_PREFIX,
)
from storage.destinations import Destination
from webui.service import WebUIService


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


def destination(style="modern") -> Destination:
    return Destination(
        id="t" * 32,
        owner_user_id="u" * 32,
        name="Teams",
        output_type="teams",
        settings={"message_style": style},
        shared=True,
        enabled=True,
        secret_configured=True,
        created_at=1,
        updated_at=1,
    )


def notification() -> Notification:
    return Notification(
        source="xo",
        category="backup",
        status="failure",
        title="Operation Critical",
        subject="Backup report for Operation Critical",
        body="Synthetic critical backup.",
        job_name="Operation Critical",
        repository="UNAS-01 | NFS | Critical Backups",
        mode="full",
        duration="44 min",
        transfer_size="49.22 GiB",
        transfer_speed="27.95 MiB/s",
        vm_total=3,
        vm_success=2,
        vm_failed=1,
        successful_vms=["VM-04 | Docker", "VM-08 | Zabbix"],
        failed_vms=["VM-14 | Windows Server"],
        vm_details={
            "VM-04 | Docker": {
                "size": "18.33 GiB",
                "speed": "27.95 MiB/s",
            },
            "VM-08 | Zabbix": {
                "size": "7.23 GiB",
                "speed": "26.99 MiB/s",
            },
            "VM-14 | Windows Server": {
                "size": "23.66 GiB",
                "speed": "34.25 MiB/s",
                "error": "Body Timeout Error",
            },
        },
    )


def synthetic_modern_png() -> bytes:
    image = Image.new("RGB", (1448, 900), (8, 12, 15))
    stream = BytesIO()
    image.save(stream, format="PNG")
    return stream.getvalue()


def configure_public_cards(monkeypatch, tmp_path):
    monkeypatch.setenv("NOWLERT_STATE_DIR", str(tmp_path / "state"))
    webui = dict(config.get("webui", default={}) or {})
    webui["public_url"] = "https://nowlert.example.test"
    monkeypatch.setitem(config._data, "webui", webui)


def image_item(payload: dict) -> dict:
    body = payload["attachments"][0]["content"]["body"]
    assert len(body) == 1
    return body[0]


def test_teams_modern_uses_the_discord_renderer_and_public_image(
    monkeypatch,
    tmp_path,
):
    configure_public_cards(monkeypatch, tmp_path)
    output = TeamsOutput()
    item = notification()
    calls = []

    def render(value, formatter=None):
        calls.append((value, formatter))
        return synthetic_modern_png()

    monkeypatch.setattr(
        output.discord_modern_output,
        "render_modern_image",
        render,
    )

    payload = output.modern_image_payload(item)
    assert payload is not None
    assert calls == [(item, None)]

    image = image_item(payload)
    assert image["type"] == "Image"
    assert image["size"] == "Stretch"
    assert image["url"].startswith(
        "https://nowlert.example.test"
        + TEAMS_MODERN_CARD_ROUTE_PREFIX
    )
    assert "Event details" not in json.dumps(payload)

    route = urlsplit(image["url"]).path
    response = WebUIService(config).response(route)
    assert response is not None
    assert response.status == 200
    assert response.content_type == "image/png"

    with Image.open(BytesIO(response.body)) as published:
        assert max(published.size) == TEAMS_MODERN_CARD_MAX_DIMENSION


def test_platform_modern_preview_is_image_only_when_public_url_exists(
    monkeypatch,
    tmp_path,
):
    configure_public_cards(monkeypatch, tmp_path)
    adapter = TeamsPlatformAdapter(resolver=public_resolver)
    monkeypatch.setattr(
        adapter.output.discord_modern_output,
        "render_modern_image",
        lambda *_args, **_kwargs: synthetic_modern_png(),
    )

    preview = adapter.preview(destination("modern"), notification())
    image = image_item(preview.payload)

    assert preview.metadata["message_style"] == "modern"
    assert preview.metadata["rendered_style"] == "modern"
    assert preview.metadata["modern_image"] is True
    assert preview.metadata["formatter"] == "DiscordModernImageRenderer"
    assert TEAMS_MODERN_CARD_ROUTE_PREFIX in image["url"]
    assert preview.metadata["payload_bytes"] < 28 * 1024


def test_teams_classic_never_invokes_the_modern_image_renderer(
    monkeypatch,
    tmp_path,
):
    configure_public_cards(monkeypatch, tmp_path)
    adapter = TeamsPlatformAdapter(resolver=public_resolver)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("Classic must not render a Modern image")

    monkeypatch.setattr(
        adapter.output.discord_modern_output,
        "render_modern_image",
        forbidden,
    )

    preview = adapter.preview(destination("classic"), notification())
    encoded = json.dumps(preview.payload)

    assert preview.metadata["message_style"] == "classic"
    assert preview.metadata["rendered_style"] == "classic"
    assert preview.metadata["modern_image"] is False
    assert TEAMS_MODERN_CARD_ROUTE_PREFIX not in encoded


def test_private_installation_keeps_native_modern_fallback(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setenv("NOWLERT_STATE_DIR", str(tmp_path / "state"))
    webui = dict(config.get("webui", default={}) or {})
    webui["public_url"] = ""
    monkeypatch.setitem(config._data, "webui", webui)

    adapter = TeamsPlatformAdapter(resolver=public_resolver)
    monkeypatch.setattr(
        adapter.output.discord_modern_output,
        "render_modern_image",
        lambda *_args, **_kwargs: synthetic_modern_png(),
    )

    preview = adapter.preview(destination("modern"), notification())
    encoded = json.dumps(preview.payload)

    assert preview.metadata["modern_image"] is False
    assert preview.metadata["formatter"] == "TeamsFormatter"
    assert TEAMS_MODERN_CARD_ROUTE_PREFIX not in encoded
    assert "Event details" in encoded


def test_public_card_route_rejects_unbounded_or_unknown_paths(
    monkeypatch,
    tmp_path,
):
    configure_public_cards(monkeypatch, tmp_path)
    service = WebUIService(config)

    missing = service.response(
        TEAMS_MODERN_CARD_ROUTE_PREFIX + ("0" * 48) + ".png"
    )
    traversal = service.response(
        TEAMS_MODERN_CARD_ROUTE_PREFIX + "../secret.png"
    )

    assert missing is not None and missing.status == 404
    assert traversal is not None and traversal.status == 404
