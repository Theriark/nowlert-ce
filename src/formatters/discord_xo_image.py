"""Rendered Xen Orchestra Discord Modern notification cards."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from models import Notification
from version import VERSION


class XenOrchestraDiscordImageRenderer:
    """Render Xen Orchestra backup notifications as production PNG cards."""

    WIDTH = 1400
    MARGIN = 26
    CARD_RADIUS = 24
    MAX_VMS = 10

    SUCCESS = (39, 209, 127)
    FAILURE = (255, 77, 95)
    SKIPPED = (63, 169, 245)
    WARNING = (242, 184, 52)

    BG_TOP = (5, 19, 34)
    BG_BOTTOM = (8, 34, 58)
    PANEL = (10, 31, 51, 238)
    PANEL_ALT = (13, 38, 62, 244)
    TEXT = (240, 246, 255)
    MUTED = (169, 190, 214)
    BORDER = (54, 111, 160)

    def __init__(self, icon_dir: Path | str = "/nowlert/assets/icons"):
        self.icon_dir = Path(icon_dir)
        self.regular = self._font(False, 27)
        self.small = self._font(False, 22)
        self.tiny = self._font(False, 19)
        self.bold = self._font(True, 28)
        self.heading = self._font(True, 38)
        self.status_font = self._font(True, 30)
        self.vm_font = self._font(True, 24)

    @staticmethod
    def _font(bold: bool, size: int):
        names = [
            (
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
                if bold
                else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
            ),
            (
                "/usr/share/fonts/dejavu/DejaVuSansCondensed-Bold.ttf"
                if bold
                else "/usr/share/fonts/dejavu/DejaVuSansCondensed.ttf"
            ),
        ]
        for name in names:
            if Path(name).is_file():
                return ImageFont.truetype(name, size=size)
        try:
            return ImageFont.load_default(size=size)
        except TypeError:
            return ImageFont.load_default()

    def render(self, notification: Notification) -> bytes:
        status, accent, status_label = self._status(notification)
        success = list(notification.successful_vms or [])[: self.MAX_VMS]
        failed = list(notification.failed_vms or [])[: self.MAX_VMS]
        skipped = list(notification.skipped_vms or [])[: self.MAX_VMS]

        vm_rows = max(
            1,
            (len(success) + 2) // 3 if not (failed or skipped) else len(success),
            len(failed),
            len(skipped),
        )
        vm_height = 215 + max(0, vm_rows - 1) * 76
        if failed or skipped:
            vm_height = max(250, 185 + vm_rows * 74)
        height = 870 + vm_height

        image = self._gradient(self.WIDTH, height)
        self._glow(image, accent)
        draw = ImageDraw.Draw(image, "RGBA")

        outer = (self.MARGIN, self.MARGIN, self.WIDTH - self.MARGIN, height - self.MARGIN)
        self._rounded(draw, outer, fill=(5, 22, 38, 238), outline=(*self.BORDER, 235), radius=self.CARD_RADIUS, width=2)
        draw.rounded_rectangle(
            (self.MARGIN, self.MARGIN, self.MARGIN + 8, height - self.MARGIN),
            radius=6,
            fill=(*accent, 255),
        )

        x0 = 62
        right = self.WIDTH - 58
        y = 62
        self._draw_server_icon(draw, x0, y + 4)
        draw.text((x0 + 72, y), "Xen Orchestra", font=self.heading, fill=self.TEXT)

        repository = self._clean(notification.repository or "Backup")
        draw.text((x0 + 72, y + 48), repository, font=self.small, fill=self.MUTED)

        self._draw_xo_art(image, right - 80, y + 2)

        badge_w = 430
        badge_x = right - badge_w - 118
        badge = (badge_x, y - 2, badge_x + badge_w, y + 88)
        self._rounded(
            draw,
            badge,
            fill=(*accent, 28),
            outline=(*accent, 190),
            radius=16,
            width=2,
        )
        self._status_square(draw, badge_x + 18, y + 16, accent, status)
        draw.text((badge_x + 70, y + 11), status_label, font=self.status_font, fill=accent)
        job = self._clean(
            notification.job_name
            or notification.title
            or notification.subject
            or "Xen Orchestra backup"
        )
        self._fit_text(draw, job, badge_x + 70, y + 52, badge_w - 88, self.small, self.TEXT)

        y = 176
        title_h = 72
        self._rounded(
            draw,
            (x0, y, right, y + title_h),
            fill=(25, 54, 93, 210),
            outline=(78, 122, 189, 175),
            radius=13,
            width=2,
        )
        report = self._clean(
            notification.subject
            or notification.body
            or f"Backup report for {job}"
        )
        self._fit_text(draw, report, x0 + 24, y + 18, right - x0 - 48, self.bold, self.TEXT)

        y += 92
        metrics_h = 68
        self._rounded(
            draw,
            (x0, y, right, y + metrics_h),
            fill=self.PANEL,
            outline=(*self.BORDER, 145),
            radius=13,
            width=1,
        )
        category = self._label(notification.category or "backup")
        event_time = self._clean(notification.end_time or notification.start_time or "")
        metric_items = [
            (status, "Severity", status_label.replace("Backup ", ""), accent),
            ("C", "Category", category, (58, 159, 239)),
            ("T", "Event time", event_time, (126, 190, 236)),
        ]
        mx = x0 + 24
        widths = [350, 350, right - x0 - 748]
        for index, ((symbol, label, value, color), width) in enumerate(zip(metric_items, widths)):
            self._mini_icon(draw, mx, y + 16, symbol, color)
            draw.text((mx + 48, y + 17), f"{label}:", font=self.bold, fill=self.TEXT)
            label_w = draw.textlength(f"{label}:", font=self.bold)
            self._fit_text(
                draw,
                value,
                mx + 55 + label_w,
                y + 19,
                width - 68 - label_w,
                self.small,
                self.TEXT,
            )
            if index < 2:
                line_x = mx + width - 16
                draw.line((line_x, y + 15, line_x, y + metrics_h - 15), fill=(91, 126, 157, 120), width=1)
            mx += width

        y += 90
        details_h = 248
        gap = 20
        half = (right - x0 - gap) // 2
        left_box = (x0, y, x0 + half, y + details_h)
        right_box = (x0 + half + gap, y, right, y + details_h)
        self._rounded(draw, left_box, fill=self.PANEL_ALT, outline=(*self.BORDER, 165), radius=16, width=2)
        self._rounded(draw, right_box, fill=self.PANEL_ALT, outline=(*self.BORDER, 165), radius=16, width=2)

        duration = self._short_duration(notification.duration)
        result = self._result_text(notification)
        left_rows = [
            ("M", "Mode", notification.mode),
            ("D", "Duration", duration),
            ("S", "Transfer size", notification.transfer_size),
            ("V", "Speed", notification.transfer_speed),
        ]
        right_rows = [
            ("R", "Repository", notification.repository),
            ("P", "Started", notification.start_time),
            ("F", "Finished", notification.end_time),
            ("G", "Result", result),
        ]
        self._detail_rows(draw, left_box, left_rows)
        self._detail_rows(draw, right_box, right_rows)

        y += details_h + 24
        vm_bottom = height - 78
        if failed:
            self._paired_vm_panels(
                draw,
                (x0, y, right, vm_bottom),
                success,
                failed,
                "FAILED VM" if len(failed) == 1 else "FAILED VMS",
                self.FAILURE,
                notification,
            )
        elif skipped:
            self._paired_vm_panels(
                draw,
                (x0, y, right, vm_bottom),
                success,
                skipped,
                "SKIPPED VM" if len(skipped) == 1 else "SKIPPED VMS",
                self.WARNING,
                notification,
            )
        else:
            self._success_panel(
                draw,
                (x0, y, right, vm_bottom),
                success,
                notification,
            )

        footer_y = height - 58
        draw.line((x0, footer_y - 10, right, footer_y - 10), fill=(83, 118, 151, 140), width=1)
        draw.text((x0 + 8, footer_y), f"Theriark - Nowlert v{VERSION}", font=self.tiny, fill=self.MUTED)
        footer = "Xen Orchestra Notification"
        footer_w = draw.textlength(footer, font=self.tiny)
        draw.text((right - footer_w - 6, footer_y), footer, font=self.tiny, fill=self.MUTED)

        output = BytesIO()
        image.convert("RGB").save(output, format="PNG", optimize=True, compress_level=7)
        return output.getvalue()

    def _success_panel(self, draw, box, names, notification):
        self._rounded(draw, box, fill=(4, 70, 58, 195), outline=(*self.SUCCESS, 220), radius=16, width=2)
        x1, y1, x2, _y2 = box
        self._status_square(draw, x1 + 22, y1 + 20, self.SUCCESS, "success", size=42)
        draw.text((x1 + 78, y1 + 23), f"SUCCESSFUL VMS ({len(names)})", font=self.bold, fill=(75, 238, 181))
        if not names:
            draw.text((x1 + 28, y1 + 90), "No VM details reported.", font=self.small, fill=self.MUTED)
            return
        columns = 3
        col_w = (x2 - x1 - 48) // columns
        for index, name in enumerate(names):
            row = index // columns
            col = index % columns
            cx = x1 + 24 + col * col_w
            cy = y1 + 82 + row * 112
            if col:
                draw.line((cx - 12, cy - 5, cx - 12, cy + 88), fill=(35, 173, 133, 110), width=1)
            self._vm(draw, cx, cy, col_w - 24, name, notification, self.SUCCESS)

    def _paired_vm_panels(self, draw, box, success, other, other_title, other_color, notification):
        x1, y1, x2, y2 = box
        gap = 18
        left_w = int((x2 - x1 - gap) * 0.58)
        left = (x1, y1, x1 + left_w, y2)
        right = (x1 + left_w + gap, y1, x2, y2)
        self._rounded(draw, left, fill=(4, 70, 58, 190), outline=(*self.SUCCESS, 210), radius=16, width=2)
        self._rounded(draw, right, fill=(*other_color, 27), outline=(*other_color, 220), radius=16, width=2)
        draw.text((left[0] + 22, y1 + 22), f"SUCCESSFUL VMS ({len(success)})", font=self.bold, fill=(75, 238, 181))
        draw.text((right[0] + 22, y1 + 22), f"{other_title} ({len(other)})", font=self.bold, fill=other_color)
        for index, name in enumerate(success):
            self._vm(draw, left[0] + 22, y1 + 72 + index * 86, left_w - 44, name, notification, self.SUCCESS)
        for index, name in enumerate(other):
            self._vm(
                draw,
                right[0] + 22,
                y1 + 72 + index * 108,
                right[2] - right[0] - 44,
                name,
                notification,
                other_color,
                include_reason=True,
            )

    def _vm(self, draw, x, y, width, name, notification, color, include_reason=False):
        detail = (notification.vm_details or {}).get(name, {}) or {}
        self._mini_icon(draw, x, y, "V", color, size=31)
        self._fit_text(draw, self._clean(name), x + 42, y + 1, width - 44, self.vm_font, self.TEXT)
        facts = []
        if detail.get("size"):
            facts.append(self._clean(detail["size"]))
        if detail.get("speed"):
            facts.append(self._clean(detail["speed"]))
        if facts:
            self._fit_text(draw, "   |   ".join(facts), x + 42, y + 35, width - 44, self.tiny, self.MUTED)
        if include_reason and detail.get("error"):
            self._fit_text(draw, self._clean(detail["error"]), x + 42, y + 64, width - 44, self.tiny, color)

    def _detail_rows(self, draw, box, rows):
        x1, y1, x2, _ = box
        y = y1 + 22
        for symbol, label, value in rows:
            if value is None or str(value).strip() == "":
                y += 52
                continue
            self._mini_icon(draw, x1 + 20, y, symbol, (98, 181, 230), size=30)
            draw.text((x1 + 62, y + 1), label, font=self.bold, fill=self.MUTED)
            label_width = 170
            self._fit_text(
                draw,
                self._clean(value),
                x1 + 62 + label_width,
                y + 4,
                x2 - (x1 + 62 + label_width) - 20,
                self.tiny,
                self.TEXT,
            )
            y += 54

    def _draw_xo_art(self, image, x, y):
        path = self.icon_dir / "discord" / "xen-orchestra.png"
        if path.is_file():
            try:
                icon = Image.open(path).convert("RGBA")
                icon.thumbnail((92, 92), Image.Resampling.LANCZOS)
                image.alpha_composite(icon, (int(x), int(y)))
                return
            except OSError:
                pass
        draw = ImageDraw.Draw(image, "RGBA")
        draw.polygon([(x + 42, y), (x + 68, y + 30), (x + 42, y + 60), (x + 16, y + 30)], fill=(105, 84, 255, 245))
        draw.rectangle((x, y + 24, x + 24, y + 36), fill=(245, 218, 89, 245))
        draw.rectangle((x + 60, y + 24, x + 84, y + 36), fill=(245, 218, 89, 245))

    def _draw_server_icon(self, draw, x, y):
        self._rounded(draw, (x, y, x + 56, y + 56), fill=(12, 56, 82, 230), outline=(72, 152, 204, 180), radius=10, width=2)
        for offset in (12, 31):
            draw.rounded_rectangle((x + 12, y + offset, x + 44, y + offset + 12), radius=3, fill=(99, 156, 186, 220))
            draw.rectangle((x + 18, y + offset + 4, x + 35, y + offset + 7), fill=(226, 243, 251, 240))

    def _status_square(self, draw, x, y, color, status, size=44):
        self._rounded(draw, (x, y, x + size, y + size), fill=(*color, 235), outline=(*color, 255), radius=9, width=1)
        mark = "✓" if status == "success" else ("×" if status == "failure" else "i")
        font = self._font(True, int(size * 0.64))
        bbox = draw.textbbox((0, 0), mark, font=font)
        tx = x + (size - (bbox[2] - bbox[0])) / 2
        ty = y + (size - (bbox[3] - bbox[1])) / 2 - 2
        draw.text((tx, ty), mark, font=font, fill=(255, 255, 255))

    def _mini_icon(self, draw, x, y, symbol, color, size=34):
        self._rounded(draw, (x, y, x + size, y + size), fill=(*color, 220), outline=(*color, 255), radius=7, width=1)
        font = self._font(True, max(14, int(size * 0.50)))
        label = str(symbol)[:1].upper()
        bbox = draw.textbbox((0, 0), label, font=font)
        draw.text(
            (
                x + (size - (bbox[2] - bbox[0])) / 2,
                y + (size - (bbox[3] - bbox[1])) / 2 - 1,
            ),
            label,
            font=font,
            fill=(255, 255, 255),
        )

    def _fit_text(self, draw, value, x, y, width, font, fill):
        text = self._clean(value)
        if draw.textlength(text, font=font) <= width:
            draw.text((x, y), text, font=font, fill=fill)
            return
        ellipsis = "…"
        while text and draw.textlength(text + ellipsis, font=font) > width:
            text = text[:-1]
        draw.text((x, y), (text.rstrip() + ellipsis) if text else ellipsis, font=font, fill=fill)

    @staticmethod
    def _clean(value):
        return " ".join(str(value or "").replace("\r", " ").replace("\n", " ").split())

    @staticmethod
    def _label(value):
        return str(value or "").replace("_", " ").strip().title()

    @staticmethod
    def _short_duration(value):
        text = str(value or "")
        return (
            text.replace(" minutes", " min")
            .replace(" minute", " min")
            .replace(" seconds", " sec")
            .replace(" second", " sec")
        )

    @classmethod
    def _status(cls, notification):
        value = str(notification.status or "").strip().casefold()
        if value in {"failure", "failed", "error", "critical"} or notification.vm_failed:
            return "failure", cls.FAILURE, "Backup Failure"
        if value in {"skipped", "warning"} or notification.vm_skipped:
            return "skipped", cls.SKIPPED, "Backup Skipped"
        return "success", cls.SUCCESS, "Backup Successful"

    @staticmethod
    def _result_text(notification):
        success = notification.vm_success or notification.successes
        failed = notification.vm_failed or notification.failures
        skipped = notification.vm_skipped or notification.skipped
        total = notification.vm_total or success + failed + skipped
        if not total:
            return ""
        parts = [f"{success} of {total} VMs successful"]
        if failed:
            parts.append(f"{failed} failed")
        if skipped:
            parts.append(f"{skipped} skipped")
        return "  |  ".join(parts)

    @classmethod
    def _gradient(cls, width, height):
        strip = Image.new("RGBA", (1, height), (*cls.BG_TOP, 255))
        pixels = strip.load()
        for y in range(height):
            ratio = y / max(height - 1, 1)
            color = tuple(
                int(cls.BG_TOP[i] * (1 - ratio) + cls.BG_BOTTOM[i] * ratio)
                for i in range(3)
            )
            pixels[0, y] = (*color, 255)
        return strip.resize((width, height))

    def _glow(self, image, accent):
        glow = Image.new("RGBA", image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(glow, "RGBA")
        draw.rounded_rectangle(
            (self.MARGIN - 4, self.MARGIN - 4, self.WIDTH - self.MARGIN + 4, image.height - self.MARGIN + 4),
            radius=self.CARD_RADIUS + 6,
            outline=(*accent, 125),
            width=8,
        )
        glow = glow.filter(ImageFilter.GaussianBlur(16))
        image.alpha_composite(glow)

    @staticmethod
    def _rounded(draw, box, *, fill, outline, radius, width):
        draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)
