"""Teams-native Classic Card v1 formatters."""

from __future__ import annotations

from typing import Any

from formatters.base import BaseFormatter
from formatters.classic_card_v1 import render_classic_card_v1
from models import Notification
from outputs.platform_common import safe_action_url


CLASSIC_FOOTER = "🦉 Nowlert CE • Classic Card"


class TeamsClassicXenOrchestraFormatter(BaseFormatter):
    """Render Xen Orchestra Classic Card v1 as a Teams Adaptive Card."""

    MAX_VMS = 10

    def format(self, notification: Notification) -> dict[str, Any]:
        lifecycle = self._lifecycle(notification)
        title = (
            f"{lifecycle['icon']} {lifecycle['label']} — "
            f"{self._job_name(notification)}"
        )
        description = self._description(
            notification,
            lifecycle["state"],
        )

        body = [
            self._teams_header(
                title,
                lifecycle["color"],
                "xo",
            ),
            {
                "type": "TextBlock",
                "text": self._truncate(description, 1200),
                "wrap": True,
                "spacing": "Small",
            },
        ]

        metrics = self._metric_columns(notification)
        if metrics:
            body.append(
                {
                    "type": "ColumnSet",
                    "spacing": "Medium",
                    "separator": True,
                    "columns": metrics,
                }
            )

        body.extend(self._sections(notification))
        body.append(
            {
                "type": "TextBlock",
                "text": CLASSIC_FOOTER,
                "isSubtle": True,
                "size": "Small",
                "spacing": "Medium",
                "separator": True,
                "wrap": True,
            }
        )

        return {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                        "$schema": (
                            "http://adaptivecards.io/schemas/"
                            "adaptive-card.json"
                        ),
                        "type": "AdaptiveCard",
                        "version": "1.4",
                        "msteams": {"width": "Full"},
                        "body": body,
                    },
                }
            ],
        }

    @staticmethod
    def _lifecycle(notification: Notification) -> dict[str, str]:
        status = str(notification.status or "").strip().casefold()
        failed = status in {
            "failure",
            "failed",
            "error",
            "critical",
        }
        skipped_count = int(notification.vm_skipped or 0)
        skipped = (
            status == "skipped"
            or (not failed and skipped_count > 0)
        )

        if failed:
            return {
                "state": "failed",
                "icon": "❌",
                "label": "Backup Failed",
                "color": "Attention",
            }
        if skipped:
            return {
                "state": "skipped",
                "icon": "⏭️",
                "label": "Backup Skipped",
                "color": "Accent",
            }
        return {
            "state": "success",
            "icon": "✅",
            "label": "Backup Successful",
            "color": "Good",
        }

    @staticmethod
    def _job_name(notification: Notification) -> str:
        return str(
            notification.job_name
            or notification.title
            or notification.subject
            or "Xen Orchestra backup"
        ).strip()

    @staticmethod
    def _description(
        notification: Notification,
        state: str,
    ) -> str:
        vm_success = int(notification.vm_success or 0)
        vm_failed = int(notification.vm_failed or 0)
        vm_total = int(notification.vm_total or 0)
        vm_skipped = int(notification.vm_skipped or 0)

        if state == "failed":
            count = max(1, vm_failed)
            suffix = "VM error" if count == 1 else "VM errors"
            return f"Backup operation failed with {count} {suffix}."

        if state == "skipped":
            protected = vm_success
            protected_label = "VM" if protected == 1 else "VMs"
            skipped_label = "VM was" if vm_skipped == 1 else "VMs were"
            return (
                f"{protected} {protected_label} protected successfully and "
                f"{vm_skipped} {skipped_label} skipped by backup policy."
            )

        protected = vm_success or vm_total
        protected_label = "VM" if protected == 1 else "VMs"
        return (
            f"{protected} {protected_label} protected successfully "
            "with no failures."
        )

    def _metric_columns(
        self,
        notification: Notification,
    ) -> list[dict[str, Any]]:
        values = (
            ("⏱️ Duration", notification.duration),
            ("📦 Transfer Size", notification.transfer_size),
            ("🚀 Transfer Speed", notification.transfer_speed),
        )
        columns = []
        for label, value in values:
            rendered = str(value or "").strip()
            if not rendered:
                continue
            columns.append(
                {
                    "type": "Column",
                    "width": "stretch",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": label,
                            "weight": "Bolder",
                            "size": "Small",
                            "wrap": True,
                        },
                        {
                            "type": "TextBlock",
                            "text": self._truncate(rendered, 1000),
                            "spacing": "Small",
                            "wrap": True,
                        },
                    ],
                }
            )
        return columns

    def _storage_value(self, notification: Notification) -> str:
        repository_parts = [
            part.strip()
            for part in str(notification.repository or "").split("|")
            if part.strip()
        ]
        if len(repository_parts) >= 3:
            repository_parts = [
                repository_parts[-1],
                *repository_parts[:-1],
            ]

        mode = str(notification.mode or "").strip()
        if mode:
            mode = mode[:1].upper() + mode[1:]
            repository_parts.append(mode)

        return " · ".join(repository_parts)

    def _sections(
        self,
        notification: Notification,
    ) -> list[dict[str, Any]]:
        sections = []

        storage = self._storage_value(notification)
        if storage:
            sections.append(
                self._section(
                    "📁 Storage",
                    self._truncate(storage, 1800),
                )
            )

        vm_sections = (
            (
                "✅ Successful VMs",
                notification.successful_vms,
                False,
            ),
            (
                "❌ Failed VMs",
                notification.failed_vms,
                True,
            ),
            (
                "⏭️ Skipped VMs",
                notification.skipped_vms,
                True,
            ),
        )
        for label, names, include_error in vm_sections:
            rendered = self._vm_lines(
                notification,
                names,
                include_error=include_error,
            )
            if rendered:
                sections.append(
                    self._section(
                        f"{label} · {len(names)}",
                        rendered,
                    )
                )

        job_id = str(notification.job_id or "").strip()
        if job_id:
            sections.append(
                self._section(
                    "🆔 Job ID",
                    self._truncate(job_id, 1000),
                )
            )

        return sections

    def _vm_lines(
        self,
        notification: Notification,
        names: list[str],
        *,
        include_error: bool,
    ) -> str:
        normalized = [
            str(name or "").strip()
            for name in names
            if str(name or "").strip()
        ]
        if not normalized:
            return ""

        lines = []
        shown = normalized[: self.MAX_VMS]
        details = notification.vm_details or {}

        for name in shown:
            item = details.get(name)
            if not isinstance(item, dict):
                item = {}

            size = str(item.get("size") or "").strip()
            line = f"**{name}**"
            if size:
                line += f" · {self._truncate(size, 240)}"
            lines.append(line)

            error = str(item.get("error") or "").strip()
            if include_error and error:
                lines.append(
                    f"**Error:** {self._truncate(error, 700)}"
                )

        remaining = len(normalized) - len(shown)
        if remaining:
            lines.append(f"… and {remaining} more")

        return "\n".join(lines)

    @staticmethod
    def _section(title: str, value: str) -> dict[str, Any]:
        return {
            "type": "Container",
            "spacing": "Medium",
            "separator": True,
            "items": [
                {
                    "type": "TextBlock",
                    "text": title,
                    "weight": "Bolder",
                    "wrap": True,
                },
                {
                    "type": "TextBlock",
                    "text": value,
                    "spacing": "Small",
                    "wrap": True,
                },
            ],
        }


class TeamsClassicFormatter(BaseFormatter):
    """Render Discord Classic semantics in the approved Teams Classic geometry."""

    _ATTENTION = {0xE74C3C, 0xED4245}
    _WARNING = {0xF1C40F, 0xF39C12}
    _GOOD = {0x2ECC71, 0x57F287}

    def format(self, notification: Notification) -> dict[str, Any]:
        classic = render_classic_card_v1(notification)
        source = str(notification.source or "").strip().casefold()
        icon_source = source if source in self.PRODUCT_ICONS else "nowlert"

        body: list[dict[str, Any]] = [
            self._teams_header(
                self._teams_text(
                    classic.get("title") or "Notification",
                    256,
                ),
                self._teams_color(classic.get("color")),
                icon_source,
            )
        ]

        description = self._teams_text(
            classic.get("description"),
            4000,
        )
        if description:
            body.append(
                {
                    "type": "TextBlock",
                    "text": description,
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
            title = self._teams_text(field.get("title"), 256)
            value = self._teams_text(field.get("value"), 3500)
            if not title and not value:
                continue

            rendered = {
                "title": title,
                "value": value,
                "inline": bool(field.get("inline", False)),
            }
            if rendered["inline"]:
                inline_fields.append(rendered)
                if len(inline_fields) == 3:
                    flush_inline_fields()
                continue

            flush_inline_fields()
            body.append(
                self._full_width_section(
                    rendered["title"],
                    rendered["value"],
                )
            )

        flush_inline_fields()

        footer = self._teams_text(
            classic.get("footer") or CLASSIC_FOOTER,
            500,
        )
        if footer:
            body.append(
                {
                    "type": "TextBlock",
                    "text": footer,
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

        return {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": card,
                }
            ],
        }

    def _teams_text(self, value: object, maximum: int) -> str:
        # Discord Classic uses inline-code markers for compact embeds. Teams
        # Classic deliberately renders the approved plain-text geometry.
        rendered = str(value or "").replace(chr(96), "").strip()
        return self._truncate(rendered, maximum)

    def _inline_column(self, field: dict[str, Any]) -> dict[str, Any]:
        return {
            "type": "Column",
            "width": "stretch",
            "items": [
                {
                    "type": "TextBlock",
                    "text": field["title"],
                    "weight": "Bolder",
                    "size": "Small",
                    "wrap": True,
                },
                {
                    "type": "TextBlock",
                    "text": field["value"],
                    "spacing": "Small",
                    "wrap": True,
                },
            ],
        }

    @staticmethod
    def _full_width_section(
        title: str,
        value: str,
    ) -> dict[str, Any]:
        items = []
        if title:
            items.append(
                {
                    "type": "TextBlock",
                    "text": title,
                    "weight": "Bolder",
                    "wrap": True,
                }
            )
        if value:
            items.append(
                {
                    "type": "TextBlock",
                    "text": value,
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


__all__ = [
    "CLASSIC_FOOTER",
    "TeamsClassicFormatter",
    "TeamsClassicXenOrchestraFormatter",
]
