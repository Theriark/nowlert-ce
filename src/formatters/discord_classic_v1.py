"""Deterministic Discord Classic Embed v1 presentation.

This is the non-AI CE port of the source-specific Classic Embed v1 layouts
validated in Nowlert EE.  It is intentionally invoked only for Discord
classic destinations; Components V2 keeps using the existing formatter path.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, is_dataclass
import re
from typing import Any


CLASSIC_FOOTER = "🦉 Nowlert CE • Classic Embed"

_WORDS = re.compile(r"[^a-z0-9]+")
_RED = 0xE74C3C
_YELLOW = 0xF1C40F
_ORANGE = 0xF39C12
_GREEN = 0x2ECC71
_BLUE = 0x3498DB


def _normal_words(value: object) -> str:
    return " ".join(_WORDS.sub(" ", str(value or "").casefold()).split())


def _code(value: object, maximum: int = 900) -> str:
    text = " ".join(str(value or "").replace(chr(96), "'").splitlines()).strip()
    if not text:
        return ""
    if len(text) > maximum:
        text = text[: max(1, maximum - 1)].rstrip() + "…"
    return chr(96) + text + chr(96)


def _field(name: str, value: object, *, inline: bool = False) -> dict[str, Any] | None:
    rendered = str(value or "").strip()
    if not rendered:
        return None
    if len(rendered) > 1024:
        rendered = rendered[:1023].rstrip() + "…"
    return {"name": name[:256], "value": rendered, "inline": inline}


def _rows_field(name: str, rows: list[tuple[str, object]], *, inline: bool = False) -> dict[str, Any] | None:
    lines = []
    for label, value in rows:
        rendered = _code(value)
        if rendered:
            lines.append(f"**{label}:** {rendered}")
    return _field(name, "\n".join(lines), inline=inline)


def _list_field(name: str, values: object) -> dict[str, Any] | None:
    if not isinstance(values, (list, tuple)):
        return None
    rendered = [str(item).strip() for item in values if str(item or "").strip()]
    if not rendered:
        return None
    return _field(name, "\n".join(f"• {_code(item)}" for item in rendered))


def _metadata_value(metadata: dict[str, Any], *names: str) -> object:
    nested = metadata.get("metadata")
    if not isinstance(nested, dict):
        nested = {}
    source_fields = metadata.get("source_fields")
    if not isinstance(source_fields, dict):
        source_fields = {}
    fields = metadata.get("fields")
    if not isinstance(fields, dict):
        fields = {}
    for name in names:
        for mapping in (metadata, nested, source_fields, fields):
            value = mapping.get(name)
            if value not in (None, ""):
                return value
    return ""


def _normalized(notification) -> dict[str, Any]:
    if is_dataclass(notification):
        value = asdict(notification)
    else:
        value = dict(getattr(notification, "__dict__", {}) or {})
    metadata = value.get("metadata")
    if not isinstance(metadata, dict):
        value["metadata"] = {}
    return value


def _original_embed(payload: object) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    embeds = payload.get("embeds")
    if not isinstance(embeds, list) or not embeds or not isinstance(embeds[0], dict):
        return {}
    return embeds[0]


def _finish(
    embed: dict[str, Any],
    payload: object,
    *,
    preserve: tuple[str, ...] = ("thumbnail", "url", "timestamp"),
) -> dict[str, Any]:
    original = _original_embed(payload)
    for key in preserve:
        if key in original and key not in embed:
            embed[key] = deepcopy(original[key])
    embed["footer"] = {"text": CLASSIC_FOOTER}
    fields = embed.get("fields")
    if isinstance(fields, list):
        embed["fields"] = fields[:25]
    return {"embeds": [embed]}


def _lifecycle(status: object, severity: object, *, state: object = "") -> tuple[int, str, str]:
    status_words = _normal_words(status)
    state_words = _normal_words(state)
    severity_words = _normal_words(severity)
    resolved = {
        "cleared", "healthy", "normal", "ok", "recovered", "recovery",
        "resolved", "restored", "success", "successful", "succeeded",
    }
    failed = {
        "abnormal", "critical", "danger", "disaster", "emergency", "error",
        "failed", "failure", "fatal", "high",
    }
    warning = {
        "alert", "attention", "average", "caution", "degraded", "medium",
        "warn", "warning",
    }
    information = {"debug", "info", "information", "informational", "notice", "test"}

    if status_words in resolved or state_words in resolved:
        label = "Resolved" if status_words in {"cleared", "recovered", "recovery", "resolved", "restored"} or state_words in {"cleared", "recovered", "recovery", "resolved", "restored"} else "Success"
        return _GREEN, "✅", label
    if status_words in failed or state_words in failed or severity_words in failed:
        return _RED, "🚨", "Failed"
    if status_words in warning or state_words in warning or severity_words in warning:
        return _ORANGE, "⚠️", "Warning"
    if severity_words in resolved:
        return _GREEN, "✅", "Resolved"
    if status_words in information or severity_words in information:
        return _BLUE, "ℹ️", "Information"
    return _BLUE, "ℹ️", "Information"


def _render_xo(notification, payload, normalized, metadata):
    """Render the compact CE Xen Orchestra Classic Embed v1 geometry."""

    status = _normal_words(normalized.get("status"))
    failed = status in {"failure", "failed", "error", "critical"}
    skipped_count = int(normalized.get("vm_skipped") or 0)
    skipped = status == "skipped" or (not failed and skipped_count > 0)

    if failed:
        color, icon, lifecycle = 0xED4245, "❌", "Backup Failed"
    elif skipped:
        color, icon, lifecycle = 0x5865F2, "⏭️", "Backup Skipped"
    else:
        color, icon, lifecycle = 0x57F287, "✅", "Backup Successful"

    job_name = str(
        normalized.get("job_name")
        or normalized.get("title")
        or normalized.get("subject")
        or "Xen Orchestra backup"
    ).strip()

    vm_success = int(normalized.get("vm_success") or 0)
    vm_failed = int(normalized.get("vm_failed") or 0)
    vm_total = int(normalized.get("vm_total") or 0)

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
        description = f"{protected} {protected_label} protected successfully with no failures."

    repository = str(normalized.get("repository") or "").strip()
    repository_parts = [
        part.strip()
        for part in repository.split("|")
        if part.strip()
    ]
    if len(repository_parts) >= 3:
        repository_parts = [repository_parts[-1], *repository_parts[:-1]]

    mode = str(normalized.get("mode") or "").strip()
    if mode:
        mode = mode[:1].upper() + mode[1:]
    storage_parts = list(repository_parts)
    if mode:
        storage_parts.append(mode)
    storage_value = " · ".join(storage_parts)

    fields: list[dict[str, Any]] = []
    for field in (
        _field("⏱️ Duration", _code(normalized.get("duration")), inline=True),
        _field("📦 Transfer Size", _code(normalized.get("transfer_size")), inline=True),
        _field("🚀 Transfer Speed", _code(normalized.get("transfer_speed")), inline=True),
        _field("📁 Storage", _code(storage_value)),
    ):
        if field is not None:
            fields.append(field)

    details = normalized.get("vm_details")
    if not isinstance(details, dict):
        details = {}

    def vm_size(vm_name: str) -> str:
        item = details.get(vm_name)
        if not isinstance(item, dict):
            item = {}
        return str(item.get("size") or "").strip()

    def vm_section(name: str, values: object, *, include_error: bool = False):
        if not isinstance(values, list) or not values:
            return None

        vm_names = [
            str(raw_name or "").strip()
            for raw_name in values
            if str(raw_name or "").strip()
        ]
        if not vm_names:
            return None

        lines = []
        shown = vm_names[:10]
        for vm_name in shown:
            size = vm_size(vm_name)
            line = f"**{vm_name}**"
            if size:
                line += f" · {_code(size)}"
            lines.append(line)

            if include_error:
                item = details.get(vm_name)
                if isinstance(item, dict) and str(item.get("error") or "").strip():
                    lines.append(f"**Error:** {_code(item.get('error'))}")

        remaining = len(vm_names) - len(shown)
        if remaining > 0:
            lines.append(f"… and {remaining} more")

        return _field(f"{name} · {len(vm_names)}", "\n".join(lines))

    for field in (
        vm_section("✅ Successful VMs", normalized.get("successful_vms")),
        vm_section("❌ Failed VMs", normalized.get("failed_vms"), include_error=True),
        vm_section("⏭️ Skipped VMs", normalized.get("skipped_vms"), include_error=True),
        _field("🆔 Job ID", _code(normalized.get("job_id"))),
    ):
        if field is not None:
            fields.append(field)

    title = f"{icon} {lifecycle} — {job_name}"[:256]
    return _finish(
        {"title": title, "description": description, "color": color, "fields": fields},
        payload,
    )

_ZABBIX_RECOGNIZED = {
    "problem name", "host", "severity", "operational data", "original problem id",
    "trigger expression", "event tags", "runbook", "problem duration", "update action",
    "update message", "current problem status", "acknowledged", "event time",
}


def _render_zabbix(notification, payload, normalized, metadata):
    source_fields = metadata.get("fields")
    if not isinstance(source_fields, dict):
        source_fields = {}
    event_type = str(metadata.get("event_type") or "problem").strip().casefold()
    if event_type not in {"problem", "update", "recovery"}:
        event_type = "recovery" if _normal_words(normalized.get("status")) in {"success", "resolved", "recovered"} else "problem"
    problem = str(metadata.get("problem_name") or normalized.get("title") or normalized.get("subject") or "Zabbix event").strip()
    host = str(metadata.get("host") or "Unknown host").strip()
    severity = str(metadata.get("severity") or "Not classified").strip()

    if event_type == "recovery":
        title = f"✅ {problem} — Resolved"[:256]
        description = f"{severity} severity problem resolved on {host}."[:4096]
        color = _GREEN
        problem_name = "✅ Problem"
    elif event_type == "update":
        title = f"🔄 {problem} — Updated"[:256]
        description = f"{severity} severity problem remains active; Zabbix reported an update for {host}."[:4096]
        color = _YELLOW
        problem_name = "🔄 Problem"
    else:
        sev_icon = {
            "disaster": "🚨", "high": "🚨", "average": "⚠️",
            "warning": "⚠️", "information": "ℹ️", "not classified": "🔔",
        }.get(_normal_words(severity), "🚨")
        title = f"{sev_icon} {problem}"[:256]
        description = f"{severity} severity problem detected on {host}."[:4096]
        color = _RED
        problem_name = "🚨 Problem"

    fields: list[dict[str, Any]] = []
    def append(field):
        if field is not None:
            fields.append(field)

    append(_rows_field(problem_name, [("Name", problem), ("Host", host), ("Severity", severity)]))
    append(_field("📈 Operational Data", _code(metadata.get("operational_data") or source_fields.get("operational data"))))
    append(_field("🧪 Trigger", _code(source_fields.get("trigger expression"))))
    append(_field("🏷️ Event Tags", _code(source_fields.get("event tags"))))
    append(_field("🆔 Problem ID", _code(metadata.get("problem_id") or source_fields.get("original problem id"))))
    if event_type == "update":
        append(_rows_field("🔄 Update", [
            ("Action", metadata.get("update_action") or source_fields.get("update action")),
            ("Message", metadata.get("update_message") or source_fields.get("update message")),
            ("Current Status", source_fields.get("current problem status")),
            ("Acknowledged", source_fields.get("acknowledged")),
        ]))
    time_label = {"problem": "Started", "update": "Updated", "recovery": "Resolved"}[event_type]
    append(_rows_field("⏱️ Timing", [
        (time_label, metadata.get("event_time") or normalized.get("end_time") or normalized.get("start_time")),
        ("Duration", normalized.get("duration") or source_fields.get("problem duration")),
    ]))
    append(_field("📘 Runbook", _code(source_fields.get("runbook"))))
    append(_rows_field("📧 Email", [("From", normalized.get("sender")), ("To", _metadata_value(metadata, "to", "recipient"))]))
    append(_field("✉️ Subject", _code(normalized.get("subject"))))

    for raw_label, raw_value in source_fields.items():
        label = _normal_words(raw_label)
        if not label or label in _ZABBIX_RECOGNIZED or not str(raw_value or "").strip():
            continue
        append(_field(f"📎 {str(raw_label).strip().title()}"[:256], _code(raw_value)))

    return _finish(
        {"title": title, "description": description, "color": color, "fields": fields},
        payload,
        preserve=("thumbnail", "url", "timestamp"),
    )


_GRAFANA_RECOGNIZED = {
    "alert name", "alert rule", "rule name", "state", "severity", "alert count",
    "folder", "organization", "dashboard", "panel", "datasource", "labels", "values",
    "starts at", "ends at", "event time", "summary", "description", "message",
}


def _render_grafana(notification, payload, normalized, metadata):
    source_fields = metadata.get("source_fields")
    if not isinstance(source_fields, dict):
        source_fields = {}
    state = str(metadata.get("state") or "").strip()
    severity = str(metadata.get("severity") or "").strip()
    status = str(normalized.get("status") or "").strip()
    alert_name = str(metadata.get("alert_name") or normalized.get("title") or normalized.get("subject") or "Grafana alert").strip()
    try:
        count = max(1, int(metadata.get("alert_count") or 1))
    except (TypeError, ValueError):
        count = 1

    state_words = _normal_words(state)
    severity_words = _normal_words(severity)
    if _normal_words(status) == "success" or state_words in {"resolved", "normal", "ok"}:
        color, icon = _GREEN, "✅"
    elif _normal_words(status) == "warning" or state_words in {"pending", "no data"} or severity_words == "warning":
        color, icon = _ORANGE, "⚠️"
    elif _normal_words(status) == "failure" or state_words in {"firing", "error"} or severity_words in {"critical", "error"}:
        color, icon = _RED, "🚨"
    else:
        color, icon = _BLUE, "ℹ️"

    grouped = f" ({count} alerts)" if count > 1 else ""
    suffix = f" — {state}" if state else ""
    title = f"{icon} {alert_name}{grouped}{suffix}"[:256]
    description = str(metadata.get("summary") or metadata.get("message") or normalized.get("body") or normalized.get("subject") or "Grafana notification").strip()[:4096]

    fields: list[dict[str, Any]] = []
    def append(field):
        if field is not None:
            fields.append(field)

    append(_rows_field("🚨 Alert" if color == _RED else "📣 Alert", [
        ("Name", alert_name), ("State", state), ("Severity", severity), ("Count", count if count > 1 else ""),
    ]))
    append(_rows_field("📂 Rule", [
        ("Rule", metadata.get("alert_rule") or metadata.get("rule_name")),
        ("Folder", metadata.get("folder")),
        ("Organization", metadata.get("organization")),
    ]))
    append(_rows_field("📊 Location", [("Dashboard", metadata.get("dashboard")), ("Panel", metadata.get("panel"))]))
    append(_field("🗄️ Datasource", _code(metadata.get("datasource"))))
    append(_field("🏷️ Labels", _code(metadata.get("labels"))))
    if count == 1:
        append(_field("📈 Values", _code(metadata.get("values"))))
    append(_rows_field("⏱️ Timing", [
        ("Started", metadata.get("starts_at") or normalized.get("start_time")),
        ("Resolved", metadata.get("ends_at") or normalized.get("end_time")),
        ("Event Time", metadata.get("event_time")),
    ]))
    append(_rows_field("📝 Details", [
        ("Summary", metadata.get("summary")),
        ("Description", metadata.get("description")),
        ("Message", metadata.get("message")),
    ]))
    if _normal_words(metadata.get("_input_type")) != "http":
        append(_rows_field("📧 Email", [("From", normalized.get("sender")), ("To", _metadata_value(metadata, "to", "recipient")), ("Subject", normalized.get("subject"))]))

    for raw_label, raw_value in source_fields.items():
        label = _normal_words(raw_label)
        if not label or label in _GRAFANA_RECOGNIZED or not str(raw_value or "").strip():
            continue
        append(_field(f"📎 {str(raw_label).strip().title()}"[:256], _code(raw_value)))

    return _finish(
        {"title": title, "description": description, "color": color, "fields": fields},
        payload,
    )


def _render_portainer(notification, payload, normalized, metadata):
    status = str(normalized.get("status") or "").strip()
    state = str(metadata.get("state") or status).strip()
    severity = str(metadata.get("severity") or status).strip()
    title_text = str(normalized.get("title") or metadata.get("summary") or metadata.get("alert_name") or "Portainer alert").strip()
    description = str(metadata.get("description") or normalized.get("body") or metadata.get("summary") or title_text).strip()[:4096]
    color, icon, lifecycle = _lifecycle(status, severity, state=state)
    state_label = str(state or "").replace("_", " ").strip().title()
    title = f"{icon} {title_text}{f' — {state_label}' if state_label else ''}"[:256]
    try:
        count = max(1, int(metadata.get("alert_count") or 1))
    except (TypeError, ValueError):
        count = 1
    try:
        truncated = max(0, int(metadata.get("truncated_alerts") or 0))
    except (TypeError, ValueError):
        truncated = 0

    fields: list[dict[str, Any]] = []
    def append(field):
        if field is not None:
            fields.append(field)

    append(_rows_field(f"{icon} Alert", [
        ("Rule", metadata.get("alert_name")),
        ("State", state),
        ("Severity", severity),
        ("Truncated", truncated if truncated else ""),
    ]))
    instance = str(metadata.get("instance") or "").strip()
    host = str(metadata.get("host") or "").strip()
    if _normal_words(host) == _normal_words(instance):
        host = ""
    append(_rows_field("📦 Portainer", [
        ("Instance", instance), ("Host", host), ("Area", metadata.get("alert_source")),
    ]))
    append(_rows_field("🔐 Authentication", [
        ("Method", metadata.get("authentication_method")), ("User", metadata.get("username")),
    ]))
    metric = str(metadata.get("metric") or "").strip()
    current_label = "Failures" if "authentication failures" in _normal_words(metric) else "Current"
    append(_rows_field("📈 Signal", [
        ("Metric", metric), (current_label, metadata.get("current_value")),
        ("Threshold", metadata.get("threshold")), ("Window", metadata.get("window")),
    ]))
    if count > 1:
        rows: list[tuple[str, object]] = [("Count", f"{count} alerts")]
        members = metadata.get("group_members")
        if isinstance(members, list):
            for index, member in enumerate(members[:8], start=1):
                if isinstance(member, dict):
                    detail = str(member.get("title") or "Portainer alert").strip()
                    qualifiers = [
                        str(member.get(key) or "").strip()
                        for key in ("instance", "username", "severity")
                        if str(member.get(key) or "").strip()
                    ]
                    if qualifiers:
                        detail += " — " + " · ".join(qualifiers)
                    rows.append((f"Alert {index}", detail))
        append(_rows_field("👥 Grouped Alerts", rows))
    append(_rows_field("⏱️ Timing", [
        ("Started", normalized.get("start_time")), ("Resolved", normalized.get("end_time")),
    ]))

    return _finish(
        {"title": title, "description": description, "color": color, "fields": fields},
        payload,
    )


def _usage_percent(metadata: dict[str, Any]) -> str:
    for key in ("used_percent", "usage_percent", "storage_usage", "usage"):
        value = metadata.get(key)
        if value not in (None, ""):
            text = str(value).strip()
            return text if "%" in text else f"{text}%"
    return ""


def _render_proxmox(notification, payload, normalized, metadata):
    status = str(normalized.get("status") or "").strip()
    state = str(metadata.get("state") or status).strip()
    severity = str(metadata.get("severity") or status).strip()
    category = str(normalized.get("category") or metadata.get("category") or "event").strip()
    title_text = str(normalized.get("title") or normalized.get("subject") or "Proxmox VE notification").strip()
    description = str(normalized.get("body") or title_text).strip()[:4096]
    color, icon, lifecycle = _lifecycle(status, severity, state=state)
    fields: list[dict[str, Any]] = []

    def append(field):
        if field is not None:
            fields.append(field)

    append(_rows_field(f"{icon} Alert", [
        ("Status", lifecycle),
        ("State", state if _normal_words(state) != _normal_words(lifecycle) else ""),
        ("Severity", severity),
        ("Category", category),
    ]))
    append(_rows_field("🟧 Proxmox VE", [
        ("Node", metadata.get("node") or metadata.get("host")),
        ("Guest", metadata.get("guest")),
        ("VMID", metadata.get("vmid")),
    ]))
    category_words = _normal_words(category)
    if category_words == "storage":
        append(_rows_field("💾 Storage", [
            ("Storage", metadata.get("storage") or normalized.get("repository")),
            ("Usage", _usage_percent(metadata)),
            ("Guest", metadata.get("guest")),
            ("VMID", metadata.get("vmid")),
        ]))
    elif category_words == "backup":
        append(_rows_field("💾 Backup", [
            ("Storage", metadata.get("storage") or normalized.get("repository")),
            ("Job", metadata.get("job_id") or normalized.get("job_id")),
            ("Guests", normalized.get("vm_total")),
            ("Guests OK", normalized.get("vm_success")),
            ("Guests Failed", normalized.get("vm_failed")),
        ]))
    else:
        label = {
            "replication": "🔄 Replication",
            "cluster": "🧩 Cluster",
            "availability": "🌐 Availability",
            "security": "🔐 Security",
            "guest": "🖥️ Guest",
            "system": "⚙️ System",
        }.get(category_words, "📋 Event Details")
        append(_rows_field(label, [
            ("Guest", metadata.get("guest")),
            ("VMID", metadata.get("vmid")),
            ("Job", metadata.get("job_id") or normalized.get("job_id")),
            ("Storage", metadata.get("storage") or normalized.get("repository")),
        ]))
    append(_list_field("❌ Failed Guests", normalized.get("failed_vms")))
    append(_list_field("🧯 Error Details", normalized.get("errors")))
    append(_list_field("✅ Successful Guests", normalized.get("successful_vms")))
    append(_rows_field("⏱️ Timing", [
        ("Started", normalized.get("start_time")),
        ("Finished", normalized.get("end_time")),
        ("Duration", normalized.get("duration")),
    ]))
    return _finish(
        {"title": f"{icon} {title_text} — {lifecycle}"[:256], "description": description, "color": color, "fields": fields},
        payload,
    )


def _source_fields(metadata: dict[str, Any]) -> dict[str, Any]:
    value = metadata.get("source_fields")
    return value if isinstance(value, dict) else {}


def _source_value(source_fields: dict[str, Any], *names: str) -> object:
    for name in names:
        value = source_fields.get(name)
        if value not in (None, ""):
            return value
    return ""


def _render_qnap(notification, payload, normalized, metadata):
    source_fields = _source_fields(metadata)
    status = str(normalized.get("status") or "").strip()
    severity = str(metadata.get("severity") or status).strip()
    category = _normal_words(normalized.get("category") or metadata.get("category") or "generic") or "generic"
    event_type = str(metadata.get("event_type") or _source_value(source_fields, "event type") or "").strip()
    nas_name = str(metadata.get("nas_name") or _source_value(source_fields, "nas name") or "").strip()
    application = str(metadata.get("application") or _source_value(source_fields, "app name", "application") or "").strip()
    title_text = str(normalized.get("title") or normalized.get("subject") or event_type or "QNAP notification").strip()
    description = str(metadata.get("message") or normalized.get("body") or title_text).strip()[:4096]
    color, icon, lifecycle = _lifecycle(status, severity)
    fields: list[dict[str, Any]] = []
    def append(field):
        if field is not None:
            fields.append(field)

    append(_rows_field(f"{icon} Alert", [("Status", lifecycle), ("Severity", severity), ("Category", category)]))
    append(_rows_field("🗄️ QNAP NAS", [("NAS", nas_name), ("Application", application), ("Event", event_type)]))
    if category == "security":
        append(_rows_field("🔐 Security", [
            ("Account", _source_value(source_fields, "account", "user", "username")),
            ("Connection", _source_value(source_fields, "connection type", "connection")),
            ("Login Result", _source_value(source_fields, "login result", "result")),
        ]))
    elif category == "backup":
        append(_rows_field("💾 Backup", [
            ("Job", _source_value(source_fields, "job name", "job")),
            ("Type", _source_value(source_fields, "job type", "type")),
            ("Source", _source_value(source_fields, "source folder", "source")),
            ("Destination", _source_value(source_fields, "destination", "target")),
            ("Job Status", _source_value(source_fields, "job status", "status")),
        ]))
    elif category == "storage":
        append(_rows_field("💽 Storage", [
            ("Disk", _source_value(source_fields, "disk", "drive")),
            ("Disk Health", _source_value(source_fields, "disk health", "drive health")),
            ("SMART Test", _source_value(source_fields, "smart test", "s.m.a.r.t. test")),
            ("SMART Result", _source_value(source_fields, "smart result", "s.m.a.r.t. result")),
            ("Storage Pool", _source_value(source_fields, "storage pool", "pool")),
            ("RAID Group", _source_value(source_fields, "raid group")),
            ("RAID Type", _source_value(source_fields, "raid type")),
            ("Pool Status", _source_value(source_fields, "pool status")),
        ]))
    elif category == "system":
        append(_rows_field("⚙️ System", [
            ("Update Type", _source_value(source_fields, "update type")),
            ("Current Version", _source_value(source_fields, "current version")),
            ("Available Version", _source_value(source_fields, "available version")),
        ]))
    elif category == "power":
        append(_rows_field("🔋 Power", [
            ("UPS Status", _source_value(source_fields, "ups status")),
            ("Power Event", _source_value(source_fields, "power event")),
            ("Estimated Runtime", _source_value(source_fields, "estimated runtime")),
        ]))
    append(_rows_field("⏱️ Timing", [
        ("Started", normalized.get("start_time") or metadata.get("event_time")),
        ("Finished", normalized.get("end_time")),
    ]))
    if lifecycle in {"Resolved", "Success"} and "recover" in _normal_words(event_type):
        display_title = f"{title_text} — Resolved"
    else:
        display_title = f"{title_text} — {lifecycle}"
    return _finish(
        {"title": f"{icon} {display_title}"[:256], "description": description, "color": color, "fields": fields},
        payload,
    )


def _render_synology(notification, payload, normalized, metadata):
    status = str(normalized.get("status") or "").strip()
    state = str(metadata.get("state") or status).strip()
    severity = str(metadata.get("severity") or status).strip()
    category = str(normalized.get("category") or metadata.get("category") or "event").strip()
    title_text = str(normalized.get("title") or normalized.get("subject") or "Synology DSM notification").strip()
    description = str(normalized.get("body") or title_text).strip()[:4096]
    nas_name = str(_metadata_value(metadata, "nas_name", "hostname", "host") or "").strip()
    model = str(_metadata_value(metadata, "model", "model name") or "").strip()
    color, icon, lifecycle = _lifecycle(status, severity, state=state)
    fields: list[dict[str, Any]] = []
    def append(field):
        if field is not None:
            fields.append(field)

    append(_rows_field(f"{icon} Alert", [("Status", lifecycle), ("Severity", severity), ("Category", category)]))
    append(_rows_field("🗄️ Synology NAS", [("NAS", nas_name), ("Model", model)]))
    cat = _normal_words(category)
    if cat == "backup":
        append(_rows_field("💾 Backup", [
            ("Task", _metadata_value(metadata, "task", "job", "backup task")),
            ("Storage", _metadata_value(metadata, "storage", "destination", "target")),
            ("Package", _metadata_value(metadata, "package", "application")),
        ]))
    elif cat == "storage":
        append(_rows_field("💽 Storage", [
            ("Storage Pool", _metadata_value(metadata, "storage_pool", "storage pool", "pool")),
            ("Volume", _metadata_value(metadata, "volume")),
            ("Storage", _metadata_value(metadata, "storage")),
        ]))
    elif cat == "disk":
        append(_rows_field("💿 Disk", [
            ("Disk", _metadata_value(metadata, "disk", "drive")),
            ("Storage Pool", _metadata_value(metadata, "storage_pool", "storage pool", "pool")),
            ("Volume", _metadata_value(metadata, "volume")),
        ]))
    elif cat == "security":
        append(_rows_field("🔐 Security", [
            ("User", _metadata_value(metadata, "username", "user", "account")),
            ("Source IP", _metadata_value(metadata, "source_ip", "source ip", "ip_address", "ip address")),
        ]))
    elif cat == "power":
        append(_rows_field("🔋 Power", [("Event", metadata.get("event_type")), ("State", metadata.get("state"))]))
    elif cat == "package":
        append(_rows_field("📦 Package", [("Package", _metadata_value(metadata, "package", "application"))]))
    else:
        label = {
            "availability": "🌐 Availability",
            "network": "🌐 Network",
            "replication": "🔄 Replication",
            "system": "⚙️ System",
        }.get(cat, "📋 Event Details")
        append(_rows_field(label, [
            ("Event", metadata.get("event_type")),
            ("Storage Pool", _metadata_value(metadata, "storage_pool", "storage pool")),
            ("Volume", _metadata_value(metadata, "volume")),
            ("Package", _metadata_value(metadata, "package", "application")),
        ]))
    append(_rows_field("⏱️ Timing", [
        ("Started", normalized.get("start_time") or metadata.get("event_time")),
        ("Finished", normalized.get("end_time")),
    ]))
    return _finish(
        {"title": f"{icon} {title_text} — {lifecycle}"[:256], "description": description, "color": color, "fields": fields},
        payload,
    )


def _truenas_alerts(metadata: dict[str, Any]) -> list[dict[str, Any]]:
    alerts = metadata.get("alerts")
    return [item for item in alerts if isinstance(item, dict)] if isinstance(alerts, list) else []


def _truenas_detail(category: str, title: str, message: str, lifecycle: str):
    words = f"{title} {message}".casefold()
    def match(pattern):
        found = re.search(pattern, message, flags=re.IGNORECASE)
        return found.group(1).strip(" .,:;") if found else ""
    if category == "power" or "ups" in words:
        state = "Recovered" if lifecycle == "Resolved" else "On battery" if "on battery" in message.casefold() else lifecycle
        return _rows_field("🔋 Power", [
            ("UPS", match(r"\bUPS\s+([A-Za-z0-9_.:-]+)")),
            ("Status", state),
            ("Cause", "Utility power loss" if "utility power loss" in message.casefold() else ""),
        ])
    if "replication" in words:
        return _rows_field("🔄 Replication", [
            ("Task", match(r"\bReplication task\s+([^\s:]+)")),
            ("Destination", match(r"\bdestination\s+([^\s]+)")),
            ("Status", lifecycle),
        ])
    if "scrub" in words:
        return _rows_field("🧹 Scrub", [
            ("Pool", match(r"\bpool\s+([A-Za-z0-9_.:-]+)")),
            ("Result", lifecycle),
            ("Error", match(r"\bfailed with\s+(?:a|an)\s+(.+)$")),
        ])
    if "smart" in words or "s.m.a.r.t" in words:
        return _rows_field("💿 Disk", [
            ("Device", match(r"\bDevice\s+([A-Za-z0-9_.:-]+)")),
            ("SMART Status", "Warning" if lifecycle == "Warning" else lifecycle),
        ])
    if category == "storage" or "pool" in words:
        detail = message.split(":", 1)[1].strip() if ":" in message else ""
        return _rows_field("💽 Storage", [
            ("Pool", match(r"\bPool\s+([A-Za-z0-9_.:-]+)")),
            ("Pool Status", match(r"\bstate is\s+([^:.]+)") or lifecycle),
            ("Condition", detail),
        ])
    if category == "backup":
        return _rows_field("💾 Backup", [("Status", lifecycle)])
    return None


def _render_truenas(notification, payload, normalized, metadata):
    alerts = _truenas_alerts(metadata)
    try:
        alert_count = int(metadata.get("alert_count") or len(alerts) or 1)
    except (TypeError, ValueError):
        alert_count = len(alerts) or 1
    status = str(normalized.get("status") or "").strip()
    severity = str(metadata.get("severity") or status).strip()
    category = str(normalized.get("category") or "generic").strip()
    recovery = bool(metadata.get("recovery")) and alert_count == 1 and _normal_words(status) == "success"
    title_text = " ".join(str(normalized.get("title") or "TrueNAS alert").split()).strip()
    title_text = title_text[:1].upper() + title_text[1:] if title_text else "TrueNAS alert"
    message = str(metadata.get("message") or normalized.get("body") or title_text).strip()
    host = str(_metadata_value(metadata, "host", "hostname") or "").strip()
    color, icon, lifecycle = _lifecycle(status, severity)
    if recovery:
        color, icon, lifecycle = _GREEN, "✅", "Resolved"
    is_grouped = alert_count > 1
    is_test = _normal_words(metadata.get("event_type")) == "test" or _normal_words(title_text) == "truenas test alert"
    fields: list[dict[str, Any]] = []
    def append(field):
        if field is not None:
            fields.append(field)

    if is_grouped:
        categories = ", ".join(str(value) for value in (metadata.get("categories") or []) if str(value).strip())
        append(_rows_field(f"{icon} Alert", [
            ("Status", lifecycle), ("Severity", severity), ("Alerts", alert_count), ("Categories", categories or category),
        ]))
    else:
        append(_rows_field(f"{icon} Alert", [("Status", lifecycle), ("Severity", severity), ("Category", category)]))
    append(_rows_field("🗄️ TrueNAS System", [("Host", host)]))
    if is_grouped:
        blocks = []
        for alert in alerts:
            _, aicon, alabel = _lifecycle(alert.get("status"), alert.get("severity"))
            atitle = " ".join(str(alert.get("title") or "TrueNAS alert").split()).strip()
            amessage = " ".join(str(alert.get("message") or "").split()).strip()
            if len(amessage) > 180:
                amessage = amessage[:179].rstrip() + "…"
            block = f"{aicon} {atitle} — {alabel}"
            if amessage:
                block += "\n" + amessage
            blocks.append(block)
        append(_field("📚 Grouped Alerts", "\n\n".join(blocks)))
    elif is_test:
        append(_rows_field("🧪 Notification Test", [("Result", "Received")]))
    else:
        append(_truenas_detail(category, title_text, message, lifecycle))
    append(_rows_field("⏱️ Timing", [
        ("Started", normalized.get("start_time") or metadata.get("event_time")),
        ("Finished", normalized.get("end_time")),
    ]))

    if is_grouped:
        description = f"{alert_count} TrueNAS alerts were reported in one notification."
    elif is_test:
        description = "TrueNAS test notification received successfully."
    elif lifecycle == "Resolved" and category == "power":
        description = "The TrueNAS UPS power alert was cleared."
    else:
        description = str(normalized.get("body") or message or title_text).strip()[:4096]
    return _finish(
        {"title": f"{icon} {title_text} — {lifecycle}"[:256], "description": description, "color": color, "fields": fields},
        payload,
    )


def _render_unifi_network(notification, payload, normalized, metadata):
    status = str(normalized.get("status") or "").strip()
    severity = str(metadata.get("severity") or status).strip()
    category = str(normalized.get("category") or metadata.get("category") or "network").strip()
    title_text = str(normalized.get("title") or normalized.get("subject") or "UniFi Network notification").strip()
    description = str(metadata.get("message") or normalized.get("body") or title_text).strip()[:4096]
    color, icon, lifecycle = _lifecycle(status, severity)
    fields: list[dict[str, Any]] = []
    def append(field):
        if field is not None:
            fields.append(field)

    append(_rows_field(f"{icon} Alert", [("Status", lifecycle), ("Severity", severity), ("Category", category)]))
    append(_rows_field("🎛️ UniFi Controller", [("Controller", _metadata_value(metadata, "controller", "host"))]))
    client = str(_metadata_value(metadata, "client_display_name", "client_alias", "client_hostname") or "").strip()
    client_hostname = str(_metadata_value(metadata, "client_hostname") or "").strip()
    append(_rows_field("💻 Client", [
        ("Client", client),
        ("Hostname", client_hostname if client_hostname.casefold() != client.casefold() else ""),
        ("IP", _metadata_value(metadata, "client_ip")),
        ("MAC", _metadata_value(metadata, "client_mac")),
    ]))
    append(_rows_field("📶 Network / Wi-Fi", [
        ("Network", _metadata_value(metadata, "network_name")),
        ("VLAN", _metadata_value(metadata, "network_vlan")),
        ("Wi-Fi", _metadata_value(metadata, "wifi_name")),
        ("Band", _metadata_value(metadata, "wifi_band")),
        ("Channel", _metadata_value(metadata, "wifi_channel")),
        ("RSSI", _metadata_value(metadata, "wifi_rssi")),
    ]))
    append(_rows_field("📍 Last Access Point", [
        ("Access Point", _metadata_value(metadata, "last_device_name")),
        ("Model", _metadata_value(metadata, "last_device_model")),
        ("IP", _metadata_value(metadata, "last_device_ip")),
        ("MAC", _metadata_value(metadata, "last_device_mac")),
    ]))
    append(_rows_field("⏱️ Timing", [
        ("Started", normalized.get("start_time") or _metadata_value(metadata, "event_time")),
        ("Duration", normalized.get("duration") or _metadata_value(metadata, "duration")),
    ]))
    return _finish(
        {"title": f"{icon} {title_text} — {lifecycle}"[:256], "description": description, "color": color, "fields": fields},
        payload,
    )


def _render_unifi_protect(notification, payload, normalized, metadata):
    from formatters.unifi import (
        format_protect_event_time,
        protect_condition_display,
        protect_device_display,
    )
    status = str(normalized.get("status") or "").strip()
    severity = str(metadata.get("severity") or status).strip()
    category = str(normalized.get("category") or metadata.get("category") or "security").strip()
    title_text = str(normalized.get("title") or normalized.get("subject") or "UniFi Protect notification").strip()
    description = str(normalized.get("body") or title_text).strip()[:4096]
    trigger_key = str(_metadata_value(metadata, "trigger_key") or "").strip()
    trigger_label = str(_metadata_value(metadata, "trigger_label") or trigger_key or title_text).strip()
    trigger_device = protect_device_display(
        _metadata_value(metadata, "trigger_device")
    )
    alarm_name = str(_metadata_value(metadata, "alarm_name") or "").strip()
    condition = protect_condition_display(
        str(_metadata_value(metadata, "condition_source") or ""),
        str(_metadata_value(metadata, "condition_operator") or ""),
        trigger_key,
        omit_redundant=bool(alarm_name),
    )
    started = format_protect_event_time(_metadata_value(metadata, "event_time", "trigger_timestamp") or normalized.get("start_time"))
    received = format_protect_event_time(_metadata_value(metadata, "outer_timestamp"))
    if received == started:
        received = ""

    color, icon, lifecycle = _lifecycle(status, severity)
    fields: list[dict[str, Any]] = []
    for field in (
        _rows_field(f"{icon} Alert", [("Status", lifecycle), ("Severity", severity), ("Category", category)]),
        _rows_field("🎯 Trigger", [
            ("Type", trigger_label),
            ("Device", trigger_device),
            ("Triggers", _metadata_value(metadata, "trigger_count")),
        ]),
        _rows_field("🚨 Alarm Rule", [
            ("Rule", alarm_name),
            ("Configured Sources", _metadata_value(metadata, "configured_source_count")),
        ]),
        _rows_field("🔎 Condition", [("Condition", condition)]),
        _rows_field("⏱️ Timing", [("Event", started), ("Webhook", received)]),
    ):
        if field is not None:
            fields.append(field)

    event_link = str(_metadata_value(metadata, "event_link") or "").strip()
    embed = {
        "title": f"{icon} {title_text} — {lifecycle}"[:256],
        "description": description,
        "color": color,
        "fields": fields,
    }
    if event_link:
        embed["url"] = event_link
    return _finish(embed, payload)


def _render_unifi_drive(notification, payload, normalized, metadata):
    status = str(normalized.get("status") or "").strip()
    severity = str(_metadata_value(metadata, "severity") or status).strip()
    category = str(normalized.get("category") or _metadata_value(metadata, "category") or "general").strip()
    raw_title = str(normalized.get("title") or normalized.get("subject") or "UniFi Drive alarm").strip()
    title_text = "Drive settings alarm" if _normal_words(raw_title) == "settings" else raw_title
    body = str(normalized.get("body") or title_text).strip()[:4096]
    color, icon, lifecycle = _lifecycle(status, severity)
    description = f"{raw_title} successfully." if lifecycle == "Success" and "completed" in _normal_words(raw_title) else body
    fields: list[dict[str, Any]] = []
    for field in (
        _rows_field(f"{icon} Alert", [("Status", lifecycle), ("Severity", severity), ("Category", category)]),
        _rows_field("🗄️ UniFi Drive", [
            ("Provider", _metadata_value(metadata, "provider") or "UniFi Drive"),
            ("System", _metadata_value(metadata, "system", "host")),
            ("Backup Task", _metadata_value(metadata, "backup_task")),
        ]),
        _rows_field("🔔 Alarm", [
            ("Name", _metadata_value(metadata, "event_title") or raw_title),
            ("Alarm ID", _metadata_value(metadata, "alarm_id")),
            ("State", _metadata_value(metadata, "event_state") or status),
        ]),
        _rows_field("⏱️ Timing", [
            ("Started", normalized.get("start_time") or _metadata_value(metadata, "event_time")),
        ]),
    ):
        if field is not None:
            fields.append(field)
    return _finish(
        {"title": f"{icon} {title_text} — {lifecycle}"[:256], "description": description, "color": color, "fields": fields},
        payload,
        preserve=("thumbnail",),
    )


def _render_hardware(notification, payload, normalized, metadata, *, source: str, label: str, default_provider: str):
    status = str(normalized.get("status") or "").strip()
    severity = str(_metadata_value(metadata, "severity") or status).strip()
    category = str(normalized.get("category") or "hardware").strip()
    title_text = str(normalized.get("title") or normalized.get("subject") or f"{label} hardware event").strip()
    body = str(normalized.get("body") or title_text).strip()[:4096]
    color, icon, lifecycle = _lifecycle(status, severity)
    fields: list[dict[str, Any]] = []
    for field in (
        _rows_field(f"{icon} Alert", [("Status", lifecycle), ("Severity", severity), ("Category", category)]),
        _rows_field(f"🖥️ {label}", [
            ("System", _metadata_value(metadata, "system")),
            ("Provider", _metadata_value(metadata, "provider", "vendor") or default_provider),
            ("Source IP", _metadata_value(metadata, "source_ip")),
        ]),
        _rows_field("🔎 Hardware Event", [
            ("Registry", _metadata_value(metadata, "registry")),
            ("Message ID", _metadata_value(metadata, "message_id") or normalized.get("subject")),
            ("Event ID", _metadata_value(metadata, "event_id")),
        ]),
        _rows_field("📍 Hardware Origin", [
            ("Origin", _metadata_value(metadata, "origin")),
            ("Sensor", _metadata_value(metadata, "sensor")),
        ]),
        _rows_field("⏱️ Timing", [("Started", normalized.get("start_time"))]),
    ):
        if field is not None:
            fields.append(field)
    return _finish(
        {"title": f"{icon} {title_text} — {lifecycle}"[:256], "description": body, "color": color, "fields": fields},
        payload,
        preserve=("thumbnail",),
    )


def _tags_text(value: object) -> str:
    if isinstance(value, (list, tuple, set)):
        return ", ".join(str(item).strip() for item in value if str(item or "").strip())
    return str(value or "").strip()


def _render_home_assistant(notification, payload, normalized, metadata):
    status = str(normalized.get("status") or "").strip()
    severity = str(_metadata_value(metadata, "severity") or status).strip()
    category = str(normalized.get("category") or "automation").strip()
    title_text = str(normalized.get("title") or normalized.get("subject") or "Home Assistant event").strip()
    body = str(normalized.get("body") or title_text).strip()[:4096]
    retry_seconds = str(_metadata_value(metadata, "retry_seconds") or "").strip()
    color, icon, lifecycle = _lifecycle(status, severity)
    fields: list[dict[str, Any]] = []
    for field in (
        _rows_field(f"{icon} Alert", [("Status", lifecycle), ("Severity", severity), ("Category", category)]),
        _rows_field("🏠 Home Assistant", [
            ("Provider", _metadata_value(metadata, "provider") or "Home Assistant"),
            ("Area", _metadata_value(metadata, "area")),
            ("Service", _metadata_value(metadata, "service")),
            ("Event Type", _metadata_value(metadata, "event_type")),
        ]),
        _rows_field("🎯 Entity / Device", [
            ("Device", _metadata_value(metadata, "device")),
            ("Entity", _metadata_value(metadata, "entity_id")),
        ]),
        _rows_field("🔎 Source Details", [
            ("Component", _metadata_value(metadata, "component")),
            ("Endpoint", _metadata_value(metadata, "endpoint")),
            ("Error", _metadata_value(metadata, "error_code")),
            ("Retry", f"{retry_seconds} seconds" if retry_seconds else ""),
            ("Tags", _tags_text(_metadata_value(metadata, "tags"))),
        ]),
        _rows_field("⏱️ Timing", [("Started", normalized.get("start_time"))]),
    ):
        if field is not None:
            fields.append(field)
    return _finish(
        {"title": f"{icon} {title_text} — {lifecycle}"[:256], "description": body, "color": color, "fields": fields},
        payload,
        preserve=("thumbnail",),
    )


_RENDERERS = {
    "xo": _render_xo,
    "zabbix": _render_zabbix,
    "grafana": _render_grafana,
    "portainer": _render_portainer,
    "proxmox": _render_proxmox,
    "qnap": _render_qnap,
    "synology": _render_synology,
    "truenas": _render_truenas,
    "unifi_network": _render_unifi_network,
    "unifi_protect": _render_unifi_protect,
    "unifi_drive": _render_unifi_drive,
    "home_assistant": _render_home_assistant,
}


def render_classic_embed_v1(notification, payload):
    """Render the approved EE v1 classic geometry without any AI-owned content."""

    normalized = _normalized(notification)
    source = str(normalized.get("source") or "").strip().casefold()
    metadata = normalized.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}

    if source == "supermicro":
        return _render_hardware(
            notification, payload, normalized, metadata,
            source=source, label="Supermicro BMC", default_provider="Supermicro BMC",
        )
    if source == "hpe_ilo":
        return _render_hardware(
            notification, payload, normalized, metadata,
            source=source, label="HPE iLO", default_provider="HPE iLO",
        )
    if source == "dell_idrac":
        return _render_hardware(
            notification, payload, normalized, metadata,
            source=source, label="Dell iDRAC", default_provider="Dell iDRAC",
        )

    renderer = _RENDERERS.get(source)
    if renderer is None:
        return payload
    return renderer(notification, payload, normalized, metadata)


__all__ = ["CLASSIC_FOOTER", "render_classic_embed_v1"]
