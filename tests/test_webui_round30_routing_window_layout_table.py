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
    old = int(time.time()) - (2 * 60 * 60)
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
    day = call(api, "GET", "/api/v2/routing-flow/1d", headers=headers).payload

    ten_destination = next(item for item in ten["destinations"] if item["id"] == destination["id"])
    day_destination = next(item for item in day["destinations"] if item["id"] == destination["id"])
    ten_filter = next(item for item in ten["filters"] if item["destination_id"] == destination["id"])
    day_filter = next(item for item in day["filters"] if item["destination_id"] == destination["id"])

    assert ten_destination["metrics"]["delivered"] == 1
    assert day_destination["metrics"]["delivered"] == 2
    assert ten_filter["metrics"]["received"] == 2
    assert ten_filter["metrics"]["filtered"] == 1
    assert day_filter["metrics"]["received"] == 4
    assert day_filter["metrics"]["filtered"] == 2


def test_layout_freely_reorders_all_three_layers_from_connected_centers():
    script = read("src/webui/routing_flow.js")
    layout = script[
        script.index("function computeFlowLayout(current, ordered, headerBottom)"):
        script.index("function positionNode", script.index("function computeFlowLayout(current, ordered, headerBottom)"))
    ]

    assert "function sortLayerByDesired(items, desired)" in script
    assert "routeItems = sortLayerByDesired(routeItems, routeDesired);" in layout
    assert "filterItems = sortLayerByDesired(filterItems, filterDesired);" in layout
    assert "destinationItems = sortLayerByDesired(destinationItems, destinationDesired);" in layout
    assert "routeOrder: routeItems" in layout
    assert "destinationOrder: destinationItems" in layout


def test_edges_use_a_bounded_short_curve_instead_of_half_gap_bends():
    script = read("src/webui/routing_flow.js")
    start = script.index("function edgeCurve(a, b)")
    block = script[start:script.index("function drawEdges()", start)]

    assert "Math.max(20, Math.min(gap * .2, 80))" in block
    assert "gap * .52" not in block


def test_filtering_table_uses_name_and_native_balanced_six_column_widths():
    script = read("src/webui/filtering.js")
    style = read("src/webui/filtering.css")

    assert '<th>Destination</th><th>Name</th><th>Filters</th><th>Status</th><th data-filter-sync-column="sharing">Sharing</th><th>Actions</th>' in script
    assert 'className: "filtering-sharing-cell"' in script
    for selector, width in (
        ("1", "17%"),
        ("2", "18%"),
        ("3", "21%"),
        ("4", "9%"),
        ("5", "11%"),
        ("6", "24%"),
    ):
        assert f".filtering-table th:nth-child({selector}) {{ width: {width}; }}" in style
    assert "overflow-x: hidden !important;" in style
