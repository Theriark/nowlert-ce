"""Discord presentation for Xen Orchestra backup events."""

from __future__ import annotations

from config import config
from formatters.discord_common import DiscordCardData, DiscordCardFormatter, DiscordFact
from models import Notification
from version import VERSION


class DiscordFormatter(DiscordCardFormatter):
    """Format Xen Orchestra notifications using the shared Discord contract."""

    MAX_VMS = 10

    def format(self, notification: Notification) -> dict:
        status_text = self._status_text(notification.status)
        job_name = (
            notification.job_name
            or notification.title
            or notification.subject
            or "Xen Orchestra backup"
        )
        details = [
            DiscordFact("🧰", "Mode", notification.mode),
            DiscordFact("⏱️", "Duration", self._short_duration(notification.duration)),
            DiscordFact("📦", "Transfer size", notification.transfer_size),
            DiscordFact("💾", "Repository", notification.repository),
            DiscordFact("🚀", "Speed", notification.transfer_speed),
            DiscordFact("📊", "Result", self._result_text(notification), False),
            DiscordFact("▶️", "Started", self._format_datetime(notification.start_time)),
            DiscordFact("🏁", "Finished", self._format_datetime(notification.end_time)),
        ]
        if config.get("notifications", "xo", "show_ids", default=False):
            details.extend((
                DiscordFact("🆔", "Run ID", notification.run_id, False),
                DiscordFact("🆔", "Job ID", notification.job_id, False),
            ))
        self._add_vm_fact(details, "❌", "Failed VM", "Failed VMs", notification.failed_vms, notification, True)
        self._add_vm_fact(details, "⚠️", "Skipped VM", "Skipped VMs", notification.skipped_vms, notification, True)
        self._add_vm_fact(details, "✅", "Successful VM", "Successful VMs", notification.successful_vms, notification, False)

        message = notification.body or notification.title or notification.subject or status_text
        return self._render_discord_card(
            DiscordCardData(
                notification=notification,
                source="xo",
                integration="Xen Orchestra",
                device=job_name,
                event=status_text,
                message=message,
                status=notification.status,
                state=status_text,
                severity=notification.status,
                category=notification.category or "backup",
                source_area=notification.repository or "Backup",
                event_time=notification.end_time or notification.start_time,
                device_icon="🗄️",
                source_area_icon="💾",
                event_icon="📋",
                details=tuple(details),
            )
        )

    def format_components_v2(self, notification: Notification) -> dict:
        """Render the approved Xen Orchestra Discord Modern backup card."""

        status_text = self._status_text(notification.status)
        status_value = str(notification.status or "").strip().casefold()
        failed = status_value in {"failure", "failed", "error", "critical"}
        skipped = (
            not failed
            and (
                status_value in {"skipped", "warning"}
                or bool(notification.vm_skipped or notification.skipped)
            )
        )
        if failed:
            status_icon, color, severity = "❌", 0xED4245, "Failure"
        elif skipped:
            status_icon, color, severity = "ℹ️", 0x3498DB, "Skipped"
        else:
            status_icon, color, severity = "✅", 0x57F287, "Success"

        job_name = (
            notification.job_name
            or notification.title
            or notification.subject
            or "Xen Orchestra backup"
        )
        repository = self._truncate(
            notification.repository or "Backup",
            280,
        )
        category = self._label(notification.category or "backup") or "Backup"
        event_time = self._format_datetime(
            notification.end_time or notification.start_time
        )
        report = (
            notification.subject
            or notification.body
            or f"Backup report for {job_name}"
        )

        title_text = f"### 🗄️ Xen Orchestra  •  {status_icon} {status_text}"
        context_text = f"-# {repository}\n**{self._truncate(job_name, 240)}**"
        icon_url = self._discord_product_icon_url("xo")
        if icon_url:
            header = {
                "type": self.COMPONENT_TYPE_SECTION,
                "components": [
                    self._discord_v2_text(title_text),
                    self._discord_v2_text(context_text),
                ],
                "accessory": {
                    "type": self.COMPONENT_TYPE_THUMBNAIL,
                    "media": {"url": icon_url},
                    "description": "Xen Orchestra logo",
                },
            }
        else:
            header = self._discord_v2_text(
                f"{title_text}\n{context_text}"
            )

        metrics = [
            f"{status_icon} **Severity:** {severity}",
            f"🔄 **Category:** {category}",
        ]
        if event_time:
            metrics.append(f"🕒 **Event time:** {event_time}")

        detail_lines: list[str] = []

        def add_detail(icon: str, label: str, value) -> None:
            if not self._meaningful_fact(value):
                return
            detail_lines.append(
                f"{icon} **{label}:** {self._truncate(value, 700)}"
            )

        add_detail("🧰", "Mode", notification.mode)
        add_detail(
            "⏱️",
            "Duration",
            self._short_duration(notification.duration),
        )
        add_detail("📦", "Transfer size", notification.transfer_size)
        add_detail("💾", "Repository", notification.repository)
        add_detail("🚀", "Speed", notification.transfer_speed)
        add_detail("📊", "Result", self._result_text(notification))
        add_detail(
            "▶️",
            "Started",
            self._format_datetime(notification.start_time),
        )
        add_detail(
            "🏁",
            "Finished",
            self._format_datetime(notification.end_time),
        )
        if config.get("notifications", "xo", "show_ids", default=False):
            add_detail("🆔", "Run ID", notification.run_id)
            add_detail("🆔", "Job ID", notification.job_id)

        children = [
            header,
            self._discord_v2_separator(),
            self._discord_v2_text(self._discord_highlight(report)),
            self._discord_v2_separator(divider=False),
            self._discord_v2_text("  •  ".join(metrics)),
            self._discord_v2_separator(),
            self._discord_v2_text(
                "**📋 Event details**\n"
                + ("\n".join(detail_lines) or "—")
            ),
        ]

        vm_sections = [
            self._modern_vm_section(
                notification,
                notification.failed_vms,
                "❌",
                "Failed VM",
                "Failed VMs",
                include_error=True,
            ),
            self._modern_vm_section(
                notification,
                notification.skipped_vms,
                "⚠️",
                "Skipped VM",
                "Skipped VMs",
                include_error=True,
            ),
            self._modern_vm_section(
                notification,
                notification.successful_vms,
                "✅",
                "Successful VM",
                "Successful VMs",
                include_error=False,
            ),
        ]
        children.extend(
            self._discord_v2_text(section)
            for section in vm_sections
            if section
        )
        children.extend((
            self._discord_v2_separator(),
            self._discord_v2_text(
                f"-# Theriark • Nowlert v{VERSION}  ·  "
                "Xen Orchestra Notification"
            ),
        ))

        return {
            "flags": self.COMPONENTS_V2_FLAG,
            "components": [
                {
                    "type": self.COMPONENT_TYPE_CONTAINER,
                    "accent_color": color,
                    "components": children,
                }
            ],
        }

    def _modern_vm_section(
        self,
        notification: Notification,
        vms: list[str],
        icon: str,
        singular: str,
        plural: str,
        *,
        include_error: bool,
    ) -> str:
        if not vms:
            return ""

        label = singular if len(vms) == 1 else plural
        lines = [f"{icon} **{label} ({len(vms)})**"]
        shown = vms[: self.MAX_VMS]
        for vm in shown:
            detail = notification.vm_details.get(vm, {}) or {}
            lines.append(f"{icon} **{self._truncate(vm, 180)}**")
            facts = []
            if detail.get("size"):
                facts.append(f"📦 {self._truncate(detail['size'], 80)}")
            if detail.get("speed"):
                facts.append(f"🚀 {self._truncate(detail['speed'], 80)}")
            repository = detail.get("repository")
            if repository and repository != notification.repository:
                facts.append(f"💾 {self._truncate(repository, 160)}")
            if facts:
                lines.append("-# " + " • ".join(facts))
            if include_error and detail.get("error"):
                lines.append(
                    "-# 🚨 "
                    + self._truncate(detail["error"], 420)
                )

        remaining = len(vms) - len(shown)
        if remaining:
            lines.append(f"-# … and {remaining} more")
        return self._truncate("\n".join(lines), 1800)

    @staticmethod
    def _status_text(status: str) -> str:
        value = str(status or "").casefold()
        if value in {"failure", "failed", "error"}:
            return "Backup Failure"
        if value in {"skipped", "warning"}:
            return "Backup Skipped"
        return "Backup Successful"

    def _result_text(self, notification: Notification) -> str:
        success = notification.vm_success or notification.successes
        failed = notification.vm_failed or notification.failures
        skipped = notification.vm_skipped or notification.skipped
        total = notification.vm_total or success + failed + skipped
        if not total:
            return ""
        parts = [f"✅ {success} of {total} VMs successful"]
        if failed:
            parts.append(f"❌ {failed} failed")
        if skipped:
            parts.append(f"⚠️ {skipped} skipped")
        return " • ".join(parts)

    def _add_vm_fact(
        self,
        details: list[DiscordFact],
        icon: str,
        singular: str,
        plural: str,
        vms: list[str],
        notification: Notification,
        include_error: bool,
    ) -> None:
        if not vms:
            return
        details.append(
            DiscordFact(
                icon,
                singular if len(vms) == 1 else plural,
                self._format_vm_details(notification, vms, icon, include_error),
                False,
            )
        )

    def _format_vm_details(
        self,
        notification: Notification,
        vms: list[str],
        icon: str,
        include_error: bool,
    ) -> str:
        lines = []
        shown = vms[: self.MAX_VMS]
        for vm in shown:
            detail = notification.vm_details.get(vm, {}) or {}
            lines.append(f"{icon} **{vm}**")
            parts = []
            if detail.get("size"):
                parts.append(f"📦 {detail['size']}")
            if detail.get("speed"):
                parts.append(f"🚀 {detail['speed']}")
            repository = detail.get("repository")
            if repository and repository != notification.repository:
                parts.append(f"💾 {repository}")
            if parts:
                lines.append("└─ " + " • ".join(parts))
            if include_error and detail.get("error"):
                lines.append(f"└─ 🚨 {detail['error']}")
        remaining = len(vms) - len(shown)
        if remaining:
            lines.append(f"… and {remaining} more")
        return "\n".join(lines)

    @staticmethod
    def _short_duration(value: str) -> str:
        if not value:
            return ""
        return (
            value.replace(" minutes", " min")
            .replace(" minute", " min")
            .replace(" seconds", " sec")
            .replace(" second", " sec")
        )
