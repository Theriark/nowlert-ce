"""Microsoft Teams presentation for Prometheus Alertmanager events."""

from __future__ import annotations

from typing import Any

from formatters.teams_common import TeamsCardData, TeamsCardFormatter, TeamsFact
from models import Notification


class PrometheusTeamsFormatter(TeamsCardFormatter):
    """Format Prometheus alerts using the shared Teams contract."""

    MAX_ALERTS = 10

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

        details = [
            TeamsFact("📥", "Receiver", metadata.get("receiver")),
            TeamsFact("🧩", "Service", metadata.get("service")),
            TeamsFact("⚙️", "Job", metadata.get("job")),
            TeamsFact("📦", "Namespace", metadata.get("namespace")),
            TeamsFact("🧱", "Pod", metadata.get("pod")),
            TeamsFact("🖥️", "Node", metadata.get("node")),
        ]
        extra_body: list[dict[str, Any]] = []
        actions: list[dict[str, Any]] = []

        if self.card_style == "classic":
            labels = self._labels_text(metadata.get("labels"))
            if labels:
                details.append(TeamsFact("🏷️", "Labels", labels))

            reason = str(metadata.get("notification_reason") or "").strip()
            if reason:
                details.append(TeamsFact("🔔", "Reason", reason))

            try:
                truncated = max(
                    0,
                    int(metadata.get("truncated_alerts") or 0),
                )
            except (TypeError, ValueError):
                truncated = 0
            if truncated:
                details.append(
                    TeamsFact("✂️", "Truncated alerts", truncated)
                )

            if notification.start_time:
                details.append(
                    TeamsFact(
                        "▶️",
                        "Started",
                        self._format_datetime(notification.start_time),
                    )
                )
            if state.casefold() == "resolved" and notification.end_time:
                details.append(
                    TeamsFact(
                        "🏁",
                        "Resolved",
                        self._format_datetime(notification.end_time),
                    )
                )

            grouped = self._grouped_alerts(metadata)
            if grouped:
                extra_body.append(grouped)

            for label, key in (
                ("Open Alertmanager", "external_url"),
                ("Open Prometheus", "generator_url"),
                ("Open runbook", "runbook_url"),
            ):
                url = str(metadata.get(key) or "").strip()
                if url:
                    actions.append(
                        {
                            "type": "Action.OpenUrl",
                            "title": label,
                            "url": url,
                        }
                    )

        return self._render_teams_card(
            TeamsCardData(
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
                details=tuple(details),
                extra_body=tuple(extra_body),
                actions=tuple(actions),
            )
        )

    def _grouped_alerts(
        self,
        metadata: dict[str, Any],
    ) -> dict[str, Any] | None:
        try:
            count = max(1, int(metadata.get("alert_count") or 1))
        except (TypeError, ValueError):
            count = 1
        if count <= 1:
            return None

        lines = []
        members = metadata.get("group_members")
        if isinstance(members, list):
            for index, member in enumerate(
                members[: self.MAX_ALERTS],
                start=1,
            ):
                if not isinstance(member, dict):
                    continue
                name = str(
                    member.get("title")
                    or f"Alert {index}"
                ).strip()
                qualifiers = []
                for key in ("state", "severity"):
                    value = str(member.get(key) or "").strip()
                    if value and value.casefold() != "unspecified":
                        qualifiers.append(self._label(value))
                member_target = str(member.get("target") or "").strip()
                if member_target:
                    qualifiers.append(member_target)
                line = f"**{self._truncate(name, 300)}**"
                if qualifiers:
                    line += " · " + " · ".join(qualifiers)
                lines.append(self._truncate(line, 900))

        if count > self.MAX_ALERTS:
            lines.append(f"… and {count - self.MAX_ALERTS} more")
        if not lines:
            return None

        return {
            "type": "Container",
            "spacing": "Medium",
            "separator": True,
            "items": [
                {
                    "type": "TextBlock",
                    "text": f"👥 Alerts · {count}",
                    "weight": "Bolder",
                    "wrap": True,
                },
                {
                    "type": "TextBlock",
                    "text": "\n".join(lines),
                    "spacing": "Small",
                    "wrap": True,
                },
            ],
        }

    @staticmethod
    def _labels_text(value: Any) -> str:
        if isinstance(value, dict):
            return ", ".join(
                f"{key}={item}"
                for key, item in value.items()
                if str(item or "").strip()
            )
        return str(value or "").strip()
