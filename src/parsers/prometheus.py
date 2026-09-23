"""Prometheus Alertmanager webhook parser."""

from __future__ import annotations

from urllib.parse import urlsplit

from models import Notification


class Parser:
    """Validate and normalize one Alertmanager notification group."""

    STATES = {"firing", "resolved"}
    FAILURE = {"alert", "critical", "emergency", "error", "failed", "failure", "fatal"}
    WARNING = {"warn", "warning", "average", "degraded"}
    INFORMATION = {"debug", "info", "information", "informational", "notice"}

    @classmethod
    def is_envelope(cls, payload) -> bool:
        if not isinstance(payload, dict):
            return False
        version = cls._text(payload.get("version"))
        if version and version != "4":
            return False
        if cls._text(payload.get("status")).casefold() not in cls.STATES:
            return False
        alerts = payload.get("alerts")
        if not isinstance(alerts, list) or not alerts:
            return False
        for name in ("groupLabels", "commonLabels", "commonAnnotations"):
            if not isinstance(payload.get(name, {}), dict):
                return False
        for alert in alerts:
            if not isinstance(alert, dict):
                return False
            if cls._text(alert.get("status")).casefold() not in cls.STATES:
                return False
            if not isinstance(alert.get("labels"), dict):
                return False
            if not isinstance(alert.get("annotations"), dict):
                return False
        return True

    def parse(self, payload: dict) -> Notification:
        if not self.is_envelope(payload):
            raise ValueError("invalid Prometheus Alertmanager webhook envelope")

        alerts = payload["alerts"]
        common_labels = dict(payload.get("commonLabels") or {})
        common_annotations = dict(payload.get("commonAnnotations") or {})
        group_labels = dict(payload.get("groupLabels") or {})
        first = alerts[0]
        first_labels = dict(first.get("labels") or {})
        first_annotations = dict(first.get("annotations") or {})

        state = self._text(payload.get("status")).casefold()
        severity = self._highest_severity(
            [
                common_labels.get("severity"),
                *(alert.get("labels", {}).get("severity") for alert in alerts),
            ]
        )
        title = self._title(common_labels, common_annotations, alerts)
        summary = self._text(
            common_annotations.get("summary")
            or first_annotations.get("summary")
        )
        description = self._text(
            common_annotations.get("description")
            or first_annotations.get("description")
        )
        body = description or summary or title

        target_labels = {**common_labels, **first_labels}
        target = self._target(target_labels)
        start_time = self._text(first.get("startsAt"))
        end_time = self._text(first.get("endsAt")) if state == "resolved" else ""

        notification = Notification(
            source="prometheus",
            category="monitoring",
            status=self._status(state, severity),
            title=title,
            subject=title,
            body=body,
            start_time=start_time,
            end_time=end_time,
        )

        runbook_url = self._url(
            common_annotations.get("runbook_url")
            or common_annotations.get("runbook")
            or common_annotations.get("runbookURL")
            or first_annotations.get("runbook_url")
            or first_annotations.get("runbook")
            or first_annotations.get("runbookURL")
        )
        generator_url = self._url(first.get("generatorURL"))
        external_url = self._url(payload.get("externalURL"))

        members = []
        for alert in alerts:
            labels = dict(alert.get("labels") or {})
            annotations = dict(alert.get("annotations") or {})
            member_severity = (
                self._text(labels.get("severity")).casefold() or "unspecified"
            )
            members.append(
                {
                    "title": self._text(labels.get("alertname")) or "Prometheus alert",
                    "state": self._text(alert.get("status")).casefold(),
                    "severity": member_severity,
                    "target": self._target(labels),
                    "starts_at": self._text(alert.get("startsAt")),
                    "ends_at": self._text(alert.get("endsAt")),
                    "generator_url": self._url(alert.get("generatorURL")),
                    "fingerprint": self._text(alert.get("fingerprint")),
                    "labels": labels,
                    "annotations": annotations,
                }
            )

        notification.metadata = {
            "provider": "Prometheus Alertmanager",
            "state": state,
            "severity": severity or "unspecified",
            "alert_name": self._text(common_labels.get("alertname"))
            or self._text(first_labels.get("alertname")),
            "summary": summary,
            "description": description,
            "instance": self._text(target_labels.get("instance")),
            "service": self._text(target_labels.get("service")),
            "job": self._text(target_labels.get("job")),
            "namespace": self._text(target_labels.get("namespace")),
            "pod": self._text(target_labels.get("pod")),
            "node": self._text(target_labels.get("node")),
            "host": target,
            "receiver": self._text(payload.get("receiver")),
            "notification_reason": self._text(payload.get("notification_reason")),
            "group_key": self._text(payload.get("groupKey")),
            "group_labels": group_labels,
            "external_url": external_url,
            "generator_url": generator_url,
            "runbook_url": runbook_url,
            "fingerprint": self._text(first.get("fingerprint")),
            "alert_count": len(alerts),
            "truncated_alerts": self._integer(payload.get("truncatedAlerts")),
            "labels": self._labels_text(common_labels or first_labels),
            "raw_labels": common_labels,
            "raw_annotations": common_annotations,
            "group_members": members,
            "deduplication_key": self._text(payload.get("groupKey")),
            "parser_confidence": "high",
            "format": "alertmanager_webhook",
        }
        return notification

    @classmethod
    def _title(cls, common_labels, common_annotations, alerts) -> str:
        common_name = cls._text(common_labels.get("alertname"))
        if common_name:
            return common_name
        names = [
            cls._text(alert.get("labels", {}).get("alertname"))
            for alert in alerts
        ]
        names = [name for name in names if name]
        unique = list(dict.fromkeys(names))
        if len(unique) == 1:
            return unique[0]
        if len(unique) > 1:
            return "Prometheus alert group"
        return cls._text(common_annotations.get("summary")) or "Prometheus alert"

    @classmethod
    def _highest_severity(cls, values) -> str:
        normalized = [
            cls._text(value).casefold()
            for value in values
            if cls._text(value)
        ]
        for group in (cls.FAILURE, cls.WARNING, cls.INFORMATION):
            for value in normalized:
                if value in group:
                    return value
        return normalized[0] if normalized else ""

    @classmethod
    def _status(cls, state: str, severity: str) -> str:
        if state == "resolved":
            return "success"
        value = cls._text(severity).casefold()
        if value in cls.FAILURE:
            return "failure"
        if value in cls.INFORMATION:
            return "information"
        return "warning"

    @classmethod
    def _target(cls, labels: dict) -> str:
        for key in ("instance", "service", "job", "pod", "node", "namespace"):
            value = cls._text(labels.get(key))
            if value:
                return value
        return ""

    @classmethod
    def _labels_text(cls, labels: dict) -> str:
        hidden = {
            "alertname", "severity", "instance", "service",
            "job", "namespace", "pod", "node",
        }
        pairs = []
        for key in sorted(labels):
            if str(key).casefold() in hidden:
                continue
            value = cls._text(labels.get(key))
            if value:
                pairs.append(f"{key}={value}")
            if len(pairs) == 12:
                break
        return ", ".join(pairs)

    @staticmethod
    def _url(value) -> str:
        text = Parser._text(value)
        if not text:
            return ""
        try:
            parsed = urlsplit(text)
        except ValueError:
            return ""
        if parsed.scheme.casefold() not in {"http", "https"} or not parsed.netloc:
            return ""
        return text

    @staticmethod
    def _integer(value) -> int:
        try:
            return max(0, int(value))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _text(value) -> str:
        return "" if value is None else str(value).strip()
