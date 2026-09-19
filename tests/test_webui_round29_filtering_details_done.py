"""Round-29 regressions for Filtering, Routing Flow details, and Destination route saving."""

from pathlib import Path

from test_route_destination_api import (
    api,
    call,
    create_destination,
    create_route,
    login,
)


ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_filter_view_shows_assigned_fallback_without_expanding_configurable_sources(api):
    headers = login(api)
    fallback = create_route(api, headers, "Fallback HTTP", source="*")
    grafana = create_route(api, headers, "Grafana HTTP", source="grafana")
    destination = create_destination(
        api,
        headers,
        "Fallback and Grafana",
        [fallback["id"], grafana["id"]],
    )

    view = call(
        api,
        "GET",
        f"/api/v2/filters/destinations/{destination['id']}",
        headers=headers,
    )
    assert view.status == 200
    integrations = view.payload["integrations"]
    assert {item["source"] for item in integrations} == {"grafana", "*"}

    fallback_row = next(item for item in integrations if item["source"] == "*")
    assert fallback_row["name"] == "Fallback"
    assert fallback_row["fallback"] is True
    assert fallback_row["configurable"] is False
    assert fallback_row["configured"] is False
    assert fallback_row["filter_enabled"] is False
    assert [item["id"] for item in fallback_row["inputs"]] == ["http"]

    # The fallback is visible as assigned routing scope, but it must not expand
    # Filtering into integrations that were never explicitly assigned.
    assert api["service"].platform.filters.available_sources(
        api["admin"].actor,
        destination["id"],
    ) == ("grafana",)


def test_filter_name_round_trips_to_overview_and_routing_flow(api):
    headers = login(api)
    grafana = create_route(api, headers, "Grafana filtered", source="grafana")
    destination = create_destination(
        api,
        headers,
        "Named filter destination",
        [grafana["id"]],
    )
    platform = api["service"].platform
    platform.filters.set_rules(
        api["admin"].actor,
        destination["id"],
        "grafana",
        {
            "policy": [
                {
                    "action": "block",
                    "conditions": {"severity": ["warning"]},
                }
            ]
        },
    )

    saved = call(
        api,
        "PUT",
        f"/api/v2/filters/destinations/{destination['id']}",
        {"name": "Operations warnings"},
        headers,
    )
    assert saved.status == 200
    assert saved.payload["filter_name"] == "Operations warnings"

    view = call(
        api,
        "GET",
        f"/api/v2/filters/destinations/{destination['id']}",
        headers=headers,
    ).payload
    assert view["filter_name"] == "Operations warnings"

    overview = call(api, "GET", "/api/v2/filters", headers=headers).payload
    record = next(
        item
        for item in overview["filters"]
        if item["destination_id"] == destination["id"]
    )
    assert record["filter_name"] == "Operations warnings"

    flow = call(
        api,
        "GET",
        "/api/v2/routing-flow/10m",
        headers=headers,
    ).payload
    filter_record = next(
        item
        for item in flow["filters"]
        if item["destination_id"] == destination["id"]
    )
    assert filter_record["filter_name"] == "Operations warnings"


def test_filter_name_rejects_overlong_values(api):
    headers = login(api)
    grafana = create_route(api, headers, "Grafana filter name", source="grafana")
    destination = create_destination(
        api,
        headers,
        "Filter name validation",
        [grafana["id"]],
    )

    response = call(
        api,
        "PUT",
        f"/api/v2/filters/destinations/{destination['id']}",
        {"name": "x" * 121},
        headers,
    )
    assert response.status == 400


def test_routing_flow_filter_details_show_fields_and_filter_metrics():
    script = read("src/webui/routing_flow.js")
    start = script.index("function showDetails(kind, identity)")
    block = script[start:script.index("function createNode", start)]

    assert "const descriptor = filterCardDescriptor(filter);" in block
    assert 'detailRow(group.label, group.values.join(", "))' in block
    assert 'detailRow("Total events", filterMetricText(filter.metrics?.received))' in block
    assert 'detailRow("Filtered out", filterMetricText(filter.metrics?.filtered))' in block
    assert 'detailRow("Reduction", filterReductionText(filter.metrics))' in block


def test_routing_flow_filter_value_tags_show_values_without_field_prefixes():
    script = read("src/webui/routing_flow.js")
    start = script.index("const filterValues = filterCardValues(filter);")
    block = script[start:script.index("const stats =", start)]

    assert 'friendlyName(value)' in block
    assert 'chip.dataset.filterValue = "1";' in block
    assert 'group.label' not in block


def test_filtering_dialog_has_filter_name_and_visible_nonconfigurable_fallback():
    script = read("src/webui/filtering.js")
    style = read("src/webui/filtering.css")

    assert 'id="filter-name-input"' in script
    assert "async function saveFilterName()" in script
    assert 'integration.fallback === true' in script
    assert '"Fallback / All notifications"' in script
    assert "fallback ? null : actionButtonForFilter" in script
    assert ".filtering-filter-name" in style


def test_destination_route_done_submits_and_persists_current_destination_form():
    routes = read("src/webui/destination_routes.js")
    dashboard = read("src/webui/dashboard.js")

    assert 'text: "Done"' in routes
    assert 'type: "submit"' in routes
    assert 'value: "routes-done"' in routes
    assert 'const saveAndStayOpen = event.submitter?.value === "routes-done" && Boolean(id);' in dashboard
    assert "route_ids: [...routeAssignmentSelection]" in dashboard
    assert 'byId("destination-routes-close")?.click();' in dashboard
