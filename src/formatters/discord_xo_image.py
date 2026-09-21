"""Rendered Xen Orchestra Discord Modern notification cards."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from models import Notification


class XenOrchestraDiscordImageRenderer:
    """Render XO backup notifications with the approved Nowlert visual system."""

    WIDTH = 1448
    BASE_HEIGHT = 1086
    MAX_VMS = 10

    VM_PANEL_TOP = 682
    VM_HEADER_HEIGHT = 92
    VM_PANEL_BOTTOM_PADDING = 28
    VM_ENTRY_HEIGHT = 122
    VM_ENTRY_REASON_HEIGHT = 166
    SUCCESS_ROW_HEIGHT = 122
    FOOTER_GAP = 26
    FOOTER_RESERVE = 88
    FOOTER_TEXT = "Nowlert CE • Modern Card"
    DETAIL_SPLIT_RATIO = 0.43
    DETAIL_LABEL_OFFSET = 84
    DETAIL_VALUE_OFFSET = 260
    STATUS_BADGE_WIDTH = 420

    # Nowlert brand surfaces.
    PAGE_BG = (18, 24, 29)
    CARD_BG = (8, 12, 15)
    CARD_BG_2 = (12, 16, 19)
    PANEL = (23, 27, 30)
    PANEL_2 = (28, 32, 35)
    PANEL_BORDER = (66, 72, 77)
    BRAND_GOLD = (244, 193, 49)
    TEXT = (246, 241, 232)
    MUTED = (183, 194, 202)
    LABEL = (166, 196, 224)

    SUCCESS = (22, 214, 115)
    FAILURE = (255, 64, 72)
    SKIPPED = (37, 166, 238)
    ICON_BLUE = (45, 163, 232)
    VM_ORANGE = (239, 111, 48)

    def __init__(self, icon_dir: Path | str = "/nowlert/assets/icons"):
        self.icon_dir = Path(icon_dir)
        self.font_micro = self._font(False, 16)
        self.font_tiny = self._font(False, 18)
        self.font_small = self._font(False, 21)
        self.font_body = self._font(False, 24)
        self.font_label = self._font(True, 24)
        self.font_vm = self._font(True, 25)
        self.font_bold = self._font(True, 29)
        self.font_title = self._font(True, 34)
        self.font_heading = self._font(True, 42)

    @staticmethod
    def _font(bold: bool, size: int):
        candidates = [
            (
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
                if bold
                else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
            ),
            (
                "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf"
                if bold
                else "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf"
            ),
        ]
        for candidate in candidates:
            if Path(candidate).is_file():
                return ImageFont.truetype(candidate, size=size)
        try:
            return ImageFont.load_default(size=size)
        except TypeError:
            return ImageFont.load_default()

    def render(self, notification: Notification) -> bytes:
        status, accent, status_label = self._status(notification)
        successful = list(notification.successful_vms or [])[: self.MAX_VMS]
        failed = list(notification.failed_vms or [])[: self.MAX_VMS]
        skipped = list(notification.skipped_vms or [])[: self.MAX_VMS]

        vm_panel_height = self._vm_panel_height(
            notification,
            successful,
            failed,
            skipped,
        )
        height = max(
            self.BASE_HEIGHT,
            (
                self.VM_PANEL_TOP
                + vm_panel_height
                + self.FOOTER_GAP
                + self.FOOTER_RESERVE
            ),
        )
        footer_y = height - self.FOOTER_RESERVE

        image = self._background(self.WIDTH, height)
        self._outer_glows(image, accent, height)
        draw = ImageDraw.Draw(image, "RGBA")

        card = (30, 38, self.WIDTH - 30, height - 38)
        self._rounded(
            draw,
            card,
            fill=(*self.CARD_BG, 247),
            outline=(*self.PANEL_BORDER, 220),
            radius=28,
            width=2,
        )
        self._draw_status_rail(draw, accent, height)
        self._draw_gold_frame(draw, card)

        x0 = 70
        right = self.WIDTH - 70

        # Header.
        header_y = 75
        xo_icon_size = 86
        self._draw_xo_art(
            image,
            x0,
            header_y + 1,
            size=xo_icon_size,
        )
        title_x = x0 + xo_icon_size + 18
        draw.text(
            (title_x, header_y + 4),
            "Xen Orchestra",
            font=self.font_heading,
            fill=self.TEXT,
        )
        repository = self._clean(notification.repository or "Backup")
        self._fit_text_adaptive(
            draw,
            repository,
            title_x,
            header_y + 58,
            610,
            (self.font_body, self.font_small, self.font_tiny),
            self.MUTED,
        )

        badge_w = self.STATUS_BADGE_WIDTH
        badge_h = 82
        badge_x = right - badge_w
        badge = (
            badge_x,
            header_y + 3,
            right,
            header_y + 3 + badge_h,
        )
        self._glow_box(image, badge, accent, 17, alpha=86)
        draw = ImageDraw.Draw(image, "RGBA")
        self._rounded(
            draw,
            badge,
            fill=(*self._tint(accent, self.CARD_BG, 0.16), 245),
            outline=(*accent, 225),
            radius=17,
            width=2,
        )
        self._status_icon(
            draw,
            badge_x + 22,
            header_y + 20,
            48,
            status,
            accent,
        )
        self._fit_text_adaptive(
            draw,
            status_label,
            badge_x + 88,
            header_y + 23,
            badge_w - 112,
            (self.font_bold, self.font_label, self.font_small),
            accent if status != "success" else (103, 239, 174),
        )
        job = self._clean(
            notification.job_name
            or notification.title
            or notification.subject
            or "Xen Orchestra backup"
        )

        # Report title bar.
        title_y = 210
        title_box = (x0, title_y, right, title_y + 76)
        self._rounded(
            draw,
            title_box,
            fill=(*self.PANEL_2, 248),
            outline=(93, 101, 108, 190),
            radius=14,
            width=2,
        )
        report = self._clean(
            notification.subject
            or notification.body
            or f"Backup report for {job}"
        )
        self._fit_text(
            draw,
            report,
            x0 + 30,
            title_y + 18,
            right - x0 - 60,
            self.font_title,
            self.TEXT,
        )

        # Summary strip.
        metric_y = 306
        metric_h = 72
        metric_box = (x0, metric_y, right, metric_y + metric_h)
        self._rounded(
            draw,
            metric_box,
            fill=(*self.PANEL, 248),
            outline=(*self.PANEL_BORDER, 200),
            radius=14,
            width=1,
        )
        event_time = self._clean(notification.end_time or notification.start_time or "")
        category = self._label(notification.category or "backup")
        metrics = [
            ("status", "Severity", status_label.replace("Backup ", ""), accent),
            ("sync", "Category", category, self.ICON_BLUE),
            ("clock", "Event time", event_time, (194, 226, 242)),
        ]
        widths = [350, 350, right - x0 - 700]
        mx = x0 + 26
        for index, ((icon, label, value, color), width) in enumerate(
            zip(metrics, widths)
        ):
            self._draw_icon_badge(
                draw,
                mx,
                metric_y + 14,
                44,
                icon,
                color,
                status=status,
            )
            label_x = mx + 60
            draw.text(
                (label_x, metric_y + 20),
                f"{label}:",
                font=self.font_label,
                fill=self.TEXT,
            )
            label_w = draw.textlength(f"{label}:", font=self.font_label)
            self._fit_text(
                draw,
                value,
                label_x + label_w + 10,
                metric_y + 22,
                width - 78 - label_w,
                self.font_small,
                self.TEXT,
            )
            if index < 2:
                line_x = mx + width - 8
                draw.line(
                    (line_x, metric_y + 18, line_x, metric_y + metric_h - 18),
                    fill=(102, 112, 119, 160),
                    width=2,
                )
            mx += width

        # Detail panels.
        detail_y = 400
        detail_h = 262
        gap = 22
        detail_width = right - x0 - gap
        left_width = int(detail_width * self.DETAIL_SPLIT_RATIO)
        left_box = (x0, detail_y, x0 + left_width, detail_y + detail_h)
        right_box = (
            x0 + left_width + gap,
            detail_y,
            right,
            detail_y + detail_h,
        )
        for box in (left_box, right_box):
            self._rounded(
                draw,
                box,
                fill=(*self.PANEL_2, 248),
                outline=(*self.PANEL_BORDER, 205),
                radius=15,
                width=2,
            )

        left_rows = [
            ("list", "Mode", notification.mode),
            ("clock", "Duration", self._short_duration(notification.duration)),
            ("cube", "Transfer size", notification.transfer_size),
            ("rocket", "Speed", notification.transfer_speed),
        ]
        right_rows = [
            ("repository", "Repository", notification.repository),
            ("play", "Started", notification.start_time),
            ("flag", "Finished", notification.end_time),
            ("chart", "Result", self._result_text(notification)),
        ]
        self._detail_rows(
            draw,
            left_box,
            left_rows,
            result_status=None,
        )
        self._detail_rows(
            draw,
            right_box,
            right_rows,
            result_status=status,
        )

        # VM outcome panels. The footer follows the content instead of
        # imposing a fixed card height, so additional VMs and reasons never
        # escape the card.
        vm_y = self.VM_PANEL_TOP
        vm_bottom = footer_y - self.FOOTER_GAP
        if failed:
            self._paired_vm_panels(
                image,
                draw,
                (x0, vm_y, right, vm_bottom),
                successful,
                failed,
                "FAILED VM" if len(failed) == 1 else "FAILED VMS",
                self.FAILURE,
                notification,
                "failure",
            )
        elif skipped:
            self._paired_vm_panels(
                image,
                draw,
                (x0, vm_y, right, vm_bottom),
                successful,
                skipped,
                "SKIPPED VM" if len(skipped) == 1 else "SKIPPED VMS",
                self.SKIPPED,
                notification,
                "skipped",
            )
        else:
            self._success_panel(
                image,
                draw,
                (x0, vm_y, right, vm_bottom),
                successful,
                notification,
            )

        # Footer: Nowlert product identity only; the integration is already
        # identified in the card header and does not need to be repeated here.
        draw.line(
            (x0, footer_y - 8, right, footer_y - 8),
            fill=(81, 89, 95, 150),
            width=1,
        )
        icon_size = 48
        icon_x = right - icon_size
        footer_w = draw.textlength(self.FOOTER_TEXT, font=self.font_small)
        draw.text(
            (icon_x - footer_w - 18, footer_y + 12),
            self.FOOTER_TEXT,
            font=self.font_small,
            fill=self.MUTED,
        )
        self._draw_nowlert_icon(
            image,
            icon_x,
            footer_y - 1,
            icon_size,
        )

        output = BytesIO()
        image.convert("RGB").save(
            output,
            format="PNG",
            optimize=True,
            compress_level=7,
        )
        return output.getvalue()

    def _vm_panel_height(
        self,
        notification,
        successful,
        failed,
        skipped,
    ) -> int:
        """Return the minimum VM panel height required by its real content."""

        if failed or skipped:
            other = failed or skipped
            successful_height = self._vm_column_height(
                notification,
                successful,
                include_reason=False,
            )
            other_height = self._vm_column_height(
                notification,
                other,
                include_reason=True,
            )
            content_height = max(successful_height, other_height)
            return max(
                250,
                (
                    self.VM_HEADER_HEIGHT
                    + content_height
                    + self.VM_PANEL_BOTTOM_PADDING
                ),
            )

        rows = max(1, (len(successful) + 2) // 3)
        return max(
            250,
            (
                self.VM_HEADER_HEIGHT
                + rows * self.SUCCESS_ROW_HEIGHT
                + self.VM_PANEL_BOTTOM_PADDING
            ),
        )

    def _vm_column_height(
        self,
        notification,
        names,
        *,
        include_reason: bool,
    ) -> int:
        """Measure a vertical VM column before allocating the image canvas."""

        if not names:
            return 80
        return sum(
            self._vm_entry_height(
                notification,
                name,
                include_reason=include_reason,
            )
            for name in names
        )

    def _vm_entry_height(
        self,
        notification,
        name,
        *,
        include_reason: bool,
    ) -> int:
        detail = (notification.vm_details or {}).get(name, {}) or {}
        if include_reason and self._clean(detail.get("error") or ""):
            return self.VM_ENTRY_REASON_HEIGHT
        return self.VM_ENTRY_HEIGHT

    def _detail_rows(self, draw, box, rows, *, result_status):
        x1, y1, x2, _ = box
        y = y1 + 28
        label_x = x1 + self.DETAIL_LABEL_OFFSET
        value_x = x1 + self.DETAIL_VALUE_OFFSET
        for _index, (icon, label, value) in enumerate(rows):
            if value is None or str(value).strip() == "":
                y += 55
                continue
            self._draw_field_icon(draw, x1 + 24, y - 3, 40, icon)
            draw.text(
                (label_x, y + 1),
                label,
                font=self.font_label,
                fill=self.LABEL,
            )
            available = x2 - value_x - 22
            if label == "Result" and result_status:
                result_color = {
                    "success": self.SUCCESS,
                    "failure": self.FAILURE,
                    "skipped": self.SKIPPED,
                }.get(result_status, self.SUCCESS)
                status_size = 34
                self._draw_icon_badge(
                    draw,
                    value_x,
                    y - 2,
                    status_size,
                    "status",
                    result_color,
                    status=result_status,
                )
                self._fit_text_adaptive(
                    draw,
                    self._clean(value),
                    value_x + status_size + 10,
                    y + 3,
                    available - status_size - 10,
                    (
                        self.font_small,
                        self.font_tiny,
                        self.font_micro,
                    ),
                    self.TEXT,
                )
            else:
                self._fit_text_adaptive(
                    draw,
                    self._clean(value),
                    value_x,
                    y + 3,
                    available,
                    (
                        self.font_small,
                        self.font_tiny,
                        self.font_micro,
                    ),
                    self.TEXT,
                )
            y += 55

    def _success_panel(self, image, draw, box, names, notification):
        self._glow_box(image, box, self.SUCCESS, 18, alpha=58)
        draw = ImageDraw.Draw(image, "RGBA")
        self._rounded(
            draw,
            box,
            fill=(0, 61, 49, 226),
            outline=(*self.SUCCESS, 230),
            radius=17,
            width=2,
        )
        x1, y1, x2, _ = box
        self._status_icon(draw, x1 + 26, y1 + 18, 48, "success", self.SUCCESS)
        draw.text(
            (x1 + 88, y1 + 25),
            f"SUCCESSFUL VMS ({len(names)})",
            font=self.font_bold,
            fill=(92, 242, 190),
        )
        if not names:
            draw.text(
                (x1 + 32, y1 + 98),
                "No VM details reported.",
                font=self.font_small,
                fill=self.MUTED,
            )
            return

        columns = 3
        col_w = (x2 - x1 - 50) // columns
        for index, name in enumerate(names):
            row = index // columns
            col = index % columns
            cx = x1 + 26 + col * col_w
            cy = y1 + 93 + row * self.SUCCESS_ROW_HEIGHT
            if col:
                divider_x = cx - 16
                draw.line(
                    (divider_x, cy - 4, divider_x, cy + 92),
                    fill=(42, 183, 132, 150),
                    width=1,
                )
            self._vm_entry(
                draw,
                cx,
                cy,
                col_w - 30,
                name,
                notification,
                self.SUCCESS,
                include_reason=False,
            )

    def _paired_vm_panels(
        self,
        image,
        draw,
        box,
        successful,
        other,
        other_title,
        other_color,
        notification,
        other_status,
    ):
        x1, y1, x2, y2 = box
        gap = 18
        left_w = int((x2 - x1 - gap) * 0.55)
        left = (x1, y1, x1 + left_w, y2)
        right = (x1 + left_w + gap, y1, x2, y2)

        self._glow_box(image, left, self.SUCCESS, 15, alpha=48)
        self._glow_box(image, right, other_color, 18, alpha=58)
        draw = ImageDraw.Draw(image, "RGBA")

        self._rounded(
            draw,
            left,
            fill=(0, 61, 49, 226),
            outline=(*self.SUCCESS, 225),
            radius=17,
            width=2,
        )
        other_fill = (
            (56, 17, 23, 232)
            if other_status == "failure"
            else (11, 50, 75, 232)
        )
        self._rounded(
            draw,
            right,
            fill=other_fill,
            outline=(*other_color, 230),
            radius=17,
            width=2,
        )

        self._status_icon(
            draw,
            left[0] + 26,
            y1 + 18,
            48,
            "success",
            self.SUCCESS,
        )
        draw.text(
            (left[0] + 88, y1 + 25),
            f"SUCCESSFUL VMS ({len(successful)})",
            font=self.font_bold,
            fill=(92, 242, 190),
        )

        self._status_icon(
            draw,
            right[0] + 26,
            y1 + 18,
            48,
            other_status,
            other_color,
        )
        draw.text(
            (right[0] + 88, y1 + 25),
            f"{other_title} ({len(other)})",
            font=self.font_bold,
            fill=(
                (255, 122, 134)
                if other_status == "failure"
                else (94, 202, 255)
            ),
        )

        success_y = y1 + self.VM_HEADER_HEIGHT
        for name in successful:
            self._vm_entry(
                draw,
                left[0] + 28,
                success_y,
                left[2] - left[0] - 56,
                name,
                notification,
                self.SUCCESS,
                include_reason=False,
            )
            success_y += self._vm_entry_height(
                notification,
                name,
                include_reason=False,
            )

        other_y = y1 + self.VM_HEADER_HEIGHT
        for name in other:
            self._vm_entry(
                draw,
                right[0] + 28,
                other_y,
                right[2] - right[0] - 56,
                name,
                notification,
                other_color,
                include_reason=True,
                reason_status=other_status,
            )
            other_y += self._vm_entry_height(
                notification,
                name,
                include_reason=True,
            )

    def _vm_entry(
        self,
        draw,
        x,
        y,
        width,
        name,
        notification,
        color,
        *,
        include_reason,
        reason_status=None,
    ):
        detail = (notification.vm_details or {}).get(name, {}) or {}
        self._draw_field_icon(draw, x, y - 2, 42, "cube")
        self._fit_text(
            draw,
            self._clean(name),
            x + 58,
            y,
            width - 58,
            self.font_vm,
            self.TEXT,
        )

        size = self._clean(detail.get("size") or "")
        speed = self._clean(detail.get("speed") or "")
        if size:
            self._draw_field_icon(draw, x + 58, y + 43, 30, "disk")
            self._fit_text(
                draw,
                size,
                x + 98,
                y + 44,
                width - 98,
                self.font_small,
                self.MUTED,
            )
        if speed:
            self._draw_field_icon(draw, x + 58, y + 76, 30, "rocket")
            self._fit_text(
                draw,
                speed,
                x + 98,
                y + 77,
                width - 98,
                self.font_small,
                self.MUTED,
            )

        if include_reason and detail.get("error"):
            reason_color = (
                self.FAILURE
                if reason_status == "failure"
                else (108, 204, 255)
            )
            self._draw_field_icon(
                draw,
                x + 58,
                y + 109,
                30,
                "alert" if reason_status == "failure" else "info",
            )
            self._wrap_text(
                draw,
                self._clean(detail["error"]),
                x + 98,
                y + 108,
                width - 98,
                self.font_tiny,
                reason_color,
                max_lines=2,
                line_gap=3,
            )

    def _draw_server_rack(self, draw, x, y):
        box = (x, y, x + 86, y + 86)
        self._rounded(
            draw,
            box,
            fill=(23, 25, 23, 242),
            outline=(*self.BRAND_GOLD, 165),
            radius=15,
            width=2,
        )
        for offset in (18, 49):
            drawer = (x + 22, y + offset, x + 64, y + offset + 18)
            self._rounded(
                draw,
                drawer,
                fill=(75, 74, 62, 245),
                outline=(124, 120, 95, 220),
                radius=4,
                width=1,
            )
            draw.rectangle(
                (x + 30, y + offset + 6, x + 52, y + offset + 10),
                fill=(232, 224, 192, 245),
            )
            draw.ellipse(
                (x + 56, y + offset + 7, x + 60, y + offset + 11),
                fill=(*self.BRAND_GOLD, 255),
            )

    def _draw_xo_art(self, image, x, y, *, size=92):
        path = self.icon_dir / "discord" / "xen-orchestra.png"
        if path.is_file():
            try:
                icon = Image.open(path).convert("RGBA")
                icon.thumbnail((size, size), Image.Resampling.LANCZOS)
                px = int(x + (size - icon.width) / 2)
                py = int(y + (size - icon.height) / 2)
                image.alpha_composite(icon, (px, py))
                return
            except OSError:
                pass
        draw = ImageDraw.Draw(image, "RGBA")
        scale = size / 92
        draw.polygon(
            [
                (x + 44 * scale, y),
                (x + 70 * scale, y + 31 * scale),
                (x + 44 * scale, y + 62 * scale),
                (x + 18 * scale, y + 31 * scale),
            ],
            fill=(105, 84, 255, 245),
        )
        draw.rectangle(
            (
                x,
                y + 24 * scale,
                x + 26 * scale,
                y + 38 * scale,
            ),
            fill=(248, 219, 76, 245),
        )
        draw.rectangle(
            (
                x + 62 * scale,
                y + 24 * scale,
                x + 88 * scale,
                y + 38 * scale,
            ),
            fill=(248, 219, 76, 245),
        )

    def _draw_icon_badge(self, draw, x, y, size, icon, color, *, status=None):
        self._rounded(
            draw,
            (x, y, x + size, y + size),
            fill=(*color, 238),
            outline=(*color, 255),
            radius=max(7, size // 5),
            width=1,
        )
        if icon == "status":
            self._draw_status_mark(
                draw,
                x,
                y,
                size,
                status or "success",
                (255, 255, 255),
            )
            return
        if icon == "sync":
            self._draw_sync(draw, x, y, size)
            return
        if icon == "clock":
            self._draw_clock(draw, x, y, size, fg=(255, 255, 255))
            return

    def _status_icon(self, draw, x, y, size, status, color):
        self._rounded(
            draw,
            (x, y, x + size, y + size),
            fill=(*color, 245),
            outline=(*color, 255),
            radius=max(8, size // 5),
            width=1,
        )
        self._draw_status_mark(
            draw,
            x,
            y,
            size,
            status,
            (255, 255, 255),
        )

    @staticmethod
    def _draw_status_mark(draw, x, y, size, status, fg):
        if status == "success":
            points = [
                (x + size * 0.23, y + size * 0.53),
                (x + size * 0.42, y + size * 0.72),
                (x + size * 0.77, y + size * 0.30),
            ]
            draw.line(points, fill=(*fg, 255), width=max(3, size // 9), joint="curve")
        elif status == "failure":
            margin = size * 0.28
            draw.line(
                (x + margin, y + margin, x + size - margin, y + size - margin),
                fill=(*fg, 255),
                width=max(3, size // 9),
            )
            draw.line(
                (x + size - margin, y + margin, x + margin, y + size - margin),
                fill=(*fg, 255),
                width=max(3, size // 9),
            )
        else:
            cx = x + size / 2
            draw.ellipse(
                (cx - size * 0.06, y + size * 0.20, cx + size * 0.06, y + size * 0.32),
                fill=(*fg, 255),
            )
            draw.rounded_rectangle(
                (cx - size * 0.06, y + size * 0.40, cx + size * 0.06, y + size * 0.76),
                radius=max(1, size // 18),
                fill=(*fg, 255),
            )

    def _draw_field_icon(self, draw, x, y, size, icon):
        if icon == "cube":
            self._draw_cube(draw, x, y, size)
        elif icon == "rocket":
            self._draw_rocket(draw, x, y, size)
        elif icon == "clock":
            self._draw_clock(draw, x, y, size)
        elif icon == "list":
            self._draw_list(draw, x, y, size)
        elif icon == "repository":
            self._draw_repository(draw, x, y, size)
        elif icon == "play":
            self._draw_play(draw, x, y, size)
        elif icon == "flag":
            self._draw_flag(draw, x, y, size)
        elif icon == "chart":
            self._draw_chart(draw, x, y, size)
        elif icon == "disk":
            self._draw_disk(draw, x, y, size)
        elif icon == "alert":
            self._draw_alert(draw, x, y, size)
        elif icon == "info":
            self._draw_info(draw, x, y, size)
        else:
            self._draw_list(draw, x, y, size)

    def _draw_list(self, draw, x, y, size):
        fg = (215, 236, 248)
        draw.rounded_rectangle(
            (x + 5, y + 3, x + size - 5, y + size - 3),
            radius=5,
            outline=(*fg, 255),
            width=max(2, size // 10),
        )
        for row in (0.30, 0.50, 0.70):
            yy = y + size * row
            draw.line(
                (x + size * 0.32, yy, x + size * 0.72, yy),
                fill=(*fg, 255),
                width=max(2, size // 12),
            )
            draw.ellipse(
                (x + size * 0.18, yy - 2, x + size * 0.24, yy + 2),
                fill=(*self.ICON_BLUE, 255),
            )

    def _draw_clock(self, draw, x, y, size, fg=None):
        color = fg or (222, 239, 247)
        pad = max(4, size // 9)
        draw.ellipse(
            (x + pad, y + pad, x + size - pad, y + size - pad),
            fill=(227, 242, 248, 245) if fg is None else None,
            outline=(*color, 255),
            width=max(2, size // 11),
        )
        cx = x + size / 2
        cy = y + size / 2
        draw.line(
            (cx, cy, cx, y + size * 0.29),
            fill=(*((74, 110, 137) if fg is None else color), 255),
            width=max(2, size // 12),
        )
        draw.line(
            (cx, cy, x + size * 0.68, y + size * 0.57),
            fill=(*((74, 110, 137) if fg is None else color), 255),
            width=max(2, size // 12),
        )

    def _draw_cube(self, draw, x, y, size):
        top = (x + size * 0.50, y + size * 0.08)
        left = (x + size * 0.12, y + size * 0.30)
        right = (x + size * 0.88, y + size * 0.30)
        mid = (x + size * 0.50, y + size * 0.51)
        bottom = (x + size * 0.50, y + size * 0.94)
        draw.polygon([top, right, mid, left], fill=(255, 169, 104, 255))
        draw.polygon([left, mid, bottom, (x + size * 0.12, y + size * 0.68)], fill=(218, 81, 35, 255))
        draw.polygon([mid, right, (x + size * 0.88, y + size * 0.68), bottom], fill=(*self.VM_ORANGE, 255))

    def _draw_rocket(self, draw, x, y, size):
        draw.ellipse(
            (x + size * 0.28, y + size * 0.10, x + size * 0.72, y + size * 0.70),
            fill=(232, 239, 248, 255),
            outline=(79, 139, 233, 255),
            width=max(1, size // 14),
        )
        draw.polygon(
            [
                (x + size * 0.50, y + size * 0.02),
                (x + size * 0.70, y + size * 0.24),
                (x + size * 0.30, y + size * 0.24),
            ],
            fill=(72, 112, 240, 255),
        )
        draw.ellipse(
            (x + size * 0.40, y + size * 0.29, x + size * 0.60, y + size * 0.49),
            fill=(76, 186, 242, 255),
        )
        draw.polygon(
            [
                (x + size * 0.36, y + size * 0.68),
                (x + size * 0.48, y + size * 0.98),
                (x + size * 0.56, y + size * 0.68),
            ],
            fill=(247, 67, 70, 255),
        )
        draw.polygon(
            [
                (x + size * 0.49, y + size * 0.68),
                (x + size * 0.58, y + size * 0.94),
                (x + size * 0.65, y + size * 0.68),
            ],
            fill=(*self.BRAND_GOLD, 255),
        )

    def _draw_repository(self, draw, x, y, size):
        fg = (216, 238, 248)
        for yy in (0.20, 0.47, 0.74):
            top = y + size * yy
            draw.rounded_rectangle(
                (x + size * 0.12, top, x + size * 0.88, top + size * 0.19),
                radius=max(2, size // 12),
                fill=(52, 99, 125, 255),
                outline=(*fg, 255),
                width=max(1, size // 14),
            )
            draw.ellipse(
                (x + size * 0.72, top + size * 0.07, x + size * 0.78, top + size * 0.13),
                fill=(*self.BRAND_GOLD, 255),
            )

    def _draw_play(self, draw, x, y, size):
        draw.polygon(
            [
                (x + size * 0.25, y + size * 0.13),
                (x + size * 0.80, y + size * 0.50),
                (x + size * 0.25, y + size * 0.87),
            ],
            fill=(230, 244, 253, 255),
            outline=(*self.ICON_BLUE, 255),
        )

    def _draw_flag(self, draw, x, y, size):
        pole_x = x + size * 0.25
        draw.line(
            (pole_x, y + size * 0.12, pole_x, y + size * 0.90),
            fill=(220, 234, 242, 255),
            width=max(2, size // 11),
        )
        cells = [
            (0, 0, (238, 238, 238)),
            (1, 0, (78, 88, 96)),
            (2, 0, (238, 238, 238)),
            (0, 1, (78, 88, 96)),
            (1, 1, (238, 238, 238)),
            (2, 1, (78, 88, 96)),
        ]
        cell = size * 0.17
        start_x = pole_x
        start_y = y + size * 0.16
        for col, row, color in cells:
            draw.rectangle(
                (
                    start_x + col * cell,
                    start_y + row * cell,
                    start_x + (col + 1) * cell,
                    start_y + (row + 1) * cell,
                ),
                fill=(*color, 255),
            )

    def _draw_chart(self, draw, x, y, size):
        draw.rounded_rectangle(
            (x + 4, y + 4, x + size - 4, y + size - 4),
            radius=max(4, size // 8),
            fill=(232, 242, 247, 245),
        )
        bars = [
            (0.22, 0.52, (36, 189, 103)),
            (0.43, 0.35, (235, 193, 48)),
            (0.64, 0.23, (40, 143, 231)),
        ]
        for xx, top, color in bars:
            draw.rectangle(
                (
                    x + size * xx,
                    y + size * top,
                    x + size * (xx + 0.12),
                    y + size * 0.78,
                ),
                fill=(*color, 255),
            )

    def _draw_disk(self, draw, x, y, size):
        draw.rounded_rectangle(
            (x + 3, y + 5, x + size - 3, y + size - 5),
            radius=max(4, size // 7),
            fill=(214, 236, 246, 255),
            outline=(92, 160, 205, 255),
            width=max(1, size // 14),
        )
        draw.rounded_rectangle(
            (x + size * 0.20, y + size * 0.24, x + size * 0.80, y + size * 0.48),
            radius=max(2, size // 12),
            fill=(96, 160, 196, 255),
        )
        draw.ellipse(
            (x + size * 0.72, y + size * 0.67, x + size * 0.82, y + size * 0.77),
            fill=(*self.SUCCESS, 255),
        )

    def _draw_alert(self, draw, x, y, size):
        draw.ellipse(
            (x + 2, y + 2, x + size - 2, y + size - 2),
            fill=(*self.FAILURE, 240),
        )
        cx = x + size / 2
        draw.rounded_rectangle(
            (cx - 2, y + size * 0.23, cx + 2, y + size * 0.60),
            radius=2,
            fill=(255, 255, 255, 255),
        )
        draw.ellipse(
            (cx - 2, y + size * 0.72, cx + 2, y + size * 0.80),
            fill=(255, 255, 255, 255),
        )

    def _draw_info(self, draw, x, y, size):
        draw.ellipse(
            (x + 2, y + 2, x + size - 2, y + size - 2),
            fill=(*self.SKIPPED, 240),
        )
        cx = x + size / 2
        draw.ellipse(
            (cx - 2, y + size * 0.20, cx + 2, y + size * 0.28),
            fill=(255, 255, 255, 255),
        )
        draw.rounded_rectangle(
            (cx - 2, y + size * 0.39, cx + 2, y + size * 0.76),
            radius=2,
            fill=(255, 255, 255, 255),
        )

    def _draw_sync(self, draw, x, y, size):
        fg = (255, 255, 255)
        draw.arc(
            (x + size * 0.20, y + size * 0.20, x + size * 0.80, y + size * 0.80),
            start=210,
            end=30,
            fill=(*fg, 255),
            width=max(3, size // 10),
        )
        draw.arc(
            (x + size * 0.20, y + size * 0.20, x + size * 0.80, y + size * 0.80),
            start=30,
            end=210,
            fill=(*fg, 255),
            width=max(3, size // 10),
        )
        draw.polygon(
            [
                (x + size * 0.72, y + size * 0.18),
                (x + size * 0.86, y + size * 0.26),
                (x + size * 0.73, y + size * 0.34),
            ],
            fill=(*fg, 255),
        )
        draw.polygon(
            [
                (x + size * 0.28, y + size * 0.82),
                (x + size * 0.14, y + size * 0.74),
                (x + size * 0.27, y + size * 0.66),
            ],
            fill=(*fg, 255),
        )

    def _draw_nowlert_icon(self, image, x, y, size):
        """Draw the packaged Nowlert product icon in the footer."""

        path = self.icon_dir / "nowlert.png"
        if path.is_file():
            try:
                icon = Image.open(path).convert("RGBA")
                icon.thumbnail(
                    (size, size),
                    Image.Resampling.LANCZOS,
                )
                px = int(x + (size - icon.width) / 2)
                py = int(y + (size - icon.height) / 2)
                image.alpha_composite(icon, (px, py))
                return
            except OSError:
                pass

        # Rendering must remain resilient if a custom package omits the asset.
        draw = ImageDraw.Draw(image, "RGBA")
        cx = x + size / 2
        cy = y + size / 2
        draw.polygon(
            [
                (x + size * 0.12, y + size * 0.18),
                (cx, y + size * 0.38),
                (x + size * 0.88, y + size * 0.18),
                (x + size * 0.76, y + size * 0.72),
                (cx, y + size * 0.92),
                (x + size * 0.24, y + size * 0.72),
            ],
            fill=(54, 57, 58, 255),
            outline=(*self.BRAND_GOLD, 230),
        )
        draw.ellipse(
            (
                x + size * 0.25,
                y + size * 0.40,
                x + size * 0.43,
                y + size * 0.58,
            ),
            fill=(*self.BRAND_GOLD, 255),
        )
        draw.ellipse(
            (
                x + size * 0.57,
                y + size * 0.40,
                x + size * 0.75,
                y + size * 0.58,
            ),
            fill=(*self.BRAND_GOLD, 255),
        )
        draw.polygon(
            [
                (cx, cy),
                (x + size * 0.43, y + size * 0.68),
                (x + size * 0.57, y + size * 0.68),
            ],
            fill=(229, 220, 199, 255),
        )

    def _draw_status_rail(self, draw, accent, height):
        draw.rounded_rectangle(
            (34, 58, 44, height - 58),
            radius=5,
            fill=(*accent, 255),
        )

    def _draw_gold_frame(self, draw, card):
        x1, y1, x2, y2 = card
        draw.rounded_rectangle(
            (x1 + 14, y1 + 14, x2 - 14, y2 - 14),
            radius=22,
            outline=(*self.BRAND_GOLD, 78),
            width=1,
        )

    def _background(self, width, height):
        image = Image.new("RGBA", (width, height), (*self.PAGE_BG, 255))
        draw = ImageDraw.Draw(image, "RGBA")
        for x in range(0, width, 88):
            draw.line((x, 0, x, height), fill=(92, 107, 116, 20), width=1)
        for y in range(0, height, 88):
            draw.line((0, y, width, y), fill=(92, 107, 116, 16), width=1)

        vignette = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        vdraw = ImageDraw.Draw(vignette, "RGBA")
        vdraw.ellipse(
            (-width * 0.2, -height * 0.3, width * 1.2, height * 1.35),
            fill=(0, 0, 0, 0),
            outline=(0, 0, 0, 90),
            width=220,
        )
        vignette = vignette.filter(ImageFilter.GaussianBlur(80))
        image.alpha_composite(vignette)
        return image

    def _outer_glows(self, image, accent, height):
        glow = Image.new("RGBA", image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(glow, "RGBA")
        draw.rounded_rectangle(
            (28, 36, self.WIDTH - 28, height - 36),
            radius=31,
            outline=(*self.BRAND_GOLD, 86),
            width=6,
        )
        draw.rounded_rectangle(
            (31, 39, self.WIDTH - 31, height - 39),
            radius=29,
            outline=(*accent, 82),
            width=5,
        )
        glow = glow.filter(ImageFilter.GaussianBlur(19))
        image.alpha_composite(glow)

    @staticmethod
    def _glow_box(image, box, color, radius, *, alpha):
        glow = Image.new("RGBA", image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(glow, "RGBA")
        draw.rounded_rectangle(
            box,
            radius=radius,
            outline=(*color, alpha),
            width=8,
        )
        glow = glow.filter(ImageFilter.GaussianBlur(13))
        image.alpha_composite(glow)

    @staticmethod
    def _rounded(draw, box, *, fill, outline, radius, width):
        draw.rounded_rectangle(
            box,
            radius=radius,
            fill=fill,
            outline=outline,
            width=width,
        )

    def _fit_text_adaptive(
        self,
        draw,
        value,
        x,
        y,
        width,
        fonts,
        fill,
    ):
        """Prefer a smaller readable font before truncating operational data."""

        text = self._clean(value)
        selected = fonts[-1]
        for font in fonts:
            if draw.textlength(text, font=font) <= width:
                selected = font
                break
        self._fit_text(
            draw,
            text,
            x,
            y,
            width,
            selected,
            fill,
        )
        return selected

    def _fit_text(self, draw, value, x, y, width, font, fill):
        text = self._clean(value)
        if draw.textlength(text, font=font) <= width:
            draw.text((x, y), text, font=font, fill=fill)
            return
        ellipsis = "…"
        while text and draw.textlength(text + ellipsis, font=font) > width:
            text = text[:-1]
        draw.text(
            (x, y),
            (text.rstrip() + ellipsis) if text else ellipsis,
            font=font,
            fill=fill,
        )

    def _wrap_text(
        self,
        draw,
        text,
        x,
        y,
        width,
        font,
        fill,
        *,
        max_lines,
        line_gap,
    ):
        words = self._clean(text).split()
        lines = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if draw.textlength(candidate, font=font) <= width:
                current = candidate
                continue
            if current:
                lines.append(current)
            current = word
            if len(lines) >= max_lines - 1:
                break
        if current and len(lines) < max_lines:
            lines.append(current)
        if len(lines) == max_lines and len(" ".join(lines).split()) < len(words):
            last = lines[-1]
            while last and draw.textlength(last + "…", font=font) > width:
                last = last[:-1]
            lines[-1] = last.rstrip() + "…"
        line_h = font.getbbox("Ag")[3] - font.getbbox("Ag")[1]
        for index, line in enumerate(lines):
            draw.text(
                (x, y + index * (line_h + line_gap)),
                line,
                font=font,
                fill=fill,
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
    def _short_duration(value):
        text = str(value or "")
        return (
            text.replace(" minutes", " min")
            .replace(" minute", " min")
            .replace(" seconds", " sec")
            .replace(" second", " sec")
        )

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
        return " | ".join(parts)

    @staticmethod
    def _clean(value):
        return " ".join(
            str(value or "").replace("\r", " ").replace("\n", " ").split()
        )

    @staticmethod
    def _label(value):
        return str(value or "").replace("_", " ").strip().title()

    @staticmethod
    def _tint(color, base, ratio):
        return tuple(
            int(base[index] * (1 - ratio) + color[index] * ratio)
            for index in range(3)
        )
