"""Safe versioned presentation for the native Nowlert Mobile Simple Card."""
from datetime import datetime, timezone
from integrations.catalog import canonical_source, integrations
from outputs.platform_common import notification_context
from storage.sanitize import sanitize_text
from formatters.classic_card_v1 import render_classic_card_v1

STYLE = "mobile_simple_card_v1"
_NAMES = {item["source"]: item["name"] for item in integrations()}


def _text(value, limit):
    return sanitize_text(value)[:limit]


def _event_time(value):
    text = _text(value, 128)
    if text.isascii() and text.isdigit() and len(text) in (10, 13):
        try:
            return datetime.fromtimestamp(int(text) / (1000 if len(text) == 13 else 1), timezone.utc).isoformat()
        except (ValueError, OverflowError, OSError):
            pass
    return text


def render_mobile_simple_card(notification):
    context = notification_context(notification)
    source = canonical_source(context["source"])
    metadata = notification.metadata or {}
    fields = []
    title = context["title"][:256]
    if source == "checkmk":
        service = _text(metadata.get("service"), 1024)
        title = "Service notification" if service else "Host notification"
        fields = [
            {"title": "Host", "value": context["host"]},
            {"title": "Service", "value": service},
            {"title": "Service state" if service else "Host state",
             "value": _text(metadata.get("native_state"), 1024)},
        ]
    else:
        # Share the reviewed source-specific semantics used by Slack/Discord,
        # while keeping the wire format independent of either destination.
        presentation = render_classic_card_v1(notification)
        title = _text(presentation.get("title") or title, 256)
        fields = [{"title": _text(field.get("title"), 128),
                   "value": _text(field.get("value"), 1024)}
                  for field in presentation.get("fields", [])[:8]]
    return {
        "style": STYLE, "source": source,
        "source_name": _NAMES.get(source, "Nowlert CE"),
        "title": title, "severity": context["severity"],
        "status": _text(metadata.get("state") or context["status"], 64),
        "event_time": _event_time(notification.start_time or metadata.get("event_time")),
        "fields": [field for field in fields if field["value"]][:8],
    }
