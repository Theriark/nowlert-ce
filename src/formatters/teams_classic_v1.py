"""Teams-native Classic Card v1 renderer."""

from __future__ import annotations

from typing import Any

from formatters.base import BaseFormatter
from formatters.classic_card_v1 import render_classic_card_v1
from models import Notification
from outputs.platform_common import safe_action_url


CLASSIC_FOOTER = "🦉 Nowlert CE • Classic Card"


class TeamsClassicFormatter(BaseFormatter):
    """Render the approved Classic Card v1 model as Adaptive Card 1.4."""

    _ATTENTION = {0xE74C3C, 0xED4245}
    _WARNING = {0xF1C40F, 0xF39C12}
    _GOOD = {0x2ECC71, 0x57F287}

    def format(self, notification: Notification) -> dict[str, Any]:
        classic = render_classic_card_v1(notification)
        source = str(notification.source or "").strip().casefold()
        icon_source = (
            source
            if source in self.PRODUCT_ICONS
            else "nowlert"
        )

        body: list[dict[str, Any]] = [
            self._teams_header(
                classic.get("title") or "Notification",
                self._teams_color(classic.get("color")),
                icon_source,
            )
        ]

        description = str(classic.get("description") or "").strip()
        if description:
            body.append(
                {
                    "type": "TextBlock",
                    "text": self._truncate(description, 4000),
                    "wrap": True,
                    "spacing": "Small",
                }
            )

        inline_fields: list[dict[str, Any]] = []

        def flush_inline_fields() -> None:
            nonlocal inline_fields
            if not inline_fields:
                return
            body.append(
                {
                    "type": "ColumnSet",
                    "spacing": "Medium",
                    "separator": True,
                    "columns": [
                        self._inline_column(field)
                        for field in inline_fields
                    ],
                }
            )
            inline_fields = []

        for field in classic.get("fields", []):
            if not isinstance(field, dict):
                continue
            title = str(field.get("title") or "").strip()
            value = str(field.get("value") or "").strip()
            if not title and not value:
                continue

            if field.get("inline"):
                inline_fields.append(field)
                if len(inline_fields) == 3:
                    flush_inline_fields()
                continue

            flush_inline_fields()
            body.append(
                self._full_width_section(
                    title,
                    value,
                )
            )

        flush_inline_fields()

        footer = str(
            classic.get("footer")
            or CLASSIC_FOOTER
        ).strip()
        if footer:
            body.append(
                {
                    "type": "TextBlock",
                    "text": self._truncate(footer, 500),
                    "isSubtle": True,
                    "size": "Small",
                    "spacing": "Medium",
                    "separator": True,
                    "wrap": True,
                }
            )

        card: dict[str, Any] = {
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "type": "AdaptiveCard",
            "version": "1.4",
            "msteams": {"width": "Full"},
            "body": body,
        }

        action = safe_action_url(classic.get("url"))
        if action:
            card["actions"] = [
                {
                    "type": "Action.OpenUrl",
                    "title": "Open event",
                    "url": action,
                }
            ]

        return self._sanitize_payload(
            {
                "type": "message",
                "attachments": [
                    {
                        "contentType": (
                            "application/vnd.microsoft.card.adaptive"
                        ),
                        "content": card,
                    }
                ],
            }
        )

    def _inline_column(self, field: dict[str, Any]) -> dict[str, Any]:
        return {
            "type": "Column",
            "width": "stretch",
            "items": [
                {
                    "type": "TextBlock",
                    "text": self._truncate(
                        field.get("title"),
                        256,
                    ),
                    "weight": "Bolder",
                    "size": "Small",
                    "wrap": True,
                },
                {
                    "type": "TextBlock",
                    "text": self._truncate(
                        field.get("value"),
                        1600,
                    ),
                    "spacing": "Small",
                    "wrap": True,
                },
            ],
        }

    def _full_width_section(
        self,
        title: str,
        value: str,
    ) -> dict[str, Any]:
        items = []
        if title:
            items.append(
                {
                    "type": "TextBlock",
                    "text": self._truncate(title, 256),
                    "weight": "Bolder",
                    "wrap": True,
                }
            )
        if value:
            items.append(
                {
                    "type": "TextBlock",
                    "text": self._truncate(value, 3500),
                    "spacing": "Small",
                    "wrap": True,
                }
            )
        return {
            "type": "Container",
            "spacing": "Medium",
            "separator": True,
            "items": items,
        }

    @classmethod
    def _teams_color(cls, value: Any) -> str:
        try:
            color = int(value)
        except (TypeError, ValueError):
            return "Accent"
        if color in cls._ATTENTION:
            return "Attention"
        if color in cls._WARNING:
            return "Warning"
        if color in cls._GOOD:
            return "Good"
        return "Accent"


TeamsClassicXenOrchestraFormatter = TeamsClassicFormatter


__all__ = [
    "CLASSIC_FOOTER",
    "TeamsClassicFormatter",
    "TeamsClassicXenOrchestraFormatter",
]
