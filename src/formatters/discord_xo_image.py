"""Rendered Xen Orchestra Discord Modern notification cards."""

from __future__ import annotations

from io import BytesIO
from math import ceil
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from models import Notification
from formatters.discord_modern_layout import ModernCardLayoutMixin


class XenOrchestraDiscordImageRenderer(ModernCardLayoutMixin):
    """Render XO backup notifications with the approved Nowlert visual system."""

    WIDTH = 2000
    BASE_HEIGHT = 1320
    CARD_SIDE_PADDING = 78
    VM_PANEL_TOP = 780
    VM_HEADER_HEIGHT = 104
    VM_PANEL_BOTTOM_PADDING = 34
    VM_ENTRY_HEIGHT = 150
    VM_ENTRY_REASON_HEIGHT = 230
    SUCCESS_ROW_HEIGHT = 150
    VM_ENTRY_HEIGHT_LARGE = 164
    VM_ENTRY_REASON_HEIGHT_LARGE = 250
    SUCCESS_ROW_HEIGHT_LARGE = 164
    VM_ENTRY_HEIGHT_COMPACT = 144
    VM_ENTRY_REASON_HEIGHT_COMPACT = 230
    SUCCESS_ROW_HEIGHT_COMPACT = 144
    FOOTER_GAP = 32
    FOOTER_RESERVE = 180
    FOOTER_ICON_SIZE = 68
    FOOTER_TEXT = "Nowlert CE • Modern Card"
    DETAIL_SPLIT_RATIO = 0.43
    DETAIL_LABEL_OFFSET = 92
    DETAIL_VALUE_OFFSET = 300
    DETAIL_LABEL_VALUE_GAP = 32
    STATUS_BADGE_WIDTH = 560
    STATUS_BADGE_HEIGHT = 128
    SUMMARY_CELL_GAP = 48
    XO_HEADER_ICON_SIZE = 144
    OUTER_GLOW_GOLD_ALPHA = 138
    OUTER_GLOW_ACCENT_ALPHA = 124
    OUTER_GLOW_BLUR = 21
    STATUS_GLOW_ALPHA = 116
    PAIRED_PANEL_LEFT_RATIO = 0.50
    PAIRED_PANEL_LONG_OTHER_LEFT_RATIO = 0.48
    PAIRED_OUTCOME_MIN_HEIGHT = 370
    EXCEPTION_BASE_HEIGHT = 1600

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
    HEADER_MUTED = (207, 212, 214)
    LABEL = (166, 196, 224)

    SUCCESS = (22, 214, 115)
    FAILURE = (255, 64, 72)
    SKIPPED = (37, 166, 238)
    ICON_BLUE = (45, 163, 232)
    VM_ORANGE = (239, 111, 48)

    def __init__(self, icon_dir: Path | str = "/nowlert/assets/icons"):
        self.icon_dir = Path(icon_dir)
        self._init_modern_fonts()
        self.font_micro = self._font(False, 40)
        self.font_tiny = self._font(False, 40)
        self.font_small = self._font(False, 40)
        self.font_detail = self._font(False, 42)
        self.font_body = self._font(False, 42)
        self.font_label = self._font(True, 40)
        self.font_vm_micro = self._font(True, 40)
        self.font_vm_compact = self._font(True, 40)
        self.font_vm = self._font(True, 42)
        self.font_vm_large = self._font(True, 44)
        self.font_vm_meta_compact = self._font(False, 40)
        self.font_vm_meta_large = self._font(False, 40)
        self.font_reason_compact = self._font(False, 40)
        self.font_reason = self._font(False, 40)
        self.font_reason_large = self._font(False, 40)
        self.font_bold = self._font(True, 46)
        self.font_title = self._font(True, 52)
        self.font_heading = self._font(True, 62)

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

    @staticmethod
    def _center_y(top: int, bottom: int, height: int) -> int:
        return top + max(0, ((bottom - top) - height) // 2)

    def _status_badge_box(
        self,
        right: int,
        header_y: int,
        header_height: int,
    ):
        """Use the full available header height for the lifecycle badge."""

        height = max(self.STATUS_BADGE_HEIGHT, header_height)
        return (
            right - self.STATUS_BADGE_WIDTH,
            header_y,
            right,
            header_y + height,
        )

    def _summary_cells(self, left: int, right: int):
        """Return three summary cells with explicit visual breathing room."""

        inner_left = left + 28
        inner_right = right - 28
        available = (
            inner_right
            - inner_left
            - self.SUMMARY_CELL_GAP * 2
        )
        first = int(available * 0.31)
        second = int(available * 0.28)
        third = available - first - second

        cell_1 = (
            inner_left,
            inner_left + first,
        )
        cell_2 = (
            cell_1[1] + self.SUMMARY_CELL_GAP,
            cell_1[1] + self.SUMMARY_CELL_GAP + second,
        )
        cell_3 = (
            cell_2[1] + self.SUMMARY_CELL_GAP,
            cell_2[1] + self.SUMMARY_CELL_GAP + third,
        )
        return [cell_1, cell_2, cell_3]

    def _event_time_only(self, value) -> str:
        """Keep only the clock portion for the compact top summary strip."""

        text = self._clean(value or "")
        if not text:
            return ""

        match = re.search(
            r"(?<!\d)(\d{1,2}:\d{2}:\d{2})"
            r"(?:\.\d+)?"
            r"(?:\s*(Z|UTC|[+-]\d{2}:?\d{2}))?",
            text,
            re.IGNORECASE,
        )
        if not match:
            return text

        clock = match.group(1)
        zone = (match.group(2) or "").upper()
        if zone == "Z":
            zone = "UTC"
        return f"{clock} {zone}".strip()

    def render(self, notification: Notification) -> bytes:
        """Render the approved Xen Orchestra card at the larger readable scale."""

        status, accent, status_label = self._status(notification)
        successful = list(notification.successful_vms or [])
        failed = list(notification.failed_vms or [])
        skipped = list(notification.skipped_vms or [])

        measure = ImageDraw.Draw(Image.new("RGB", (self.WIDTH, 1)))
        x0 = self.CARD_SIDE_PADDING
        right = self.WIDTH - self.CARD_SIDE_PADDING
        header_y = 82
        xo_icon_size = self.XO_HEADER_ICON_SIZE
        title_x = x0 + xo_icon_size + 20
        badge_w = self.STATUS_BADGE_WIDTH
        badge_x = right - badge_w

        repository = self._clean(notification.repository or "Backup")
        repository_width = max(320, badge_x - title_x - 34)
        repository_lines = self._wrapped_text_lines(
            measure, repository, repository_width, self.font_body
        ) or ["Backup"]
        body_line_h = self.font_body.getbbox("Ag")[3] - self.font_body.getbbox("Ag")[1]
        header_height = max(
            150,
            76 + len(repository_lines) * (body_line_h + 6),
            self.STATUS_BADGE_HEIGHT,
        )

        report = self._clean(
            notification.subject
            or notification.body
            or (
                "Backup report for "
                + self._clean(
                    notification.job_name
                    or notification.title
                    or "Xen Orchestra backup"
                )
            )
        )
        report_width = right - x0 - 60
        report_lines = self._wrapped_text_lines(
            measure, report, report_width, self.font_title
        ) or ["Xen Orchestra backup"]
        title_line_h = self.font_title.getbbox("Ag")[3] - self.font_title.getbbox("Ag")[1]
        title_y = header_y + header_height + 24
        title_h = max(88, 30 + len(report_lines) * (title_line_h + 5))

        metric_y = title_y + title_h + 20
        metric_h = 112
        detail_y = metric_y + metric_h + 24
        gap = 24
        detail_width = right - x0 - gap
        left_width = int(detail_width * self.DETAIL_SPLIT_RATIO)
        right_width = detail_width - left_width

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
        detail_h = max(
            300,
            self._detail_rows_height(
                measure, left_width, left_rows, result_status=None
            ),
            self._detail_rows_height(
                measure, right_width, right_rows, result_status=status
            ),
        )

        vm_y = max(self.VM_PANEL_TOP, detail_y + detail_h + 24)
        vm_panel_height = self._vm_panel_height(
            notification, successful, failed, skipped
        )
        height = max(
            self.BASE_HEIGHT,
            vm_y + vm_panel_height + self.FOOTER_GAP + self.FOOTER_RESERVE,
        )
        if failed or skipped:
            height = max(
                height,
                self.EXCEPTION_BASE_HEIGHT,
            )
        footer_y = self._footer_y(height)

        image = self._background(self.WIDTH, height)
        self._outer_glows(image, accent, height)
        draw = ImageDraw.Draw(image, "RGBA")

        card = (30, 38, self.WIDTH - 30, height - 38)
        self._rounded(
            draw, card, fill=(*self.CARD_BG, 247),
            outline=(*self.PANEL_BORDER, 220), radius=28, width=2,
        )
        self._draw_status_rail(draw, accent, height)
        self._draw_gold_frame(draw, card)

        self._draw_xo_art(
            image, x0, header_y - 4, size=xo_icon_size
        )
        draw.text(
            (title_x, header_y + 2),
            "Xen Orchestra",
            font=self.font_heading,
            fill=self.TEXT,
        )
        self._wrap_text(
            draw, repository, title_x, header_y + 68,
            repository_width, self.font_body, self.HEADER_MUTED,
            max_lines=None, line_gap=5,
        )

        badge = self._status_badge_box(
            right,
            header_y,
            header_height,
        )
        badge_x = badge[0]
        self._glow_box(
            image, badge, accent, 18, alpha=self.STATUS_GLOW_ALPHA
        )
        draw = ImageDraw.Draw(image, "RGBA")
        self._rounded(
            draw, badge,
            fill=(*self._tint(accent, self.CARD_BG, 0.16), 245),
            outline=(*accent, 225), radius=18, width=2,
        )
        badge_icon_size = 64
        badge_icon_y = self._center_y(
            badge[1],
            badge[3],
            badge_icon_size,
        )
        self._status_icon(
            draw,
            badge_x + 28,
            badge_icon_y,
            badge_icon_size,
            status,
            accent,
        )
        draw.text(
            (
                badge_x + 112,
                (badge[1] + badge[3]) // 2,
            ),
            status_label,
            font=self.font_bold,
            fill=accent if status != "success" else (103, 239, 174),
            anchor="lm",
        )

        title_box = (x0, title_y, right, title_y + title_h)
        self._rounded(
            draw, title_box, fill=(*self.PANEL_2, 248),
            outline=(93, 101, 108, 190), radius=14, width=2,
        )
        self._wrap_text(
            draw, report, x0 + 30, title_y + 16,
            report_width, self.font_title, self.TEXT,
            max_lines=None, line_gap=5,
        )

        metric_box = (x0, metric_y, right, metric_y + metric_h)
        self._rounded(
            draw, metric_box, fill=(*self.PANEL, 248),
            outline=(*self.PANEL_BORDER, 200), radius=14, width=1,
        )
        event_time = self._event_time_only(
            notification.end_time
            or notification.start_time
            or ""
        )
        category = self._label(notification.category or "backup")
        metrics = [
            ("status", "Severity", status_label.replace("Backup ", ""), accent),
            ("sync", "Category", category, self.ICON_BLUE),
            ("clock", "Event time", event_time, (194, 226, 242)),
        ]
        cells = self._summary_cells(x0, right)
        summary_icon_size = 54
        summary_mid_y = metric_y + metric_h // 2
        for index, (
            (icon, label, value, color),
            cell,
        ) in enumerate(zip(metrics, cells)):
            cell_x1, cell_x2 = cell
            icon_y = self._center_y(
                metric_y,
                metric_y + metric_h,
                summary_icon_size,
            )
            self._draw_icon_badge(
                draw,
                cell_x1,
                icon_y,
                summary_icon_size,
                icon,
                color,
                status=status,
            )
            label_x = cell_x1 + 74
            draw.text(
                (label_x, summary_mid_y),
                f"{label}:",
                font=self.font_label,
                fill=self.TEXT,
                anchor="lm",
            )
            label_w = draw.textlength(
                f"{label}:",
                font=self.font_label,
            )
            value_x = label_x + label_w + 18
            draw.text(
                (value_x, summary_mid_y),
                value,
                font=self.font_detail,
                fill=self.TEXT,
                anchor="lm",
            )
            if index < 2:
                next_left = cells[index + 1][0]
                line_x = (
                    cell_x2 + next_left
                ) // 2
                draw.line(
                    (
                        line_x,
                        metric_y + 22,
                        line_x,
                        metric_y + metric_h - 22,
                    ),
                    fill=(102, 112, 119, 160),
                    width=2,
                )

        left_box = (
            x0, detail_y, x0 + left_width, detail_y + detail_h
        )
        right_box = (
            x0 + left_width + gap, detail_y, right, detail_y + detail_h
        )
        for box in (left_box, right_box):
            self._rounded(
                draw, box, fill=(*self.PANEL_2, 248),
                outline=(*self.PANEL_BORDER, 205), radius=15, width=2,
            )
        self._detail_rows(draw, left_box, left_rows, result_status=None)
        self._detail_rows(draw, right_box, right_rows, result_status=status)

        vm_bottom = footer_y - self.FOOTER_GAP
        if failed and skipped:
            self._mixed_vm_panels(
                image,
                draw,
                (x0, vm_y, right, vm_bottom),
                successful,
                failed,
                skipped,
                notification,
            )
        elif failed:
            self._paired_vm_panels(
                image, draw, (x0, vm_y, right, vm_bottom),
                successful, failed,
                "FAILED VM" if len(failed) == 1 else "FAILED VMS",
                self.FAILURE, notification, "failure",
            )
        elif skipped:
            self._paired_vm_panels(
                image, draw, (x0, vm_y, right, vm_bottom),
                successful, skipped,
                "SKIPPED VM" if len(skipped) == 1 else "SKIPPED VMS",
                self.SKIPPED, notification, "skipped",
            )
        else:
            self._success_panel(
                image, draw, (x0, vm_y, right, vm_bottom),
                successful, notification,
            )

        draw.line(
            (x0, footer_y - 10, right, footer_y - 10),
            fill=(81, 89, 95, 170), width=2,
        )
        icon_size = self.FOOTER_ICON_SIZE
        icon_x = x0 + 18
        icon_y = footer_y + 18
        self._draw_nowlert_icon(
            image,
            icon_x,
            icon_y,
            icon_size,
        )
        draw.text(
            (
                icon_x + icon_size + 18,
                icon_y + icon_size // 2,
            ),
            self.FOOTER_TEXT,
            font=self.font_small,
            fill=self.MUTED,
            anchor="lm",
        )

        output = BytesIO()
        image.convert("RGB").save(
            output, format="PNG", optimize=True, compress_level=7
        )
        return output.getvalue()

    def _vm_panel_height(
        self,
        notification,
        successful,
        failed,
        skipped,
    ) -> int:
        """Return the VM panel height required by the approved dynamic layout."""

        total_vm_count = (
            len(successful) + len(failed) + len(skipped)
        )
        style = self._vm_style(total_vm_count)
        panel_width = self.WIDTH - self.CARD_SIDE_PADDING * 2

        if failed and skipped:
            gap = 18
            entry_padding = 32
            column_width = (
                panel_width - gap * 2
            ) // 3
            entry_width = max(
                180,
                column_width - entry_padding * 2,
            )
            heights = [
                self._vm_column_height(
                    notification,
                    successful,
                    include_reason=False,
                    vm_count=total_vm_count,
                    entry_width=entry_width,
                ),
                self._vm_column_height(
                    notification,
                    failed,
                    include_reason=True,
                    vm_count=total_vm_count,
                    entry_width=entry_width,
                ),
                self._vm_column_height(
                    notification,
                    skipped,
                    include_reason=True,
                    vm_count=total_vm_count,
                    entry_width=entry_width,
                ),
            ]
            return max(
                330,
                self.VM_HEADER_HEIGHT
                + max(heights)
                + self.VM_PANEL_BOTTOM_PADDING,
            )

        if failed or skipped:
            other = failed or skipped
            gap = 18
            entry_padding = 36
            left_width = int(
                (panel_width - gap) * self.PAIRED_PANEL_LEFT_RATIO
            )
            right_width = panel_width - left_width - gap
            successful_height = self._vm_column_height(
                notification,
                successful,
                include_reason=False,
                vm_count=total_vm_count,
                entry_width=max(180, left_width - entry_padding * 2),
            )
            other_height = self._vm_column_height(
                notification,
                other,
                include_reason=True,
                vm_count=total_vm_count,
                entry_width=max(180, right_width - entry_padding * 2),
            )
            return max(
                self.PAIRED_OUTCOME_MIN_HEIGHT,
                self.VM_HEADER_HEIGHT
                + max(successful_height, other_height)
                + self.VM_PANEL_BOTTOM_PADDING,
            )

        if not successful:
            return 330

        columns = 3
        horizontal_padding = 38
        col_w = (
            panel_width - horizontal_padding * 2
        ) // columns
        entry_width = max(180, col_w - 38)
        content_height = 0
        for start in range(0, len(successful), columns):
            group = successful[start:start + columns]
            content_height += max(
                max(
                    self._vm_entry_height(
                        notification,
                        name,
                        include_reason=False,
                        vm_count=total_vm_count,
                        entry_width=entry_width,
                    )
                    for name in group
                ),
                style["row_height"],
            )

        return max(
            330,
            self.VM_HEADER_HEIGHT
            + content_height
            + self.VM_PANEL_BOTTOM_PADDING,
        )

    def _vm_column_height(
        self,
        notification,
        names,
        *,
        include_reason: bool,
        vm_count: int,
        entry_width: int | None = None,
    ) -> int:
        """Measure a vertical VM column before allocating the image canvas."""

        if not names:
            return 80
        return sum(
            self._vm_entry_height(
                notification,
                name,
                include_reason=include_reason,
                vm_count=vm_count,
                entry_width=entry_width,
            )
            for name in names
        )

    def _vm_entry_height(
        self,
        notification,
        name,
        *,
        include_reason: bool,
        vm_count: int,
        entry_width: int | None = None,
    ) -> int:
        detail = (notification.vm_details or {}).get(name, {}) or {}
        style = self._vm_style(vm_count)

        extra_name_height = 0
        if entry_width:
            measure = ImageDraw.Draw(Image.new("RGB", (1, 1)))
            name_width = max(140, entry_width - style["name_offset"])
            name_lines = self._wrapped_text_lines(
                measure,
                self._clean(name),
                name_width,
                style["name_font"],
            ) or [self._clean(name)]
            name_line_h = (
                style["name_font"].getbbox("Ag")[3]
                - style["name_font"].getbbox("Ag")[1]
            )
            extra_name_height = max(0, len(name_lines) - 1) * (
                name_line_h + 4
            )

        base_height = style["entry_height"] + extra_name_height
        reason = self._clean(detail.get("error") or "")
        if not include_reason or not reason:
            return base_height
        if not entry_width:
            return max(base_height, style["reason_height"])

        measure = ImageDraw.Draw(Image.new("RGB", (1, 1)))
        reason_width = max(160, entry_width - style["meta_offset"])
        lines = self._wrapped_text_lines(
            measure,
            reason,
            reason_width,
            style["reason_font"],
        )
        line_h = (
            style["reason_font"].getbbox("Ag")[3]
            - style["reason_font"].getbbox("Ag")[1]
        )
        required = (
            style["reason_y"]
            + extra_name_height
            + max(1, len(lines)) * (line_h + 4)
            + 20
        )
        return max(base_height, style["reason_height"], required)

    def _vm_style(self, vm_count: int) -> dict:
        """Scale VM typography for normal, busy, and unusually large jobs."""

        if vm_count <= 6:
            return {
                "name_font": self.font_vm_large,
                "name_fallback_font": self.font_vm,
                "meta_font": self.font_vm_meta_large,
                "reason_font": self.font_reason_large,
                "entry_height": self.VM_ENTRY_HEIGHT_LARGE,
                "reason_height": self.VM_ENTRY_REASON_HEIGHT_LARGE,
                "row_height": self.SUCCESS_ROW_HEIGHT_LARGE,
                "main_icon": 48,
                "meta_icon": 34,
                "name_offset": 66,
                "meta_offset": 112,
                "size_y": 54,
                "speed_y": 96,
                "reason_y": 138,
            }
        if vm_count <= 12:
            return {
                "name_font": self.font_vm,
                "name_fallback_font": self.font_vm_compact,
                "meta_font": self.font_small,
                "reason_font": self.font_reason,
                "entry_height": self.VM_ENTRY_HEIGHT,
                "reason_height": self.VM_ENTRY_REASON_HEIGHT,
                "row_height": self.SUCCESS_ROW_HEIGHT,
                "main_icon": 46,
                "meta_icon": 32,
                "name_offset": 64,
                "meta_offset": 108,
                "size_y": 52,
                "speed_y": 92,
                "reason_y": 132,
            }
        return {
            "name_font": self.font_vm_compact,
            "name_fallback_font": self.font_vm_micro,
            "meta_font": self.font_vm_meta_compact,
            "reason_font": self.font_reason_compact,
            "entry_height": self.VM_ENTRY_HEIGHT_COMPACT,
            "reason_height": self.VM_ENTRY_REASON_HEIGHT_COMPACT,
            "row_height": self.SUCCESS_ROW_HEIGHT_COMPACT,
            "main_icon": 44,
            "meta_icon": 30,
            "name_offset": 60,
            "meta_offset": 102,
            "size_y": 50,
            "speed_y": 88,
            "reason_y": 126,
        }

    def _detail_rows_height(
        self,
        draw,
        width,
        rows,
        *,
        result_status,
    ):
        """Measure the approved detail panel without shrinking or clipping."""

        y = 30
        line_h = (
            self.font_detail.getbbox("Ag")[3]
            - self.font_detail.getbbox("Ag")[1]
        )
        for _icon, label, value in rows:
            if value is None or str(value).strip() == "":
                y += 66
                continue
            label_end = (
                self.DETAIL_LABEL_OFFSET
                + draw.textlength(
                    self._clean(label),
                    font=self.font_label,
                )
            )
            value_x = max(
                self.DETAIL_VALUE_OFFSET,
                ceil(label_end + self.DETAIL_LABEL_VALUE_GAP),
            )
            available = max(120, width - value_x - 24)
            if label == "Result" and result_status:
                available = max(120, available - 50)
            lines = self._wrapped_text_lines(
                draw,
                self._clean(value),
                available,
                self.font_detail,
            ) or [""]
            y += max(66, len(lines) * (line_h + 5) + 12)
        return y + 24

    def _detail_rows(
        self,
        draw,
        box,
        rows,
        *,
        result_status,
    ):
        x1, y1, x2, _ = box
        y = y1 + 30
        line_h = (
            self.font_detail.getbbox("Ag")[3]
            - self.font_detail.getbbox("Ag")[1]
        )
        label_x = x1 + self.DETAIL_LABEL_OFFSET

        for _index, (icon, label, value) in enumerate(rows):
            if value is None or str(value).strip() == "":
                y += 66
                continue
            self._draw_field_icon(draw, x1 + 24, y - 4, 44, icon)
            draw.text(
                (label_x, y + 2),
                label,
                font=self.font_label,
                fill=self.LABEL,
            )
            value_x = self._detail_value_x(draw, x1, label)
            available = max(120, x2 - value_x - 24)

            if label == "Result" and result_status:
                result_color = {
                    "success": self.SUCCESS,
                    "failure": self.FAILURE,
                    "skipped": self.SKIPPED,
                }.get(result_status, self.SUCCESS)
                status_size = 38
                self._draw_icon_badge(
                    draw,
                    value_x,
                    y - 2,
                    status_size,
                    "status",
                    result_color,
                    status=result_status,
                )
                text_x = value_x + status_size + 12
                text_width = max(
                    120,
                    available - status_size - 12,
                )
                self._wrap_text(
                    draw,
                    self._clean(value),
                    text_x,
                    y + 2,
                    text_width,
                    self.font_detail,
                    self.TEXT,
                    max_lines=None,
                    line_gap=5,
                )
                lines = self._wrapped_text_lines(
                    draw,
                    self._clean(value),
                    text_width,
                    self.font_detail,
                ) or [""]
            else:
                self._wrap_text(
                    draw,
                    self._clean(value),
                    value_x,
                    y + 2,
                    available,
                    self.font_detail,
                    self.TEXT,
                    max_lines=None,
                    line_gap=5,
                )
                lines = self._wrapped_text_lines(
                    draw,
                    self._clean(value),
                    available,
                    self.font_detail,
                ) or [""]
            y += max(66, len(lines) * (line_h + 5) + 12)

    def _success_panel(
        self,
        image,
        draw,
        box,
        names,
        notification,
    ):
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
        self._status_icon(
            draw, x1 + 28, y1 + 22, 54, "success", self.SUCCESS
        )
        draw.text(
            (x1 + 98, y1 + 29),
            f"SUCCESSFUL VMS ({len(names)})",
            font=self.font_bold,
            fill=(92, 242, 190),
        )
        if not names:
            draw.text(
                (x1 + 36, y1 + self.VM_HEADER_HEIGHT),
                "No VM details reported.",
                font=self.font_small,
                fill=self.MUTED,
            )
            return

        columns = 3
        total_vm_count = len(names)
        horizontal_padding = 38
        col_w = (
            x2 - x1 - horizontal_padding * 2
        ) // columns
        entry_width = max(180, col_w - 38)
        cy = y1 + self.VM_HEADER_HEIGHT

        for start in range(0, len(names), columns):
            group = names[start:start + columns]
            row_height = max(
                self._vm_entry_height(
                    notification,
                    name,
                    include_reason=False,
                    vm_count=total_vm_count,
                    entry_width=entry_width,
                )
                for name in group
            )
            for col, name in enumerate(group):
                cx = x1 + horizontal_padding + col * col_w
                if col:
                    divider_x = cx - 19
                    draw.line(
                        (
                            divider_x,
                            cy - 4,
                            divider_x,
                            cy + row_height - 20,
                        ),
                        fill=(42, 183, 132, 150),
                        width=1,
                    )
                self._vm_entry(
                    draw,
                    cx,
                    cy,
                    entry_width,
                    name,
                    notification,
                    self.SUCCESS,
                    include_reason=False,
                    vm_count=total_vm_count,
                )
            cy += row_height

    def _mixed_vm_panels(
        self,
        image,
        draw,
        box,
        successful,
        failed,
        skipped,
        notification,
    ):
        """Render rare mixed success/failure/skipped results without hiding data."""

        x1, y1, x2, y2 = box
        gap = 18
        panel_width = (x2 - x1 - gap * 2) // 3
        specs = [
            (
                successful,
                "SUCCESSFUL VMS",
                self.SUCCESS,
                "success",
                (0, 61, 49, 226),
                (92, 242, 190),
            ),
            (
                failed,
                "FAILED VMS",
                self.FAILURE,
                "failure",
                (56, 17, 23, 232),
                (255, 122, 134),
            ),
            (
                skipped,
                "SKIPPED VMS",
                self.SKIPPED,
                "skipped",
                (11, 50, 75, 232),
                (94, 202, 255),
            ),
        ]
        total_vm_count = len(successful) + len(failed) + len(skipped)

        for index, (names, title, color, status, fill, title_color) in enumerate(specs):
            px1 = x1 + index * (panel_width + gap)
            px2 = x2 if index == 2 else px1 + panel_width
            panel = (px1, y1, px2, y2)
            self._glow_box(image, panel, color, 17, alpha=56)
            draw = ImageDraw.Draw(image, "RGBA")
            self._rounded(
                draw,
                panel,
                fill=fill,
                outline=(*color, 230),
                radius=17,
                width=2,
            )
            self._status_icon(
                draw,
                px1 + 24,
                y1 + 22,
                50,
                status,
                color,
            )
            draw.text(
                (px1 + 88, y1 + 30),
                f"{title} ({len(names)})",
                font=self.font_bold,
                fill=title_color,
            )

            entry_padding = 32
            entry_width = max(
                180,
                px2 - px1 - entry_padding * 2,
            )
            entry_y = y1 + self.VM_HEADER_HEIGHT
            for name in names:
                self._vm_entry(
                    draw,
                    px1 + entry_padding,
                    entry_y,
                    entry_width,
                    name,
                    notification,
                    color,
                    include_reason=status != "success",
                    reason_status=status,
                    vm_count=total_vm_count,
                )
                entry_y += self._vm_entry_height(
                    notification,
                    name,
                    include_reason=status != "success",
                    vm_count=total_vm_count,
                    entry_width=entry_width,
                )

    def _paired_panel_left_ratio(
        self,
        successful,
        other,
        notification,
    ) -> float:
        """Keep failure and skipped cards on the same approved split."""

        return self.PAIRED_PANEL_LEFT_RATIO

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
        left_ratio = self._paired_panel_left_ratio(
            successful,
            other,
            notification,
        )
        left_w = int((x2 - x1 - gap) * left_ratio)
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
            left[0] + 28,
            y1 + 22,
            54,
            "success",
            self.SUCCESS,
        )
        draw.text(
            (left[0] + 98, y1 + 29),
            f"SUCCESSFUL VMS ({len(successful)})",
            font=self.font_bold,
            fill=(92, 242, 190),
        )

        self._status_icon(
            draw,
            right[0] + 28,
            y1 + 22,
            54,
            other_status,
            other_color,
        )
        draw.text(
            (right[0] + 98, y1 + 29),
            f"{other_title} ({len(other)})",
            font=self.font_bold,
            fill=(
                (255, 122, 134)
                if other_status == "failure"
                else (94, 202, 255)
            ),
        )

        total_vm_count = len(successful) + len(other)
        entry_padding = 36
        success_width = (
            left[2] - left[0] - entry_padding * 2
        )
        other_width = (
            right[2] - right[0] - entry_padding * 2
        )

        success_y = y1 + self.VM_HEADER_HEIGHT
        for name in successful:
            self._vm_entry(
                draw,
                left[0] + entry_padding,
                success_y,
                success_width,
                name,
                notification,
                self.SUCCESS,
                include_reason=False,
                vm_count=total_vm_count,
            )
            success_y += self._vm_entry_height(
                notification,
                name,
                include_reason=False,
                vm_count=total_vm_count,
                entry_width=success_width,
            )

        other_y = y1 + self.VM_HEADER_HEIGHT
        for name in other:
            self._vm_entry(
                draw,
                right[0] + entry_padding,
                other_y,
                other_width,
                name,
                notification,
                other_color,
                include_reason=True,
                reason_status=other_status,
                vm_count=total_vm_count,
            )
            other_y += self._vm_entry_height(
                notification,
                name,
                include_reason=True,
                vm_count=total_vm_count,
                entry_width=other_width,
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
        vm_count,
        reason_status=None,
    ):
        detail = (notification.vm_details or {}).get(name, {}) or {}
        style = self._vm_style(vm_count)
        main_icon = style["main_icon"]
        meta_icon = style["meta_icon"]
        name_offset = style["name_offset"]
        meta_offset = style["meta_offset"]

        self._draw_field_icon(draw, x, y - 2, main_icon, "cube")
        name_width = max(140, width - name_offset)
        name_lines = self._wrapped_text_lines(
            draw,
            self._clean(name),
            name_width,
            style["name_font"],
        ) or [self._clean(name)]
        name_line_h = (
            style["name_font"].getbbox("Ag")[3]
            - style["name_font"].getbbox("Ag")[1]
        )
        self._wrap_text(
            draw,
            self._clean(name),
            x + name_offset,
            y,
            name_width,
            style["name_font"],
            self.TEXT,
            max_lines=None,
            line_gap=4,
        )
        extra_name_height = max(0, len(name_lines) - 1) * (
            name_line_h + 4
        )

        size = self._clean(detail.get("size") or "")
        speed = self._clean(detail.get("speed") or "")
        size_y = y + style["size_y"] + extra_name_height
        speed_y = y + style["speed_y"] + extra_name_height
        reason_y = y + style["reason_y"] + extra_name_height

        if size:
            self._draw_field_icon(
                draw, x + name_offset, size_y, meta_icon, "disk"
            )
            self._wrap_text(
                draw,
                size,
                x + meta_offset,
                size_y + 1,
                max(100, width - meta_offset),
                style["meta_font"],
                self.MUTED,
                max_lines=None,
                line_gap=4,
            )
        if speed:
            self._draw_field_icon(
                draw, x + name_offset, speed_y, meta_icon, "rocket"
            )
            self._wrap_text(
                draw,
                speed,
                x + meta_offset,
                speed_y + 1,
                max(100, width - meta_offset),
                style["meta_font"],
                self.MUTED,
                max_lines=None,
                line_gap=4,
            )

        if include_reason and detail.get("error"):
            reason_color = (
                self.FAILURE
                if reason_status == "failure"
                else (108, 204, 255)
            )
            self._draw_field_icon(
                draw,
                x + name_offset,
                reason_y,
                meta_icon,
                "alert" if reason_status == "failure" else "info",
            )
            self._wrap_text(
                draw,
                self._clean(detail["error"]),
                x + meta_offset,
                reason_y,
                max(120, width - meta_offset),
                style["reason_font"],
                reason_color,
                max_lines=None,
                line_gap=4,
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
                alpha = icon.getchannel("A")
                bbox = alpha.getbbox()
                if bbox:
                    icon = icon.crop(bbox)
                if icon.width and icon.height:
                    scale = min(
                        size / icon.width,
                        size / icon.height,
                    )
                    icon = icon.resize(
                        (
                            max(1, int(round(icon.width * scale))),
                            max(1, int(round(icon.height * scale))),
                        ),
                        Image.Resampling.LANCZOS,
                    )
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
            outline=(*self.BRAND_GOLD, self.OUTER_GLOW_GOLD_ALPHA),
            width=8,
        )
        draw.rounded_rectangle(
            (31, 39, self.WIDTH - 31, height - 39),
            radius=29,
            outline=(*accent, self.OUTER_GLOW_ACCENT_ALPHA),
            width=7,
        )
        glow = glow.filter(
            ImageFilter.GaussianBlur(
                self.OUTER_GLOW_BLUR
            )
        )
        image.alpha_composite(glow)

    @staticmethod
    def _glow_box(image, box, color, radius, *, alpha):
        glow = Image.new("RGBA", image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(glow, "RGBA")
        draw.rounded_rectangle(
            box,
            radius=radius,
            outline=(*color, alpha),
            width=10,
        )
        glow = glow.filter(ImageFilter.GaussianBlur(15))
        image.alpha_composite(glow)

    def _footer_y(self, height):
        return height - self.FOOTER_RESERVE

    @staticmethod
    def _rounded(draw, box, *, fill, outline, radius, width):
        draw.rounded_rectangle(
            box,
            radius=radius,
            fill=fill,
            outline=outline,
            width=width,
        )

    def _detail_value_x(self, draw, x1, label):
        """Keep field values visibly separated from variable-width labels."""

        label_x = x1 + self.DETAIL_LABEL_OFFSET
        label_end = label_x + draw.textlength(
            self._clean(label),
            font=self.font_label,
        )
        return max(
            x1 + self.DETAIL_VALUE_OFFSET,
            ceil(label_end + self.DETAIL_LABEL_VALUE_GAP),
        )

    def _draw_result_value(
        self,
        draw,
        value,
        x,
        y,
        width,
        accent,
    ):
        """Draw the result summary with the exceptional outcome accented."""

        segments = self._result_segments(value, accent)
        plain = "".join(text for text, _color in segments)
        font = self._select_font(
            draw,
            plain,
            width,
            (
                self.font_detail,
                self.font_small,
                self.font_tiny,
            ),
        )
        if draw.textlength(plain, font=font) > width:
            self._fit_text(
                draw,
                plain,
                x,
                y,
                width,
                font,
                self.TEXT,
            )
            return

        cursor = x
        for text_value, color in segments:
            draw.text(
                (cursor, y),
                text_value,
                font=font,
                fill=color,
            )
            cursor += draw.textlength(text_value, font=font)

    def _result_segments(self, value, accent):
        """Split result text so failed/skipped counts carry lifecycle colour."""

        text = self._clean(value)
        if " | " not in text:
            return [(text, self.TEXT)]
        primary, exceptional = text.split(" | ", 1)
        return [
            (primary, self.TEXT),
            (" | ", self.MUTED),
            (exceptional, accent),
        ]

    @staticmethod
    def _select_font(draw, text, width, fonts):
        selected = fonts[-1]
        for font in fonts:
            if draw.textlength(text, font=font) <= width:
                return font
            selected = font
        return selected

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

    @staticmethod
    def _wrapped_text_lines(
        draw,
        text,
        width,
        font,
    ):
        words = str(text or "").split()
        lines = []
        current = ""

        def split_token(token):
            if draw.textlength(token, font=font) <= width:
                return [token]
            parts = []
            chunk = ""
            for character in token:
                candidate = chunk + character
                if (
                    chunk
                    and draw.textlength(
                        candidate,
                        font=font,
                    )
                    > width
                ):
                    parts.append(chunk)
                    chunk = character
                else:
                    chunk = candidate
            if chunk:
                parts.append(chunk)
            return parts

        for word in words:
            for part in split_token(word):
                candidate = f"{current} {part}".strip()
                if (
                    not current
                    or draw.textlength(
                        candidate,
                        font=font,
                    )
                    <= width
                ):
                    current = candidate
                    continue
                lines.append(current)
                current = part
        if current:
            lines.append(current)
        return lines

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
        max_lines=None,
        line_gap,
    ):
        lines = self._wrapped_text_lines(
            draw,
            self._clean(text),
            width,
            font,
        )
        if max_lines is not None and len(lines) > max_lines:
            lines = lines[:max_lines]
            last = lines[-1]
            while (
                last
                and draw.textlength(
                    last + "…",
                    font=font,
                )
                > width
            ):
                last = last[:-1]
            lines[-1] = last.rstrip() + "…"

        line_h = (
            font.getbbox("Ag")[3]
            - font.getbbox("Ag")[1]
        )
        for index, line in enumerate(lines):
            draw.text(
                (
                    x,
                    y + index * (line_h + line_gap),
                ),
                line,
                font=font,
                fill=fill,
            )
        return len(lines)

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
