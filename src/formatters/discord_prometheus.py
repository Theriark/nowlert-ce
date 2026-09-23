"""Discord presentation for Prometheus Alertmanager events."""

from __future__ import annotations

from formatters.discord_common import (
    DiscordCardData,
    DiscordCardFormatter,
    DiscordFact,
)
from models import Notification


class PrometheusDiscordFormatter(DiscordCardFormatter):
    """Format Prometheus alerts using the shared card contract."""

    CLASSIC_FOOTER = "🦉 Nowlert CE • Classic Card"

    def _classic_code(self, value, maximum=900) -> str:
        text = " ".join(
            self._sanitize_text(value).replace(chr(96), "'").splitlines()
        ).strip()
        if not text:
            return ""
        if len(text) > maximum:
            text = text[: max(1, maximum - 1)].rstrip() + "…"
        return f"`{text}`"

    def _classic_field(self, name, value, *, inline=False):
        rendered = str(value or "").strip()
        if not rendered:
            return None
        return {
            "name": str(name or "")[:256],
            "value": rendered[:1024],
            "inline": bool(inline),
        }

    def _classic_compact_context(self, metadata) -> str:
        parts = []
        for label, key in (
            ("Service", "service"),
            ("Job", "job"),
            ("Namespace", "namespace"),
            ("Pod", "pod"),
            ("Node", "node"),
        ):
            value = self._classic_code(metadata.get(key), 220)
            if value:
                parts.append(f"**{label}:** {value}")
        return " · ".join(parts)

    @staticmethod
    def _classic_severity_icon(severity) -> str:
        value = str(severity or "").strip().casefold()
        if value in {
            "critical", "danger", "disaster", "emergency", "error",
            "failed", "failure", "fatal", "high",
        }:
            return "🚨"
        if value in {
            "alert", "average", "caution", "degraded", "medium",
            "warn", "warning",
        }:
            return "⚠️"
        return "ℹ️"

    def format_discord_classic(self, notification: Notification) -> dict:
        """Render only Discord Classic with the compact XO-style geometry."""

        metadata = (
            notification.metadata
            if isinstance(notification.metadata, dict)
            else {}
        )
        status = str(notification.status or "").strip()
        state = str(metadata.get("state") or status).strip()
        severity = str(metadata.get("severity") or "unspecified").strip()
        severity_label = (
            severity.replace("_", " ").strip().title()
            or "Unspecified"
        )
        title_text = str(
            notification.title
            or notification.subject
            or "Prometheus alert"
        ).strip()
        description = str(
            metadata.get("description")
            or metadata.get("summary")
            or notification.body
            or title_text
        ).strip()[:4096]

        status_icon, color, default_state = self._discord_status(
            status,
            severity,
        )
        state_label = self._label(state) or default_state

        target = str(
            metadata.get("instance")
            or metadata.get("service")
            or metadata.get("job")
            or metadata.get("pod")
            or metadata.get("node")
            or metadata.get("namespace")
            or ""
        ).strip()
        receiver = str(metadata.get("receiver") or "").strip()

        fields = []

        def append(field):
            if field is not None:
                fields.append(field)

        append(
            self._classic_field(
                f"{self._classic_severity_icon(severity)} Severity",
                self._classic_code(severity_label),
                inline=True,
            )
        )
        append(
            self._classic_field(
                "🎯 Target",
                self._classic_code(target),
                inline=True,
            )
        )
        append(
            self._classic_field(
                "📥 Receiver",
                self._classic_code(receiver),
                inline=True,
            )
        )

        context = self._classic_compact_context(metadata)
        reason = self._classic_code(metadata.get("notification_reason"), 500)
        truncated = self._classic_code(metadata.get("truncated_alerts"), 120)
        prometheus_lines = []
        if context:
            prometheus_lines.append(context)
        if reason:
            prometheus_lines.append(f"**Reason:** {reason}")
        if truncated and truncated != "`0`":
            prometheus_lines.append(f"**Truncated:** {truncated}")
        append(
            self._classic_field(
                "📈 Prometheus",
                "\n".join(prometheus_lines),
            )
        )

        labels = metadata.get("labels")
        append(
            self._classic_field(
                "🏷️ Labels",
                self._classic_code(labels),
            )
        )

        try:
            count = max(1, int(metadata.get("alert_count") or 1))
        except (TypeError, ValueError):
            count = 1

        if count > 1:
            member_lines = []
            members = metadata.get("group_members")
            if isinstance(members, list):
                for index, member in enumerate(members[:10], start=1):
                    if not isinstance(member, dict):
                        continue
                    name = str(
                        member.get("title")
                        or f"Alert {index}"
                    ).strip()
                    qualifiers = [
                        str(member.get(key) or "").strip().title()
                        for key in ("state", "severity")
                        if str(member.get(key) or "").strip()
                    ]
                    member_target = str(
                        member.get("target") or ""
                    ).strip()
                    if member_target:
                        qualifiers.append(member_target)
                    line = f"**{name}**"
                    if qualifiers:
                        line += " · " + " · ".join(qualifiers)
                    member_lines.append(line)
            if count > 10:
                member_lines.append(f"… and {count - 10} more")
            append(
                self._classic_field(
                    f"👥 Alerts · {count}",
                    "\n".join(member_lines),
                )
            )

        timing_lines = []
        started = self._classic_code(notification.start_time)
        if started:
            timing_lines.append(f"**Started:** {started}")
        if state.casefold() == "resolved":
            resolved = self._classic_code(notification.end_time)
            if resolved:
                timing_lines.append(f"**Resolved:** {resolved}")
        append(
            self._classic_field(
                "⏱️ Timing",
                "\n".join(timing_lines),
            )
        )

        links = []
        for label, key in (
            ("Alertmanager", "external_url"),
            ("Prometheus", "generator_url"),
            ("Runbook", "runbook_url"),
        ):
            url = str(metadata.get(key) or "").strip()
            if url:
                links.append(f"[{label}]({url})")
        append(
            self._classic_field(
                "🔗 Links",
                " · ".join(links),
            )
        )

        embed = {
            "title": (
                f"{status_icon} {title_text} — {state_label}"
            )[:256],
            "description": description,
            "color": color,
            "fields": fields[:25],
            # Use the base packaged Prometheus artwork for the Classic
            # thumbnail. The adapter uploads this local asset directly.
            "thumbnail": {"url": "nowlert-asset://prometheus.png"},
            "footer": {"text": self.CLASSIC_FOOTER},
        }
        return {"embeds": [embed]}

    def format(self, notification: Notification) -> dict:
        metadata = notification.metadata or {}
        state = str(metadata.get("state") or notification.status or "").strip()
        title = notification.title or "Prometheus alert"
        target = (
            metadata.get("instance")
            or metadata.get("service")
            or metadata.get("job")
            or metadata.get("pod")
            or metadata.get("node")
            or metadata.get("namespace")
            or "Prometheus"
        )
        event_time = (
            notification.end_time
            if state.casefold() == "resolved" and notification.end_time
            else notification.start_time
        )
        return self._render_discord_card(
            DiscordCardData(
                notification=notification,
                source="prometheus",
                integration="Prometheus",
                device=target,
                event=title,
                message=notification.body or title,
                status=notification.status,
                state=state,
                severity=metadata.get("severity") or notification.status,
                category=notification.category or "monitoring",
                source_area=metadata.get("job")
                or metadata.get("receiver")
                or "Monitoring",
                event_time=event_time,
                device_icon="🔥",
                source_area_icon="📈",
                event_icon="🚨",
                details=(
                    DiscordFact("📥", "Receiver", metadata.get("receiver")),
                    DiscordFact("🧩", "Service", metadata.get("service")),
                    DiscordFact("⚙️", "Job", metadata.get("job")),
                    DiscordFact("📦", "Namespace", metadata.get("namespace")),
                    DiscordFact("🧱", "Pod", metadata.get("pod")),
                    DiscordFact("🖥️", "Node", metadata.get("node")),
                ),
                url=metadata.get("generator_url")
                or metadata.get("external_url")
                or "",
            )
        )
