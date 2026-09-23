"""Microsoft Teams presentation for Prometheus Alertmanager events."""

from __future__ import annotations

from formatters.teams_common import TeamsCardData, TeamsCardFormatter, TeamsFact
from models import Notification


class PrometheusTeamsFormatter(TeamsCardFormatter):
    """Format Prometheus alerts using the shared Teams contract."""

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
                details=(
                    TeamsFact("📥", "Receiver", metadata.get("receiver")),
                    TeamsFact("🧩", "Service", metadata.get("service")),
                    TeamsFact("⚙️", "Job", metadata.get("job")),
                    TeamsFact("📦", "Namespace", metadata.get("namespace")),
                    TeamsFact("🧱", "Pod", metadata.get("pod")),
                    TeamsFact("🖥️", "Node", metadata.get("node")),
                ),
            )
        )
