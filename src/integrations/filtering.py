"""Destination-filter schemas derived from normalized integration events."""

from __future__ import annotations

from copy import deepcopy

from integrations.catalog import canonical_source, integration, integrations


# Only stable Notification attributes and normalized parser metadata are exposed.
# Raw parser payloads/source_fields are deliberately excluded from Filtering.
_TEXT_FIELDS = {
    "xo": (
        ("job_name", "Job name", ("job_name", "title")),
        ("job_id", "Job ID", ("job_id",)),
        ("run_id", "Run ID", ("run_id",)),
        ("mode", "Mode", ("mode",)),
        ("repository", "Repository", ("repository",)),
        ("vm", "VM", ("successful_vms", "failed_vms", "skipped_vms")),
    ),
    "zabbix": (
        ("host", "Host", ("metadata.host",)),
        ("problem_name", "Problem name", ("metadata.problem_name", "title")),
        ("event_type", "Event type", ("metadata.event_type",)),
        ("problem_id", "Problem ID", ("metadata.problem_id",)),
        ("operational_data", "Operational data", ("metadata.operational_data",)),
    ),
    "grafana": (
        ("alert_name", "Alert name", ("metadata.alert_name", "title")),
        ("alert_rule", "Alert rule", ("metadata.alert_rule", "metadata.rule_name")),
        ("folder", "Folder", ("metadata.folder",)),
        ("dashboard", "Dashboard", ("metadata.dashboard",)),
        ("panel", "Panel", ("metadata.panel",)),
        ("organization", "Organization", ("metadata.organization",)),
        ("datasource", "Data source", ("metadata.datasource",)),
        ("labels", "Labels", ("metadata.labels",)),
    ),
    "prometheus": (
        ("alert_name", "Alert name", ("metadata.alert_name", "title")),
        ("receiver", "Receiver", ("metadata.receiver",)),
        ("instance", "Instance", ("metadata.instance", "metadata.host")),
        ("service", "Service", ("metadata.service",)),
        ("job", "Job", ("metadata.job",)),
        ("namespace", "Namespace", ("metadata.namespace",)),
        ("pod", "Pod", ("metadata.pod",)),
        ("node", "Node", ("metadata.node",)),
        ("summary", "Summary", ("metadata.summary", "subject")),
        ("description", "Description", ("metadata.description", "body")),
        ("labels", "Labels", ("metadata.labels",)),
        (
            "group_key",
            "Group key",
            ("metadata.group_key", "metadata.deduplication_key"),
        ),
        ("fingerprint", "Fingerprint", ("metadata.fingerprint",)),
    ),
    "portainer": (
        ("host", "Instance / host", ("metadata.host", "metadata.instance")),
        ("alert_name", "Alert name", ("metadata.alert_name", "title")),
        ("alert_source", "Alert source", ("metadata.alert_source",)),
        ("metric", "Metric", ("metadata.metric",)),
        ("source_label", "Source label", ("metadata.source_label",)),
        ("authentication_method", "Authentication method", ("metadata.authentication_method",)),
        ("username", "Username", ("metadata.username",)),
        ("created_by", "Created by", ("metadata.created_by",)),
    ),
    "proxmox": (
        ("node", "Node", ("metadata.node", "metadata.host")),
        ("guest", "Guest", ("metadata.guest",)),
        ("vmid", "VM / CT ID", ("metadata.vmid",)),
        ("category", "Category", ("metadata.category", "category")),
        ("event_type", "Event type", ("metadata.event_type",)),
        ("job_id", "Job ID", ("metadata.job_id", "job_id")),
        ("storage", "Storage", ("metadata.storage", "repository")),
    ),
    "qnap": (
        ("nas_name", "NAS name", ("metadata.nas_name",)),
        ("application", "Application", ("metadata.application",)),
        ("category", "Category", ("metadata.category", "category")),
        ("event_type", "Event type", ("metadata.event_type",)),
        ("title", "Title", ("title",)),
    ),
    "synology": (
        ("nas_name", "NAS name", ("metadata.nas_name", "metadata.host", "metadata.hostname")),
        ("model", "Model", ("metadata.model",)),
        ("storage", "Storage", ("metadata.storage",)),
        ("storage_pool", "Storage pool", ("metadata.storage_pool",)),
        ("volume", "Volume", ("metadata.volume",)),
        ("disk", "Disk / drive", ("metadata.disk",)),
        ("package", "Package", ("metadata.package",)),
        ("task", "Task / job", ("metadata.task",)),
        ("username", "Username", ("metadata.username",)),
        ("source_ip", "Source IP", ("metadata.source_ip",)),
        ("category", "Category", ("metadata.category", "category")),
        ("event_type", "Event type", ("metadata.event_type",)),
    ),
    "truenas": (
        ("host", "Host", ("metadata.host", "metadata.hostname")),
        ("event_type", "Event type", ("metadata.event_type", "metadata.event_types")),
        ("event_title", "Event title", ("metadata.event_title", "title")),
        ("category", "Category", ("metadata.categories", "category")),
        ("message", "Message", ("metadata.message", "body")),
    ),
    "unifi_network": (
        ("event_name", "Event name", ("metadata.event_name", "title")),
        ("category", "Category", ("metadata.category", "category")),
        ("controller", "Controller", ("metadata.controller", "metadata.host")),
        ("client", "Client", ("metadata.client_display_name", "metadata.client_alias", "metadata.client_hostname")),
        ("client_ip", "Client IP", ("metadata.client_ip",)),
        ("client_mac", "Client MAC", ("metadata.client_mac",)),
        ("network_name", "Network", ("metadata.network_name",)),
        ("network_subnet", "Network subnet", ("metadata.network_subnet",)),
        ("network_vlan", "VLAN", ("metadata.network_vlan",)),
        ("wifi_name", "Wi-Fi", ("metadata.wifi_name",)),
        ("wifi_band", "Wi-Fi band", ("metadata.wifi_band",)),
        ("wifi_channel", "Wi-Fi channel", ("metadata.wifi_channel",)),
        ("last_device_name", "Last device", ("metadata.last_device_name",)),
        ("alarm_id", "Alarm ID", ("metadata.alarm_id",)),
    ),
    "unifi_protect": (
        ("alarm_name", "Alarm name", ("metadata.alarm_name",)),
        ("condition_source", "Condition source", ("metadata.condition_source",)),
        ("condition_operator", "Condition operator", ("metadata.condition_operator",)),
        ("trigger_key", "Trigger", ("metadata.trigger_key", "metadata.trigger_label")),
        ("trigger_device", "Device / camera", ("metadata.trigger_device", "metadata.trigger_device_id")),
        ("event_id", "Event ID", ("metadata.event_id",)),
        ("alarm_id", "Alarm ID", ("metadata.alarm_id",)),
    ),
    "unifi_drive": (
        ("system", "System", ("metadata.system", "metadata.host")),
        ("event_title", "Event title", ("metadata.event_title", "title")),
        ("alarm_name", "Alarm name", ("metadata.alarm_name",)),
        ("alarm_id", "Alarm ID", ("metadata.alarm_id",)),
        ("backup_task", "Backup task", ("metadata.backup_task", "job_name")),
        ("event_state", "Event state", ("metadata.event_state",)),
        ("category", "Category", ("metadata.category", "category")),
    ),
    "supermicro": (
        ("system", "System", ("metadata.system",)),
        ("sensor", "Sensor / component", ("metadata.sensor",)),
        ("category", "Category", ("category",)),
        ("registry", "Registry", ("metadata.registry",)),
        ("message_id", "Message ID", ("metadata.message_id",)),
        ("source_ip", "Source IP", ("metadata.source_ip",)),
        ("origin", "Origin", ("metadata.origin",)),
        ("event_id", "Event ID", ("metadata.event_id",)),
    ),
    "hpe_ilo": (
        ("system", "System", ("metadata.system",)),
        ("sensor", "Sensor / component", ("metadata.sensor",)),
        ("category", "Category", ("category",)),
        ("registry", "Registry", ("metadata.registry",)),
        ("message_id", "Message ID", ("metadata.message_id",)),
        ("source_ip", "Source IP", ("metadata.source_ip",)),
        ("origin", "Origin", ("metadata.origin",)),
        ("event_id", "Event ID", ("metadata.event_id",)),
    ),
    "dell_idrac": (
        ("system", "System", ("metadata.system",)),
        ("sensor", "Sensor / component", ("metadata.sensor",)),
        ("category", "Category", ("category",)),
        ("registry", "Registry", ("metadata.registry",)),
        ("message_id", "Message ID", ("metadata.message_id",)),
        ("source_ip", "Source IP", ("metadata.source_ip",)),
        ("origin", "Origin", ("metadata.origin",)),
        ("event_id", "Event ID", ("metadata.event_id",)),
    ),
    "home_assistant": (
        ("service", "Service", ("metadata.service",)),
        ("component", "Component", ("metadata.component",)),
        ("event_type", "Event type", ("metadata.event_type",)),
        ("entity_id", "Entity ID", ("metadata.entity_id",)),
        ("device", "Device", ("metadata.device",)),
        ("endpoint", "Endpoint", ("metadata.endpoint",)),
        ("error_code", "Error code", ("metadata.error_code",)),
        ("retry_seconds", "Retry seconds", ("metadata.retry_seconds",)),
        ("area", "Area", ("metadata.area",)),
        ("tags", "Tags", ("metadata.tags",)),
        ("event_state", "Event state", ("metadata.event_state",)),
    ),
    "email": (
        ("mailbox", "Mailbox", ("metadata.mailbox", "metadata.mailbox_id")),
        ("sender", "Sender", ("sender", "metadata.sender")),
        ("sender_domain", "Sender domain", ("metadata.sender_domain",)),
        ("recipient", "Recipient", ("metadata.recipient", "metadata.recipients")),
        ("subject", "Subject", ("subject", "metadata.subject")),
        ("group", "Email group", ("metadata.group", "metadata.group_id")),
        ("rule", "Email rule", ("metadata.rule", "metadata.rule_id")),
        ("classification", "Classification", ("metadata.classification",)),
        ("provider", "Provider", ("metadata.provider",)),
    ),
}


def filter_schema(source: str) -> dict | None:
    """Return the stable filtering vocabulary for one built-in integration."""

    item = integration(source)
    if item is None:
        return None
    source = canonical_source(item["source"])
    fields = []
    route_filters = item.get("route_filters", {})
    severities = list(route_filters.get("severities") or [])
    statuses = list(route_filters.get("statuses") or [])
    if severities:
        fields.append(
            {
                "key": "severity",
                "label": "Severity",
                "kind": "enum",
                "values": severities,
                "paths": ["metadata.severity", "status"],
            }
        )
    if statuses:
        fields.append(
            {
                "key": "status",
                "label": "Status",
                "kind": "enum",
                "values": statuses,
                "paths": ["metadata.state", "metadata.event_state", "metadata.status", "status"],
            }
        )
    for key, label, paths in _TEXT_FIELDS.get(source, ()):
        fields.append(
            {
                "key": key,
                "label": label,
                "kind": "text",
                "values": [],
                "paths": list(paths),
            }
        )
    return {
        "source": source,
        "name": item["name"],
        "icon_key": item["icon_key"],
        "category": item["category"],
        "inputs": deepcopy(item["inputs"]),
        "fields": fields,
    }


def filter_schemas() -> list[dict]:
    """Return filtering schemas in the same stable order as the catalogue."""

    return [
        schema
        for item in integrations()
        if (schema := filter_schema(item["source"])) is not None
    ]


def sources_for_input(input_type: str = "") -> tuple[str, ...]:
    """Return built-in integration sources compatible with an input transport."""

    requested = str(input_type or "").strip().casefold()
    result = []
    for item in integrations():
        inputs = {
            str(value.get("id") or "").strip().casefold()
            for value in item["inputs"]
        }
        if not requested or requested in inputs:
            result.append(canonical_source(item["source"]))
    return tuple(result)
