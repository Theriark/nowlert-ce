"""Native application notifications, without an agent or polling service."""

from __future__ import annotations

import re

from models import Notification


NAMES = {
    "semaphore": "Semaphore",
    "sonarr": "Sonarr",
    "radarr": "Radarr",
    "metabase": "Metabase",
    "github_actions": "GitHub Actions",
}


def text(value, limit=4000):
    return str(value or "").strip()[:limit]


def object_value(payload, key):
    value = payload.get(key)
    return value if isinstance(value, dict) else {}


class Parser:
    def __init__(self, source):
        if source not in NAMES:
            raise ValueError("unsupported application")
        self.source = source

    def is_envelope(self, payload):
        if not isinstance(payload, dict):
            return False
        if self.source in {"sonarr", "radarr"}:
            return bool(text(payload.get("eventType"))) and isinstance(payload.get("instanceName"), str)
        if self.source == "metabase":
            data = object_value(payload, "data")
            return payload.get("type") == "alert" and data.get("type") == "question" and bool(data.get("question_name"))
        if self.source == "github_actions":
            if "zen" in payload and isinstance(payload.get("hook"), dict):
                return True  # Native webhook registration ping.
            run = object_value(payload, "workflow_run") or object_value(payload, "workflow_job")
            return bool(run.get("id")) and bool(object_value(payload, "repository").get("full_name")) and bool(payload.get("action"))
        attachments = payload.get("attachments")
        return isinstance(attachments, list) and bool(attachments) and all(
            isinstance(item, dict) and text(item.get("title")).startswith("Task:")
            and re.search(r"execution #\d+, status:", text(item.get("text")), re.I)
            for item in attachments
        )

    def parse(self, payload):
        if not self.is_envelope(payload):
            raise ValueError(f"invalid {NAMES[self.source]} notification")
        if self.source == "semaphore":
            return [self._semaphore(item) for item in payload["attachments"]]
        if self.source in {"sonarr", "radarr"}:
            return [self._servarr(payload)]
        if self.source == "metabase":
            data = payload["data"]
            raw = object_value(data, "raw_data")
            rows = raw.get("rows") if isinstance(raw.get("rows"), list) else []
            state = "test" if payload.get("alert_id") is None else "firing"
            return [self._notification(
                text(data["question_name"]), f"Question alert: {text(data['question_name'])}. {len(rows)} result row(s).",
                state, "information", "monitoring", {
                    "question_id": text(data.get("question_id")), "question": text(data["question_name"]),
                    "alert_id": text(payload.get("alert_id")), "creator": text(payload.get("alert_creator_name")),
                    "action_link": text(data.get("question_url")), "row_count": len(rows), "event_type": "question_alert",
                }, start_time=text(payload.get("sent_at")),
            )]
        if "zen" in payload:
            return [self._notification("GitHub webhook connected", text(payload.get("zen")), "test", "information", "automation", {})]
        run = object_value(payload, "workflow_run") or object_value(payload, "workflow_job")
        repository = text(payload["repository"]["full_name"])
        state = text(run.get("conclusion") or run.get("status") or payload["action"]).casefold()
        severity = "error" if state in {"failure", "timed_out", "action_required", "startup_failure"} else "information"
        return [self._notification(
            text(run.get("name") or "GitHub Actions run"), f"{repository}: {text(run.get('name'))} — {state}",
            state, severity, "automation", {
                "repository": repository, "workflow": text(run.get("name")), "branch": text(run.get("head_branch")),
                "commit": text(run.get("head_sha")), "action": text(payload["action"]),
                "event_type": "workflow_run" if "workflow_run" in payload else "workflow_job",
                "actor": text(object_value(payload, "sender").get("login")), "action_link": text(run.get("html_url")),
            }, run_id=text(run.get("id")), start_time=text(run.get("run_started_at") or run.get("started_at")),
            end_time=text(run.get("completed_at")),
        )]

    def _servarr(self, payload):
        event = text(payload["eventType"])
        health = object_value(payload, "health")
        media = object_value(payload, "series" if self.source == "sonarr" else "movie")
        severity = text(payload.get("level") or health.get("type") or "information").casefold()
        if event == "HealthIssue" and severity not in {"warning", "error", "critical"}:
            severity = "warning"
        if event == "ManualInteractionRequired":
            severity = "warning"
        state = "resolved" if event == "HealthRestored" else "test" if event == "Test" else "firing" if event in {"HealthIssue", "ManualInteractionRequired"} else "information"
        message = text(payload.get("message") or health.get("message") or object_value(payload, "release").get("releaseTitle") or media.get("title") or event)
        return self._notification(
            f"{NAMES[self.source]}: {event}", message, state, severity, "automation", {
                "event_type": event, "instance": text(payload.get("instanceName")), "media_title": text(media.get("title")),
                "download_client": text(payload.get("downloadClient")), "download_id": text(payload.get("downloadId")),
                "health_type": text(payload.get("type") or health.get("source")), "message": message,
                "action_link": text(payload.get("wikiUrl") or health.get("wikiUrl") or payload.get("applicationUrl")),
            },
        )

    def _semaphore(self, attachment):
        message = text(attachment["text"])
        match = re.search(r"execution #(\d+), status:\s*(.*?)!?(?:\n|$)", message, re.I)
        result = match.group(2).rstrip("!").strip().casefold()
        state = next((value for value in ("failure", "failed", "success", "waiting", "running", "stopped") if value in result), result)
        fields = {text(field.get("title")).casefold(): text(field.get("value")) for field in attachment.get("fields", []) if isinstance(field, dict)}
        return self._notification(
            text(attachment["title"])[5:].strip(), message, state,
            "error" if state in {"failure", "failed"} else "information", "automation", {
                "template": text(attachment["title"])[5:].strip(), "actor": fields.get("author", ""),
                "version": fields.get("version", ""), "action_link": text(attachment.get("title_link")),
                "event_type": "task_result",
            }, run_id=match.group(1),
        )

    def _notification(self, title, body, state, severity, category, metadata, **kwargs):
        status = "success" if state in {"success", "resolved"} else "failure" if severity in {"error", "critical"} else "warning" if severity == "warning" else "information"
        metadata = {**metadata, "state": state, "severity": severity, "provider": NAMES[self.source], "parser_confidence": "high"}
        return Notification(source=self.source, category=category, status=status, title=title, subject=title, body=body, metadata=metadata, **kwargs)
