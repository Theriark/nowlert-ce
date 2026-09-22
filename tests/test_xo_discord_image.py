"""Xen Orchestra Discord Modern image-card rendering and delivery."""

from __future__ import annotations

import json
import socket
from io import BytesIO
from math import ceil

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
            assert image.width == renderer.WIDTH
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

            # The approved detail panel remains dark/neutral rather than
            # inheriting a lifecycle-colored background.
            panel = image.getpixel(
                (
                    renderer.CARD_SIDE_PADDING + 10,
                    renderer.VM_PANEL_TOP - 10,
                )
            )
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


def test_xo_success_panel_keeps_every_vm_at_readable_size(tmp_path, monkeypatch):
    renderer = XenOrchestraDiscordImageRenderer(tmp_path)
    item = xo_notification("success")
    item.successful_vms = [f"VM-{index:02d} | Workload {index}" for index in range(1, 21)]
    item.vm_success = item.vm_total = 20
    item.vm_details = {name: {"size": "10.00 GiB", "speed": "20.00 MiB/s"}
                       for name in item.successful_vms}
    drawn = []
    original = ImageDraw.ImageDraw.text

    def record(self, xy, text, *args, **kwargs):
        drawn.append((str(text), kwargs.get("font")))
        return original(self, xy, text, *args, **kwargs)

    monkeypatch.setattr(ImageDraw.ImageDraw, "text", record)
    data = renderer.render(item)
    with Image.open(BytesIO(data)) as image:
        assert image.height > renderer.BASE_HEIGHT
    # A larger job must add rows, never hide VMs or select a compact font.
    painted = " ".join(text for text, _ in drawn)
    for name in item.successful_vms:
        assert name in painted
    assert all(font.size >= 36 for text, font in drawn
               if font is not None and "Nowlert CE" not in text)


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
        draw = ImageDraw.Draw(image)
        right = renderer.WIDTH - renderer.CARD_SIDE_PADDING
        icon_x = renderer._footer_identity_x(draw, right)
        footer_crop = image.crop(
            (
                icon_x,
                image.height - renderer.FOOTER_RESERVE,
                icon_x + renderer.FOOTER_ICON_SIZE,
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

    assert renderer.STATUS_BADGE_WIDTH == 560


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


def test_xo_footer_is_right_aligned_with_bottom_breathing_room(tmp_path):
    logo = Image.new("RGBA", (80, 80), (255, 0, 255, 255))
    logo.save(tmp_path / "nowlert.png")

    renderer = XenOrchestraDiscordImageRenderer(tmp_path)
    data = renderer.render(xo_notification("success"))

    with Image.open(BytesIO(data)).convert("RGB") as image:
        draw = ImageDraw.Draw(image)
        right = renderer.WIDTH - renderer.CARD_SIDE_PADDING
        icon_x = renderer._footer_identity_x(draw, right)
        footer_icon = list(
            image.crop(
                (
                    icon_x,
                    image.height - renderer.FOOTER_RESERVE,
                    icon_x + renderer.FOOTER_ICON_SIZE,
                    image.height - 38,
                )
            ).getdata()
        )
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
        assert any(
            red > 220 and green < 60 and blue > 220
            for red, green, blue in footer_icon
        )
        assert not any(
            red > 220 and green < 60 and blue > 220
            for red, green, blue in left_footer
        )

    assert renderer.FOOTER_RESERVE >= 118


def test_xo_detail_values_wrap_at_readable_size_without_truncation(tmp_path):
    renderer = XenOrchestraDiscordImageRenderer(tmp_path)
    image = Image.new("RGB", (renderer.WIDTH, renderer.BASE_HEIGHT))
    draw = ImageDraw.Draw(image)

    x0 = renderer.CARD_SIDE_PADDING
    right = renderer.WIDTH - renderer.CARD_SIDE_PADDING
    gap = 24
    detail_width = right - x0 - gap
    left_width = int(detail_width * renderer.DETAIL_SPLIT_RATIO)
    right_x1 = x0 + left_width + gap
    right_width = right - right_x1

    for label, value in (
        ("Repository", "UNAS-01 | NFS | Non-Critical Backups"),
        ("Result", "2 of 3 VMs successful | 1 skipped"),
    ):
        value_x = renderer._detail_value_x(draw, right_x1, label)
        available = max(120, right - value_x - 24)
        if label == "Result":
            available = max(120, available - 50)
        lines = renderer._wrapped_text_lines(
            draw,
            value,
            available,
            renderer.font_detail,
        )
        assert lines
        assert " ".join(lines) == value
        assert all(
            draw.textlength(line, font=renderer.font_detail) <= available
            for line in lines
        )

def test_xo_header_icon_is_large_and_trims_transparent_padding(tmp_path):
    discord_dir = tmp_path / "discord"
    discord_dir.mkdir()

    icon = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
    draw = ImageDraw.Draw(icon)
    draw.rectangle((80, 80, 120, 120), fill=(255, 0, 255, 255))
    icon.save(discord_dir / "xen-orchestra.png")

    renderer = XenOrchestraDiscordImageRenderer(tmp_path)
    data = renderer.render(xo_notification("success"))

    assert renderer.XO_HEADER_ICON_SIZE >= 120

    with Image.open(BytesIO(data)).convert("RGB") as image:
        crop = image.crop((65, 65, 205, 205))
        magenta = sum(
            1
            for red, green, blue in crop.getdata()
            if red > 220 and green < 60 and blue > 220
        )
        # Transparent padding is cropped before fitting, so the visible logo
        # occupies a substantial part of the header slot.
        assert magenta > 7000


def test_xo_failure_and_skipped_use_same_approved_panel_split(tmp_path):
    renderer = XenOrchestraDiscordImageRenderer(tmp_path)
    failure = xo_notification("failure")
    skipped = xo_notification("skipped")

    failure_ratio = renderer._paired_panel_left_ratio(
        failure.successful_vms,
        failure.failed_vms,
        failure,
    )
    skipped_ratio = renderer._paired_panel_left_ratio(
        skipped.successful_vms,
        skipped.skipped_vms,
        skipped,
    )

    assert failure_ratio == renderer.PAIRED_PANEL_LEFT_RATIO
    assert skipped_ratio == renderer.PAIRED_PANEL_LEFT_RATIO
    assert failure_ratio == skipped_ratio

def test_xo_vm_name_wraps_instead_of_shrinking_or_ellipsizing(tmp_path):
    renderer = XenOrchestraDiscordImageRenderer(tmp_path)
    image = Image.new("RGB", (renderer.WIDTH, renderer.BASE_HEIGHT))
    draw = ImageDraw.Draw(image)
    style = renderer._vm_style(3)

    name = (
        "VM-12 | Maintenance Window With A Very Long Operational Name "
        "That Must Remain Complete"
    )
    available = 360
    lines = renderer._wrapped_text_lines(
        draw,
        name,
        available,
        style["name_font"],
    )

    assert len(lines) > 1
    assert " ".join(lines) == name
    assert style["name_font"].size >= 36
    assert all(
        draw.textlength(line, font=style["name_font"]) <= available
        for line in lines
    )

def test_xo_exception_reason_type_is_more_readable(tmp_path):
    renderer = XenOrchestraDiscordImageRenderer(tmp_path)

    comfortable = renderer._vm_style(3)
    standard = renderer._vm_style(9)
    compact = renderer._vm_style(20)

    assert comfortable["reason_font"].size >= 21
    assert standard["reason_font"].size >= 20
    assert compact["reason_font"].size >= 18


def test_xo_vm_typography_never_drops_below_readable_floor(tmp_path):
    renderer = XenOrchestraDiscordImageRenderer(tmp_path)

    comfortable = renderer._vm_style(3)
    standard = renderer._vm_style(9)
    compact = renderer._vm_style(20)

    for style in (comfortable, standard, compact):
        assert style["name_font"].size >= 36
        assert style["name_fallback_font"].size >= 36
        assert style["meta_font"].size >= 36
        assert style["reason_font"].size >= 36

    assert comfortable["row_height"] > standard["row_height"]
    assert standard["row_height"] > compact["row_height"]

def test_xo_result_exception_uses_lifecycle_accent(tmp_path):
    renderer = XenOrchestraDiscordImageRenderer(tmp_path)

    failure = renderer._result_segments(
        "2 of 3 VMs successful | 1 failed",
        renderer.FAILURE,
    )
    skipped = renderer._result_segments(
        "2 of 3 VMs successful | 1 skipped",
        renderer.SKIPPED,
    )
    success = renderer._result_segments(
        "3 of 3 VMs successful",
        renderer.SUCCESS,
    )

    assert failure[-1] == ("1 failed", renderer.FAILURE)
    assert skipped[-1] == ("1 skipped", renderer.SKIPPED)
    assert success == [("3 of 3 VMs successful", renderer.TEXT)]


def test_xo_normal_vm_card_uses_larger_operational_type(tmp_path):
    renderer = XenOrchestraDiscordImageRenderer(tmp_path)
    style = renderer._vm_style(3)

    assert style["name_font"].size >= 28
    assert style["meta_font"].size >= 23
    assert style["reason_font"].size >= 19


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



def test_xo_uses_dedicated_approved_renderer_not_shared_standard_card(
    tmp_path,
    monkeypatch,
):
    renderer = XenOrchestraDiscordImageRenderer(tmp_path)

    def shared_layout_must_not_run(**_kwargs):
        raise AssertionError(
            "Xen Orchestra must keep its dedicated approved renderer"
        )

    monkeypatch.setattr(
        renderer,
        "_render_standard_card",
        shared_layout_must_not_run,
    )

    data = renderer.render(xo_notification("success"))
    assert data.startswith(b"\x89PNG\r\n\x1a\n")


def test_xo_card_is_larger_without_changing_non_xo_cards(tmp_path):
    renderer = XenOrchestraDiscordImageRenderer(tmp_path)

    assert renderer.WIDTH == 2000
    assert renderer.BASE_HEIGHT >= 1320
    assert renderer.STATUS_BADGE_WIDTH >= 560
    assert renderer.STATUS_BADGE_HEIGHT >= 128
    assert renderer.FOOTER_ICON_SIZE >= 64


def test_xo_readability_fonts_are_larger_than_approved_baseline(tmp_path):
    renderer = XenOrchestraDiscordImageRenderer(tmp_path)

    assert renderer.font_heading.size >= 54
    assert renderer.font_title.size >= 46
    assert renderer.font_body.size >= 38
    assert renderer.font_detail.size >= 38
    assert renderer.font_label.size >= 36
    assert renderer.font_vm_large.size >= 40
    assert renderer.font_small.size >= 36


def test_xo_failure_and_skipped_share_same_card_dimensions(tmp_path):
    renderer = XenOrchestraDiscordImageRenderer(tmp_path)

    failure = renderer.render(xo_notification("failure"))
    skipped = renderer.render(xo_notification("skipped"))

    with Image.open(BytesIO(failure)) as failure_image:
        failure_size = failure_image.size
    with Image.open(BytesIO(skipped)) as skipped_image:
        skipped_size = skipped_image.size

    assert failure_size == skipped_size


def test_non_xo_modern_width_remains_unchanged():
    from formatters.discord_modern_image import DiscordModernImageRenderer

    assert DiscordModernImageRenderer.WIDTH == 1448



def test_xo_event_time_strip_shows_time_only(tmp_path):
    renderer = XenOrchestraDiscordImageRenderer(tmp_path)

    assert renderer._event_time_only(
        "2026-09-22 02:03:25 UTC"
    ) == "02:03:25 UTC"
    assert renderer._event_time_only(
        "2026-09-22T02:03:25Z"
    ) == "02:03:25 UTC"
    assert renderer._event_time_only(
        "02:03:25"
    ) == "02:03:25"


def test_xo_summary_cells_have_explicit_breathing_room(tmp_path):
    renderer = XenOrchestraDiscordImageRenderer(tmp_path)

    cells = renderer._summary_cells(
        renderer.CARD_SIDE_PADDING,
        renderer.WIDTH - renderer.CARD_SIDE_PADDING,
    )

    assert len(cells) == 3
    assert cells[1][0] - cells[0][1] >= renderer.SUMMARY_CELL_GAP
    assert cells[2][0] - cells[1][1] >= renderer.SUMMARY_CELL_GAP


def test_xo_status_badge_fills_header_height_and_centers_icon(tmp_path):
    renderer = XenOrchestraDiscordImageRenderer(tmp_path)

    header_y = 82
    header_height = 154
    badge = renderer._status_badge_box(
        renderer.WIDTH - renderer.CARD_SIDE_PADDING,
        header_y,
        header_height,
    )

    assert badge[3] - badge[1] == header_height
    icon_y = renderer._center_y(
        badge[1],
        badge[3],
        64,
    )
    assert icon_y - badge[1] == (header_height - 64) // 2


def test_xo_readability_scale_increases_with_larger_card(tmp_path):
    renderer = XenOrchestraDiscordImageRenderer(tmp_path)

    assert renderer.font_heading.size >= 62
    assert renderer.font_title.size >= 52
    assert renderer.font_body.size >= 42
    assert renderer.font_detail.size >= 42
    assert renderer.font_label.size >= 40
    assert renderer.font_bold.size >= 46
    assert renderer.font_small.size >= 40



def test_xo_reference_detail_values_fit_single_line_at_readable_size(tmp_path):
    renderer = XenOrchestraDiscordImageRenderer(tmp_path)
    image = Image.new("RGB", (renderer.WIDTH, renderer.BASE_HEIGHT))
    draw = ImageDraw.Draw(image)

    x0 = renderer.CARD_SIDE_PADDING
    right = renderer.WIDTH - renderer.CARD_SIDE_PADDING
    gap = 24
    detail_width = right - x0 - gap
    left_width = int(detail_width * renderer.DETAIL_SPLIT_RATIO)
    right_x1 = x0 + left_width + gap

    labels = ("Repository", "Started", "Finished", "Result")
    value_x = max(
        renderer._detail_value_x(draw, right_x1, label)
        for label in labels
    )
    available = right - value_x - 24

    for value in (
        "UNAS-01 | NFS | Non-Critical Backups",
        "2026-09-22 01:59:47 UTC",
        "2026-09-22 02:27:47 UTC",
    ):
        assert draw.textlength(
            value,
            font=renderer.font_detail,
        ) <= available

    result_available = available - 50
    assert draw.textlength(
        "2 of 3 VMs successful | 1 failed",
        font=renderer.font_detail,
    ) <= result_available


def test_xo_detail_result_uses_lifecycle_colored_renderer(tmp_path, monkeypatch):
    renderer = XenOrchestraDiscordImageRenderer(tmp_path)
    image = Image.new("RGB", (renderer.WIDTH, renderer.BASE_HEIGHT))
    draw = ImageDraw.Draw(image)
    calls = []

    def capture(draw_arg, value, x, y, width, accent):
        calls.append((value, accent, width))

    monkeypatch.setattr(renderer, "_draw_result_value", capture)

    renderer._detail_rows(
        draw,
        (900, 200, 1900, 520),
        [("chart", "Result", "2 of 3 VMs successful | 1 failed")],
        result_status="failure",
    )

    assert len(calls) == 1
    value, accent, width = calls[0]
    assert value == "2 of 3 VMs successful | 1 failed"
    assert accent == renderer.FAILURE
    assert width > 0


def test_xo_footer_icon_is_large_and_trims_transparent_padding(tmp_path):
    logo = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
    draw = ImageDraw.Draw(logo)
    draw.rectangle((80, 80, 120, 120), fill=(255, 0, 255, 255))
    logo.save(tmp_path / "nowlert.png")

    renderer = XenOrchestraDiscordImageRenderer(tmp_path)
    assert renderer.FOOTER_ICON_SIZE >= 96

    image = Image.new(
        "RGBA",
        (renderer.FOOTER_ICON_SIZE, renderer.FOOTER_ICON_SIZE),
        (0, 0, 0, 0),
    )
    renderer._draw_nowlert_icon(
        image,
        0,
        0,
        renderer.FOOTER_ICON_SIZE,
    )

    magenta = sum(
        1
        for red, green, blue, alpha in image.getdata()
        if alpha > 0 and red > 220 and green < 60 and blue > 220
    )
    assert magenta > 6000



def test_xo_success_badge_is_shifted_left_without_moving_other_badges(tmp_path):
    renderer = XenOrchestraDiscordImageRenderer(tmp_path)
    right = renderer.WIDTH - renderer.CARD_SIDE_PADDING
    header_y = 82
    header_height = 154

    success = renderer._status_badge_box(
        right,
        header_y,
        header_height,
        status="success",
    )
    failure = renderer._status_badge_box(
        right,
        header_y,
        header_height,
        status="failure",
    )

    assert renderer.SUCCESS_BADGE_LEFT_SHIFT == 48
    assert success[2] == right
    assert failure[2] == right
    assert success[2] - success[0] == (
        renderer.STATUS_BADGE_WIDTH
        + renderer.SUCCESS_BADGE_LEFT_SHIFT
    )
    assert failure[2] - failure[0] == renderer.STATUS_BADGE_WIDTH


def test_xo_failed_vm_reason_has_extra_space_after_speed(tmp_path):
    renderer = XenOrchestraDiscordImageRenderer(tmp_path)
    style = renderer._vm_style(3)
    base_y = 500

    failure_y = renderer._vm_reason_y(
        base_y,
        style,
        0,
        "failure",
    )
    skipped_y = renderer._vm_reason_y(
        base_y,
        style,
        0,
        "skipped",
    )

    assert failure_y - skipped_y == renderer.FAILED_REASON_TOP_GAP
    assert renderer.FAILED_REASON_TOP_GAP >= 24


def test_xo_footer_identity_is_right_aligned_without_changing_size(tmp_path):
    renderer = XenOrchestraDiscordImageRenderer(tmp_path)
    image = Image.new("RGB", (renderer.WIDTH, renderer.BASE_HEIGHT))
    draw = ImageDraw.Draw(image)
    right = renderer.WIDTH - renderer.CARD_SIDE_PADDING

    icon_x = renderer._footer_identity_x(draw, right)
    text_width = ceil(
        draw.textlength(
            renderer.FOOTER_TEXT,
            font=renderer.font_small,
        )
    )
    group_right = (
        icon_x
        + renderer.FOOTER_ICON_SIZE
        + 18
        + text_width
    )

    assert renderer.WIDTH == 2000
    assert renderer.FOOTER_ICON_SIZE == 96
    assert icon_x > renderer.WIDTH // 2
    assert group_right == right - 18



def test_xo_success_matches_frozen_failure_and_skipped_card_size(tmp_path):
    renderer = XenOrchestraDiscordImageRenderer(tmp_path)

    success = renderer.render(xo_notification("success"))
    failure = renderer.render(xo_notification("failure"))
    skipped = renderer.render(xo_notification("skipped"))

    with Image.open(BytesIO(success)) as success_image:
        success_size = success_image.size
    with Image.open(BytesIO(failure)) as failure_image:
        failure_size = failure_image.size
    with Image.open(BytesIO(skipped)) as skipped_image:
        skipped_size = skipped_image.size

    assert renderer.WIDTH == 2000
    assert renderer.SUCCESS_BASE_HEIGHT == renderer.EXCEPTION_BASE_HEIGHT
    assert success_size == failure_size == skipped_size


def test_xo_failure_and_skipped_badge_geometry_stays_frozen(tmp_path):
    renderer = XenOrchestraDiscordImageRenderer(tmp_path)
    right = renderer.WIDTH - renderer.CARD_SIDE_PADDING
    header_y = 82
    header_height = 154

    failure = renderer._status_badge_box(
        right,
        header_y,
        header_height,
        status="failure",
    )
    skipped = renderer._status_badge_box(
        right,
        header_y,
        header_height,
        status="skipped",
    )

    expected = (
        right - renderer.STATUS_BADGE_WIDTH,
        header_y,
        right,
        header_y + header_height,
    )
    assert failure == expected
    assert skipped == expected
