"""Microsoft Teams Modern image parity with Discord."""

from __future__ import annotations

from io import BytesIO
import json
import socket
from urllib.parse import parse_qs, urlsplit

from PIL import Image

from config import config
from models import Notification
from outputs.platform import TeamsPlatformAdapter
from outputs.teams import TeamsOutput
from outputs.teams_modern_image import (
    TEAMS_MODERN_CARD_MAX_DIMENSION,
    TEAMS_MODERN_CARD_PUBLIC_PATH,
    TEAMS_MODERN_CARD_QUERY_NAME,
    TEAMS_MODERN_CARD_URL_PREFIX,
    load_teams_modern_image,
)
from storage.destinations import Destination


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


class Response:
    status_code = 202
    text = ""


class HTTPClient:
    def __init__(self):
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return Response()


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
    monkeypatch.setenv(
        "NOWLERT_TEAMS_PUBLIC_BASE_URL",
        "https://nowlert.example.test",
    )


def image_item(payload: dict) -> dict:
    body = payload["attachments"][0]["content"]["body"]
    assert len(body) == 1
    return body[0]


def image_filename(url: str) -> str:
    parsed = urlsplit(url)
    values = parse_qs(parsed.query).get(
        TEAMS_MODERN_CARD_QUERY_NAME,
        [],
    )
    assert len(values) == 1
    return values[0]


def test_teams_modern_uses_discord_renderer_and_public_health_path(
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
    parsed = urlsplit(image["url"])
    assert image["type"] == "Image"
    assert image["size"] == "Stretch"
    assert parsed.scheme == "https"
    assert parsed.netloc == "nowlert.example.test"
    assert parsed.path == TEAMS_MODERN_CARD_PUBLIC_PATH
    assert image["url"].startswith(
        "https://nowlert.example.test"
        + TEAMS_MODERN_CARD_URL_PREFIX
    )
    assert "Event details" not in json.dumps(payload)

    published = load_teams_modern_image(
        config,
        image_filename(image["url"]),
    )
    assert published is not None
    with Image.open(BytesIO(published)) as rendered:
        assert max(rendered.size) == TEAMS_MODERN_CARD_MAX_DIMENSION


def test_platform_modern_preview_is_image_only_when_public_origin_exists(
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
    assert TEAMS_MODERN_CARD_URL_PREFIX in image["url"]
    assert preview.metadata["payload_bytes"] < 28 * 1024
    assert "error_code" not in preview.metadata


def test_teams_classic_never_invokes_modern_image_renderer(
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
    assert TEAMS_MODERN_CARD_QUERY_NAME not in encoded


def test_missing_public_origin_fails_closed_instead_of_native_card(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setenv("NOWLERT_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.delenv("NOWLERT_TEAMS_PUBLIC_BASE_URL", raising=False)
    webui = dict(config.get("webui", default={}) or {})
    webui["public_url"] = ""
    monkeypatch.setitem(config._data, "webui", webui)

    client = HTTPClient()
    adapter = TeamsPlatformAdapter(
        http_client=client,
        resolver=public_resolver,
    )
    monkeypatch.setattr(
        adapter.output.discord_modern_output,
        "render_modern_image",
        lambda *_args, **_kwargs: synthetic_modern_png(),
    )

    preview = adapter.preview(destination("modern"), notification())
    result = adapter.deliver(
        destination("modern"),
        b"https://example.com/teams-workflow",
        notification(),
    )

    assert preview.metadata["modern_image"] is False
    assert preview.metadata["formatter"] == "DiscordModernImageRenderer"
    assert preview.metadata["error_code"] == (
        "teams_modern_image_unavailable"
    )
    assert preview.payload["error"] == "teams_modern_image_unavailable"
    assert "Event details" not in json.dumps(preview.payload)
    assert result.success is False
    assert result.error_code == "teams_modern_image_unavailable"
    assert client.calls == []


def test_public_card_loader_rejects_unknown_or_traversal_tokens(
    monkeypatch,
    tmp_path,
):
    configure_public_cards(monkeypatch, tmp_path)

    assert load_teams_modern_image(
        config,
        ("0" * 48) + ".png",
    ) is None
    assert load_teams_modern_image(
        config,
        "../secret.png",
    ) is None
