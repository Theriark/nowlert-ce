"""Shared source-specific grouping for Modern image and native cards."""

from copy import deepcopy
import re

_MARKDOWN_MARKS = re.compile(r"[*_`~]")
_CLASSIFICATION_ROW = re.compile(r"^(severity|category)\s*:", re.IGNORECASE)

MODERN_SECTION_PROFILES = {
    "zabbix": (
        ("Problem", ("problem", "operational data"), False),
        ("Trigger", ("trigger", "problem id"), False),
        ("Response", ("runbook", "timing"), False),
    ),
    "grafana": (
        ("Rule & Location", ("rule", "location"), False),
        ("Data", ("datasource", "labels", "values"), False),
        ("Alert details", ("alerts", "evaluation error"), True),
        ("Timing & Links", ("timing", "links"), False),
    ),
    "prometheus": (
        ("Target", ("target",), False),
        ("Prometheus", ("prometheus", "labels"), False),
        ("Alert details", ("alerts",), True),
        ("Timing & Links", ("timing", "links"), False),
    ),
    "portainer": (
        ("Environment", ("portainer", "authentication"), False),
        ("Signal", ("signal", "grouped alerts"), False),
        ("Timing", ("timing",), False),
    ),
    "proxmox": (
        ("Proxmox VE", ("proxmox ve",), False),
        ("Job & Storage", ("backup", "storage"), False),
        ("Timing", ("timing",), False),
    ),
    "qnap": (
        ("QNAP NAS", ("qnap nas",), False),
        (
            "Event details",
            ("storage", "security", "system", "backup", "power"),
            False,
        ),
        ("Timing", ("timing",), False),
    ),
    "synology": (
        ("Synology NAS", ("synology nas",), False),
        ("Event details", ("storage", "backup", "power"), False),
        ("Timing", ("timing",), False),
    ),
    "truenas": (
        ("TrueNAS System", ("truenas system",), False),
        (
            "Event details",
            (
                "disk",
                "power",
                "storage",
                "notification test",
                "scrub",
                "replication",
            ),
            False,
        ),
        ("Grouped Alerts", ("grouped alerts",), True),
        ("Timing", ("timing",), False),
    ),
    "unifi_network": (
        (
            "Controller & Network",
            ("unifi controller", "network / wi-fi"),
            False,
        ),
        (
            "Client / Access Point",
            ("client", "last access point"),
            False,
        ),
        ("Timing", ("timing",), False),
    ),
    "unifi_protect": (
        ("Trigger", ("trigger",), False),
        ("Alarm Rule", ("alarm rule",), False),
        ("Timing", ("timing",), False),
    ),
    "unifi_drive": (
        ("Drive Event", ("alarm",), True),
        ("Timing", ("timing",), False),
    ),
    "supermicro": (
        ("System", ("supermicro bmc",), False),
        ("Hardware Event", ("hardware event",), False),
        ("Recommended Action", ("recommended action",), True),
        ("Timing", ("timing",), False),
    ),
    "hpe_ilo": (
        ("System", ("hpe ilo",), False),
        ("Hardware Event", ("hardware event",), False),
        ("Recommended Action", ("recommended action",), True),
        ("Timing", ("timing",), False),
    ),
    "dell_idrac": (
        ("System", ("dell idrac",), False),
        ("Hardware Event", ("hardware event",), False),
        ("Recommended Action", ("recommended action",), True),
        ("Timing", ("timing",), False),
    ),
    "home_assistant": (
        (
            "Home Assistant",
            ("home assistant", "entity / device"),
            False,
        ),
        ("Source Details", ("source details",), True),
        ("Timing", ("timing",), False),
    ),
    "redfish": (
        ("Source & Event", ("source", "hardware event"), False),
        ("Recommended Action", ("recommended action",), True),
        ("Timing", ("timing",), False),
    ),
    "generic": (
        ("Source & Context", ("source", "email", "context"), False),
        ("Timing", ("timing",), False),
    ),
    "nowlert": (
        ("Source & Context", ("source", "context"), False),
        ("Timing", ("timing",), False),
    ),
}


def _is_classification_only_alert(field):
    """True for a Classic "Alert" group that only repeats Severity/Category."""

    if not isinstance(field, dict):
        return False
    name = re.sub(r"^[^A-Za-z0-9]+", "", str(field.get("name") or ""))
    if name.strip().casefold() != "alert":
        return False
    rows = [
        _MARKDOWN_MARKS.sub("", line).strip()
        for line in str(field.get("value") or "").splitlines()
    ]
    rows = [row for row in rows if row]
    return bool(rows) and all(_CLASSIFICATION_ROW.match(row) for row in rows)


def without_repeated_classification(payload):
    """Copy a Classic payload minus an Alert group repeating the summary cells.

    Modern cards already show Severity and Category in the classification
    strip, so a Classic Alert group holding only those rows would render again
    as a redundant "Additional details" panel. Groups with any other row, and
    every other field, are kept; the Classic payload itself is not modified.
    """

    embeds = payload.get("embeds") if isinstance(payload, dict) else None
    if not isinstance(embeds, list) or not embeds or not isinstance(embeds[0], dict):
        return payload
    fields = embeds[0].get("fields")
    if not isinstance(fields, list) or not any(
        _is_classification_only_alert(field) for field in fields
    ):
        return payload
    result = deepcopy(payload)
    result["embeds"][0]["fields"] = [
        field for field in fields if not _is_classification_only_alert(field)
    ]
    return result
