"""Read-only overview of existing routing; no ingestion or configuration writes."""
from __future__ import annotations

import time

from integrations.catalog import canonical_source, integration
from integrations.filtering import filter_schema, sources_for_input
from storage.routing_flow import delivery_snapshot, empty_metrics


WINDOWS = {"15m": 900, "1h": 3600, "1d": 86400}


def _public_policy_rules(filters, policy):
    rules = list(policy.get("policy_rules") or []) if policy else []
    public = getattr(filters, "_public_policy_rules", None)
    if callable(public):
        return public(rules)
    return [
        {
            "action": str(item.get("action") or "allow"),
            "conditions": {
                str(key): list(values)
                for key, values in (item.get("conditions") or {}).items()
            },
        }
        for item in rules
        if isinstance(item, dict)
    ]


def _policy_display(policy_rules, labels):
    """Map current allow/block rules into the existing read-only flow UI contract."""
    clauses = []
    display_labels = {}
    for index, rule in enumerate(policy_rules):
        key = f"__policy_{index}"
        action = str(rule.get("action") or "allow").strip().upper()
        parts = []
        for field, values in (rule.get("conditions") or {}).items():
            label = labels.get(field, str(field).replace("_", " "))
            parts.append(f"{label}: {', '.join(str(value) for value in values)}")
        if not parts:
            continue
        clauses.append({key: [" AND ".join(parts)]})
        display_labels[key] = action
    return clauses, display_labels


def snapshot(api, actor, range_key):
    if range_key not in WINDOWS:
        raise ValueError("routing flow range is invalid")
    now = int(time.time())
    since = now - WINDOWS[range_key]
    stats = delivery_snapshot(api.database, actor, since)
    visible_routes, route_errors = api.routes.list_visible_safe(actor)
    visible_destinations = api.destinations.list_visible(actor)
    route_ids = {route.id for route in visible_routes}
    destination_ids = {destination.id for destination in visible_destinations}
    routes, destinations, links = [], [], []

    for route in visible_routes:
        source = canonical_source(route.source)
        metadata = integration(source) or {}
        routes.append(
            {
                "id": route.id,
                "name": route.name,
                "source": source,
                "integration_name": metadata.get(
                    "name", "Fallback" if source == "*" else source
                ),
                "input_type": route.input_type,
                "enabled": route.enabled,
                "destination_ids": [
                    destination_id
                    for destination_id in route.destination_ids
                    if destination_id in destination_ids
                ],
                "metrics": stats["by_route"].get(route.id, empty_metrics()),
            }
        )

    access = api.destination_access
    for destination in visible_destinations:
        assigned = [
            route
            for route in visible_routes
            if destination.id in route.destination_ids
        ]
        channel = str(
            destination.settings.get("channel")
            or destination.settings.get("channel_name")
            or ""
        )
        if "://" in channel:
            channel = ""
        destinations.append(
            {
                "id": destination.id,
                "name": destination.name,
                "output_type": destination.output_type,
                "channel": channel[:200],
                "enabled": destination.enabled,
                "shared": destination.shared,
                "route_ids": [route.id for route in assigned],
                "metrics": stats["by_destination"].get(
                    destination.id, empty_metrics()
                ),
            }
        )

        destination_row = access.destination_row(destination.id)
        filter_visible = access.can_manage_filters(actor, destination_row)
        policies = (
            api.filters._policies_for_destination(destination.id)
            if filter_visible
            else {}
        )
        for route in assigned:
            source = canonical_source(route.source)
            sources = (
                sources_for_input(route.input_type)
                if source == "*"
                else [source]
            )
            source_policies = []
            for key in sources:
                schema = filter_schema(key) or {"fields": [], "name": key}
                labels = {
                    field["key"]: field["label"]
                    for field in schema["fields"]
                }
                if not filter_visible:
                    source_policies.append(
                        {
                            "source": key,
                            "name": schema.get("name", key),
                            "restricted": True,
                            "configured": True,
                            "enabled": True,
                            "policy_rules": [],
                            "rules": {"__restricted": ["Filter details private"]},
                            "legacy_clauses": [],
                            "labels": {**labels, "__restricted": "Access"},
                        }
                    )
                    continue

                policy = policies.get(key)
                policy_rules = _public_policy_rules(api.filters, policy)
                display_clauses, display_labels = _policy_display(
                    policy_rules, labels
                )
                configured = bool(
                    policy and (policy_rules or policy.get("clauses"))
                )
                source_policies.append(
                    {
                        "source": key,
                        "name": schema.get("name", key),
                        "restricted": False,
                        "configured": configured,
                        "enabled": api.filters.filter_enabled(
                            destination.id, key
                        ),
                        "policy_rules": policy_rules,
                        "rules": (
                            {}
                            if display_clauses
                            else api.filters._public_rules(key, policy)
                        ),
                        "legacy_clauses": (
                            display_clauses
                            if display_clauses
                            else api.filters._legacy_public(key, policy)
                        ),
                        "labels": {**labels, **display_labels},
                    }
                )
            links.append(
                {
                    "route_id": route.id,
                    "destination_id": destination.id,
                    "enabled": route.enabled and destination.enabled,
                    "fallback": source == "*",
                    "policies": source_policies,
                    "metrics": stats["by_link"].get(
                        (route.id, destination.id), empty_metrics()
                    ),
                }
            )

    history = []
    for item in stats["history"]:
        history.append(
            {
                **item,
                "route_id": (
                    item["route_id"] if item["route_id"] in route_ids else None
                ),
                "destination_id": (
                    item["destination_id"]
                    if item["destination_id"] in destination_ids
                    else None
                ),
            }
        )

    return {
        "range": range_key,
        "since": since,
        "generated_at": now,
        "capabilities": {"received": False, "filtered": False, "latency": False},
        "metrics": stats["metrics"],
        "routes": routes,
        "destinations": destinations,
        "links": links,
        "history": history,
        "errors": [
            {"component": "Routes", "message": error["message"]}
            for error in route_errors
        ],
    }
