"""High-readability Discord Modern cards for Nowlert integrations."""

from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from io import BytesIO
from pathlib import Path
import re

from PIL import Image, ImageDraw

from formatters.discord_xo_image import XenOrchestraDiscordImageRenderer
from formatters.presentation import PresentationMixin
from models import Notification


class DiscordModernImageRenderer(XenOrchestraDiscordImageRenderer):
    """Render Classic Card v1 content in the approved Nowlert visual system."""

    WIDTH = 1448
    MIN_HEIGHT = 760
    HEADER_Y = 70
    TITLE_Y = 214
    SUMMARY_Y = 316
    CONTENT_TOP = 412
    FOOTER_RESERVE = 128
    SECTION_GAP = 22
    COLUMN_GAP = 22
    CARD_PADDING = 70
    HEADER_ICON_WIDTH = 150
    HEADER_ICON_HEIGHT = 112
    STATUS_BADGE_WIDTH = 420
    PAIR_MAX_HEIGHT = 210
    PAIR_MAX_LINES = 5
    HEADER_LOGO_WIDTHS = {
        "qnap": 230,
        "synology": 220,
        "unifi_network": 240,
        "unifi_protect": 220,
        "unifi_drive": 220,
        "dell_idrac": 190,
        "supermicro": 190,
        "hpe_ilo": 180,
        "redfish": 180,
    }

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

    SECTION_PROFILES = {
        "zabbix": (
            ("Problem", ("problem", "operational data"), False),
            ("Trigger", ("trigger", "problem id"), False),
            ("Response", ("runbook", "timing"), False),
        ),
        "grafana": (
            ("Rule & Location", ("rule", "location"), False),
            ("Data", ("datasource", "labels", "values"), False),
            ("Alert details", ("alerts", "evaluation error"), True),
            ("Timing & Links", ("timing", "links"), False),
        ),
        "portainer": (
            ("Environment", ("portainer", "authentication"), False),
            ("Signal", ("signal", "grouped alerts"), False),
            ("Timing", ("timing",), False),
        ),
        "proxmox": (
            ("Proxmox VE", ("proxmox ve",), False),
            ("Job & Storage", ("backup", "storage"), False),
            ("Timing", ("timing",), False),
        ),
        "qnap": (
            ("QNAP NAS", ("qnap nas",), False),
            (
                "Event details",
                ("storage", "security", "system", "backup", "power"),
                False,
            ),
            ("Timing", ("timing",), False),
        ),
        "synology": (
            ("Synology NAS", ("synology nas",), False),
            ("Event details", ("storage", "backup", "power"), False),
            ("Timing", ("timing",), False),
        ),
        "truenas": (
            ("TrueNAS System", ("truenas system",), False),
            (
                "Event details",
                (
                    "disk",
                    "power",
                    "storage",
                    "notification test",
                    "scrub",
                    "replication",
                ),
                False,
            ),
            ("Grouped Alerts", ("grouped alerts",), True),
            ("Timing", ("timing",), False),
        ),
        "unifi_network": (
            (
                "Controller & Network",
                ("unifi controller", "network / wi-fi"),
                False,
            ),
            (
                "Client / Access Point",
                ("client", "last access point"),
                False,
            ),
            ("Timing", ("timing",), False),
        ),
        "unifi_protect": (
            ("Trigger", ("trigger",), False),
            ("Alarm Rule", ("alarm rule",), False),
            ("Timing", ("timing",), False),
        ),
        "unifi_drive": (
            ("Drive Event", ("alarm",), True),
            ("Timing", ("timing",), False),
        ),
        "supermicro": (
            ("System", ("supermicro bmc",), False),
            ("Hardware Event", ("hardware event",), False),
            ("Timing", ("timing",), False),
        ),
        "hpe_ilo": (
            ("System", ("hpe ilo",), False),
            ("Hardware Event", ("hardware event",), False),
            ("Timing", ("timing",), False),
        ),
        "dell_idrac": (
            ("System", ("dell idrac",), False),
            ("Hardware Event", ("hardware event",), False),
            ("Timing", ("timing",), False),
        ),
        "home_assistant": (
            (
                "Home Assistant",
                ("home assistant", "entity / device"),
                False,
            ),
            ("Source Details", ("source details",), True),
            ("Timing", ("timing",), False),
        ),
        "redfish": (
            ("Source & Event", ("source", "hardware event"), False),
            ("Recommended Action", ("recommended action",), True),
            ("Timing", ("timing",), False),
        ),
        "generic": (
            ("Source & Context", ("source", "email", "context"), False),
            ("Timing", ("timing",), False),
        ),
        "nowlert": (
            ("Source & Context", ("source", "context"), False),
            ("Timing", ("timing",), False),
        ),
    }

    MARKDOWN_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")
    MARKDOWN_MARKS = re.compile(r"(\*\*|__|~~|\x60)")
    LEADING_SYMBOLS = re.compile(r"^[^A-Za-z0-9]+")
    STATUS_SUFFIX = re.compile(
        r"\s+[—-]\s+(Success|Successful|Failed|Failure|Warning|"
        r"Information|Resolved|Recovered|Firing|Pending|Skipped|Updated)\s*$",
        re.IGNORECASE,
    )

    def __init__(self, icon_dir: Path | str = "/nowlert/assets/icons"):
        super().__init__(icon_dir)
        self.font_section = self._font(True, 35)
        self.font_message = self._font(False, 31)
        self.font_message_small = self._font(False, 28)
        self.font_field = self._font(True, 28)
        self.font_value = self._font(False, 30)
        self.font_value_small = self._font(False, 27)
        self.font_header_context = self._font(False, 28)
        self.font_summary = self._font(False, 27)

    def render(
        self,
        notification: Notification,
        classic_payload: dict,
    ) -> bytes:
        embed = self._embed(classic_payload)
        source = (
            str(notification.source or "generic").strip().casefold()
            or "generic"
        )
        integration = self.INTEGRATION_NAMES.get(
            source,
            self._label(source) or "Nowlert",
        )
        accent = self._embed_accent(embed)
        lifecycle = self._lifecycle(embed, notification)
        status_kind = self._status_kind(lifecycle, accent)
        title = self._event_title(embed, notification, lifecycle)
        description = self._description(embed, title)
        raw_fields = self._fields(embed)
        sections = self._build_sections(source, raw_fields)
        severity = self._summary_severity(notification, lifecycle)
        category = self._summary_category(notification)
        event_time = self._summary_time(notification, raw_fields)
        context = self._context(notification, integration)

        dummy = Image.new("RGB", (self.WIDTH, 1))
        measure = ImageDraw.Draw(dummy)
        content_width = self.WIDTH - self.CARD_PADDING * 2

        message_lines = []
        message_height = 0
        if description:
            message_lines = self._wrapped_lines(
                measure,
                description,
                content_width - 58,
                self.font_message,
            )
            message_height = max(
                116,
                68 + len(message_lines) * 40,
            )

        current_y = self.CONTENT_TOP
        if message_height:
            current_y += message_height + self.SECTION_GAP

        layout, details_height = self._section_layout(
            measure,
            sections,
            content_width,
        )
        if not sections and not description:
            details_height = 118

        height = max(
            self.MIN_HEIGHT,
            (
                current_y
                + details_height
                + 34
                + self.FOOTER_RESERVE
            ),
        )
        footer_y = self._footer_y(height)

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

        self._draw_header(
            image,
            draw,
            source,
            integration,
            context,
            lifecycle,
            accent,
            status_kind,
            x0,
            right,
        )
        self._draw_event_title(
            draw,
            title,
            x0,
            right,
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

        content_y = self.CONTENT_TOP
        if message_height:
            self._draw_message(
                draw,
                x0,
                right,
                content_y,
                message_height,
                message_lines,
            )
            content_y += message_height + self.SECTION_GAP

        if sections:
            self._draw_sections(
                draw,
                x0,
                content_y,
                layout,
                accent,
            )
        else:
            self._draw_empty_details(
                draw,
                x0,
                right,
                content_y,
            )

        self._draw_footer(
            image,
            draw,
            x0,
            right,
            footer_y,
        )

        output = BytesIO()
        image.convert("RGB").save(
            output,
            format="PNG",
            optimize=True,
            compress_level=7,
        )
        return output.getvalue()

    def _draw_header(
        self,
        image,
        draw,
        source,
        integration,
        context,
        lifecycle,
        accent,
        status_kind,
        x0,
        right,
    ):
        logo_width = self.HEADER_LOGO_WIDTHS.get(
            source,
            self.HEADER_ICON_WIDTH,
        )
        self._draw_product_icon(
            image,
            source,
            x0,
            self.HEADER_Y - 8,
            logo_width,
            self.HEADER_ICON_HEIGHT,
        )
        title_x = x0 + logo_width + 18
        header_text_width = max(
            340,
            (
                right
                - self.STATUS_BADGE_WIDTH
                - 24
                - title_x
            ),
        )
        draw.text(
            (title_x, self.HEADER_Y + 1),
            integration,
            font=self.font_heading,
            fill=self.TEXT,
        )
        self._fit_text_adaptive(
            draw,
            context,
            title_x,
            self.HEADER_Y + 62,
            header_text_width,
            (
                self.font_header_context,
                self.font_body,
                self.font_small,
            ),
            self.HEADER_MUTED,
        )

        badge_w = self.STATUS_BADGE_WIDTH
        badge_h = 82
        badge_x = right - badge_w
        badge = (
            badge_x,
            self.HEADER_Y + 2,
            right,
            self.HEADER_Y + 2 + badge_h,
        )
        self._glow_box(
            image,
            badge,
            accent,
            17,
            alpha=self.STATUS_GLOW_ALPHA,
        )
        draw = ImageDraw.Draw(image, "RGBA")
        self._rounded(
            draw,
            badge,
            fill=(*self._tint(accent, self.CARD_BG, 0.16), 245),
            outline=(*accent, 230),
            radius=17,
            width=2,
        )
        self._status_icon(
            draw,
            badge_x + 22,
            self.HEADER_Y + 20,
            48,
            status_kind,
            accent,
        )
        self._fit_text_adaptive(
            draw,
            lifecycle,
            badge_x + 88,
            self.HEADER_Y + 22,
            badge_w - 114,
            (
                self.font_bold,
                self.font_label,
                self.font_small,
            ),
            accent,
        )

    def _draw_event_title(self, draw, title, x0, right):
        box = (
            x0,
            self.TITLE_Y,
            right,
            self.TITLE_Y + 78,
        )
        self._rounded(
            draw,
            box,
            fill=(*self.PANEL_2, 248),
            outline=(93, 101, 108, 195),
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
        height = 78
        self._rounded(
            draw,
            (x0, y, right, y + height),
            fill=(*self.PANEL, 248),
            outline=(*self.PANEL_BORDER, 205),
            radius=14,
            width=1,
        )
        metrics = [
            ("status", "Severity", severity, accent, status_kind),
            ("sync", "Category", category, self.ICON_BLUE, None),
            ("clock", "Event time", event_time or "—", (194, 226, 242), None),
        ]
        widths = [365, 365, right - x0 - 730]
        mx = x0 + 26
        for index, ((icon, label, value, color, status), width) in enumerate(
            zip(metrics, widths)
        ):
            self._draw_icon_badge(
                draw,
                mx,
                y + 14,
                46,
                icon,
                color,
                status=status,
            )
            label_x = mx + 64
            label_text = f"{label}:"
            draw.text(
                (label_x, y + 21),
                label_text,
                font=self.font_label,
                fill=self.TEXT,
            )
            label_w = draw.textlength(
                label_text,
                font=self.font_label,
            )
            self._fit_text_adaptive(
                draw,
                value,
                label_x + label_w + 12,
                y + 22,
                width - 84 - label_w,
                (
                    self.font_summary,
                    self.font_small,
                    self.font_tiny,
                ),
                self.TEXT,
            )
            if index < 2:
                line_x = mx + width - 8
                draw.line(
                    (
                        line_x,
                        y + 18,
                        line_x,
                        y + height - 18,
                    ),
                    fill=(102, 112, 119, 160),
                    width=2,
                )
            mx += width

    def _draw_message(
        self,
        draw,
        x0,
        right,
        y,
        height,
        lines,
    ):
        box = (x0, y, right, y + height)
        self._rounded(
            draw,
            box,
            fill=(*self.PANEL, 248),
            outline=(*self.PANEL_BORDER, 210),
            radius=15,
            width=2,
        )
        self._draw_field_icon(
            draw,
            x0 + 24,
            y + 17,
            36,
            "list",
        )
        draw.text(
            (x0 + 70, y + 18),
            "Event message",
            font=self.font_section,
            fill=self.LABEL,
        )
        line_y = y + 66
        for line in lines:
            draw.text(
                (x0 + 28, line_y),
                line,
                font=self.font_message,
                fill=self.TEXT,
            )
            line_y += 40

    def _draw_empty_details(self, draw, x0, right, y):
        box = (x0, y, right, y + 118)
        self._rounded(
            draw,
            box,
            fill=(*self.PANEL_2, 248),
            outline=(*self.PANEL_BORDER, 195),
            radius=15,
            width=2,
        )
        draw.text(
            (x0 + 28, y + 40),
            "No additional event details.",
            font=self.font_message,
            fill=self.MUTED,
        )

    def _draw_footer(self, image, draw, x0, right, y):
        draw.line(
            (x0, y - 8, right, y - 8),
            fill=(81, 89, 95, 150),
            width=1,
        )
        icon_size = 40
        self._draw_nowlert_icon(
            image,
            x0 + 18,
            y + 4,
            icon_size,
        )
        draw.text(
            (x0 + 18 + icon_size + 12, y + 10),
            self.FOOTER_TEXT,
            font=self.font_small,
            fill=self.MUTED,
        )

    def _build_sections(self, source, fields):
        prepared = []
        for field in fields:
            name = self._field_title(field.get("name"))
            value = self._plain(
                field.get("value"),
                preserve_lines=True,
            )
            if not value:
                continue
            normalized = self._normalize_field_name(name)
            if normalized in {"timing", "time"}:
                value = self._normalize_timing_block(value)
            if normalized == "alert":
                # The Alert field repeats severity already shown in the summary.
                continue
            prepared.append(
                {
                    "name": name,
                    "normalized": normalized,
                    "value": value,
                }
            )

        profile = self.SECTION_PROFILES.get(
            source,
            self.SECTION_PROFILES["generic"],
        )
        used = set()
        sections = []

        for title, patterns, full_width in profile:
            matched = []
            for index, field in enumerate(prepared):
                if index in used:
                    continue
                if any(
                    self._field_matches(
                        field["normalized"],
                        pattern,
                    )
                    for pattern in patterns
                ):
                    matched.append(field)
                    used.add(index)
            if not matched:
                continue
            force_full = full_width or any(
                (
                    field["normalized"].startswith("grouped alerts")
                    or field["normalized"].startswith("alerts ")
                )
                for field in matched
            )
            section_title = title
            if (
                title == "Event details"
                and len(matched) == 1
            ):
                section_title = matched[0]["name"]

            sections.append(
                {
                    "title": section_title,
                    "fields": matched,
                    "full_width": force_full,
                }
            )

        leftovers = [
            field
            for index, field in enumerate(prepared)
            if index not in used
        ]
        if leftovers:
            sections.append(
                {
                    "title": "Additional details",
                    "fields": leftovers,
                    "full_width": len(leftovers) > 2,
                }
            )
        return sections

    def _section_layout(self, draw, sections, content_width):
        if not sections:
            return [], 0

        column_width = (
            content_width - self.COLUMN_GAP
        ) // 2
        layout = []
        y = 0
        index = 0

        while index < len(sections):
            current = sections[index]
            if current["full_width"]:
                measured = self._measure_section(
                    draw,
                    current,
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
                continue

            if (
                index + 1 < len(sections)
                and not sections[index + 1]["full_width"]
            ):
                left = self._measure_section(
                    draw,
                    current,
                    column_width,
                )
                right = self._measure_section(
                    draw,
                    sections[index + 1],
                    column_width,
                )
                if (
                    self._section_can_pair(left)
                    and self._section_can_pair(right)
                ):
                    row_height = max(
                        left["height"],
                        right["height"],
                    )
                    left.update(
                        {
                            "x": 0,
                            "y": y,
                            "width": column_width,
                            "height": row_height,
                        }
                    )
                    right.update(
                        {
                            "x": column_width + self.COLUMN_GAP,
                            "y": y,
                            "width": column_width,
                            "height": row_height,
                        }
                    )
                    layout.extend((left, right))
                    y += row_height + self.SECTION_GAP
                    index += 2
                    continue

            measured = self._measure_section(
                draw,
                current,
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

    def _section_can_pair(self, measured):
        return (
            measured["height"] <= self.PAIR_MAX_HEIGHT
            and measured["line_count"] <= self.PAIR_MAX_LINES
            and measured["field_count"] <= 2
        )

    def _measure_section(self, draw, section, width):
        inner_width = width - 54
        content = []
        height = 70
        line_count = 0
        hide_single_name = (
            len(section["fields"]) == 1
            and self._normalize_field_name(
                section["title"]
            )
            == section["fields"][0]["normalized"]
        )

        for field_index, field in enumerate(section["fields"]):
            show_name = not (
                hide_single_name
                and field_index == 0
            )
            field_content = {
                "name": field["name"],
                "show_name": show_name,
                "lines": [],
            }
            if show_name:
                height += 36

            for raw_line in field["value"].split("\n"):
                raw_line = raw_line.strip()
                if not raw_line:
                    continue
                wrapped = self._wrapped_lines(
                    draw,
                    raw_line,
                    inner_width,
                    self.font_value,
                )
                if not wrapped:
                    wrapped = ["—"]
                field_content["lines"].extend(
                    wrapped
                )
                line_count += len(wrapped)
                height += len(wrapped) * 38

            if field_index + 1 < len(section["fields"]):
                height += 16
            content.append(field_content)

        return {
            "title": section["title"],
            "content": content,
            "height": max(134, height + 20),
            "line_count": line_count,
            "field_count": len(section["fields"]),
        }

    def _draw_sections(
        self,
        draw,
        x0,
        y0,
        layout,
        accent,
    ):
        for section in layout:
            x1 = x0 + section["x"]
            y1 = y0 + section["y"]
            x2 = x1 + section["width"]
            y2 = y1 + section["height"]
            self._rounded(
                draw,
                (x1, y1, x2, y2),
                fill=(*self.PANEL_2, 248),
                outline=(*self.PANEL_BORDER, 210),
                radius=15,
                width=2,
            )
            self._draw_field_icon(
                draw,
                x1 + 22,
                y1 + 17,
                36,
                self._section_icon(section["title"]),
            )
            draw.text(
                (x1 + 70, y1 + 18),
                section["title"],
                font=self.font_section,
                fill=self.LABEL,
            )

            line_y = y1 + 68
            for field_index, field in enumerate(
                section["content"]
            ):
                if field["show_name"]:
                    draw.text(
                        (x1 + 28, line_y),
                        field["name"],
                        font=self.font_field,
                        fill=self.HEADER_MUTED,
                    )
                    line_y += 36

                for line in field["lines"]:
                    self._draw_detail_line(
                        draw,
                        line,
                        x1 + 28,
                        line_y,
                        section["width"] - 56,
                        accent,
                    )
                    line_y += 38

                if field_index + 1 < len(
                    section["content"]
                ):
                    line_y += 16

    def _draw_detail_line(
        self,
        draw,
        line,
        x,
        y,
        width,
        accent,
    ):
        color = self._line_color(
            line,
            accent,
        )
        key, value = self._split_key_value(line)
        if not key:
            self._fit_text_adaptive(
                draw,
                line,
                x,
                y,
                width,
                (
                    self.font_value,
                    self.font_value_small,
                    self.font_tiny,
                ),
                color,
            )
            return

        key_text = f"{key}:"
        draw.text(
            (x, y),
            key_text,
            font=self.font_field,
            fill=self.LABEL,
        )
        key_width = draw.textlength(
            key_text,
            font=self.font_field,
        )
        value_x = x + key_width + 12
        available = width - key_width - 12
        if available < 150:
            value_x = x
            available = width
        self._fit_text_adaptive(
            draw,
            value,
            value_x,
            y + 1,
            available,
            (
                self.font_value,
                self.font_value_small,
                self.font_tiny,
            ),
            color,
        )

    def _draw_product_icon(
        self,
        image,
        source,
        x,
        y,
        box_width,
        box_height,
    ):
        candidates = []
        discord_icon = (
            PresentationMixin.DISCORD_PRODUCT_ICONS.get(
                source
            )
        )
        product_icon = PresentationMixin.PRODUCT_ICONS.get(
            source
        )
        if discord_icon:
            candidates.append(discord_icon)
        if (
            product_icon
            and product_icon not in candidates
        ):
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
                scale = min(
                    box_width / icon.width,
                    box_height / icon.height,
                )
                icon = icon.resize(
                    (
                        max(
                            1,
                            int(
                                round(
                                    icon.width * scale
                                )
                            ),
                        ),
                        max(
                            1,
                            int(
                                round(
                                    icon.height * scale
                                )
                            ),
                        ),
                    ),
                    Image.Resampling.LANCZOS,
                )
                px = int(
                    x + (box_width - icon.width) / 2
                )
                py = int(
                    y + (box_height - icon.height) / 2
                )
                image.alpha_composite(
                    icon,
                    (px, py),
                )
                return
            except OSError:
                continue

        draw = ImageDraw.Draw(image, "RGBA")
        self._rounded(
            draw,
            (
                x + 8,
                y + 8,
                x + box_height - 8,
                y + box_height - 8,
            ),
            fill=(37, 40, 42, 245),
            outline=(*self.BRAND_GOLD, 190),
            radius=18,
            width=2,
        )
        initial = (
            self.INTEGRATION_NAMES.get(source)
            or "N"
        )[:1].upper()
        font = self._font(
            True,
            int(box_height * 0.44),
        )
        bbox = draw.textbbox(
            (0, 0),
            initial,
            font=font,
        )
        draw.text(
            (
                x
                + (
                    box_height
                    - (bbox[2] - bbox[0])
                )
                / 2,
                y
                + (
                    box_height
                    - (bbox[3] - bbox[1])
                )
                / 2
                - 4,
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
        if (
            not isinstance(embeds, list)
            or not embeds
        ):
            return {}
        embed = embeds[0]
        return (
            embed
            if isinstance(embed, dict)
            else {}
        )

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
        value = (
            embed.get("color")
            if isinstance(embed, dict)
            else None
        )
        if (
            isinstance(value, int)
            and 0 <= value <= 0xFFFFFF
        ):
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
            }.get(
                value.casefold(),
                value.title(),
            )

        status = str(
            notification.status or ""
        ).strip()
        metadata = notification.metadata or {}
        severity = str(
            metadata.get("severity") or ""
        ).strip()
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

    def _event_title(
        self,
        embed,
        notification,
        lifecycle,
    ):
        title = self._plain(
            embed.get("title") or ""
        )
        title = self.STATUS_SUFFIX.sub(
            "",
            title,
        ).strip()
        title = self.LEADING_SYMBOLS.sub(
            "",
            title,
        ).strip()
        if title:
            return title
        source = str(
            notification.source or ""
        ).casefold()
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
        if (
            self._normalize(value)
            == self._normalize(title)
        ):
            return ""
        return value

    def _summary_severity(
        self,
        notification,
        lifecycle,
    ):
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

    def _summary_time(
        self,
        notification,
        fields,
    ):
        metadata = notification.metadata or {}
        candidates = (
            metadata.get("event_time"),
            notification.end_time,
            notification.start_time,
        )
        for candidate in candidates:
            formatted = self._format_time(
                candidate
            )
            if formatted:
                return formatted

        for field in fields:
            name = self._normalize_field_name(
                self._field_title(
                    field.get("name")
                )
            )
            if name not in {
                "timing",
                "time",
                "event",
            }:
                continue
            value = self._plain(
                field.get("value"),
                preserve_lines=True,
            )
            for line in value.split("\n"):
                _key, candidate = (
                    self._split_key_value(line)
                )
                formatted = self._format_time(
                    candidate
                )
                if formatted:
                    return formatted
        return ""

    def _format_time(self, value):
        text = self._plain(value)
        if (
            not text
            or text in {"—", "-"}
        ):
            return ""

        numeric = text.replace(".", "", 1)
        if numeric.isdigit():
            try:
                number = float(text)
                if number > 100000000000:
                    number /= 1000.0
                if number > 100000000:
                    parsed = datetime.fromtimestamp(
                        number,
                        tz=timezone.utc,
                    )
                    return parsed.strftime(
                        "%Y-%m-%d %H:%M:%S UTC"
                    )
            except (
                OverflowError,
                OSError,
                ValueError,
            ):
                pass

        iso_candidate = text
        if iso_candidate.endswith("Z"):
            iso_candidate = (
                iso_candidate[:-1] + "+00:00"
            )
        try:
            parsed = datetime.fromisoformat(
                iso_candidate
            )
            if parsed.tzinfo is None:
                return parsed.strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            parsed = parsed.astimezone(
                timezone.utc
            )
            return parsed.strftime(
                "%Y-%m-%d %H:%M:%S UTC"
            )
        except ValueError:
            pass

        try:
            parsed = parsedate_to_datetime(text)
            if parsed.tzinfo is None:
                return parsed.strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            parsed = parsed.astimezone(
                timezone.utc
            )
            return parsed.strftime(
                "%Y-%m-%d %H:%M:%S UTC"
            )
        except (
            TypeError,
            ValueError,
            OverflowError,
        ):
            return text

    def _normalize_timing_block(self, value):
        lines = []
        for raw_line in self._plain(
            value,
            preserve_lines=True,
        ).split("\n"):
            line = raw_line.strip()
            if not line:
                continue
            key, candidate = self._split_key_value(
                line
            )
            if not key:
                lines.append(line)
                continue
            formatted = self._format_time(
                candidate
            )
            lines.append(
                f"{key}: {formatted or candidate}"
            )
        return "\n".join(lines)

    def _context(
        self,
        notification,
        integration,
    ):
        metadata = notification.metadata or {}
        source = (
            str(
                notification.source
                or "generic"
            )
            .strip()
            .casefold()
            or "generic"
        )
        for key in self.CONTEXT_KEYS.get(
            source,
            (),
        ):
            text = self._plain(
                metadata.get(key)
            )
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
            text = self._plain(
                metadata.get(key)
            )
            if text:
                return text
        category = self._label(
            notification.category
        )
        if (
            category
            and category != "Generic"
        ):
            return category
        return integration

    def _field_title(self, value):
        text = self._plain(value)
        text = self.LEADING_SYMBOLS.sub(
            "",
            text,
        ).strip()
        return (
            text
            or "Event details"
        )

    @staticmethod
    def _normalize_field_name(value):
        return " ".join(
            str(value or "")
            .casefold()
            .replace("•", " ")
            .split()
        )

    @staticmethod
    def _field_matches(name, pattern):
        normalized = str(name or "")
        pattern = str(pattern or "")
        return (
            normalized == pattern
            or normalized.startswith(
                pattern + " "
            )
            or normalized.startswith(
                pattern + " ("
            )
        )

    @staticmethod
    def _section_icon(title):
        value = str(
            title or ""
        ).casefold()
        if any(
            token in value
            for token in (
                "timing",
                "time",
                "response",
            )
        ):
            return "clock"
        if any(
            token in value
            for token in (
                "storage",
                "disk",
                "data",
                "repository",
            )
        ):
            return "repository"
        if any(
            token in value
            for token in (
                "alert",
                "problem",
                "signal",
                "event",
                "trigger",
            )
        ):
            return "chart"
        return "list"

    @staticmethod
    def _status_kind(
        lifecycle,
        accent,
    ):
        value = str(
            lifecycle or ""
        ).casefold()
        if any(
            token in value
            for token in (
                "fail",
                "critical",
                "error",
            )
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
        if (
            accent[0] > 200
            and accent[1] < 150
        ):
            return "failure"
        return "skipped"

    def _line_color(
        self,
        line,
        accent,
    ):
        normalized = str(
            line or ""
        ).casefold()
        if self._contains_status_word(
            normalized,
            (
                "failed",
                "failure",
                "critical",
                "error",
                "unrecoverable",
            ),
        ):
            return self.FAILURE
        if self._contains_status_word(
            normalized,
            (
                "warning",
                "warn",
                "degraded",
                "predictive",
                "pending",
                "updated",
            ),
        ):
            return self.BRAND_GOLD
        if self._contains_status_word(
            normalized,
            (
                "success",
                "resolved",
                "healthy",
                "normal",
                "recovered",
                "cleared",
            ),
        ):
            return self.SUCCESS
        return self.TEXT

    @staticmethod
    def _contains_status_word(
        value,
        words,
    ):
        if not value:
            return False
        pattern = (
            r"(?<![A-Za-z0-9_])(?:"
            + "|".join(
                re.escape(word)
                for word in words
            )
            + r")(?![A-Za-z0-9_])"
        )
        return re.search(
            pattern,
            value,
            re.IGNORECASE,
        ) is not None

    @staticmethod
    def _split_key_value(line):
        text = str(
            line or ""
        ).strip()
        if ":" not in text:
            return "", text
        key, value = text.split(
            ":",
            1,
        )
        key = key.strip()
        value = value.strip()
        if (
            not key
            or not value
            or len(key) > 30
        ):
            return "", text
        return key, value

    def _plain(
        self,
        value,
        preserve_lines=False,
    ):
        if value is None:
            return ""
        text = str(value).replace(
            "\r",
            "",
        )
        text = self.MARKDOWN_LINK.sub(
            r"\1",
            text,
        )
        text = self.MARKDOWN_MARKS.sub(
            "",
            text,
        )
        text = text.replace(
            "\\n",
            "\n",
        )
        if preserve_lines:
            lines = [
                " ".join(
                    line.split()
                )
                for line in text.split("\n")
            ]
            return "\n".join(
                line
                for line in lines
                if line
            ).strip()
        return " ".join(
            text.split()
        ).strip()

    @staticmethod
    def _normalize(value):
        return " ".join(
            str(
                value or ""
            )
            .casefold()
            .split()
        )

    @staticmethod
    def _label(value):
        words = re.sub(
            r"[_-]+",
            " ",
            str(
                value or ""
            ).strip(),
        ).split()
        acronyms = {
            "qnap",
            "ups",
            "ip",
            "id",
        }
        return (
            " ".join(
                word.upper()
                if word.casefold()
                in acronyms
                else word.capitalize()
                for word in words
            )
            or "Generic"
        )

    def _wrapped_lines(
        self,
        draw,
        value,
        width,
        font,
    ):
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
                for part in self._split_long_token(
                    draw,
                    word,
                    width,
                    font,
                ):
                    candidate = (
                        f"{current} {part}"
                        .strip()
                    )
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

    @staticmethod
    def _split_long_token(
        draw,
        token,
        width,
        font,
    ):
        if draw.textlength(token, font=font) <= width:
            return [token]

        parts = []
        current = ""
        for character in token:
            candidate = current + character
            if (
                current
                and draw.textlength(
                    candidate,
                    font=font,
                )
                > width
            ):
                parts.append(current)
                current = character
            else:
                current = candidate
        if current:
            parts.append(current)
        return parts
