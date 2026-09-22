"""Measured, non-truncating components shared by every Discord Modern image.

All measurements are per render. A long event cannot leave dimensions on the
renderer that affect the next event (renderer instances are shared by workers).
"""
from __future__ import annotations

from io import BytesIO
from math import ceil

from PIL import Image, ImageDraw, ImageFilter


class ModernCardLayoutMixin:
    """The Xen Orchestra visual system, with fixed readable type and flowing boxes."""

    MODERN_PADDING = 70
    MODERN_GAP = 22

    def _init_modern_fonts(self):
        def build(sizes):
            bold_roles = {
                "heading",
                "title",
                "badge",
                "section",
                "label",
            }
            return {
                role: self._font(
                    role in bold_roles,
                    size,
                )
                for role, size in sizes.items()
            }

        default = build(
            {
                "heading": 54,
                "title": 42,
                "badge": 38,
                "section": 38,
                "label": 36,
                "body": 40,
                "context": 36,
                "footer": 28,
            }
        )
        self.modern_font_profiles = {
            "default": default,
            "xo_large": build(
                {
                    "heading": 66,
                    "title": 60,
                    "badge": 48,
                    "section": 52,
                    "label": 50,
                    "body": 56,
                    "context": 46,
                    "footer": 34,
                }
            ),
            "xo_match": build(
                {
                    "heading": 62,
                    "title": 52,
                    "badge": 46,
                    "section": 46,
                    "label": 40,
                    "body": 42,
                    "context": 40,
                    "footer": 40,
                }
            ),
        }
        self.modern_fonts = default

    def _modern_fonts_for(self, profile="default"):
        return self.modern_font_profiles.get(
            profile,
            self.modern_fonts,
        )

    def _modern_lines(
        self,
        draw,
        value,
        width,
        role,
        fonts=None,
    ):
        """Wrap paragraphs and indivisible identifiers without ellipses or scaling."""
        fonts = fonts or self.modern_fonts
        font = fonts[role]
        result = []
        for paragraph in str(value or "—").splitlines():
            result.extend(self._wrapped_text_lines(draw, paragraph, width, font) or [""])
        return result or ["—"]

    def _modern_text(
        self,
        draw,
        value,
        width,
        role="body",
        color=None,
        fonts=None,
    ):
        fonts = fonts or self.modern_fonts
        lines = self._modern_lines(
            draw,
            value,
            width,
            role,
            fonts,
        )
        font = fonts[role]
        # Ascent + descent also covers accented characters and fallback glyphs.
        line_height = max(font.size + 10, sum(font.getmetrics()))
        return {
            "lines": lines,
            "role": role,
            "font": font,
            "height": len(lines) * line_height,
            "line_height": line_height,
            "color": color or self.TEXT,
        }

    def _modern_paint_text(self, draw, text, x, y):
        for index, line in enumerate(text["lines"]):
            draw.text(
                (x, y + index * text["line_height"]),
                line,
                font=text["font"],
                fill=text["color"],
                anchor="lt",
            )

    def _modern_panel(self, draw, panel, width, fonts=None):
        """Measure a neutral details panel or a colored outcome panel."""
        fonts = fonts or self.modern_fonts
        inside = width - 48
        rows = []
        y = 22
        title = panel.get("title")
        if title:
            text = self._modern_text(
                draw,
                title,
                inside - 54,
                "section",
                panel.get("accent") or self.LABEL,
                fonts,
            )
            rows.append({"x": 76, "y": y, "text": text,
                         "icon": "status" if panel.get("accent") else "list"})
            y += text["height"] + 16
        for row in panel.get("rows", []):
            label, value = row.get("label", ""), row.get("value", "")
            icon = row.get("icon")
            x = 24 + (46 if icon else 0)
            available = width - x - 24
            if label:
                label_width = ceil(
                    draw.textlength(
                        label,
                        font=fonts["label"],
                    )
                )
                # Keep short key/value pairs on one line; longer keys or values
                # get their own row rather than competing for a tiny column.
                value_width = available - label_width - 24
                inline = value_width >= 180
                label_text = self._modern_text(
                    draw,
                    label,
                    label_width + 1 if inline else available,
                    "label",
                    self.LABEL,
                    fonts,
                )
                rows.append({"x": x, "y": y, "text": label_text, "icon": icon})
                if inline:
                    text = self._modern_text(
                        draw,
                        value,
                        value_width,
                        color=row.get("color"),
                        fonts=fonts,
                    )
                    rows.append({"x": x + label_width + 24, "y": y, "text": text})
                    y += max(label_text["height"], text["height"]) + 10
                    continue
                y += label_text["height"] + 2
                icon = None
            text = self._modern_text(
                draw,
                value,
                available,
                row.get("role", "body"),
                row.get("color"),
                fonts,
            )
            rows.append({"x": x, "y": y, "text": text, "icon": icon})
            y += text["height"] + row.get("gap", 10)
        entries = panel.get("entries", [])
        if entries:
            columns = min(panel.get("columns", 1), len(entries))
            while columns > 1:
                entry_width = (width - 24) // columns
                if all(
                    len(
                        self._modern_lines(
                            draw,
                            entry[0]["value"],
                            entry_width - 94,
                            "section",
                            fonts,
                        )
                    )
                    <= 2
                    for entry in entries
                ):
                    break
                columns -= 1
            entry_width = (width - 24) // columns
            for start in range(0, len(entries), columns):
                measured = [
                    self._modern_panel(
                        draw,
                        {"rows": entry},
                        entry_width,
                        fonts,
                    )
                    for entry in entries[
                        start:start + columns
                    ]
                ]
                row_height = max(entry["height"] for entry in measured)
                for column, entry in enumerate(measured):
                    for row in entry["paint"]:
                        rows.append({**row, "x": row["x"] + 12 + column * entry_width,
                                     "y": row["y"] + y - 16})
                y += row_height - 16
        return {**panel, "width": width, "height": max(96, y + 12), "paint": rows}

    def _modern_panel_rows(
        self,
        draw,
        panels,
        width,
        fonts=None,
    ):
        """Pair compact panels; let dense panels use the full available width."""
        fonts = fonts or self.modern_fonts
        result, y, index = [], 0, 0
        half = (width - self.MODERN_GAP) // 2
        while index < len(panels):
            current = panels[index]
            if (index + 1 < len(panels) and not current.get("full_width")
                    and not panels[index + 1].get("full_width")):
                pair = [
                    self._modern_panel(
                        draw,
                        panel,
                        half,
                        fonts,
                    )
                    for panel in panels[
                        index:index + 2
                    ]
                ]
                # Moderate wrapping is intentional; dense paragraphs get full
                # width so the card is not made needlessly tall in Discord.
                if max(p["height"] for p in pair) <= 660:
                    height = max(p["height"] for p in pair)
                    for col, panel in enumerate(pair):
                        result.append({**panel, "x": col * (half + self.MODERN_GAP),
                                       "y": y, "height": height})
                    y += height + self.MODERN_GAP
                    index += 2
                    continue
            panel = self._modern_panel(
                draw,
                current,
                width,
                fonts,
            )
            result.append({**panel, "x": 0, "y": y})
            y += panel["height"] + self.MODERN_GAP
            index += 1
        return result, max(0, y - self.MODERN_GAP)

    def _standard_card_plan(
        self,
        *,
        integration,
        context,
        badge,
        title,
        severity,
        category,
        event_time,
        details,
        outcomes,
        font_profile="default",
    ):
        """Compute every bounding box before allocating the final image."""
        fonts = self._modern_fonts_for(
            font_profile
        )
        draw = ImageDraw.Draw(
            Image.new("RGB", (self.WIDTH, 1))
        )
        x0 = self.MODERN_PADDING
        width = self.WIDTH - 2 * x0
        badge_width = min(
            ceil(width * .47),
            max(
                getattr(self, "MODERN_BADGE_MIN_WIDTH", 0),
                260,
                108 + ceil(
                    draw.textlength(
                        badge,
                        font=fonts["badge"],
                    )
                ),
            ),
        )
        badge_text = self._modern_text(
            draw,
            badge,
            badge_width - 104,
            "badge",
            fonts=fonts,
        )
        badge_height = max(80, badge_text["height"] + 32)
        heading_width = width - 140 - badge_width - 24
        heading = self._modern_text(
            draw,
            integration,
            heading_width,
            "heading",
            fonts=fonts,
        )
        subtitle = self._modern_text(
            draw,
            context,
            heading_width,
            "context",
            self.HEADER_MUTED,
            fonts,
        )
        y = 72
        header_height = max(
            120,
            heading["height"] + 8 + subtitle["height"],
            badge_height,
        )
        if getattr(
            self,
            "MODERN_BADGE_FILL_HEADER",
            False,
        ):
            badge_height = header_height
        header = {
            "y": y,
            "heading": heading,
            "subtitle": subtitle,
            "badge": badge_text,
            "badge_width": badge_width,
            "badge_height": badge_height,
            "header_height": header_height,
        }
        y += header_height + 24
        report = self._modern_text(
            draw,
            title,
            width - 48,
            "title",
            fonts=fonts,
        )
        title_box = (x0, y, x0 + width, y + report["height"] + 30)
        y = title_box[3] + self.MODERN_GAP
        summary = []
        offset = 0
        summary_height = 0
        widths = [int(width * .26), int(width * .25)]
        widths.append(width - sum(widths))
        for (label, value, icon), cell_width in zip(
                [("Severity", severity, "status"), ("Category", category, "sync"),
                 ("Event time", event_time or "—", "clock")], widths):
            label_text = self._modern_text(
                draw,
                label,
                cell_width - 76,
                "label",
                fonts=fonts,
            )
            value_text = self._modern_text(
                draw,
                value,
                cell_width - 32,
                "context",
                fonts=fonts,
            )
            summary.append({"x": offset, "width": cell_width, "label": label_text,
                            "value": value_text, "icon": icon})
            summary_height = max(summary_height, label_text["height"] + value_text["height"] + 28)
            offset += cell_width
        summary_box = (x0, y, x0 + width, y + summary_height)
        y = summary_box[3] + self.MODERN_GAP
        detail_panels, detail_height = (
            self._modern_panel_rows(
                draw,
                details,
                width,
                fonts,
            )
        )
        for panel in detail_panels:
            panel["y"] += y
        y += detail_height + (self.MODERN_GAP if detail_panels else 0)
        outcome_panels, outcome_height = (
            self._modern_panel_rows(
                draw,
                outcomes,
                width,
                fonts,
            )
        )
        for panel in outcome_panels:
            panel["y"] += y
        y += outcome_height
        natural_footer_y = y + 28
        height = max(
            natural_footer_y + self.FOOTER_RESERVE,
            getattr(self, "MODERN_MIN_HEIGHT", 0),
        )
        footer_y = max(
            natural_footer_y,
            height - self.FOOTER_RESERVE,
        )
        return {"header": header, "report": report, "title_box": title_box,
                "summary": summary, "summary_box": summary_box,
                "panels": detail_panels + outcome_panels,
                "footer_y": footer_y, "height": height,
                "font_profile": font_profile}

    def _render_standard_card(
        self,
        *,
        source,
        accent,
        status,
        font_profile="default",
        **content,
    ):
        fonts = self._modern_fonts_for(
            font_profile
        )
        plan = self._standard_card_plan(
            **content,
            font_profile=font_profile,
        )
        height = plan["height"]
        image = self._background(self.WIDTH, height)
        self._outer_glows(image, accent, height)
        draw = ImageDraw.Draw(image, "RGBA")
        outer = (30, 38, self.WIDTH - 30, height - 38)
        self._rounded(draw, outer, fill=(*self.CARD_BG, 247),
                      outline=(*self.PANEL_BORDER, 220), radius=28, width=2)
        self._modern_glow(image, (34, 56, 44, height - 56), accent, 6, 220)
        draw = ImageDraw.Draw(image, "RGBA")
        self._draw_status_rail(draw, accent, height)
        self._draw_gold_frame(draw, outer)
        x0, right = self.MODERN_PADDING, self.WIDTH - self.MODERN_PADDING
        header = plan["header"]
        y = header["y"]
        if source == "xo":
            self._draw_xo_art(image, x0, y, size=120)
        else:
            self._draw_product_icon(image, source, x0, y, 120, 112)
        self._modern_paint_text(draw, header["heading"], x0 + 140, y)
        self._modern_paint_text(draw, header["subtitle"], x0 + 140,
                                y + header["heading"]["height"] + 8)
        badge_box = (right - header["badge_width"], y, right, y + header["badge_height"])
        self._modern_glow(image, badge_box, accent, 17, 170)
        draw = ImageDraw.Draw(image, "RGBA")
        self._rounded(draw, badge_box, fill=(*self._tint(accent, self.CARD_BG, .16), 245),
                      outline=(*accent, 230), radius=17, width=2)
        if getattr(self, "MODERN_XO_ICON_STYLE", False):
            badge_icon_size = 64
            badge_icon_y = y + max(
                0,
                (header["badge_height"] - badge_icon_size) // 2,
            )
            badge_text_y = y + max(
                0,
                (
                    header["badge_height"]
                    - header["badge"]["height"]
                ) // 2,
            )
            self._modern_status_icon(
                draw,
                badge_box[0] + 28,
                badge_icon_y,
                badge_icon_size,
                status,
                accent,
            )
            self._modern_paint_text(
                draw,
                {**header["badge"], "color": accent},
                badge_box[0] + 112,
                badge_text_y,
            )
        else:
            self._modern_status_icon(
                draw,
                badge_box[0] + 18,
                y + 18,
                44,
                status,
                accent,
            )
            self._modern_paint_text(
                draw,
                {**header["badge"], "color": accent},
                badge_box[0] + 80,
                y + 16,
            )
        self._rounded(draw, plan["title_box"], fill=(*self.PANEL_2, 248),
                      outline=(93, 101, 108, 195), radius=14, width=2)
        self._modern_paint_text(draw, plan["report"], x0 + 24, plan["title_box"][1] + 15)
        box = plan["summary_box"]
        self._rounded(draw, box, fill=(*self.PANEL, 248),
                      outline=(*self.PANEL_BORDER, 205), radius=14, width=1)
        for index, cell in enumerate(plan["summary"]):
            x = x0 + cell["x"] + 16
            xo_icons = getattr(
                self,
                "MODERN_XO_ICON_STYLE",
                False,
            )
            icon_size = 54 if xo_icons else 36
            icon_y = box[1] + (
                16 if xo_icons else 12
            )
            text_offset = 66 if xo_icons else 46
            if cell["icon"] == "status":
                self._modern_status_icon(
                    draw,
                    x,
                    icon_y,
                    icon_size,
                    status,
                    accent,
                )
            else:
                self._draw_icon_badge(
                    draw,
                    x,
                    icon_y,
                    icon_size,
                    cell["icon"],
                    self.ICON_BLUE,
                )
            self._modern_paint_text(
                draw,
                cell["label"],
                x + text_offset,
                box[1] + 12,
            )
            self._modern_paint_text(
                draw,
                cell["value"],
                x,
                box[1] + 16 + cell["label"]["height"],
            )
            if index:
                draw.line((x - 16, box[1] + 16, x - 16, box[3] - 16),
                          fill=(*self.PANEL_BORDER, 180), width=2)
        for panel in plan["panels"]:
            px, py = x0 + panel["x"], panel["y"]
            panel_accent = panel.get("accent")
            box = (px, py, px + panel["width"], py + panel["height"])
            if panel_accent:
                self._modern_glow(image, box, panel_accent, 15, 110)
                draw = ImageDraw.Draw(image, "RGBA")
            self._rounded(draw, box,
                          fill=(*(self._tint(panel_accent, self.CARD_BG, .20)
                                  if panel_accent else self.PANEL_2), 248),
                          outline=(*(panel_accent or self.PANEL_BORDER), 225), radius=15, width=2)
            for row in panel["paint"]:
                rx, ry = px + row["x"], py + row["y"]
                if row.get("icon") == "status":
                    status_icon_size = (
                        54
                        if getattr(
                            self,
                            "MODERN_XO_ICON_STYLE",
                            False,
                        )
                        else 38
                    )
                    self._modern_status_icon(
                        draw,
                        px + 22,
                        ry,
                        status_icon_size,
                        panel.get("status", status),
                        panel_accent or accent,
                    )
                elif row.get("icon"):
                    field_icon_size = (
                        44
                        if getattr(
                            self,
                            "MODERN_XO_ICON_STYLE",
                            False,
                        )
                        else 30
                    )
                    self._draw_field_icon(
                        draw,
                        rx - 46,
                        ry + 3,
                        field_icon_size,
                        row["icon"],
                    )
                self._modern_paint_text(draw, row["text"], rx, ry)
        footer_y = plan["footer_y"]
        draw.line((x0, footer_y - 8, right, footer_y - 8), fill=(81, 89, 95, 150), width=1)
        self._draw_nowlert_icon(image, x0 + 18, footer_y + 4, 40)
        draw.text(
            (x0 + 70, footer_y + 10),
            self.FOOTER_TEXT,
            font=fonts["footer"],
            fill=self.MUTED,
        )
        output = BytesIO()
        image.convert("RGB").save(output, format="PNG", optimize=True, compress_level=7)
        return output.getvalue()

    def _modern_status_icon(self, draw, x, y, size, status, accent):
        if status != "warning":
            self._status_icon(draw, x, y, size, status, accent)
            return
        draw.polygon([(x + size / 2, y), (x + size, y + size), (x, y + size)], fill=accent)
        draw.line((x + size / 2, y + size * .30, x + size / 2, y + size * .63),
                  fill=self.CARD_BG, width=max(3, size // 10))
        draw.ellipse((x + size * .45, y + size * .76, x + size * .55, y + size * .86),
                     fill=self.CARD_BG)

    @staticmethod
    def _modern_glow(image, box, color, radius, alpha):
        """Blur only the component bounds, not the entire growing card."""
        padding = 30
        left, top = max(0, int(box[0]) - padding), max(0, int(box[1]) - padding)
        right = min(image.width, int(box[2]) + padding)
        bottom = min(image.height, int(box[3]) + padding)
        glow = Image.new("RGBA", (right - left, bottom - top))
        draw = ImageDraw.Draw(glow)
        draw.rounded_rectangle((box[0] - left, box[1] - top, box[2] - left, box[3] - top),
                               radius=radius, outline=(*color, alpha), width=10)
        image.alpha_composite(glow.filter(ImageFilter.GaussianBlur(9)), (left, top))
