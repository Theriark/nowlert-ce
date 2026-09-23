"""Shared Microsoft Teams Adaptive Card presentation contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from formatters.base import BaseFormatter
from version import VERSION


@dataclass(frozen=True)
class TeamsFact:
    """One icon-labelled integration-specific card detail."""

    icon: str
    label: str
    value: Any


@dataclass(frozen=True)
class TeamsCardData:
    """Normalized data consumed by the shared Teams renderer."""

    source: str
    integration: str
    device: str
    event: str
    message: str
    status: str = "information"
    state: str = ""
    severity: str = ""
    category: str = ""
    source_area: str = ""
    event_time: Any = ""
    device_icon: str = "🖥️"
    source_area_icon: str = "📍"
    event_icon: str = "🔔"
    details: tuple[TeamsFact, ...] = ()
    extra_body: tuple[dict[str, Any], ...] = ()
    actions: tuple[dict[str, Any], ...] = ()


class TeamsCardFormatter(BaseFormatter):
    """Render normalized integration data using one native Teams card layout."""

    MODERN_FOOTER = "Nowlert CE • Modern Card"
    CLASSIC_FOOTER = "Nowlert CE • Classic Card"
    CARD_STYLES = {"modern", "classic"}

    def __init__(self, *, card_style: str = "modern") -> None:
        normalized = str(card_style or "modern").strip().casefold()
        if normalized not in self.CARD_STYLES:
            raise ValueError("Teams card_style must be modern or classic")
        self.card_style = normalized

    def _render_teams_card(self, data: TeamsCardData) -> dict[str, Any]:
        status_icon, color, default_state = self._teams_status(
            data.status,
            data.severity,
        )
        state = self._label(data.state) or default_state
        severity = self._label(data.severity) or default_state
        category = self._label(data.category) or "Event"
        source_area = self._label(data.source_area) or category
        device = self._truncate(data.device or data.integration, 160)
        event = self._truncate(data.event or "Notification", 280)
        message = self._truncate(data.message or event, 4000)
        event_time = self._format_datetime(data.event_time)

        metrics = [
            self._teams_metric(status_icon, "Severity", severity),
            self._teams_metric(
                self._category_icon(data.category),
                "Category",
                category,
            ),
        ]
        if event_time:
            metrics.append(
                self._teams_metric("🕒", "Event time", event_time)
            )
        for index, metric in enumerate(metrics):
            metric["spacing"] = "Medium" if index else "None"
            metric["separator"] = index > 0

        # Keep the legacy top-level text/color metadata because a few external
        # consumers inspect the Adaptive Card JSON before Teams renders it.
        legacy_title = (
            f"{data.device_icon} {status_icon} {device} • {event}"
        )
        header = self._teams_modern_header(
            data=data,
            legacy_title=legacy_title,
            color=color,
            status_icon=status_icon,
            state=state,
            device=device,
            event=event,
            source_area=source_area,
        )

        body: list[dict[str, Any]] = [
            header,
            {
                "type": "TextBlock",
                "text": (
                    f"{data.integration} • {status_icon} **{state}** • "
                    f"{data.source_area_icon} {source_area}"
                ),
                "isSubtle": True,
                "size": "Small",
                "spacing": "Small",
                "wrap": True,
            },
            {
                "type": "Container",
                "style": "emphasis",
                "spacing": "Medium",
                "separator": True,
                "items": [
                    {
                        "type": "TextBlock",
                        "text": self._truncate(
                            f"{data.event_icon} {message}",
                            4000,
                        ),
                        "weight": "Bolder",
                        "size": "Medium",
                        "wrap": True,
                    }
                ],
            },
            {
                "type": "ColumnSet",
                "spacing": "Medium",
                "separator": True,
                "columns": metrics,
            },
        ]

        facts = [
            {
                "title": f"{fact.icon} {self._truncate(fact.label, 120)}:",
                "value": self._truncate(fact.value, 1000),
            }
            for fact in data.details
            if self._meaningful_fact(fact.value)
        ]
        if facts:
            body.append(
                {
                    "type": "Container",
                    "style": "emphasis",
                    "spacing": "Medium",
                    "separator": True,
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": "🧾 Event details",
                            "weight": "Bolder",
                            "size": "Medium",
                            "wrap": True,
                        },
                        {
                            "type": "FactSet",
                            "spacing": "Small",
                            "facts": facts,
                        },
                    ],
                }
            )

        body.extend(data.extra_body)
        body.append(self._teams_footer())

        card: dict[str, Any] = {
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "type": "AdaptiveCard",
            "version": "1.4",
            "msteams": {"width": "Full"},
            "body": body,
        }
        if data.actions:
            card["actions"] = list(data.actions)
        return {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": card,
                }
            ],
        }

    def _teams_modern_header(
        self,
        *,
        data: TeamsCardData,
        legacy_title: str,
        color: str,
        status_icon: str,
        state: str,
        device: str,
        event: str,
        source_area: str,
    ) -> dict[str, Any]:
        """Build the shared native Teams header and lifecycle badge."""

        status_style = color.casefold()
        heading_items: list[dict[str, Any]] = [
            {
                "type": "TextBlock",
                "text": self._truncate(data.integration or "Nowlert", 160),
                "weight": "Bolder",
                "size": "Large",
                "wrap": True,
            },
            {
                "type": "TextBlock",
                "text": (
                    f"{data.device_icon} {device} • "
                    f"{data.source_area_icon} {source_area}"
                ),
                "isSubtle": True,
                "size": "Small",
                "spacing": "Small",
                "wrap": True,
            },
            {
                "type": "TextBlock",
                "text": event,
                "weight": "Bolder",
                "size": "Medium",
                "spacing": "Medium",
                "wrap": True,
            },
            {
                "type": "ColumnSet",
                "spacing": "Small",
                "columns": [
                    {
                        "type": "Column",
                        "width": "auto",
                        "items": [
                            {
                                "type": "Container",
                                "style": status_style,
                                "items": [
                                    {
                                        "type": "TextBlock",
                                        "text": f"{status_icon} {state}",
                                        "weight": "Bolder",
                                        "horizontalAlignment": "Center",
                                        "wrap": True,
                                    }
                                ],
                            }
                        ],
                    }
                ],
            },
        ]

        columns: list[dict[str, Any]] = [
            {
                "type": "Column",
                "width": "stretch",
                "verticalContentAlignment": "Center",
                "items": heading_items,
            }
        ]
        icon_url = self._product_icon_url(data.source)
        if icon_url:
            normalized_source = str(data.source or "").strip().casefold()
            icon_pixels = self.TEAMS_ICON_PIXELS.get(
                normalized_source,
                48,
            )
            icon_size = f"{icon_pixels}px"
            columns.append(
                {
                    "type": "Column",
                    "width": "auto",
                    "verticalContentAlignment": "Center",
                    "items": [
                        {
                            "type": "Image",
                            "url": icon_url,
                            "altText": f"{data.integration} icon",
                            "size": "Small",
                            "width": icon_size,
                            "height": icon_size,
                        }
                    ],
                }
            )

        return {
            "type": "ColumnSet",
            "text": self._truncate(legacy_title, 512),
            "color": color,
            "spacing": "None",
            "columns": columns,
        }

    def _teams_footer(self) -> dict[str, Any]:
        """Render the shared footer with the selected Teams card identity."""

        footer = (
            self.CLASSIC_FOOTER
            if self.card_style == "classic"
            else self.MODERN_FOOTER
        )
        icon_url = self._product_icon_url("nowlert")

        if self.card_style == "classic":
            if not icon_url:
                return {
                    "type": "TextBlock",
                    "text": footer,
                    "isSubtle": True,
                    "size": "Small",
                    "spacing": "Medium",
                    "separator": True,
                    "horizontalAlignment": "Right",
                    "wrap": True,
                }

            return {
                "type": "ColumnSet",
                "text": footer,
                "spacing": "Medium",
                "separator": True,
                "columns": [
                    {
                        "type": "Column",
                        "width": "stretch",
                        "items": [],
                    },
                    {
                        "type": "Column",
                        "width": "auto",
                        "verticalContentAlignment": "Center",
                        "items": [
                            {
                                "type": "Image",
                                "url": icon_url,
                                "altText": "Nowlert icon",
                                "width": "32px",
                                "height": "32px",
                            }
                        ],
                    },
                    {
                        "type": "Column",
                        "width": "auto",
                        "verticalContentAlignment": "Center",
                        "spacing": "Small",
                        "items": [
                            {
                                "type": "TextBlock",
                                "text": footer,
                                "isSubtle": True,
                                "size": "Small",
                                "horizontalAlignment": "Right",
                                "wrap": True,
                            }
                        ],
                    },
                ],
            }

        if not icon_url:
            return {
                "type": "TextBlock",
                "text": (
                    f"{footer}\n"
                    f"Theriark • Nowlert v{VERSION}"
                ),
                "isSubtle": True,
                "size": "Small",
                "spacing": "Medium",
                "separator": True,
                "wrap": True,
            }

        return {
            "type": "ColumnSet",
            "text": footer,
            "spacing": "Medium",
            "separator": True,
            "columns": [
                {
                    "type": "Column",
                    "width": "auto",
                    "verticalContentAlignment": "Center",
                    "items": [
                        {
                            "type": "Image",
                            "url": icon_url,
                            "altText": "Nowlert icon",
                            "width": "32px",
                            "height": "32px",
                        }
                    ],
                },
                {
                    "type": "Column",
                    "width": "stretch",
                    "verticalContentAlignment": "Center",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": footer,
                            "isSubtle": True,
                            "size": "Small",
                            "wrap": True,
                        },
                        {
                            "type": "TextBlock",
                            "text": f"Theriark • Nowlert v{VERSION}",
                            "isSubtle": True,
                            "size": "Small",
                            "spacing": "None",
                            "wrap": True,
                        }
                    ],
                },
            ],
        }

    def _teams_modern_footer(self) -> dict[str, Any]:
        """Backward-compatible alias for the shared native Teams footer."""

        return self._teams_footer()

    @staticmethod
    def _teams_metric(icon: str, label: str, value: Any) -> dict[str, Any]:
        return {
            "type": "Column",
            "width": "stretch",
            "items": [
                {
                    "type": "TextBlock",
                    "text": f"{icon} {label}",
                    "weight": "Bolder",
                    "size": "Small",
                    "isSubtle": True,
                    "wrap": True,
                },
                {
                    "type": "TextBlock",
                    "text": str(value),
                    "weight": "Bolder",
                    "spacing": "Small",
                    "wrap": True,
                },
            ],
        }

    @staticmethod
    def _teams_status(status: Any, severity: Any = "") -> tuple[str, str, str]:
        status_value = str(status or "").strip().casefold()
        severity_value = str(severity or "").strip().casefold()
        resolved = {
            "cleared", "normal", "ok", "recovered", "resolved", "success",
            "successful",
        }
        critical = {
            "critical", "danger", "disaster", "emergency", "error",
            "failed", "failure", "high",
        }
        warning = {
            "alert", "average", "caution", "degraded", "medium", "warn",
            "warning",
        }

        # The current event state wins over a historical severity. A recovery
        # from a disaster is green, while an informational event carrying a
        # critical severity remains red.
        if status_value in resolved:
            return "✅", "Good", "Resolved"
        if status_value in critical:
            return "🚨", "Attention", "Critical"
        if status_value in warning:
            return "⚠️", "Warning", "Warning"
        values = {severity_value}
        if values & critical:
            return "🚨", "Attention", "Critical"
        if values & warning:
            return "⚠️", "Warning", "Warning"
        if values & resolved:
            return "✅", "Good", "Resolved"
        return "ℹ️", "Accent", "Information"

    @staticmethod
    def _category_icon(category: Any) -> str:
        value = str(category or "").strip().casefold()
        rules = (
            (("storage", "disk", "raid", "volume"), "💾"),
            (("security", "auth", "login"), "🛡️"),
            (("backup", "replication", "sync"), "🔄"),
            (("power", "ups", "battery"), "🔌"),
            (("network", "wifi", "ethernet"), "🌐"),
            (("update", "firmware"), "⬆️"),
            (("thermal", "temperature", "fan"), "🌡️"),
            (("memory", "dimm", "ecc"), "🧠"),
            (("system", "hardware"), "⚙️"),
        )
        for terms, icon in rules:
            if any(term in value for term in terms):
                return icon
        return "📁"

    @staticmethod
    def _label(value: Any) -> str:
        text = str(value or "").replace("_", " ").strip()
        if not text:
            return ""

        def label_token(token: str) -> str:
            parts = token.split("-")
            return "-".join(
                part
                if part.isupper() or any(character.isdigit() for character in part)
                else part.capitalize()
                for part in parts
            )

        return " ".join(label_token(token) for token in text.split())

    def _meaningful_fact(self, value: Any) -> bool:
        """Reject empty and formatter-sentinel values without hiding zero."""

        if value is None:
            return False
        text = self._sanitize_text(value).strip()
        return text.casefold() not in {"", "-", "—", "n/a", "none", "null"}
