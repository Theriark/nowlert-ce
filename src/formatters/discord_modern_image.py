"""Image renderer for Discord Modern cards outside Xen Orchestra."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
import re

from PIL import Image, ImageDraw

from formatters.discord_xo_image import XenOrchestraDiscordImageRenderer
from formatters.presentation import PresentationMixin
from models import Notification


class DiscordModernImageRenderer(XenOrchestraDiscordImageRenderer):
    """Render Classic Card v1 information in the approved XO visual system."""

    WIDTH = 1448
    HEADER_Y = 72
    TITLE_Y = 208
    SUMMARY_Y = 304
    CONTENT_TOP = 398
    FOOTER_RESERVE = 116
    SECTION_GAP = 18
    COLUMN_GAP = 18
    CARD_PADDING = 70

    INTEGRATION_NAMES = {
        "xo": "Xen Orchestra",
        "nowlert": "Nowlert",
        "zabbix": "Zabbix",
        "grafana": "Grafana",
        "portainer": "Portainer",
        "proxmox": "Proxmox",
        "qnap": "QNAP",
        "synology": "Synology",
        "truenas": "TrueNAS",
        "unifi_network": "UniFi Network",
        "unifi_protect": "UniFi Protect",
        "unifi_drive": "UniFi Drive",
        "supermicro": "Supermicro",
        "hpe_ilo": "HPE iLO",
        "dell_idrac": "Dell iDRAC",
        "home_assistant": "Home Assistant",
        "redfish": "Redfish",
        "generic": "Generic Webhook",
    }

    CONTEXT_KEYS = {
        "zabbix": ("host", "hostname"),
        "grafana": ("rule_name", "alert_rule", "folder", "host"),
        "portainer": ("instance", "endpoint", "host"),
        "proxmox": ("node", "cluster", "host"),
        "qnap": ("nas_name", "hostname", "host"),
        "synology": ("nas_name", "hostname", "host"),
        "truenas": ("host", "hostname"),
        "unifi_network": ("controller", "network_name", "wifi_name"),
        "unifi_protect": ("trigger_device", "alarm_name", "controller"),
        "unifi_drive": ("system", "backup_task"),
        "supermicro": ("system", "host"),
        "hpe_ilo": ("system", "host"),
        "dell_idrac": ("system", "host"),
        "home_assistant": ("device", "area", "entity_id"),
        "redfish": ("system", "provider", "host"),
        "nowlert": ("host", "component"),
        "generic": ("host", "device", "provider"),
    }

    MARKDOWN_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")
    MARKDOWN_MARKS = re.compile(r"(\*\*|__|~~|\x60)")
    LEADING_SYMBOLS = re.compile(r"^[^A-Za-z0-9]+")
    STATUS_SUFFIX = re.compile(
        r"\s+[—-]\s+(Success|Successful|Failed|Failure|Warning|"
        r"Information|Resolved|Recovered|Firing|Pending|Skipped)\s*$",
        re.IGNORECASE,
    )

    def __init__(self, icon_dir: Path | str = "/nowlert/assets/icons"):
        super().__init__(icon_dir)
        self.font_section = self._font(True, 25)
        self.font_message = self._font(False, 23)
        self.font_value = self._font(False, 21)
        self.font_value_small = self._font(False, 18)
        self.font_header_context = self._font(False, 22)

    def render(
        self,
        notification: Notification,
        classic_payload: dict,
    ) -> bytes:
        embed = self._embed(classic_payload)
        source = str(notification.source or "generic").strip().casefold() or "generic"
        integration = self.INTEGRATION_NAMES.get(
            source,
            self._label(source) or "Nowlert",
        )
        accent = self._embed_accent(embed)
        lifecycle = self._lifecycle(embed, notification)
        title = self._event_title(embed, notification, lifecycle)
        description = self._description(embed, title)
        severity = self._summary_severity(notification, lifecycle)
        category = self._summary_category(notification)
        event_time = self._summary_time(notification)
        context = self._context(notification, integration)
        fields = self._fields(embed)

        dummy = Image.new("RGB", (self.WIDTH, 1))
        measure = ImageDraw.Draw(dummy)
        content_width = self.WIDTH - self.CARD_PADDING * 2

        message_height = 0
        message_lines = []
        if description:
            message_lines = self._wrapped_lines(
                measure,
                description,
                content_width - 54,
                self.font_message,
            )
            message_height = max(82, 50 + len(message_lines) * 31)

        details_top = self.CONTENT_TOP
        if message_height:
            details_top += message_height + self.SECTION_GAP

        layout, details_height = self._field_layout(
            measure,
            fields,
            content_width,
        )

        if not fields and not description:
            details_height = 94

        footer_y = details_top + details_height + 24
        height = max(
            900,
            footer_y + self.FOOTER_RESERVE,
        )

        image = self._background(self.WIDTH, height)
        self._outer_glows(image, accent, height)
        draw = ImageDraw.Draw(image, "RGBA")

        outer = (30, 38, self.WIDTH - 30, height - 38)
        self._rounded(
            draw,
            outer,
            fill=(*self.CARD_BG, 247),
            outline=(*self.PANEL_BORDER, 220),
            radius=28,
            width=2,
        )
        self._draw_status_rail(draw, accent, height)
        self._draw_gold_frame(draw, outer)

        x0 = self.CARD_PADDING
        right = self.WIDTH - self.CARD_PADDING

        self._draw_product_icon(
            image,
            source,
            x0,
            self.HEADER_Y - 7,
            104,
        )
        title_x = x0 + 120
        draw.text(
            (title_x, self.HEADER_Y + 2),
            integration,
            font=self.font_heading,
            fill=self.TEXT,
        )
        self._fit_text_adaptive(
            draw,
            context,
            title_x,
            self.HEADER_Y + 60,
            610,
            (
                self.font_body,
                self.font_header_context,
                self.font_small,
            ),
            self.HEADER_MUTED,
        )

        badge_w = 405
        badge_h = 80
        badge_x = right - badge_w
        badge = (
            badge_x,
            self.HEADER_Y + 3,
            right,
            self.HEADER_Y + 3 + badge_h,
        )
        self._glow_box(image, badge, accent, 17, alpha=76)
        draw = ImageDraw.Draw(image, "RGBA")
        self._rounded(
            draw,
            badge,
            fill=(*self._tint(accent, self.CARD_BG, 0.15), 245),
            outline=(*accent, 230),
            radius=17,
            width=2,
        )
        status_kind = self._status_kind(lifecycle, accent)
        self._status_icon(
            draw,
            badge_x + 22,
            self.HEADER_Y + 20,
            46,
            status_kind,
            accent,
        )
        self._fit_text_adaptive(
            draw,
            lifecycle,
            badge_x + 84,
            self.HEADER_Y + 22,
            badge_w - 108,
            (
                self.font_bold,
                self.font_label,
                self.font_small,
            ),
            accent,
        )

        title_box = (x0, self.TITLE_Y, right, self.TITLE_Y + 76)
        self._rounded(
            draw,
            title_box,
            fill=(*self.PANEL_2, 248),
            outline=(93, 101, 108, 190),
            radius=14,
            width=2,
        )
        self._fit_text_adaptive(
            draw,
            title,
            x0 + 28,
            self.TITLE_Y + 18,
            right - x0 - 56,
            (
                self.font_title,
                self.font_bold,
                self.font_label,
            ),
            self.TEXT,
        )

        self._draw_summary(
            draw,
            x0,
            right,
            severity,
            category,
            event_time,
            accent,
            status_kind,
        )

        current_y = self.CONTENT_TOP
        if message_height:
            box = (x0, current_y, right, current_y + message_height)
            self._rounded(
                draw,
                box,
                fill=(*self.PANEL, 248),
                outline=(*self.PANEL_BORDER, 205),
                radius=15,
                width=2,
            )
            draw.text(
                (x0 + 24, current_y + 16),
                "Event message",
                font=self.font_section,
                fill=self.LABEL,
            )
            line_y = current_y + 51
            for line in message_lines:
                draw.text(
                    (x0 + 26, line_y),
                    line,
                    font=self.font_message,
                    fill=self.TEXT,
                )
                line_y += 31
            current_y += message_height + self.SECTION_GAP

        if fields:
            self._draw_fields(
                draw,
                x0,
                current_y,
                layout,
                accent,
            )
        else:
            box = (x0, current_y, right, current_y + 94)
            self._rounded(
                draw,
                box,
                fill=(*self.PANEL_2, 248),
                outline=(*self.PANEL_BORDER, 190),
                radius=15,
                width=2,
            )
            draw.text(
                (x0 + 24, current_y + 31),
                "No additional event details.",
                font=self.font_message,
                fill=self.MUTED,
            )

        footer_line_y = footer_y
        draw.line(
            (x0, footer_line_y - 8, right, footer_line_y - 8),
            fill=(81, 89, 95, 150),
            width=1,
        )
        icon_size = 40
        self._draw_nowlert_icon(
            image,
            x0 + 18,
            footer_line_y + 4,
            icon_size,
        )
        draw.text(
            (x0 + 18 + icon_size + 12, footer_line_y + 10),
            "Nowlert CE • Modern Card",
            font=self.font_small,
            fill=self.MUTED,
        )

        output = BytesIO()
        image.convert("RGB").save(
            output,
            format="PNG",
            optimize=True,
            compress_level=7,
        )
        return output.getvalue()

    def _draw_summary(
        self,
        draw,
        x0,
        right,
        severity,
        category,
        event_time,
        accent,
        status_kind,
    ):
        y = self.SUMMARY_Y
        height = 72
        self._rounded(
            draw,
            (x0, y, right, y + height),
            fill=(*self.PANEL, 248),
            outline=(*self.PANEL_BORDER, 200),
            radius=14,
            width=1,
        )
        metrics = [
            ("status", "Severity", severity, accent, status_kind),
            ("sync", "Category", category, self.ICON_BLUE, None),
            ("clock", "Event time", event_time or "—", (194, 226, 242), None),
        ]
        widths = [350, 350, right - x0 - 700]
        mx = x0 + 26
        for index, ((icon, label, value, color, status), width) in enumerate(
            zip(metrics, widths)
        ):
            self._draw_icon_badge(
                draw,
                mx,
                y + 14,
                44,
                icon,
                color,
                status=status,
            )
            label_x = mx + 60
            draw.text(
                (label_x, y + 20),
                f"{label}:",
                font=self.font_label,
                fill=self.TEXT,
            )
            label_w = draw.textlength(f"{label}:", font=self.font_label)
            self._fit_text_adaptive(
                draw,
                value,
                label_x + label_w + 10,
                y + 21,
                width - 78 - label_w,
                (
                    self.font_detail,
                    self.font_small,
                    self.font_tiny,
                ),
                self.TEXT,
            )
            if index < 2:
                line_x = mx + width - 8
                draw.line(
                    (line_x, y + 18, line_x, y + height - 18),
                    fill=(102, 112, 119, 160),
                    width=2,
                )
            mx += width

    def _field_layout(self, draw, fields, content_width):
        col_gap = self.COLUMN_GAP
        col_width = (content_width - col_gap) // 2
        layout = []
        y = 0
        index = 0
        while index < len(fields):
            field = fields[index]
            inline = bool(field.get("inline"))
            if (
                inline
                and index + 1 < len(fields)
                and bool(fields[index + 1].get("inline"))
            ):
                left = self._measure_field(draw, field, col_width)
                right = self._measure_field(
                    draw,
                    fields[index + 1],
                    col_width,
                )
                row_h = max(left["height"], right["height"])
                left.update(
                    {
                        "x": 0,
                        "y": y,
                        "width": col_width,
                        "height": row_h,
                    }
                )
                right.update(
                    {
                        "x": col_width + col_gap,
                        "y": y,
                        "width": col_width,
                        "height": row_h,
                    }
                )
                layout.extend((left, right))
                y += row_h + self.SECTION_GAP
                index += 2
                continue

            measured = self._measure_field(
                draw,
                field,
                content_width,
            )
            measured.update(
                {
                    "x": 0,
                    "y": y,
                    "width": content_width,
                }
            )
            layout.append(measured)
            y += measured["height"] + self.SECTION_GAP
            index += 1

        return layout, max(0, y - self.SECTION_GAP)

    def _measure_field(self, draw, field, width):
        title = self._field_title(field.get("name"))
        value = self._plain(
            field.get("value"),
            preserve_lines=True,
        )
        lines = self._wrapped_lines(
            draw,
            value,
            width - 52,
            self.font_value,
        )
        if not lines:
            lines = ["—"]
        height = max(94, 58 + len(lines) * 29)
        return {
            "title": title,
            "lines": lines,
            "height": height,
        }

    def _draw_fields(self, draw, x0, y0, layout, accent):
        for item in layout:
            x1 = x0 + item["x"]
            y1 = y0 + item["y"]
            x2 = x1 + item["width"]
            y2 = y1 + item["height"]
            self._rounded(
                draw,
                (x1, y1, x2, y2),
                fill=(*self.PANEL_2, 248),
                outline=(*self.PANEL_BORDER, 205),
                radius=15,
                width=2,
            )
            self._draw_field_icon(
                draw,
                x1 + 22,
                y1 + 18,
                34,
                self._section_icon(item["title"]),
            )
            draw.text(
                (x1 + 68, y1 + 20),
                item["title"],
                font=self.font_section,
                fill=self.LABEL,
            )
            line_y = y1 + 57
            for line in item["lines"]:
                color = self.TEXT
                normalized = line.casefold()
                if any(
                    token in normalized
                    for token in (
                        "failed",
                        "failure",
                        "critical",
                        "error",
                    )
                ):
                    color = self.FAILURE
                elif any(
                    token in normalized
                    for token in ("skipped", "warning", "warn")
                ):
                    color = (
                        self.SKIPPED
                        if "skipped" in normalized
                        else self.BRAND_GOLD
                    )
                elif any(
                    token in normalized
                    for token in (
                        "success",
                        "resolved",
                        "healthy",
                        "normal",
                    )
                ):
                    color = self.SUCCESS
                self._fit_text_adaptive(
                    draw,
                    line,
                    x1 + 26,
                    line_y,
                    item["width"] - 52,
                    (
                        self.font_value,
                        self.font_value_small,
                        self.font_micro,
                    ),
                    color,
                )
                line_y += 29

    def _draw_product_icon(self, image, source, x, y, size):
        candidates = []
        discord_icon = PresentationMixin.DISCORD_PRODUCT_ICONS.get(source)
        product_icon = PresentationMixin.PRODUCT_ICONS.get(source)
        if discord_icon:
            candidates.append(discord_icon)
        if product_icon and product_icon not in candidates:
            candidates.append(product_icon)
        if source not in PresentationMixin.PRODUCT_ICONS:
            candidates.append(
                PresentationMixin.PRODUCT_ICONS["nowlert"]
            )

        for relative in candidates:
            path = self.icon_dir / relative
            if not path.is_file():
                continue
            try:
                icon = Image.open(path).convert("RGBA")
                alpha = icon.getchannel("A")
                bbox = alpha.getbbox()
                if bbox:
                    icon = icon.crop(bbox)
                if not icon.width or not icon.height:
                    continue
                scale = min(size / icon.width, size / icon.height)
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
                continue

        draw = ImageDraw.Draw(image, "RGBA")
        self._rounded(
            draw,
            (x + 8, y + 8, x + size - 8, y + size - 8),
            fill=(37, 40, 42, 245),
            outline=(*self.BRAND_GOLD, 190),
            radius=18,
            width=2,
        )
        initial = (
            self.INTEGRATION_NAMES.get(source)
            or "N"
        )[:1].upper()
        font = self._font(True, int(size * 0.44))
        bbox = draw.textbbox((0, 0), initial, font=font)
        draw.text(
            (
                x + (size - (bbox[2] - bbox[0])) / 2,
                y + (size - (bbox[3] - bbox[1])) / 2 - 4,
            ),
            initial,
            font=font,
            fill=self.TEXT,
        )

    @staticmethod
    def _embed(payload):
        if not isinstance(payload, dict):
            return {}
        embeds = payload.get("embeds")
        if not isinstance(embeds, list) or not embeds:
            return {}
        embed = embeds[0]
        return embed if isinstance(embed, dict) else {}

    @staticmethod
    def _fields(embed):
        fields = (
            embed.get("fields", [])
            if isinstance(embed, dict)
            else []
        )
        return [
            item
            for item in fields
            if isinstance(item, dict)
        ]

    def _embed_accent(self, embed):
        value = embed.get("color") if isinstance(embed, dict) else None
        if isinstance(value, int) and 0 <= value <= 0xFFFFFF:
            return (
                (value >> 16) & 0xFF,
                (value >> 8) & 0xFF,
                value & 0xFF,
            )
        return self.SKIPPED

    def _lifecycle(self, embed, notification):
        title = (
            str(embed.get("title") or "")
            if isinstance(embed, dict)
            else ""
        )
        match = self.STATUS_SUFFIX.search(
            self._plain(title)
        )
        if match:
            value = match.group(1)
            return {
                "successful": "Success",
                "failure": "Failed",
                "recovered": "Resolved",
            }.get(value.casefold(), value.title())

        status = str(notification.status or "").strip()
        metadata = notification.metadata or {}
        severity = str(metadata.get("severity") or "").strip()
        words = f"{status} {severity}".casefold()
        if any(
            token in words
            for token in (
                "critical",
                "fatal",
                "failure",
                "failed",
                "error",
                "disaster",
            )
        ):
            return "Failed"
        if any(
            token in words
            for token in (
                "warning",
                "warn",
                "degraded",
                "caution",
            )
        ):
            return "Warning"
        if any(
            token in words
            for token in (
                "success",
                "resolved",
                "recovered",
                "healthy",
                "normal",
                "ok",
            )
        ):
            return "Success"
        return "Information"

    def _event_title(self, embed, notification, lifecycle):
        title = self._plain(embed.get("title") or "")
        title = self.STATUS_SUFFIX.sub("", title).strip()
        if title:
            return title
        source = str(notification.source or "").casefold()
        return self._plain(
            notification.title
            or notification.subject
            or (
                f"{self.INTEGRATION_NAMES.get(source, 'Nowlert')} "
                "notification"
            )
        )

    def _description(self, embed, title):
        value = self._plain(
            embed.get("description") or "",
            preserve_lines=True,
        )
        if self._normalize(value) == self._normalize(title):
            return ""
        return value

    def _summary_severity(self, notification, lifecycle):
        metadata = notification.metadata or {}
        return (
            self._plain(
                metadata.get("severity")
                or notification.status
                or lifecycle
            )
            or lifecycle
        )

    def _summary_category(self, notification):
        metadata = notification.metadata or {}
        return self._label(
            notification.category
            or metadata.get("category")
            or "event"
        )

    def _summary_time(self, notification):
        metadata = notification.metadata or {}
        return self._plain(
            metadata.get("event_time")
            or notification.end_time
            or notification.start_time
            or ""
        )

    def _context(self, notification, integration):
        metadata = notification.metadata or {}
        source = (
            str(notification.source or "generic").strip().casefold()
            or "generic"
        )
        for key in self.CONTEXT_KEYS.get(source, ()):
            text = self._plain(metadata.get(key))
            if text:
                return text
        for key in (
            "host",
            "hostname",
            "device",
            "system",
            "provider",
            "source",
        ):
            text = self._plain(metadata.get(key))
            if text:
                return text
        category = self._label(notification.category)
        if category and category != "Generic":
            return category
        return integration

    def _field_title(self, value):
        text = self._plain(value)
        text = self.LEADING_SYMBOLS.sub("", text).strip()
        return text or "Event details"

    @staticmethod
    def _section_icon(title):
        value = str(title or "").casefold()
        if any(
            token in value
            for token in ("timing", "time", "duration")
        ):
            return "clock"
        if any(
            token in value
            for token in (
                "storage",
                "volume",
                "disk",
                "repository",
                "datasource",
            )
        ):
            return "repository"
        if any(
            token in value
            for token in (
                "result",
                "status",
                "alert",
                "problem",
            )
        ):
            return "chart"
        return "list"

    @staticmethod
    def _status_kind(lifecycle, accent):
        value = str(lifecycle or "").casefold()
        if any(
            token in value
            for token in ("fail", "critical", "error")
        ):
            return "failure"
        if "skip" in value:
            return "skipped"
        if any(
            token in value
            for token in (
                "success",
                "resolved",
                "recovered",
                "normal",
                "healthy",
            )
        ):
            return "success"
        if accent[0] > 200 and accent[1] < 150:
            return "failure"
        return "skipped"

    def _plain(self, value, preserve_lines=False):
        if value is None:
            return ""
        text = str(value).replace("\r", "")
        text = self.MARKDOWN_LINK.sub(r"\1", text)
        text = self.MARKDOWN_MARKS.sub("", text)
        text = text.replace("\\n", "\n")
        if preserve_lines:
            lines = [
                " ".join(line.split())
                for line in text.split("\n")
            ]
            return "\n".join(
                line for line in lines if line
            ).strip()
        return " ".join(text.split()).strip()

    @staticmethod
    def _normalize(value):
        return " ".join(
            str(value or "").casefold().split()
        )

    @staticmethod
    def _label(value):
        words = re.sub(
            r"[_-]+",
            " ",
            str(value or "").strip(),
        ).split()
        acronyms = {"qnap", "ups", "ip", "id"}
        return (
            " ".join(
                word.upper()
                if word.casefold() in acronyms
                else word.capitalize()
                for word in words
            )
            or "Generic"
        )

    def _wrapped_lines(self, draw, value, width, font):
        text = self._plain(
            value,
            preserve_lines=True,
        )
        if not text:
            return []
        lines = []
        for raw in text.split("\n"):
            words = raw.split()
            if not words:
                continue
            current = ""
            for word in words:
                candidate = f"{current} {word}".strip()
                if (
                    not current
                    or draw.textlength(candidate, font=font) <= width
                ):
                    current = candidate
                    continue
                lines.append(current)
                current = word
            if current:
                lines.append(current)
        return lines
