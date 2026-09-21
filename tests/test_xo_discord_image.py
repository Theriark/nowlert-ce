"""Xen Orchestra Discord Modern image-card rendering and delivery."""

from __future__ import annotations

import json
import socket
from io import BytesIO

from PIL import Image, ImageDraw

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
            assert image.width == 1448
            assert image.height >= 1086
            assert image.mode in {"RGB", "RGBA"}
        assert len(data) < 5 * 1024 * 1024


def test_xo_image_renderer_uses_nowlert_brand_and_state_accents(tmp_path):
    renderer = XenOrchestraDiscordImageRenderer(tmp_path)

    expected = {
        "success": renderer.SUCCESS,
        "failure": renderer.FAILURE,
        "skipped": renderer.SKIPPED,
    }

    for kind, accent in expected.items():
        data = renderer.render(xo_notification(kind))
        with Image.open(BytesIO(data)).convert("RGB") as image:
            # The approved template keeps Nowlert's dark graphite background.
            page = image.getpixel((8, 8))
            assert max(page) < 45

            # The left lifecycle rail is the state colour.
            rail = image.getpixel((39, 500))
            assert all(abs(rail[i] - accent[i]) <= 8 for i in range(3))

            # The main information panel remains dark/neutral rather than
            # inheriting a blue Discord background.
            panel = image.getpixel((500, 430))
            assert max(panel) < 80


def test_xo_card_grows_to_keep_all_vm_content_inside(tmp_path):
    renderer = XenOrchestraDiscordImageRenderer(tmp_path)

    success = xo_notification("success")
    success_data = renderer.render(success)
    with Image.open(BytesIO(success_data)) as image:
        baseline_height = image.height

    crowded = xo_notification("success")
    crowded.successful_vms = [
        f"VM-{index:02d} | Workload {index}"
        for index in range(1, 21)
    ]
    crowded.vm_success = len(crowded.successful_vms)
    crowded.vm_total = len(crowded.successful_vms)
    crowded.vm_details = {
        name: {
            "size": f"{index}.00 GiB",
            "speed": f"{20 + index}.00 MiB/s",
        }
        for index, name in enumerate(crowded.successful_vms, start=1)
    }

    crowded_data = renderer.render(crowded)
    with Image.open(BytesIO(crowded_data)) as image:
        assert image.height > baseline_height
        footer_y = image.height - renderer.FOOTER_RESERVE
        available_vm_height = (
            footer_y
            - renderer.FOOTER_GAP
            - renderer.VM_PANEL_TOP
        )
        required_vm_height = renderer._vm_panel_height(
            crowded,
            crowded.successful_vms,
            [],
            [],
        )
        assert available_vm_height >= required_vm_height


def test_xo_success_panel_uses_three_columns_and_grows_past_ten_vms(tmp_path):
    renderer = XenOrchestraDiscordImageRenderer(tmp_path)
    item = xo_notification("success")
    item.successful_vms = [
        f"VM-{index:02d} | Workload {index}"
        for index in range(1, 21)
    ]
    item.vm_success = 20
    item.vm_total = 20
    item.vm_details = {
        name: {
            "size": f"{index}.00 GiB",
            "speed": f"{20 + index}.00 MiB/s",
        }
        for index, name in enumerate(item.successful_vms, start=1)
    }

    data = renderer.render(item)
    with Image.open(BytesIO(data)) as image:
        expected_rows = 7
        expected_height = max(
            renderer.BASE_HEIGHT,
            (
                renderer.VM_PANEL_TOP
                + renderer.VM_HEADER_HEIGHT
                + expected_rows * renderer.SUCCESS_ROW_HEIGHT
                + renderer.VM_PANEL_BOTTOM_PADDING
                + renderer.FOOTER_GAP
                + renderer.FOOTER_RESERVE
            ),
        )
        assert image.height == expected_height

    assert len(item.successful_vms) == 20


def test_xo_paired_panels_keep_all_reported_vms_in_vertical_lists(tmp_path):
    renderer = XenOrchestraDiscordImageRenderer(tmp_path)
    item = xo_notification("failure")
    item.successful_vms = [
        f"VM-S{index:02d} | Success {index}"
        for index in range(1, 13)
    ]
    item.failed_vms = [
        f"VM-F{index:02d} | Failed {index}"
        for index in range(1, 9)
    ]
    item.vm_success = len(item.successful_vms)
    item.vm_failed = len(item.failed_vms)
    item.vm_total = item.vm_success + item.vm_failed
    item.vm_details = {
        **{
            name: {"size": "10.00 GiB", "speed": "20.00 MiB/s"}
            for name in item.successful_vms
        },
        **{
            name: {
                "size": "10.00 GiB",
                "speed": "20.00 MiB/s",
                "error": "Synthetic failure",
            }
            for name in item.failed_vms
        },
    }

    data = renderer.render(item)
    with Image.open(BytesIO(data)) as image:
        footer_y = image.height - renderer.FOOTER_RESERVE
        available_vm_height = (
            footer_y
            - renderer.FOOTER_GAP
            - renderer.VM_PANEL_TOP
        )
        required_vm_height = renderer._vm_panel_height(
            item,
            item.successful_vms,
            item.failed_vms,
            [],
        )
        assert available_vm_height >= required_vm_height

    assert len(item.successful_vms) == 12
    assert len(item.failed_vms) == 8


def test_xo_paired_card_grows_for_success_rows_and_long_reason(tmp_path):
    renderer = XenOrchestraDiscordImageRenderer(tmp_path)
    item = xo_notification("skipped")
    item.vm_details["VM-12 | Maintenance Window"]["error"] = (
        "Backup policy excluded this VM during its maintenance window "
        "because the protected workload remained inside a scheduled "
        "maintenance period."
    )

    data = renderer.render(item)
    with Image.open(BytesIO(data)) as image:
        assert image.height > renderer.BASE_HEIGHT
        footer_y = image.height - renderer.FOOTER_RESERVE
        available_vm_height = (
            footer_y
            - renderer.FOOTER_GAP
            - renderer.VM_PANEL_TOP
        )
        required_vm_height = renderer._vm_panel_height(
            item,
            item.successful_vms,
            [],
            item.skipped_vms,
        )
        assert available_vm_height >= required_vm_height


def test_xo_footer_uses_packaged_nowlert_icon(tmp_path):
    logo = Image.new("RGBA", (80, 80), (255, 0, 255, 255))
    logo.save(tmp_path / "nowlert.png")

    renderer = XenOrchestraDiscordImageRenderer(tmp_path)
    data = renderer.render(xo_notification("success"))

    with Image.open(BytesIO(data)).convert("RGB") as image:
        footer_crop = image.crop(
            (
                65,
                image.height - renderer.FOOTER_RESERVE,
                175,
                image.height - 38,
            )
        )
        pixels = list(footer_crop.getdata())
        assert any(
            red > 220 and green < 60 and blue > 220
            for red, green, blue in pixels
        )


def test_xo_header_uses_xo_icon_on_left_and_status_badge_at_right(tmp_path):
    discord_dir = tmp_path / "discord"
    discord_dir.mkdir()
    xo = Image.new("RGBA", (80, 80), (255, 0, 255, 255))
    xo.save(discord_dir / "xen-orchestra.png")

    renderer = XenOrchestraDiscordImageRenderer(tmp_path)
    data = renderer.render(xo_notification("success"))

    with Image.open(BytesIO(data)).convert("RGB") as image:
        left = list(image.crop((60, 65, 175, 175)).getdata())
        right_icon_area = list(
            image.crop((image.width - 190, 65, image.width - 65, 175)).getdata()
        )
        assert any(
            red > 220 and green < 60 and blue > 220
            for red, green, blue in left
        )
        assert not any(
            red > 220 and green < 60 and blue > 220
            for red, green, blue in right_icon_area
        )

    assert renderer.STATUS_BADGE_WIDTH == 420


def test_xo_footer_identity_is_nowlert_ce_modern_card():
    assert XenOrchestraDiscordImageRenderer.FOOTER_TEXT == (
        "Nowlert CE • Modern Card"
    )


def test_xo_transfer_size_has_clear_label_value_spacing(tmp_path):
    renderer = XenOrchestraDiscordImageRenderer(tmp_path)
    image = Image.new("RGB", (renderer.WIDTH, renderer.BASE_HEIGHT))
    draw = ImageDraw.Draw(image)

    x1 = 70
    label_x = x1 + renderer.DETAIL_LABEL_OFFSET
    label_end = label_x + draw.textlength(
        "Transfer size",
        font=renderer.font_label,
    )
    value_x = renderer._detail_value_x(draw, x1, "Transfer size")

    assert value_x - label_end >= renderer.DETAIL_LABEL_VALUE_GAP


def test_xo_footer_is_left_aligned_with_bottom_breathing_room(tmp_path):
    logo = Image.new("RGBA", (80, 80), (255, 0, 255, 255))
    logo.save(tmp_path / "nowlert.png")

    renderer = XenOrchestraDiscordImageRenderer(tmp_path)
    data = renderer.render(xo_notification("success"))

    with Image.open(BytesIO(data)).convert("RGB") as image:
        left_footer = list(
            image.crop(
                (
                    65,
                    image.height - renderer.FOOTER_RESERVE,
                    175,
                    image.height - 38,
                )
            ).getdata()
        )
        right_footer = list(
            image.crop(
                (
                    image.width - 175,
                    image.height - renderer.FOOTER_RESERVE,
                    image.width - 65,
                    image.height - 38,
                )
            ).getdata()
        )
        assert any(
            red > 220 and green < 60 and blue > 220
            for red, green, blue in left_footer
        )
        assert not any(
            red > 220 and green < 60 and blue > 220
            for red, green, blue in right_footer
        )

    assert renderer.FOOTER_RESERVE >= 110


def test_xo_detail_values_fit_repository_and_skipped_result(tmp_path):
    renderer = XenOrchestraDiscordImageRenderer(tmp_path)
    image = Image.new("RGB", (renderer.WIDTH, renderer.BASE_HEIGHT))
    draw = ImageDraw.Draw(image)

    x0 = 70
    right = renderer.WIDTH - 70
    gap = 22
    detail_width = right - x0 - gap
    left_width = int(detail_width * renderer.DETAIL_SPLIT_RATIO)
    right_x1 = x0 + left_width + gap
    repository = "UNAS-01 | NFS | Non-Critical Backups"
    value_x = renderer._detail_value_x(draw, right_x1, "Repository")
    available = right - value_x - 22
    repository_font = renderer._fit_text_adaptive(
        draw,
        repository,
        value_x,
        0,
        available,
        (
            renderer.font_small,
            renderer.font_tiny,
            renderer.font_micro,
        ),
        renderer.TEXT,
    )
    assert draw.textlength(repository, font=repository_font) <= available

    result = "2 of 3 VMs successful | 1 skipped"
    result_value_x = renderer._detail_value_x(draw, right_x1, "Result")
    result_available = right - result_value_x - 22 - 34 - 10
    result_font = renderer._fit_text_adaptive(
        draw,
        result,
        result_value_x + 44,
        0,
        result_available,
        (
            renderer.font_small,
            renderer.font_tiny,
            renderer.font_micro,
        ),
        renderer.TEXT,
    )
    assert draw.textlength(result, font=result_font) <= result_available


def test_xo_skipped_card_uses_blue_not_warning_yellow(tmp_path):
    renderer = XenOrchestraDiscordImageRenderer(tmp_path)
    data = renderer.render(xo_notification("skipped"))

    with Image.open(BytesIO(data)).convert("RGB") as image:
        rail = image.getpixel((39, 500))
        assert rail[2] > rail[0]
        assert rail[2] > rail[1]


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
