"""Read-only overview of existing routing; no ingestion or configuration writes."""
from __future__ import annotations

import time

from integrations.catalog import canonical_source, integration
from integrations.filtering import filter_schema, sources_for_input
from storage.routing_flow import delivery_snapshot, empty_metrics


WINDOWS = {
    "10m": 10 * 60,
    "15m": 15 * 60,
    "1h": 60 * 60,
    "3h": 10800,
    "6h": 21600,
    "1d": 24 * 60 * 60,
    "1m": 31 * 24 * 60 * 60,
    "1y": 366 * 24 * 60 * 60,
}


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
    routes, destinations, links, filters = [], [], [], []

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

    filters_overview = []
    overview_loader = getattr(api, "_filters_overview", None)
    if callable(overview_loader):
        response = overview_loader(actor)
        payload = response.payload if isinstance(response.payload, dict) else {}
        filters_overview = list(payload.get("filters") or [])
    filters_by_destination = {
        str(item.get("destination_id")): item
        for item in filters_overview
        if isinstance(item, dict) and item.get("destination_id")
    }

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

        filtering_record = filters_by_destination.get(str(destination.id))
        filter_sources = []
        active_filter_sources = []
        filter_policies = []
        filter_route_ids = []
        filter_metrics = {**empty_metrics(), "last_activity_at": 0}

        if filtering_record is not None:
            filter_policies = [
                dict(item)
                for item in filtering_record.get("integrations") or []
                if isinstance(item, dict) and item.get("configured")
            ]
            filter_sources = [
                canonical_source(item.get("source"))
                for item in filter_policies
                if item.get("source")
            ]
            active_filter_sources = [
                canonical_source(item.get("source"))
                for item in filter_policies
                if item.get("source") and item.get("filter_enabled", True)
            ]

            for candidate in assigned:
                candidate_source = canonical_source(candidate.source)
                candidate_sources = (
                    sources_for_input(candidate.input_type)
                    if candidate_source == "*"
                    else [candidate_source]
                )
                if (
                    candidate.enabled
                    and any(source in filter_sources for source in candidate_sources)
                ):
                    filter_route_ids.append(candidate.id)

            for source in filter_sources:
                source_metrics = stats.get("by_filter", {}).get(
                    (destination.id, source), empty_metrics()
                )
                for metric_key in (
                    "received",
                    "filtered",
                    "delivered",
                    "pending",
                    "failed",
                ):
                    filter_metrics[metric_key] += int(
                        source_metrics.get(metric_key, 0) or 0
                    )
                filter_metrics["last_activity_at"] = max(
                    int(filter_metrics.get("last_activity_at", 0) or 0),
                    int(source_metrics.get("last_activity_at", 0) or 0),
                )

        destination_filter_id = (
            f"{destination.id}:filter"
            if filter_policies and filter_route_ids
            else None
        )
        if destination_filter_id is not None:
            filters.append(
                {
                    "id": destination_filter_id,
                    "name": str(
                        filtering_record.get("destination_name")
                        or destination.name
                    ),
                    "destination_id": destination.id,
                    "sources": filter_sources,
                    "active_sources": active_filter_sources,
                    "route_ids": filter_route_ids,
                    "configured_count": int(
                        filtering_record.get("configured_count")
                        or len(filter_policies)
                    ),
                    "active_count": int(
                        filtering_record.get("active_count")
                        or len(active_filter_sources)
                    ),
                    "policies": filter_policies,
                    "metrics": filter_metrics,
                }
            )

        # Preserve the per-link policy details contract for Route/edge
        # inspectors, but keep the filter-card model sourced exclusively from
        # the canonical Filtering overview above.
        destination_row = api.destination_access.destination_row(destination.id)
        filter_visible = api.destination_access.can_manage_filters(
            actor, destination_row
        )
        link_policies = api.filters._policies_for_destination(destination.id)

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
                policy = link_policies.get(key)
                policy_rules = _public_policy_rules(api.filters, policy)
                configured = bool(
                    policy and (policy_rules or policy.get("clauses"))
                )
                source_enabled = bool(
                    configured and key in active_filter_sources
                )
                if not filter_visible:
                    # Keep the privacy marker for API consumers, and expose a
                    # second sanitized presentation policy only when that real
                    # owner-managed filter is configured. The WebUI ignores the
                    # restricted marker and can render the managed policy without
                    # learning any rule values.
                    source_policies.append(
                        {
                            "source": key,
                            "name": schema.get("name", key),
                            "restricted": True,
                            "configured": configured,
                            "enabled": source_enabled,
                            "policy_rules": [],
                            "rules": (
                                {"__restricted": ["Filter details private"]}
                                if configured
                                else {}
                            ),
                            "legacy_clauses": [],
                            "labels": {**labels, "__restricted": "Access"},
                        }
                    )
                    if configured:
                        source_policies.append(
                            {
                                "source": key,
                                "name": schema.get("name", key),
                                "restricted": False,
                                "managed": True,
                                "configured": True,
                                "enabled": source_enabled,
                                "policy_rules": [],
                                "rules": {"__managed": ["Managed by administrator"]},
                                "legacy_clauses": [],
                                "labels": {**labels, "__managed": "Filter"},
                            }
                        )
                    continue

                display_clauses, display_labels = _policy_display(
                    policy_rules, labels
                )
                source_policies.append(
                    {
                        "source": key,
                        "name": schema.get("name", key),
                        "restricted": False,
                        "configured": configured,
                        "enabled": source_enabled,
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
                    "filter_ids": (
                        [destination_filter_id]
                        if destination_filter_id is not None
                        and any(
                            key in active_filter_sources
                            for key in sources
                        )
                        else []
                    ),
                    "direct": any(
                        key not in active_filter_sources
                        for key in sources
                    ),
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
        "capabilities": {"received": True, "filtered": True, "latency": False},
        "metrics": stats["metrics"],
        "routes": routes,
        "destinations": destinations,
        "filters": filters,
        "links": links,
        "history": history,
        "errors": [
            {"component": "Routes", "message": error["message"]}
            for error in route_errors
        ],
    }
