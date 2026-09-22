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
    MODERN_FONT_PROFILE = "default"
    MODERN_MIN_HEIGHT = 0
    MODERN_BADGE_MIN_WIDTH = 0
    MODERN_BADGE_FILL_HEADER = False
    MODERN_XO_ICON_STYLE = False
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

    def render(self, notification: Notification, classic_payload: dict) -> bytes:
        embed = self._embed(classic_payload)
        source = str(notification.source or "generic").strip().casefold() or "generic"
        integration = self.INTEGRATION_NAMES.get(source, self._label(source) or "Nowlert")
        lifecycle = self._lifecycle(embed, notification)
        status = self._status_kind(lifecycle, self._embed_accent(embed))
        if lifecycle.casefold() in {"warning", "pending", "updated"} or (
            status == "skipped" and self._embed_accent(embed)[0] > 200
            and self._embed_accent(embed)[1] > 150 and self._embed_accent(embed)[2] < 180
        ):
            status = "warning"
        accent = {"success": self.SUCCESS, "failure": self.FAILURE,
                  "warning": self.BRAND_GOLD, "skipped": self.SKIPPED}[status]
        title = self._event_title(embed, notification, lifecycle)
        description = self._description(embed, title)
        fields = self._fields(embed)
        sections = self._build_sections(source, fields)
        details, outcomes = [], []
        outcome_names = {"alert details", "grouped alerts", "recommended action", "drive event"}
        for section in sections:
            rows = []
            for field in section["fields"]:
                if field["normalized"] != self._normalize_field_name(section["title"]):
                    rows.append({"value": field["name"], "role": "label", "color": self.LABEL})
                for line in field["value"].splitlines():
                    # Classic rows delimit labels with colon + whitespace.
                    # URL schemes, timestamps and identifiers must stay intact.
                    key, value = (self._split_key_value(line)
                                  if re.match(r"^[^:]{1,30}:\s", line) else ("", line))
                    rows.append({"label": f"{key}:" if key else "", "value": value,
                                 "icon": self._section_icon(key or field["name"]),
                                 "color": self._line_color(line, accent)})
            panel = {"title": section["title"], "rows": rows,
                     "full_width": section["full_width"]}
            if section["title"].casefold() in outcome_names:
                outcomes.append({**panel, "accent": accent, "status": status})
            else:
                details.append(panel)
        category = self._summary_category(notification)
        # A domain-qualified badge stays meaningful without guessing what event
        # occurred from the integration alone (Portainer can report many events).
        domain = category if category.casefold() not in {"event", "generic", "monitoring"} else ""
        label = {"Success": "Successful", "Failed": "Failure"}.get(lifecycle, lifecycle)
        badge = f"{domain} {label}".strip()
        message = description or title
        outcomes.insert(0, {"title": f"{domain.upper()} RESULT".strip() if status == "success"
                            else "EVENT DETAILS", "accent": accent, "status": status,
                            "rows": [{"icon": "cube", "value": message}], "full_width": True})
        return self._render_standard_card(
            source=source, integration=integration, context=self._context(notification, integration),
            badge=badge, title=title, severity=self._summary_severity(notification, lifecycle),
            category=category, event_time=self._summary_time(notification, fields),
            details=details,
            outcomes=outcomes,
            accent=accent,
            status=status,
            font_profile=self.MODERN_FONT_PROFILE,
        )

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
            if normalized == "alert" and value.casefold().startswith("severity:") and "\n" not in value:
                # Only omit the single severity row already in the summary.
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
        if str(notification.status or "").strip().casefold() == "skipped":
            return "Skipped"
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

        if "skipped" in words:
            return "Skipped"
        if "pending" in words:
            return "Pending"

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

    def _summary_cells_for_metrics(
        self,
        left: int,
        right: int,
        metrics,
    ):
        """Return summary geometry, allowing source-specific text spacing."""

        return self._summary_cells(left, right)

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



class ZabbixDiscordModernImageRenderer(DiscordModernImageRenderer):
    """Render Zabbix with the exact frozen Xen Orchestra visual metrics."""

    DISCORD_WIDTH_COMPENSATION = 64
    WIDTH = (
        XenOrchestraDiscordImageRenderer.WIDTH
        + DISCORD_WIDTH_COMPENSATION
    )
    MIN_HEIGHT = XenOrchestraDiscordImageRenderer.SUCCESS_BASE_HEIGHT
    BASE_HEIGHT = XenOrchestraDiscordImageRenderer.SUCCESS_BASE_HEIGHT
    CARD_SIDE_PADDING = XenOrchestraDiscordImageRenderer.CARD_SIDE_PADDING
    FOOTER_GAP = XenOrchestraDiscordImageRenderer.FOOTER_GAP
    FOOTER_RESERVE = XenOrchestraDiscordImageRenderer.FOOTER_RESERVE
    FOOTER_ICON_SIZE = XenOrchestraDiscordImageRenderer.FOOTER_ICON_SIZE
    STATUS_BADGE_WIDTH = XenOrchestraDiscordImageRenderer.STATUS_BADGE_WIDTH
    STATUS_BADGE_HEIGHT = XenOrchestraDiscordImageRenderer.STATUS_BADGE_HEIGHT
    SUMMARY_CELL_GAP = (
        XenOrchestraDiscordImageRenderer.SUMMARY_CELL_GAP
        + 24
    )
    SUMMARY_FIRST_CELL_RATIO = 0.28
    SUMMARY_SECOND_CELL_RATIO = 0.32
    SUMMARY_LABEL_OFFSET = 78
    SUMMARY_VALUE_GAP = 20
    HEADER_ICON_SIZE = XenOrchestraDiscordImageRenderer.XO_HEADER_ICON_SIZE

    HEADER_Y = 82
    HEADER_MIN_HEIGHT = 150
    TITLE_MIN_HEIGHT = 88
    SUMMARY_HEIGHT = 112
    CONTENT_GAP = 24
    DETAIL_ICON_SIZE = 44
    SUMMARY_ICON_SIZE = 54
    BADGE_ICON_SIZE = 64
    PANEL_TITLE_STATUS_ICON_SIZE = 54
    PANEL_TITLE_ICON_SIZE = 54

    ZABBIX_XO_SECTION_ICONS = {
        "problem": "list",
        "trigger": "chart",
        "response": "clock",
    }
    ZABBIX_XO_FIELD_ICONS = {
        "host": "repository",
        "severity": "status",
        "operational data": "chart",
        "problem id": "list",
        "trigger": "chart",
        "started": "play",
        "updated": "flag",
        "resolved": "flag",
        "finished": "flag",
        "duration": "clock",
        "runbook": "list",
    }

    # Compatibility flags retained for the generic renderer API, but this
    # class uses its own XO-exact drawing path below.
    MODERN_PADDING = CARD_SIDE_PADDING
    MODERN_GAP = CONTENT_GAP
    MODERN_FONT_PROFILE = "xo_match"
    MODERN_MIN_HEIGHT = BASE_HEIGHT
    MODERN_BADGE_MIN_WIDTH = STATUS_BADGE_WIDTH
    MODERN_BADGE_FILL_HEADER = True
    MODERN_XO_ICON_STYLE = True

    @staticmethod
    def _zabbix_line_height(font) -> int:
        return max(font.size + 8, sum(font.getmetrics()))

    def _summary_cells(self, left: int, right: int):
        """Give Category/Event time more breathing room without resizing text."""

        inner_left = left + 28
        inner_right = right - 28
        available = (
            inner_right
            - inner_left
            - self.SUMMARY_CELL_GAP * 2
        )
        first = int(
            available * self.SUMMARY_FIRST_CELL_RATIO
        )
        second = int(
            available * self.SUMMARY_SECOND_CELL_RATIO
        )
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

    def _line_color(
        self,
        line,
        accent,
    ):
        color = super()._line_color(line, accent)
        if (
            accent == self.FAILURE
            and re.match(
                r"^\s*Started:\s",
                str(line or ""),
                re.IGNORECASE,
            )
        ):
            return self.FAILURE
        return color

    def _zabbix_xo_section_icon(self, title: str) -> str:
        return self.ZABBIX_XO_SECTION_ICONS.get(
            self._clean(title).casefold(),
            "list",
        )

    def _zabbix_xo_field_icon(
        self,
        panel_title: str,
        label: str,
        value: str,
        fallback: str | None,
    ) -> str:
        key = self._clean(label).rstrip(":").casefold()
        if key in self.ZABBIX_XO_FIELD_ICONS:
            return self.ZABBIX_XO_FIELD_ICONS[key]

        panel_key = self._clean(panel_title).casefold()
        value_key = self._clean(value).casefold()
        if panel_key == "trigger":
            return "chart"
        if panel_key == "response":
            if "runbook" in value_key:
                return "list"
            if any(token in value_key for token in ("started", "updated", "resolved", "finished")):
                return "flag"
        if fallback in {
            "cube",
            "rocket",
            "clock",
            "list",
            "repository",
            "play",
            "flag",
            "chart",
            "disk",
            "alert",
            "info",
            "status",
        }:
            return fallback
        return "list"

    def _zabbix_fill_standard_rows(
        self,
        panels,
        content_y: int,
        target_bottom: int,
    ):
        """Use all XO baseline content space without changing font sizes."""

        if len(panels) != 4:
            return panels, None

        row_ys = sorted({panel["y"] for panel in panels})
        if len(row_ys) != 2:
            return panels, None

        rows = [
            [panel for panel in panels if panel["y"] == row_y]
            for row_y in row_ys
        ]
        if any(len(row) != 2 for row in rows):
            return panels, None

        row_heights = [
            max(panel["height"] for panel in row)
            for row in rows
        ]
        natural_total = (
            row_heights[0]
            + self.CONTENT_GAP
            + row_heights[1]
        )
        available = target_bottom - content_y
        if natural_total > available:
            return panels, None

        extra = available - natural_total
        first_extra = extra // 2
        second_extra = extra - first_extra
        stretched = []
        first_height = row_heights[0] + first_extra
        second_height = row_heights[1] + second_extra
        second_y = content_y + first_height + self.CONTENT_GAP

        for panel in rows[0]:
            stretched.append(
                {
                    **panel,
                    "y": content_y,
                    "height": first_height,
                }
            )
        for panel in rows[1]:
            stretched.append(
                {
                    **panel,
                    "y": second_y,
                    "height": second_height,
                }
            )

        return stretched, target_bottom

    def _zabbix_measure_panel(self, draw, panel, width):
        """Measure a Zabbix section using XO fonts without shrinking text."""

        y = 15
        paint = []
        title = self._clean(panel.get("title") or "")
        accent = panel.get("accent")
        panel_title = title
        if title:
            title_width = max(160, width - 118)
            title_lines = (
                self._wrapped_text_lines(
                    draw,
                    title,
                    title_width,
                    self.font_bold,
                )
                or [title]
            )
            title_line_height = self._zabbix_line_height(self.font_bold)
            title_height = max(
                (
                    self.PANEL_TITLE_STATUS_ICON_SIZE
                    if accent
                    else self.PANEL_TITLE_ICON_SIZE
                ),
                len(title_lines) * title_line_height,
            )
            paint.append(
                {
                    "kind": "title",
                    "y": y,
                    "lines": title_lines,
                    "line_height": title_line_height,
                }
            )
            y += title_height + 14

        for row in panel.get("rows", []):
            role = row.get("role")
            label = self._clean(row.get("label") or "")
            value = self._clean(row.get("value") or "") or "—"
            color = row.get("color") or self.TEXT
            icon = self._zabbix_xo_field_icon(
                panel_title,
                label,
                value,
                row.get("icon"),
            )

            if role == "label" and not label:
                lines = (
                    self._wrapped_text_lines(
                        draw,
                        value,
                        width - 48,
                        self.font_label,
                    )
                    or [value]
                )
                line_height = self._zabbix_line_height(self.font_label)
                paint.append(
                    {
                        "kind": "subheading",
                        "y": y,
                        "lines": lines,
                        "line_height": line_height,
                        "color": row.get("color") or self.HEADER_MUTED,
                    }
                )
                y += len(lines) * line_height + 8
                continue

            icon_space = self.DETAIL_ICON_SIZE + 20 if icon else 0
            text_x = 28 + icon_space
            available = max(180, width - text_x - 28)
            body_line_height = self._zabbix_line_height(self.font_detail)
            label_line_height = self._zabbix_line_height(self.font_label)

            if label:
                label_width = draw.textlength(label, font=self.font_label)
                value_width = available - label_width - 18
                if value_width >= 220:
                    value_lines = (
                        self._wrapped_text_lines(
                            draw,
                            value,
                            value_width,
                            self.font_detail,
                        )
                        or [value]
                    )
                    row_height = max(
                        self.DETAIL_ICON_SIZE if icon else 0,
                        label_line_height,
                        len(value_lines) * body_line_height,
                    )
                    paint.append(
                        {
                            "kind": "inline",
                            "y": y,
                            "icon": icon,
                            "text_x": text_x,
                            "label": label,
                            "label_width": label_width,
                            "value_lines": value_lines,
                            "value_line_height": body_line_height,
                            "color": color,
                        }
                    )
                    y += row_height + 8
                    continue

                value_lines = (
                    self._wrapped_text_lines(
                        draw,
                        value,
                        available,
                        self.font_detail,
                    )
                    or [value]
                )
                row_height = (
                    label_line_height
                    + 4
                    + len(value_lines) * body_line_height
                )
                row_height = max(
                    row_height,
                    self.DETAIL_ICON_SIZE if icon else 0,
                )
                paint.append(
                    {
                        "kind": "stacked",
                        "y": y,
                        "icon": icon,
                        "text_x": text_x,
                        "label": label,
                        "value_lines": value_lines,
                        "value_line_height": body_line_height,
                        "label_line_height": label_line_height,
                        "color": color,
                    }
                )
                y += row_height + 8
                continue

            value_lines = (
                self._wrapped_text_lines(
                    draw,
                    value,
                    available,
                    self.font_detail,
                )
                or [value]
            )
            row_height = max(
                self.DETAIL_ICON_SIZE if icon else 0,
                len(value_lines) * body_line_height,
            )
            paint.append(
                {
                    "kind": "value",
                    "y": y,
                    "icon": icon,
                    "text_x": text_x,
                    "value_lines": value_lines,
                    "value_line_height": body_line_height,
                    "color": color,
                }
            )
            y += row_height + 8

        return {
            **panel,
            "width": width,
            "height": max(120, y + 7),
            "paint": paint,
        }

    def _zabbix_content_plan(self, draw, details, outcomes, x0, right, start_y):
        """Pack standard Zabbix rows into the frozen XO 2000x1600 baseline."""

        width = right - x0
        gap = self.CONTENT_GAP
        half = (width - gap) // 2
        panels = []
        y = start_y
        detail_index = 0
        outcome_index = 0

        def append_pair(left_panel, right_panel):
            nonlocal y
            measured = [
                self._zabbix_measure_panel(draw, left_panel, half),
                self._zabbix_measure_panel(draw, right_panel, half),
            ]
            pair_height = max(item["height"] for item in measured)
            for column, item in enumerate(measured):
                panels.append(
                    {
                        **item,
                        "x": x0 + column * (half + gap),
                        "y": y,
                        "height": pair_height,
                    }
                )
            y += pair_height + gap

        # Problem + Trigger stay side-by-side exactly as in the approved card.
        if len(details) >= 2:
            append_pair(details[0], details[1])
            detail_index = 2

        # The standard Zabbix card has Response plus one lifecycle result.
        # Put those on the same second row so Discord does not downscale a
        # needlessly tall image. Long/extra content still grows below.
        if detail_index < len(details) and outcome_index < len(outcomes):
            append_pair(details[detail_index], outcomes[outcome_index])
            detail_index += 1
            outcome_index += 1

        for panel in details[detail_index:]:
            measured = self._zabbix_measure_panel(draw, panel, width)
            panels.append({**measured, "x": x0, "y": y})
            y += measured["height"] + gap

        for panel in outcomes[outcome_index:]:
            measured = self._zabbix_measure_panel(draw, panel, width)
            panels.append({**measured, "x": x0, "y": y})
            y += measured["height"] + gap

        return panels, max(start_y, y - gap)

    def _zabbix_draw_panel(self, image, draw, panel, accent, status):
        x1 = panel["x"]
        y1 = panel["y"]
        x2 = x1 + panel["width"]
        y2 = y1 + panel["height"]
        panel_accent = panel.get("accent")

        if panel_accent:
            self._glow_box(
                image,
                (x1, y1, x2, y2),
                panel_accent,
                15,
                alpha=110,
            )
            draw = ImageDraw.Draw(image, "RGBA")

        self._rounded(
            draw,
            (x1, y1, x2, y2),
            fill=(
                *(
                    self._tint(panel_accent, self.CARD_BG, 0.20)
                    if panel_accent
                    else self.PANEL_2
                ),
                248,
            ),
            outline=(*(panel_accent or self.PANEL_BORDER), 225),
            radius=15,
            width=2,
        )

        for item in panel["paint"]:
            py = y1 + item["y"]
            kind = item["kind"]

            if kind == "title":
                if panel_accent:
                    self._status_icon(
                        draw,
                        x1 + 24,
                        py,
                        self.PANEL_TITLE_STATUS_ICON_SIZE,
                        panel.get("status", status),
                        panel_accent,
                    )
                    title_x = x1 + 98
                    title_color = panel_accent
                else:
                    self._draw_field_icon(
                        draw,
                        x1 + 24,
                        py,
                        self.PANEL_TITLE_ICON_SIZE,
                        self._zabbix_xo_section_icon(
                            panel.get("title") or ""
                        ),
                    )
                    title_x = x1 + 98
                    title_color = self.LABEL
                for index, line in enumerate(item["lines"]):
                    draw.text(
                        (
                            title_x,
                            py + index * item["line_height"],
                        ),
                        line,
                        font=self.font_bold,
                        fill=title_color,
                    )
                continue

            if kind == "subheading":
                for index, line in enumerate(item["lines"]):
                    draw.text(
                        (
                            x1 + 24,
                            py + index * item["line_height"],
                        ),
                        line,
                        font=self.font_label,
                        fill=item["color"],
                    )
                continue

            icon = item.get("icon")
            if icon == "status":
                self._status_icon(
                    draw,
                    x1 + 24,
                    py + 2,
                    self.DETAIL_ICON_SIZE,
                    status,
                    accent,
                )
            elif icon:
                self._draw_field_icon(
                    draw,
                    x1 + 24,
                    py + 2,
                    self.DETAIL_ICON_SIZE,
                    icon,
                )
            text_x = x1 + item["text_x"]

            if kind == "inline":
                draw.text(
                    (text_x, py),
                    item["label"],
                    font=self.font_label,
                    fill=self.LABEL,
                )
                value_x = text_x + item["label_width"] + 18
                for index, line in enumerate(item["value_lines"]):
                    draw.text(
                        (
                            value_x,
                            py + index * item["value_line_height"],
                        ),
                        line,
                        font=self.font_detail,
                        fill=item["color"],
                    )
                continue

            if kind == "stacked":
                draw.text(
                    (text_x, py),
                    item["label"],
                    font=self.font_label,
                    fill=self.LABEL,
                )
                value_y = py + item["label_line_height"] + 4
                for index, line in enumerate(item["value_lines"]):
                    draw.text(
                        (
                            text_x,
                            value_y + index * item["value_line_height"],
                        ),
                        line,
                        font=self.font_detail,
                        fill=item["color"],
                    )
                continue

            for index, line in enumerate(item["value_lines"]):
                draw.text(
                    (
                        text_x,
                        py + index * item["value_line_height"],
                    ),
                    line,
                    font=self.font_detail,
                    fill=item["color"],
                )

    def _standard_badge_box(
        self,
        draw,
        right: int,
        header_y: int,
        header_height: int,
        status: str,
        label: str,
    ):
        """Return the frozen badge geometry unless a source overrides it."""

        return self._status_badge_box(
            right,
            header_y,
            header_height,
            status=status,
        )

    def _render_standard_card(
        self,
        *,
        source,
        accent,
        status,
        font_profile="default",
        **content,
    ):
        """Render Zabbix on the exact XO geometry, fonts, icons and footer."""

        integration = content["integration"]
        context = content["context"]
        badge_label = content["badge"]
        title = content["title"]
        severity = content["severity"]
        category = content["category"]
        event_time = self._event_time_only(content["event_time"])
        details = content["details"]
        outcomes = content["outcomes"]

        measure = ImageDraw.Draw(Image.new("RGB", (self.WIDTH, 1)))
        x0 = self.CARD_SIDE_PADDING
        right = self.WIDTH - self.CARD_SIDE_PADDING
        header_y = self.HEADER_Y
        title_x = x0 + self.HEADER_ICON_SIZE + 20

        badge_probe = self._standard_badge_box(
            measure,
            right,
            header_y,
            self.HEADER_MIN_HEIGHT,
            status,
            badge_label,
        )
        context_width = max(320, badge_probe[0] - title_x - 34)
        context_lines = (
            self._wrapped_text_lines(
                measure,
                context,
                context_width,
                self.font_body,
            )
            or [context]
        )
        body_line_height = self._zabbix_line_height(self.font_body)
        header_height = max(
            self.HEADER_MIN_HEIGHT,
            76 + len(context_lines) * (body_line_height + 6),
            self.STATUS_BADGE_HEIGHT,
        )

        title_width = right - x0 - 60
        title_lines = (
            self._wrapped_text_lines(
                measure,
                title,
                title_width,
                self.font_title,
            )
            or [title]
        )
        title_line_height = self._zabbix_line_height(self.font_title)
        title_y = header_y + header_height + 24
        title_height = max(
            self.TITLE_MIN_HEIGHT,
            30 + len(title_lines) * (title_line_height + 5),
        )

        summary_y = title_y + title_height + 20
        content_y = summary_y + self.SUMMARY_HEIGHT + self.CONTENT_GAP
        panels, content_bottom = self._zabbix_content_plan(
            measure,
            details,
            outcomes,
            x0,
            right,
            content_y,
        )

        baseline_footer_y = self.BASE_HEIGHT - self.FOOTER_RESERVE
        standard_target_bottom = baseline_footer_y - self.FOOTER_GAP
        panels, filled_bottom = self._zabbix_fill_standard_rows(
            panels,
            content_y,
            standard_target_bottom,
        )
        if filled_bottom is not None:
            content_bottom = filled_bottom

        required_footer_y = content_bottom + self.FOOTER_GAP
        footer_y = max(baseline_footer_y, required_footer_y)
        height = max(
            self.BASE_HEIGHT,
            footer_y + self.FOOTER_RESERVE,
        )

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

        self._draw_product_icon(
            image,
            source,
            x0,
            header_y - 4,
            self.HEADER_ICON_SIZE,
            self.HEADER_ICON_SIZE,
        )
        draw.text(
            (title_x, header_y + 2),
            integration,
            font=self.font_heading,
            fill=self.TEXT,
        )
        self._wrap_text(
            draw,
            context,
            title_x,
            header_y + 68,
            context_width,
            self.font_body,
            self.HEADER_MUTED,
            max_lines=None,
            line_gap=5,
        )

        badge = self._standard_badge_box(
            draw,
            right,
            header_y,
            header_height,
            status,
            badge_label,
        )
        badge_x = badge[0]
        self._glow_box(
            image,
            badge,
            accent,
            18,
            alpha=self.STATUS_GLOW_ALPHA,
        )
        draw = ImageDraw.Draw(image, "RGBA")
        self._rounded(
            draw,
            badge,
            fill=(*self._tint(accent, self.CARD_BG, 0.16), 245),
            outline=(*accent, 225),
            radius=18,
            width=2,
        )
        badge_icon_y = self._center_y(
            badge[1],
            badge[3],
            self.BADGE_ICON_SIZE,
        )
        self._status_icon(
            draw,
            badge_x + 28,
            badge_icon_y,
            self.BADGE_ICON_SIZE,
            status,
            accent,
        )
        draw.text(
            (
                badge_x + 112,
                (badge[1] + badge[3]) // 2,
            ),
            badge_label,
            font=self.font_bold,
            fill=accent if status != "success" else (103, 239, 174),
            anchor="lm",
        )

        title_box = (
            x0,
            title_y,
            right,
            title_y + title_height,
        )
        self._rounded(
            draw,
            title_box,
            fill=(*self.PANEL_2, 248),
            outline=(93, 101, 108, 190),
            radius=14,
            width=2,
        )
        self._wrap_text(
            draw,
            title,
            x0 + 30,
            title_y + 16,
            title_width,
            self.font_title,
            self.TEXT,
            max_lines=None,
            line_gap=5,
        )

        summary_box = (
            x0,
            summary_y,
            right,
            summary_y + self.SUMMARY_HEIGHT,
        )
        self._rounded(
            draw,
            summary_box,
            fill=(*self.PANEL, 248),
            outline=(*self.PANEL_BORDER, 200),
            radius=14,
            width=1,
        )
        metrics = [
            ("status", "Severity", severity, accent),
            ("sync", "Category", category, self.ICON_BLUE),
            ("clock", "Event time", event_time, (194, 226, 242)),
        ]
        cells = self._summary_cells_for_metrics(
            x0,
            right,
            metrics,
        )
        summary_mid_y = summary_y + self.SUMMARY_HEIGHT // 2
        for index, ((icon, label, value, color), cell) in enumerate(
            zip(metrics, cells)
        ):
            cell_x1, cell_x2 = cell
            icon_y = self._center_y(
                summary_y,
                summary_y + self.SUMMARY_HEIGHT,
                self.SUMMARY_ICON_SIZE,
            )
            self._draw_icon_badge(
                draw,
                cell_x1,
                icon_y,
                self.SUMMARY_ICON_SIZE,
                icon,
                color,
                status=status,
            )
            label_x = cell_x1 + self.SUMMARY_LABEL_OFFSET
            draw.text(
                (label_x, summary_mid_y),
                f"{label}:",
                font=self.font_label,
                fill=self.TEXT,
                anchor="lm",
            )
            label_width = draw.textlength(
                f"{label}:",
                font=self.font_label,
            )
            draw.text(
                (
                    label_x + label_width + self.SUMMARY_VALUE_GAP,
                    summary_mid_y,
                ),
                value,
                font=self.font_detail,
                fill=self.TEXT,
                anchor="lm",
            )
            if index < 2:
                next_left = cells[index + 1][0]
                divider_x = (cell_x2 + next_left) // 2
                draw.line(
                    (
                        divider_x,
                        summary_y + 22,
                        divider_x,
                        summary_y + self.SUMMARY_HEIGHT - 22,
                    ),
                    fill=(102, 112, 119, 160),
                    width=2,
                )

        for panel in panels:
            self._zabbix_draw_panel(
                image,
                draw,
                panel,
                accent,
                status,
            )

        draw.line(
            (
                x0,
                footer_y - 10,
                right,
                footer_y - 10,
            ),
            fill=(81, 89, 95, 170),
            width=2,
        )
        footer_x = self._footer_identity_x(draw, right)
        footer_icon_y = footer_y + 18
        self._draw_nowlert_icon(
            image,
            footer_x,
            footer_icon_y,
            self.FOOTER_ICON_SIZE,
        )
        draw.text(
            (
                footer_x + self.FOOTER_ICON_SIZE + 18,
                footer_icon_y + self.FOOTER_ICON_SIZE // 2,
            ),
            self.FOOTER_TEXT,
            font=self.font_small,
            fill=self.MUTED,
            anchor="lm",
        )

        output = BytesIO()
        image.convert("RGB").save(
            output,
            format="PNG",
            optimize=True,
            compress_level=7,
        )
        return output.getvalue()



class GrafanaDiscordModernImageRenderer(ZabbixDiscordModernImageRenderer):
    """Render Grafana Modern cards with the frozen Zabbix/XO visual system."""

    STATUS_BADGE_WIDTH = 640

    GRAFANA_XO_SECTION_ICONS = {
        "rule & location": "chart",
        "data": "repository",
        "timing & links": "clock",
        "alert details": "alert",
        "event details": "alert",
        "alerting result": "status",
    }
    GRAFANA_XO_FIELD_ICONS = {
        "rule": "chart",
        "folder": "repository",
        "dashboard": "chart",
        "panel": "chart",
        "datasource": "repository",
        "labels": "list",
        "values": "chart",
        "started": "play",
        "updated": "flag",
        "resolved": "flag",
        "finished": "flag",
        "duration": "clock",
        "links": "list",
        "dashboard link": "list",
        "panel link": "list",
        "silence link": "list",
        "rule link": "list",
        "alerts": "alert",
        "evaluation error": "alert",
    }

    def _line_color(
        self,
        line,
        accent,
    ):
        color = super()._line_color(line, accent)
        if (
            accent in {self.BRAND_GOLD, self.SKIPPED}
            and re.match(
                r"^\s*Started:\s",
                str(line or ""),
                re.IGNORECASE,
            )
        ):
            return accent
        return color

    def _zabbix_content_plan(
        self,
        draw,
        details,
        outcomes,
        x0,
        right,
        start_y,
    ):
        """Keep a normal grouped Grafana alert on the 1600px baseline."""

        if not (len(details) == 3 and len(outcomes) == 2):
            return super()._zabbix_content_plan(
                draw,
                details,
                outcomes,
                x0,
                right,
                start_y,
            )

        primary = outcomes[0]
        extra = outcomes[1]
        primary_title = self._clean(
            primary.get("title") or "EVENT DETAILS"
        )
        extra_title = self._clean(
            extra.get("title") or "Alert details"
        )
        combined_title = " · ".join(
            title
            for title in (primary_title, extra_title)
            if title
        )
        combined_outcome = {
            **primary,
            "title": combined_title,
            "rows": (
                list(primary.get("rows", []))
                + list(extra.get("rows", []))
            ),
        }

        return super()._zabbix_content_plan(
            draw,
            details,
            [combined_outcome],
            x0,
            right,
            start_y,
        )

    def _zabbix_xo_section_icon(self, title: str) -> str:
        return self.GRAFANA_XO_SECTION_ICONS.get(
            self._clean(title).casefold(),
            "list",
        )

    def _zabbix_xo_field_icon(
        self,
        panel_title: str,
        label: str,
        value: str,
        fallback: str | None,
    ) -> str:
        key = self._clean(label).rstrip(":").casefold()
        if key in self.GRAFANA_XO_FIELD_ICONS:
            return self.GRAFANA_XO_FIELD_ICONS[key]

        panel_key = self._clean(panel_title).casefold()
        if panel_key == "rule & location":
            return "chart"
        if panel_key == "data":
            return "repository"
        if panel_key == "timing & links":
            value_key = self._clean(value).casefold()
            if any(
                token in value_key
                for token in ("started", "updated", "resolved", "finished")
            ):
                return "flag"
            return "clock"
        if panel_key == "alert details":
            return "alert"

        return super()._zabbix_xo_field_icon(
            panel_title,
            label,
            value,
            fallback,
        )



class PortainerDiscordModernImageRenderer(GrafanaDiscordModernImageRenderer):
    """Render Portainer cards on the frozen Grafana/Zabbix/XO baseline."""

    # Portainer's longer Environment category needs a little more horizontal
    # room so Severity / Category / Event time remain visually aligned.
    SUMMARY_FIRST_CELL_RATIO = 0.27
    SUMMARY_SECOND_CELL_RATIO = 0.36

    PORTAINER_XO_SECTION_ICONS = {
        "environment": "repository",
        "signal": "chart",
        "timing": "clock",
    }
    PORTAINER_XO_FIELD_ICONS = {
        "portainer": "repository",
        "instance": "repository",
        "area": "list",
        "authentication": "list",
        "method": "list",
        "user": "list",
        "signal": "chart",
        "metric": "chart",
        "count": "list",
        "started": "play",
        "updated": "flag",
        "resolved": "flag",
        "finished": "flag",
        "duration": "clock",
    }

    def _zabbix_content_plan(
        self,
        draw,
        details,
        outcomes,
        x0,
        right,
        start_y,
    ):
        return ZabbixDiscordModernImageRenderer._zabbix_content_plan(
            self,
            draw,
            details,
            outcomes,
            x0,
            right,
            start_y,
        )

    def _zabbix_xo_section_icon(self, title: str) -> str:
        return self.PORTAINER_XO_SECTION_ICONS.get(
            self._clean(title).casefold(),
            "list",
        )

    def _zabbix_xo_field_icon(
        self,
        panel_title: str,
        label: str,
        value: str,
        fallback: str | None,
    ) -> str:
        key = self._clean(label).rstrip(":").casefold()
        if key in self.PORTAINER_XO_FIELD_ICONS:
            return self.PORTAINER_XO_FIELD_ICONS[key]

        panel_key = self._clean(panel_title).casefold()
        if panel_key == "environment":
            return "repository"
        if panel_key == "signal":
            return "chart"
        if panel_key == "timing":
            return "clock"

        return ZabbixDiscordModernImageRenderer._zabbix_xo_field_icon(
            self,
            panel_title,
            label,
            value,
            fallback,
        )


class ProxmoxDiscordModernImageRenderer(GrafanaDiscordModernImageRenderer):
    """Render Proxmox cards on the frozen Grafana/Zabbix/XO baseline."""

    PROXMOX_XO_SECTION_ICONS = {
        "proxmox ve": "repository",
        "job & storage": "disk",
        "timing": "clock",
    }
    PROXMOX_XO_FIELD_ICONS = {
        "node": "repository",
        "guest": "cube",
        "vmid": "list",
        "backup": "list",
        "storage": "disk",
        "job": "list",
        "duration": "clock",
        "guests ok": "status",
        "guests failed": "alert",
        "failed guests": "alert",
        "error details": "alert",
        "successful guests": "status",
        "started": "play",
        "updated": "flag",
        "resolved": "flag",
        "finished": "flag",
    }

    def _zabbix_content_plan(
        self,
        draw,
        details,
        outcomes,
        x0,
        right,
        start_y,
    ):
        return ZabbixDiscordModernImageRenderer._zabbix_content_plan(
            self,
            draw,
            details,
            outcomes,
            x0,
            right,
            start_y,
        )

    def _zabbix_xo_section_icon(self, title: str) -> str:
        return self.PROXMOX_XO_SECTION_ICONS.get(
            self._clean(title).casefold(),
            "list",
        )

    def _zabbix_xo_field_icon(
        self,
        panel_title: str,
        label: str,
        value: str,
        fallback: str | None,
    ) -> str:
        key = self._clean(label).rstrip(":").casefold()
        if key in self.PROXMOX_XO_FIELD_ICONS:
            return self.PROXMOX_XO_FIELD_ICONS[key]

        panel_key = self._clean(panel_title).casefold()
        if panel_key == "proxmox ve":
            return "repository"
        if panel_key == "job & storage":
            return "disk"
        if panel_key == "timing":
            return "clock"

        return ZabbixDiscordModernImageRenderer._zabbix_xo_field_icon(
            self,
            panel_title,
            label,
            value,
            fallback,
        )



class QNAPDiscordModernImageRenderer(GrafanaDiscordModernImageRenderer):
    """Render QNAP cards on the frozen Grafana/Zabbix/XO baseline."""

    # QNAP's Information severity is wider than the common Warning/Error
    # values, so keep Category readable and push Event time into the same
    # clean alignment used by the approved standardized cards.
    SUMMARY_FIRST_CELL_RATIO = 0.27
    SUMMARY_SECOND_CELL_RATIO = 0.36

    def _summary_cells_for_metrics(
        self,
        left: int,
        right: int,
        metrics,
    ):
        """Give QNAP Information/System enough room without moving other cards."""

        values = [
            self._clean(metric[2]).casefold()
            for metric in metrics
        ]
        if not (
            len(values) == 3
            and values[0] == "information"
            and values[1] == "system"
        ):
            return super()._summary_cells_for_metrics(
                left,
                right,
                metrics,
            )

        inner_left = left + 28
        inner_right = right - 28
        available = (
            inner_right
            - inner_left
            - self.SUMMARY_CELL_GAP * 2
        )
        first = int(available * 0.34)
        second = int(available * 0.30)
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

    QNAP_XO_SECTION_ICONS = {
        "qnap nas": "repository",
        "event details": "list",
        "timing": "clock",
    }
    QNAP_XO_FIELD_ICONS = {
        "nas": "repository",
        "application": "list",
        "storage pool": "disk",
        "pool": "disk",
        "volume": "disk",
        "disk": "disk",
        "drive": "disk",
        "drive bay": "disk",
        "raid group": "disk",
        "raid level": "disk",
        "smart status": "status",
        "smart test": "status",
        "backup job": "list",
        "job name": "list",
        "task": "list",
        "source": "repository",
        "destination": "repository",
        "repository": "repository",
        "ups": "alert",
        "power event": "alert",
        "power source": "alert",
        "battery level": "chart",
        "battery capacity": "chart",
        "runtime remaining": "clock",
        "account": "list",
        "user": "list",
        "username": "list",
        "source ip": "repository",
        "ip address": "repository",
        "protocol": "list",
        "firmware version": "list",
        "current version": "list",
        "available version": "list",
        "new version": "list",
        "started": "play",
        "updated": "flag",
        "resolved": "flag",
        "finished": "flag",
        "duration": "clock",
    }

    def _zabbix_content_plan(
        self,
        draw,
        details,
        outcomes,
        x0,
        right,
        start_y,
    ):
        return ZabbixDiscordModernImageRenderer._zabbix_content_plan(
            self,
            draw,
            details,
            outcomes,
            x0,
            right,
            start_y,
        )

    def _zabbix_fill_standard_rows(
        self,
        panels,
        content_y: int,
        target_bottom: int,
    ):
        """Fill the QNAP three-panel information layout to the footer."""

        if len(panels) != 3:
            return ZabbixDiscordModernImageRenderer._zabbix_fill_standard_rows(
                self,
                panels,
                content_y,
                target_bottom,
            )

        row_ys = sorted({panel["y"] for panel in panels})
        if len(row_ys) != 2:
            return panels, None

        first_row = [
            panel
            for panel in panels
            if panel["y"] == row_ys[0]
        ]
        second_row = [
            panel
            for panel in panels
            if panel["y"] == row_ys[1]
        ]
        if len(first_row) != 2 or len(second_row) != 1:
            return panels, None

        first_height = max(panel["height"] for panel in first_row)
        second_panel = second_row[0]
        natural_total = (
            first_height
            + self.CONTENT_GAP
            + second_panel["height"]
        )
        available = target_bottom - content_y
        if natural_total > available:
            return panels, None

        second_y = content_y + first_height + self.CONTENT_GAP
        second_height = target_bottom - second_y
        stretched = [
            {
                **panel,
                "y": content_y,
                "height": first_height,
            }
            for panel in first_row
        ]
        stretched.append(
            {
                **second_panel,
                "y": second_y,
                "height": second_height,
            }
        )
        return stretched, target_bottom

    def _zabbix_xo_section_icon(self, title: str) -> str:
        return self.QNAP_XO_SECTION_ICONS.get(
            self._clean(title).casefold(),
            "list",
        )

    def _zabbix_xo_field_icon(
        self,
        panel_title: str,
        label: str,
        value: str,
        fallback: str | None,
    ) -> str:
        key = self._clean(label).rstrip(":").casefold()
        if key in self.QNAP_XO_FIELD_ICONS:
            return self.QNAP_XO_FIELD_ICONS[key]

        panel_key = self._clean(panel_title).casefold()
        if panel_key == "qnap nas":
            return "repository"
        if panel_key == "event details":
            return "list"
        if panel_key == "timing":
            return "clock"

        return ZabbixDiscordModernImageRenderer._zabbix_xo_field_icon(
            self,
            panel_title,
            label,
            value,
            fallback,
        )


class SynologyDiscordModernImageRenderer(GrafanaDiscordModernImageRenderer):
    """Render Synology cards on the frozen Grafana/Zabbix/XO baseline."""

    SYNOLOGY_XO_SECTION_ICONS = {
        "synology nas": "repository",
        "event details": "list",
        "timing": "clock",
    }
    SYNOLOGY_XO_FIELD_ICONS = {
        "nas": "repository",
        "model": "repository",
        "storage pool": "disk",
        "storage": "disk",
        "volume": "disk",
        "disk": "disk",
        "package": "list",
        "task": "list",
        "user": "list",
        "username": "list",
        "source ip": "repository",
        "ip address": "repository",
        "started": "play",
        "updated": "flag",
        "resolved": "flag",
        "finished": "flag",
        "duration": "clock",
    }

    def _zabbix_content_plan(
        self,
        draw,
        details,
        outcomes,
        x0,
        right,
        start_y,
    ):
        return ZabbixDiscordModernImageRenderer._zabbix_content_plan(
            self,
            draw,
            details,
            outcomes,
            x0,
            right,
            start_y,
        )

    def _zabbix_xo_section_icon(self, title: str) -> str:
        return self.SYNOLOGY_XO_SECTION_ICONS.get(
            self._clean(title).casefold(),
            "list",
        )

    def _zabbix_xo_field_icon(
        self,
        panel_title: str,
        label: str,
        value: str,
        fallback: str | None,
    ) -> str:
        key = self._clean(label).rstrip(":").casefold()
        if key in self.SYNOLOGY_XO_FIELD_ICONS:
            return self.SYNOLOGY_XO_FIELD_ICONS[key]

        panel_key = self._clean(panel_title).casefold()
        if panel_key == "synology nas":
            return "repository"
        if panel_key == "event details":
            return "list"
        if panel_key == "timing":
            return "clock"

        return ZabbixDiscordModernImageRenderer._zabbix_xo_field_icon(
            self,
            panel_title,
            label,
            value,
            fallback,
        )



class _StandardizedSourceDiscordModernImageRenderer(
    GrafanaDiscordModernImageRenderer
):
    """Shared frozen renderer for the next standardized integration batch."""

    def _zabbix_content_plan(
        self,
        draw,
        details,
        outcomes,
        x0,
        right,
        start_y,
    ):
        return ZabbixDiscordModernImageRenderer._zabbix_content_plan(
            self,
            draw,
            details,
            outcomes,
            x0,
            right,
            start_y,
        )

    def _standard_badge_box(
        self,
        draw,
        right: int,
        header_y: int,
        header_height: int,
        status: str,
        label: str,
    ):
        """Keep long lifecycle badges horizontal at the frozen font size."""

        text_width = int(
            draw.textlength(
                self._clean(label),
                font=self.font_bold,
            )
        )
        badge_width = max(
            self.STATUS_BADGE_WIDTH,
            text_width + 146,
        )
        shift = (
            self.SUCCESS_BADGE_LEFT_SHIFT
            if status == "success"
            else 0
        )
        height = max(
            self.STATUS_BADGE_HEIGHT,
            header_height,
        )
        return (
            right - badge_width - shift,
            header_y,
            right,
            header_y + height,
        )

    def _event_time_only(self, value) -> str:
        """Use only the clock in the compact summary; Timing keeps the timezone."""

        text = super()._event_time_only(value)
        match = re.search(
            r"(?<!\\d)(\\d{1,2}:\\d{2}:\\d{2})",
            text,
        )
        return match.group(1) if match else text

    def _summary_cells_for_metrics(
        self,
        left: int,
        right: int,
        metrics,
    ):
        """Allocate the summary from measured text so groups never collide."""

        draw = ImageDraw.Draw(
            Image.new("RGB", (self.WIDTH, 1))
        )
        required = []
        for _icon, label, value, _color in metrics:
            width = (
                self.SUMMARY_LABEL_OFFSET
                + draw.textlength(
                    f"{label}:",
                    font=self.font_label,
                )
                + self.SUMMARY_VALUE_GAP
                + draw.textlength(
                    self._clean(value),
                    font=self.font_detail,
                )
            )
            required.append(int(width) + 1)

        # The new standardized sources keep the frozen 72px group gaps.
        # A slightly tighter outer inset gives long values such as
        # Information / Administration enough room without shrinking fonts.
        inner_padding = 22
        inner_left = left + inner_padding
        inner_right = right - inner_padding
        available = (
            inner_right
            - inner_left
            - self.SUMMARY_CELL_GAP * 2
        )

        if sum(required) <= available:
            widths = list(required)
            extra = available - sum(widths)
            first_extra = extra // 4
            second_extra = extra // 4
            widths[0] += first_extra
            widths[1] += second_extra
            widths[2] += extra - first_extra - second_extra
        else:
            # Extremely long/custom values still get the established fallback
            # geometry; normal supported values fit the measured allocation.
            cells = self._summary_cells(left, right)
            widths = [
                cell_right - cell_left
                for cell_left, cell_right in cells
            ]
            inner_left = cells[0][0]

        cell_1 = (
            inner_left,
            inner_left + widths[0],
        )
        cell_2 = (
            cell_1[1] + self.SUMMARY_CELL_GAP,
            cell_1[1] + self.SUMMARY_CELL_GAP + widths[1],
        )
        cell_3 = (
            cell_2[1] + self.SUMMARY_CELL_GAP,
            cell_2[1] + self.SUMMARY_CELL_GAP + widths[2],
        )
        return [cell_1, cell_2, cell_3]

    def _zabbix_fill_standard_rows(
        self,
        panels,
        content_y: int,
        target_bottom: int,
    ):
        """Use the complete 1600px baseline for sparse one/two/three-panel cards."""

        if not panels:
            return panels, None

        available = target_bottom - content_y
        row_ys = sorted(
            {panel["y"] for panel in panels}
        )
        rows = [
            [
                panel
                for panel in panels
                if panel["y"] == row_y
            ]
            for row_y in row_ys
        ]
        row_heights = [
            max(panel["height"] for panel in row)
            for row in rows
        ]
        natural_total = (
            sum(row_heights)
            + self.CONTENT_GAP * max(0, len(rows) - 1)
        )
        if natural_total > available:
            return panels, None

        # The frozen base already handles the canonical 2 x 2 layout.
        if len(panels) == 4:
            return ZabbixDiscordModernImageRenderer._zabbix_fill_standard_rows(
                self,
                panels,
                content_y,
                target_bottom,
            )

        valid_sparse = (
            len(rows) <= 2
            and all(len(row) <= 2 for row in rows)
            and len(panels) <= 3
        )
        if not valid_sparse:
            return panels, None

        extra = available - natural_total
        extras = [0] * len(rows)
        if len(rows) == 1:
            extras[0] = extra
        elif len(rows) == 2:
            extras[0] = extra // 2
            extras[1] = extra - extras[0]

        stretched = []
        y = content_y
        for row_index, row in enumerate(rows):
            row_height = row_heights[row_index] + extras[row_index]
            for panel in row:
                stretched.append(
                    {
                        **panel,
                        "y": y,
                        "height": row_height,
                    }
                )
            y += row_height
            if row_index + 1 < len(rows):
                y += self.CONTENT_GAP

        return stretched, target_bottom


class TrueNASDiscordModernImageRenderer(
    _StandardizedSourceDiscordModernImageRenderer
):
    """Render TrueNAS cards on the frozen Grafana/Zabbix/XO baseline."""

    TRUENAS_XO_SECTION_ICONS = {
        "truenas system": "repository",
        "disk": "disk",
        "power": "alert",
        "storage": "disk",
        "notification test": "info",
        "scrub": "disk",
        "replication": "repository",
        "grouped alerts": "alert",
        "timing": "clock",
        "additional details": "list",
        "event details": "alert",
    }
    TRUENAS_XO_FIELD_ICONS = {
        "host": "repository",
        "pool": "disk",
        "pool status": "status",
        "device": "disk",
        "disk": "disk",
        "ups": "alert",
        "cause": "alert",
        "task": "list",
        "destination": "repository",
        "condition": "status",
        "error": "alert",
        "severity": "status",
        "alerts": "alert",
        "alert count": "list",
        "result": "status",
        "started": "play",
        "updated": "flag",
        "resolved": "flag",
        "finished": "flag",
        "duration": "clock",
    }

    def _zabbix_xo_section_icon(self, title: str) -> str:
        key = self._clean(title).casefold()
        if key.endswith(" result"):
            return "status"
        return self.TRUENAS_XO_SECTION_ICONS.get(
            key,
            "list",
        )

    def _zabbix_xo_field_icon(
        self,
        panel_title: str,
        label: str,
        value: str,
        fallback: str | None,
    ) -> str:
        key = self._clean(label).rstrip(":").casefold()
        if key in self.TRUENAS_XO_FIELD_ICONS:
            return self.TRUENAS_XO_FIELD_ICONS[key]
        return ZabbixDiscordModernImageRenderer._zabbix_xo_field_icon(
            self,
            panel_title,
            label,
            value,
            fallback,
        )


class UniFiNetworkDiscordModernImageRenderer(
    _StandardizedSourceDiscordModernImageRenderer
):
    """Render UniFi Network cards on the frozen standardized baseline."""

    UNIFI_NETWORK_XO_SECTION_ICONS = {
        "controller & network": "repository",
        "client / access point": "cube",
        "timing": "clock",
        "additional details": "list",
        "event details": "alert",
    }
    UNIFI_NETWORK_XO_FIELD_ICONS = {
        "controller": "repository",
        "network": "chart",
        "network / wi-fi": "chart",
        "wi-fi": "chart",
        "vlan": "list",
        "client": "cube",
        "access point": "cube",
        "last access point": "cube",
        "model": "cube",
        "mode": "list",
        "ip": "repository",
        "ip address": "repository",
        "band": "chart",
        "channel": "list",
        "wireless": "chart",
        "duration": "clock",
        "started": "play",
        "updated": "flag",
        "resolved": "flag",
        "finished": "flag",
    }

    def _zabbix_xo_section_icon(self, title: str) -> str:
        key = self._clean(title).casefold()
        if key.endswith(" result"):
            return "status"
        return self.UNIFI_NETWORK_XO_SECTION_ICONS.get(
            key,
            "list",
        )

    def _zabbix_xo_field_icon(
        self,
        panel_title: str,
        label: str,
        value: str,
        fallback: str | None,
    ) -> str:
        key = self._clean(label).rstrip(":").casefold()
        if key in self.UNIFI_NETWORK_XO_FIELD_ICONS:
            return self.UNIFI_NETWORK_XO_FIELD_ICONS[key]
        return ZabbixDiscordModernImageRenderer._zabbix_xo_field_icon(
            self,
            panel_title,
            label,
            value,
            fallback,
        )


class UniFiProtectDiscordModernImageRenderer(
    _StandardizedSourceDiscordModernImageRenderer
):
    """Render UniFi Protect cards on the frozen standardized baseline."""

    UNIFI_PROTECT_XO_SECTION_ICONS = {
        "trigger": "chart",
        "alarm rule": "alert",
        "timing": "clock",
        "additional details": "list",
        "event details": "alert",
    }
    UNIFI_PROTECT_XO_FIELD_ICONS = {
        "type": "chart",
        "trigger type": "chart",
        "device": "cube",
        "trigger device": "cube",
        "rule": "alert",
        "alarm rule": "alert",
        "condition": "list",
        "event": "play",
        "started": "play",
        "updated": "flag",
        "resolved": "flag",
        "finished": "flag",
        "duration": "clock",
    }

    def _zabbix_xo_section_icon(self, title: str) -> str:
        key = self._clean(title).casefold()
        if key.endswith(" result"):
            return "status"
        return self.UNIFI_PROTECT_XO_SECTION_ICONS.get(
            key,
            "list",
        )

    def _zabbix_xo_field_icon(
        self,
        panel_title: str,
        label: str,
        value: str,
        fallback: str | None,
    ) -> str:
        key = self._clean(label).rstrip(":").casefold()
        if key in self.UNIFI_PROTECT_XO_FIELD_ICONS:
            return self.UNIFI_PROTECT_XO_FIELD_ICONS[key]
        return ZabbixDiscordModernImageRenderer._zabbix_xo_field_icon(
            self,
            panel_title,
            label,
            value,
            fallback,
        )


class UniFiDriveDiscordModernImageRenderer(
    _StandardizedSourceDiscordModernImageRenderer
):
    """Render UniFi Drive cards on the frozen standardized baseline."""

    UNIFI_DRIVE_XO_SECTION_ICONS = {
        "drive event": "disk",
        "timing": "clock",
        "additional details": "list",
        "event details": "alert",
    }
    UNIFI_DRIVE_XO_FIELD_ICONS = {
        "system": "repository",
        "backup task": "disk",
        "alarm": "alert",
        "alarm rule": "alert",
        "alarm id": "list",
        "started": "play",
        "updated": "flag",
        "resolved": "flag",
        "finished": "flag",
        "duration": "clock",
    }

    def _zabbix_xo_section_icon(self, title: str) -> str:
        key = self._clean(title).casefold()
        if key.endswith(" result"):
            return "status"
        return self.UNIFI_DRIVE_XO_SECTION_ICONS.get(
            key,
            "list",
        )

    def _zabbix_xo_field_icon(
        self,
        panel_title: str,
        label: str,
        value: str,
        fallback: str | None,
    ) -> str:
        key = self._clean(label).rstrip(":").casefold()
        if key in self.UNIFI_DRIVE_XO_FIELD_ICONS:
            return self.UNIFI_DRIVE_XO_FIELD_ICONS[key]
        return ZabbixDiscordModernImageRenderer._zabbix_xo_field_icon(
            self,
            panel_title,
            label,
            value,
            fallback,
        )
