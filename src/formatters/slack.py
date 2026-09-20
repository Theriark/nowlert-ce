"""Bounded Slack presentation for normalized notifications."""

from __future__ import annotations

from formatters.presentation import PresentationMixin
from models import Notification
from outputs.platform_common import safe_action_url


CLASSIC_FOOTER = "🦉 Nowlert CE • Classic Card"


class SlackFormatter(PresentationMixin):
    """Render source-specific classic cards with a generic Block Kit fallback."""

    def format(self, notification: Notification, *, include_metadata: bool = True) -> dict:
        if str(notification.source or "").strip().casefold() == "xo":
            return self._format_xo_classic(notification)

        metadata = notification.metadata or {}
        title = self._truncate(
            notification.title or notification.subject or "Notification",
            150,
        )
        source = self._truncate(
            metadata.get("provider") or notification.source or "Nowlert",
            100,
        )
        severity = self._truncate(
            metadata.get("severity") or notification.status or "information",
            64,
        )
        host = self._truncate(
            metadata.get("host")
            or metadata.get("hostname")
            or metadata.get("device")
            or metadata.get("node"),
            128,
        )
        message = self._truncate(notification.body or title, 2800)
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": title, "emoji": True},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": self._escape(message)},
            },
        ]
        fields = [
            self._field("Source", source),
            self._field("Severity", severity),
        ]
        if notification.status:
            fields.append(self._field("Status", notification.status))
        if host:
            fields.append(self._field("Host", host))
        if include_metadata and notification.category:
            fields.append(self._field("Category", notification.category))
        blocks.append({"type": "section", "fields": fields[:10]})

        event_time = metadata.get("event_time") or notification.start_time
        context = f"Nowlert • {source}"
        if event_time:
            formatted = self._format_datetime(event_time)
            if formatted:
                context += f" • {formatted}"
        blocks.append(
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": self._escape(context)[:2000]}
                ],
            }
        )

        action = safe_action_url(metadata.get("action_link"))
        if action:
            blocks.append(
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Open event",
                                "emoji": True,
                            },
                            "url": action,
                        }
                    ],
                }
            )
        return self._sanitize_payload({"text": title, "blocks": blocks[:50]})

    def _format_xo_classic(self, notification: Notification) -> dict:
        """Mirror the approved Discord Classic Xen Orchestra card in Slack."""

        status = str(notification.status or "").strip().casefold()
        failed = status in {"failure", "failed", "error", "critical"}
        skipped_count = int(getattr(notification, "vm_skipped", 0) or 0)
        skipped = status == "skipped" or (not failed and skipped_count > 0)

        if failed:
            color, icon, lifecycle = "#ED4245", "❌", "Backup Failed"
        elif skipped:
            color, icon, lifecycle = "#5865F2", "⏭️", "Backup Skipped"
        else:
            color, icon, lifecycle = "#57F287", "✅", "Backup Successful"

        job_name = str(
            getattr(notification, "job_name", "")
            or notification.title
            or notification.subject
            or "Xen Orchestra backup"
        ).strip()
        title = self._truncate(f"{icon} {lifecycle} — {job_name}", 200)

        vm_success = int(getattr(notification, "vm_success", 0) or 0)
        vm_failed = int(getattr(notification, "vm_failed", 0) or 0)
        vm_total = int(getattr(notification, "vm_total", 0) or 0)

        if failed:
            count = max(1, vm_failed)
            description = (
                f"Backup operation failed with {count} VM error."
                if count == 1
                else f"Backup operation failed with {count} VM errors."
            )
        elif skipped:
            protected = vm_success
            protected_label = "VM" if protected == 1 else "VMs"
            skipped_label = "VM was" if skipped_count == 1 else "VMs were"
            description = (
                f"{protected} {protected_label} protected successfully and "
                f"{skipped_count} {skipped_label} skipped by backup policy."
            )
        else:
            protected = vm_success or vm_total
            protected_label = "VM" if protected == 1 else "VMs"
            description = (
                f"{protected} {protected_label} protected successfully "
                "with no failures."
            )

        repository = str(getattr(notification, "repository", "") or "").strip()
        repository_parts = [
            part.strip()
            for part in repository.split("|")
            if part.strip()
        ]
        if len(repository_parts) >= 3:
            repository_parts = [repository_parts[-1], *repository_parts[:-1]]

        mode = str(getattr(notification, "mode", "") or "").strip()
        if mode:
            mode = mode[:1].upper() + mode[1:]
        storage_parts = list(repository_parts)
        if mode:
            storage_parts.append(mode)
        storage_value = " · ".join(storage_parts)

        fields = []
        for field in (
            self._classic_field(
                "⏱️ Duration",
                self._classic_code(getattr(notification, "duration", "")),
                short=True,
            ),
            self._classic_field(
                "📦 Transfer Size",
                self._classic_code(getattr(notification, "transfer_size", "")),
                short=True,
            ),
            self._classic_field(
                "🚀 Transfer Speed",
                self._classic_code(getattr(notification, "transfer_speed", "")),
                short=True,
            ),
            self._classic_field(
                "📁 Storage",
                self._classic_code(storage_value),
            ),
            self._classic_vm_field(
                "✅ Successful VMs",
                getattr(notification, "successful_vms", None),
                getattr(notification, "vm_details", None),
            ),
            self._classic_vm_field(
                "❌ Failed VMs",
                getattr(notification, "failed_vms", None),
                getattr(notification, "vm_details", None),
                include_error=True,
            ),
            self._classic_vm_field(
                "⏭️ Skipped VMs",
                getattr(notification, "skipped_vms", None),
                getattr(notification, "vm_details", None),
                include_error=True,
            ),
            self._classic_field(
                "🆔 Job ID",
                self._classic_code(getattr(notification, "job_id", "")),
            ),
        ):
            if field is not None:
                fields.append(field)

        attachment = {
            "color": color,
            "title": title,
            "text": description,
            "fields": fields[:10],
            "footer": CLASSIC_FOOTER,
            "mrkdwn_in": ["text", "fields"],
        }
        icon_url = self._product_icon_url("xo")
        if icon_url:
            attachment["thumb_url"] = icon_url

        return self._sanitize_payload(
            {
                "text": title,
                "attachments": [attachment],
            }
        )

    def _classic_vm_field(
        self,
        name,
        values,
        details,
        *,
        include_error: bool = False,
    ):
        if not isinstance(values, list) or not values:
            return None
        if not isinstance(details, dict):
            details = {}

        vm_names = [
            str(value or "").strip()
            for value in values
            if str(value or "").strip()
        ]
        if not vm_names:
            return None

        lines = []
        shown = vm_names[:10]
        for vm_name in shown:
            item = details.get(vm_name)
            if not isinstance(item, dict):
                item = {}
            size = str(item.get("size") or "").strip()
            line = f"*{self._escape(vm_name)}*"
            if size:
                line += f" · {self._classic_code(size)}"
            lines.append(line)

            if include_error and str(item.get("error") or "").strip():
                lines.append(
                    f"*Error:* {self._classic_code(item.get('error'))}"
                )

        remaining = len(vm_names) - len(shown)
        if remaining > 0:
            lines.append(f"… and {remaining} more")

        return self._classic_field(
            f"{name} · {len(vm_names)}",
            "\n".join(lines),
        )

    def _classic_field(self, title, value, *, short: bool = False):
        rendered = str(value or "").strip()
        if not rendered:
            return None
        return {
            "title": self._truncate(title, 200),
            "value": rendered[:1800],
            "short": bool(short),
        }

    def _classic_code(self, value):
        rendered = " ".join(
            str(value or "").replace(chr(96), "'").splitlines()
        ).strip()
        if not rendered:
            return ""
        if len(rendered) > 900:
            rendered = rendered[:899].rstrip() + "…"
        return f"`{self._escape(rendered)}`"

    def _field(self, label, value):
        return {
            "type": "mrkdwn",
            "text": f"*{self._escape(label)}*\n{self._escape(value)[:1800]}",
        }

    @staticmethod
    def _escape(value) -> str:
        return (
            str(value or "")
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
