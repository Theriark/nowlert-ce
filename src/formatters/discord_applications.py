"""Presentation of native application notification events."""
from formatters.discord_common import DiscordCardFormatter, DiscordCardData, DiscordFact
from parsers.application_alerts import NAMES


class ApplicationDiscordFormatter(DiscordCardFormatter):
    def format(self, notification):
        metadata = notification.metadata or {}
        details = tuple(
            DiscordFact("📋", label, metadata.get(key))
            for key, label in (
                ("host", "Host"), ("service", "Service"), ("native_state", "Check state"),
                ("notification_type", "Notification type"), ("site", "Site"),
                ("template", "Template"), ("actor", "Actor"), ("version", "Version"),
                ("media_title", "Media"), ("download_client", "Download client"),
                ("question", "Question"), ("row_count", "Result rows"),
                ("branch", "Branch"), ("commit", "Commit"), ("event_type", "Event type"),
            )
            if metadata.get(key) not in (None, "")
        )
        if notification.run_id:
            details += (DiscordFact("📋", "Run ID", notification.run_id),)
        return self._render_discord_card(DiscordCardData(
            source=notification.source, integration=NAMES[notification.source],
            device=metadata.get("host") or metadata.get("instance") or metadata.get("repository") or NAMES[notification.source],
            event=notification.title, message=notification.body, status=notification.status,
            state=metadata.get("state", ""), severity=metadata.get("severity", ""),
            category=notification.category, source_area=metadata.get("event_type") or notification.category,
            event_time=notification.end_time or notification.start_time,
            details=details,
            url=metadata.get("action_link", ""), notification=notification,
        ))
