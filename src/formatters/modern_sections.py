"""Shared source-specific grouping for Modern image and native cards."""

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
        ("Timing", ("timing",), False),
    ),
    "hpe_ilo": (
        ("System", ("hpe ilo",), False),
        ("Hardware Event", ("hardware event",), False),
        ("Timing", ("timing",), False),
    ),
    "dell_idrac": (
        ("System", ("dell idrac",), False),
        ("Hardware Event", ("hardware event",), False),
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

