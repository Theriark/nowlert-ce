"""Bounded native Mobile payloads from CE's safe notification context."""
import hashlib
from storage.sanitize import sanitize_text

from outputs.platform_common import notification_context


def mobile_payload(destination, notification, settings):
    context = notification_context(notification)
    raw_metadata = notification.metadata or {}
    if not context["host"]:
        context["host"] = sanitize_text(raw_metadata.get("system") or raw_metadata.get("trigger_device_id")
            or raw_metadata.get("trigger_device") or raw_metadata.get("nas_name"))[:256]
    recovery = context["status"].casefold() in {"ok", "resolved", "recovery", "recovered", "success", "healthy"}
    severity = context["severity"].casefold()
    priority = "default" if recovery else {
        "warning": "high", "warn": "high", "critical": "urgent", "fatal": "urgent",
        "disaster": "urgent", "error": "high",
    }.get(severity, "default")
    metadata = {
        "producer": "nowlert-ce", "source_name": f"Nowlert CE · {context['source'] or 'alerts'}",
        "source": context["source"], "severity": context["severity"],
        "status": context["status"], "category": context["category"],
        "host": context["host"], "ce_event_id": context["event_id"],
    }
    route = (notification.metadata or {}).get("_ce_route")
    if isinstance(route, dict):
        metadata["route_id"] = sanitize_text(route.get("id"))[:128]
        metadata["route_name"] = sanitize_text(route.get("name"))[:128]
    # Group source/host/category, independently of changing titles and severity.
    thread_seed = "\x1f".join((destination.id, context["source"], context["host"], context["category"]))
    event_seed = "\x1f".join((destination.id, settings["topic_id"], context["event_id"],
        context["source"], context["host"], context["category"], context["status"],
        sanitize_text(notification.start_time), sanitize_text(notification.end_time),
        context["severity"], context["title"], context["body"],
        metadata.get("route_id", ""), metadata.get("route_name", "")))
    return {
        "target": {"type": "topic", "id": settings["topic_id"]},
        "content": {"title": context["title"][:256], "body": context["body"],
                    "metadata": metadata,
                    "actions": [{"type": "acknowledge", "label": "Acknowledge"}]},
        "priority": priority, "ttl_seconds": 86400,
        "thread_key": "nowlert-ce:" + hashlib.sha256(thread_seed.encode()).hexdigest()[:40],
        "idempotency_key": "nowlert-ce:" + hashlib.sha256(event_seed.encode()).hexdigest(),
    }
