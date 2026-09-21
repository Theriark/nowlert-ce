"""Xen Orchestra Discord Modern image-card rendering and delivery."""

from __future__ import annotations

import json
import socket
from io import BytesIO

from PIL import Image

from formatters.discord_xo_image import XenOrchestraDiscordImageRenderer
from models import Notification
from outputs.platform import DiscordPlatformAdapter
from storage.destinations import Destination


PUBLIC_ADDRESS = "93.184.216.34"


def public_resolver(host, port, **_kwargs):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (PUBLIC_ADDRESS, port))]


def destination(modern: bool) -> Destination:
    return Destination(
        id="discord-xo",
        owner_user_id="owner",
        name="Discord XO",
        output_type="discord",
        settings={"components_v2": modern},
        shared=False,
        enabled=True,
        secret_configured=True,
        created_at=1,
        updated_at=1,
    )


def xo_notification(kind: str = "success") -> Notification:
    status = {
        "success": "success",
        "failure": "failure",
        "skipped": "skipped",
    }[kind]
    item = Notification(
        source="xo",
        subject=(
            "Backup report for [NON-CRITICAL - 01] Administration"
            if kind == "success"
            else (
                "Backup report for [CRITICAL - 02] Operation Critical"
                if kind == "failure"
                else "Backup report for [WEEKLY - 03] Archive Rotation"
            )
        ),
        category="backup",
        status=status,
        job_name=(
            "[NON-CRITICAL - 01] Administration"
            if kind == "success"
            else (
                "[CRITICAL - 02] Operation Critical"
                if kind == "failure"
                else "[WEEKLY - 03] Archive Rotation"
            )
        ),
        mode="full",
        duration="28 minutes",
        transfer_size="52.06 GiB",
        repository="UNAS-01 | NFS | Non-Critical Backups",
        transfer_speed="33.73 MiB/s",
        start_time="2026-09-21 19:12:49 UTC",
        end_time="2026-09-21 19:40:49 UTC",
        vm_total=3,
    )
    if kind == "success":
        item.vm_success = 3
        item.successful_vms = ["VM-01 | Admin", "VM-06 | XO-02", "VM-02 | XO-01"]
        item.vm_details = {
            "VM-01 | Admin": {"size": "45.01 GiB", "speed": "33.73 MiB/s"},
            "VM-06 | XO-02": {"size": "3.42 GiB", "speed": "28.11 MiB/s"},
            "VM-02 | XO-01": {"size": "3.62 GiB", "speed": "22.27 MiB/s"},
        }
    elif kind == "failure":
        item.vm_success = 2
        item.vm_failed = 1
        item.successful_vms = ["VM-04 | Docker", "VM-08 | Zabbix"]
        item.failed_vms = ["VM-14 | Windows Server"]
        item.vm_details = {
            "VM-04 | Docker": {"size": "18.33 GiB", "speed": "27.95 MiB/s"},
            "VM-08 | Zabbix": {"size": "7.23 GiB", "speed": "26.99 MiB/s"},
            "VM-14 | Windows Server": {
                "size": "23.66 GiB",
                "speed": "34.25 MiB/s",
                "error": "Body Timeout Error",
            },
        }
    else:
        item.vm_success = 2
        item.vm_skipped = 1
        item.successful_vms = ["VM-03 | Home Assistant", "VM-09 | Management"]
        item.skipped_vms = ["VM-12 | Maintenance Window"]
        item.vm_details = {
            "VM-03 | Home Assistant": {"size": "12.40 GiB", "speed": "24.70 MiB/s"},
            "VM-09 | Management": {"size": "13.90 GiB", "speed": "26.10 MiB/s"},
            "VM-12 | Maintenance Window": {
                "size": "5.50 GiB",
                "error": "Backup policy excluded this VM during its maintenance window",
            },
        }
    return item


def test_xo_image_renderer_produces_png_for_all_outcomes(tmp_path):
    renderer = XenOrchestraDiscordImageRenderer(tmp_path)

    images = [renderer.render(xo_notification(kind)) for kind in ("success", "failure", "skipped")]

    assert all(data.startswith(b"\x89PNG\r\n\x1a\n") for data in images)
    assert len({data for data in images}) == 3
    for data in images:
        with Image.open(BytesIO(data)) as image:
            assert image.width == 1400
            assert image.height >= 1000
            assert image.mode in {"RGB", "RGBA"}
        assert len(data) < 5 * 1024 * 1024


class Response:
    status_code = 200
    text = ""

    def __init__(self, filename="nowlert-xen-orchestra.png"):
        self.filename = filename

    def json(self):
        url = (
            "https://cdn.discordapp.com/attachments/1/2/"
            + self.filename
        )
        proxy_url = (
            "https://media.discordapp.net/attachments/1/2/"
            + self.filename
        )
        return {
            "attachments": [
                {
                    "id": "2",
                    "filename": self.filename,
                    "content_type": "image/png",
                    "url": url,
                    "proxy_url": proxy_url,
                }
            ],
            "components": [],
        }


class HTTPClient:
    def __init__(self):
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        filename = "nowlert-xen-orchestra.png"
        files = kwargs.get("files")
        if isinstance(files, dict) and "files[0]" in files:
            filename = files["files[0]"][0]
        return Response(filename)


def test_xo_modern_delivery_is_image_only(monkeypatch):
    client = HTTPClient()
    adapter = DiscordPlatformAdapter(
        http_client=client,
        resolver=public_resolver,
    )
    image = b"\x89PNG\r\n\x1a\nsynthetic"
    monkeypatch.setattr(
        adapter.output,
        "render_xo_modern_image",
        lambda _notification: image,
    )

    result = adapter.deliver(
        destination(True),
        b"https://discord.com/api/webhooks/123/token",
        xo_notification("success"),
    )

    assert result.success is True
    assert len(client.calls) == 1
    url, kwargs = client.calls[0]
    assert url == "https://discord.com/api/webhooks/123/token?wait=true"
    assert "json" not in kwargs
    payload = json.loads(kwargs["data"]["payload_json"])
    assert payload == {
        "attachments": [
            {
                "id": 0,
                "filename": "nowlert-xen-orchestra.png",
                "description": "Xen Orchestra notification",
            }
        ],
        "allowed_mentions": {"parse": []},
    }
    filename, content, content_type = kwargs["files"]["files[0]"]
    assert filename == "nowlert-xen-orchestra.png"
    assert content == image
    assert content_type == "image/png"
    assert kwargs["timeout"] == 15


def test_xo_classic_delivery_does_not_use_image_renderer(monkeypatch):
    client = HTTPClient()
    adapter = DiscordPlatformAdapter(
        http_client=client,
        resolver=public_resolver,
    )

    def fail_if_called(_notification):
        raise AssertionError("Classic Discord must not render an XO image card")

    monkeypatch.setattr(
        adapter.output,
        "render_xo_modern_image",
        fail_if_called,
    )
    monkeypatch.setattr(
        adapter.output,
        "_thumbnail_media",
        lambda _payload: None,
    )
    monkeypatch.setattr(
        adapter.output,
        "_local_icon",
        lambda _payload, _formatter: None,
    )

    result = adapter.deliver(
        destination(False),
        b"https://discord.com/api/webhooks/123/token",
        xo_notification("success"),
    )

    assert result.success is True
    assert len(client.calls) == 1
    _url, kwargs = client.calls[0]
    assert "json" in kwargs
    assert "files" not in kwargs


def test_xo_modern_falls_back_to_native_card_if_rendering_fails(monkeypatch):
    client = HTTPClient()
    adapter = DiscordPlatformAdapter(
        http_client=client,
        resolver=public_resolver,
    )
    monkeypatch.setattr(
        adapter.output,
        "render_xo_modern_image",
        lambda _notification: None,
    )
    monkeypatch.setattr(
        adapter.output,
        "_thumbnail_media",
        lambda _payload: None,
    )
    monkeypatch.setattr(
        adapter.output,
        "_local_icon",
        lambda _payload, _formatter: None,
    )

    result = adapter.deliver(
        destination(True),
        b"https://discord.com/api/webhooks/123/token",
        xo_notification("success"),
    )

    assert result.success is True
    assert len(client.calls) == 1
    url, kwargs = client.calls[0]
    assert "with_components=true" in url
    assert "json" in kwargs
    assert kwargs["json"]["flags"] == 32768
