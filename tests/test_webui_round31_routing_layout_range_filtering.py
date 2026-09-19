"""Round-31 regressions for Routing Flow layout/ranges and Filtering columns."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_filtering_live_table_owns_name_sharing_and_six_column_geometry():
    filtering = read("src/webui/filtering.js")
    management = read("src/webui/management_consistency.js")
    ownership = read("src/webui/filtering_ownership_sync.js")
    styles = read("src/webui/filtering.css")
    ownership_styles = read("src/webui/filtering_ownership_sync.css")

    assert '<th>Destination</th><th>Name</th><th>Filters</th><th>Status</th><th data-filter-sync-column="sharing">Sharing</th><th>Actions</th>' in filtering
    assert 'className: "filtering-sharing-cell"' in filtering
    assert 'const nameHeading = headerRow.children[1];' in ownership
    assert 'nameHeading.textContent !== "Name"' in ownership
    assert "syncFilteringTableHeading" not in management
    assert ".filtering-table th:nth-child(6) { width: 24%; }" in styles
    assert ".filtering-table th:nth-child(6) { width: 17%; }" not in ownership_styles


def test_routing_flow_range_is_owned_by_routing_flow_and_visible_selector():
    routing = read("src/webui/routing_flow.js")
    dashboard = read("src/webui/operations_dashboard.js")
    acceptance = read("src/webui/operations_acceptance.js")

    assert 'const ROUTING_RANGE_KEYS = new Set(["10m", "1h", "1d", "1m", "1y"]);' in routing
    assert 'const FLOW_RANGES = new Set(["10m", "1h", "1d", "1m", "1y"]);' in acceptance
    assert "syncRangeOptionsFromDashboard" not in routing
    assert "installRoutingFlowRanges" not in dashboard
    assert "const requestRange = selectedRoutingRange();" in routing
    assert 'String(next.range || "") !== requestRange' in routing
    assert 'String(cached.range || "") !== range' in routing
    assert "delete state.routingFlowSnapshots[nextRange]" not in routing
    assert "refresh({ allowCache: true, forceRender: true });" in routing
    assert 'byId("rf-range")?.value || "15m"' not in acceptance


def test_routing_flow_layout_reorders_every_layer_toward_connected_neighbors():
    routing = read("src/webui/routing_flow.js")
    layout = routing[
        routing.index("function computeFlowLayout(current, ordered, headerBottom)"):
        routing.index("function positionNode", routing.index("function computeFlowLayout(current, ordered, headerBottom)"))
    ]
    assert "function sortLayerByDesired(items, desired)" in routing
    assert "routeItems = sortLayerByDesired(routeItems, routeDesired);" in layout
    assert "filterItems = sortLayerByDesired(filterItems, filterDesired);" in layout
    assert "destinationItems = sortLayerByDesired(destinationItems, destinationDesired);" in layout
    assert "routeOrder: routeItems" in layout
    assert "destinationOrder: destinationItems" in layout
    assert "Math.max(20, Math.min(gap * .2, 80))" in routing
