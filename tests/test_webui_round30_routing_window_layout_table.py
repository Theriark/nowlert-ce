"""Round-30 Routing Flow window/layout and Filtering table regressions."""

from pathlib import Path
import time

from models import Notification
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


def test_filter_details_do_not_repeat_generic_active_status():
    script = read("src/webui/routing_flow.js")
    start = script.index("const filter = current.filters.find(item => item.id === identity);")
    block = script[start:script.index("drawEdges();", start)]

    assert 'detailRow("Status", "Active")' not in block
    assert 'detailRow("Sources", sourceNames.join(", ") || "Managed")' in block
    assert 'detailIdentityRow("Destination", destinationLogo(d), d.name)' in block
    assert 'detailRow("Total events", filterMetricText(filter.metrics?.received))' in block
    assert 'detailRow("Filtered out", filterMetricText(filter.metrics?.filtered))' in block


def test_range_change_uses_visible_selection_and_preserves_matching_cache():
    script = read("src/webui/routing_flow.js")

    assert "function selectedRoutingRange()" in script
    assert "function changeRoutingRange(nextRange)" in script
    assert "delete state.routingFlowSnapshots[nextRange];" not in script
    assert "refresh({ allowCache: true, forceRender: true });" in script
    assert "async function refresh(options = {})" in script
    assert "const allowCache = options.allowCache !== false;" in script
    assert "const forceRender = options.forceRender === true;" in script
    assert "if (allowCache) hydrateCachedRoutingFlow();" in script
    assert "const requestRange = selectedRoutingRange();" in script
    assert 'String(cached.range || "") !== range' in script
    assert 'String(next.range || "") !== requestRange' in script
    assert "if (forceRender || nextSignature !== signature)" in script
    assert 'changeRoutingRange($("rf-range").value)' in script


def test_server_metrics_for_filters_and_destinations_follow_requested_window(api):
    headers = login(api)
    route = create_route(api, headers, "Grafana windowed", source="grafana")
    destination = create_destination(
        api,
        headers,
        "Windowed destination",
        [route["id"]],
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

    def fire_pair():
        platform.delivery.deliver(
            api["admin"].actor,
            Notification(
                source="grafana",
                title="blocked warning",
                metadata={"severity": "warning", "_input_type": "http"},
            ),
        )
        platform.delivery.deliver(
            api["admin"].actor,
            Notification(
                source="grafana",
                title="delivered information",
                metadata={"severity": "information", "_input_type": "http"},
            ),
        )

    fire_pair()
    old = int(time.time()) - 1800
    with api["database"].transaction() as connection:
        connection.execute(
            "UPDATE routing_flow_events SET created_at = ?",
            (old,),
        )
        connection.execute(
            "UPDATE delivery_attempts SET created_at = ?, completed_at = ?",
            (old, old),
        )

    fire_pair()

    ten = call(api, "GET", "/api/v2/routing-flow/10m", headers=headers).payload
    hour = call(api, "GET", "/api/v2/routing-flow/1h", headers=headers).payload

    ten_destination = next(item for item in ten["destinations"] if item["id"] == destination["id"])
    hour_destination = next(item for item in hour["destinations"] if item["id"] == destination["id"])
    ten_filter = next(item for item in ten["filters"] if item["destination_id"] == destination["id"])
    hour_filter = next(item for item in hour["filters"] if item["destination_id"] == destination["id"])

    assert ten_destination["metrics"]["delivered"] == 1
    assert hour_destination["metrics"]["delivered"] == 2
    assert ten_filter["metrics"]["received"] == 2
    assert ten_filter["metrics"]["filtered"] == 1
    assert hour_filter["metrics"]["received"] == 4
    assert hour_filter["metrics"]["filtered"] == 2


def test_layout_keeps_barycentric_vertical_alignment_instead_of_reanchoring_columns():
    script = read("src/webui/routing_flow.js")

    assert "function shiftCentersToTop(" not in script
    assert "routeCenters = shiftCentersToTop(" not in script
    assert "filterCenters = shiftCentersToTop(" not in script
    assert "destinationCenters = shiftCentersToTop(" not in script
    assert "const routeDesired = new Map" in script
    assert "const filterDesired = new Map" in script
    assert "const destinationDesired = new Map" in script


def test_edges_use_a_bounded_short_curve_instead_of_half_gap_bends():
    script = read("src/webui/routing_flow.js")
    start = script.index("function edgeCurve(a, b)")
    block = script[start:script.index("function drawEdges()", start)]

    assert "Math.max(20, Math.min(gap * .2, 80))" in block
    assert "gap * .52" not in block


def test_filtering_table_uses_name_header_and_balanced_five_column_widths():
    script = read("src/webui/filtering.js")
    style = read("src/webui/filtering.css")

    assert "<th>Destination</th><th>Name</th><th>Filters</th><th>Status</th><th>Actions</th>" in script
    assert ".filtering-table th:nth-child(1) { width: 20%; }" in style
    assert ".filtering-table th:nth-child(2) { width: 18%; }" in style
    assert ".filtering-table th:nth-child(3) { width: 37%; }" in style
    assert ".filtering-table th:nth-child(4) { width: 10%; }" in style
    assert ".filtering-table th:nth-child(5) { width: 15%; }" in style
    assert ".filtering-table th:nth-child(2) { width: 56%; text-align: center; }" not in style
