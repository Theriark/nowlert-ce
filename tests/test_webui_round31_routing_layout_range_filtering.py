"""Round-31 regressions for Routing Flow layout/ranges and Filtering columns."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_filtering_live_table_keeps_name_and_sizes_all_six_columns():
    filtering = read("src/webui/filtering.js")
    management = read("src/webui/management_consistency.js")
    ownership = read("src/webui/filtering_ownership_sync.js")
    styles = read("src/webui/filtering_ownership_sync.css")
    base_styles = read("src/webui/filtering.css")

    assert "<th>Destination</th><th>Name</th><th>Filters</th><th>Status</th><th>Actions</th>" in filtering
    assert 'heading = node("th", "", "Sharing")' in ownership
    assert 'second.textContent = "Configuration"' not in management
    assert 'second.textContent = "Name"' in management
    for selector, width in (
        ("1", "18%"),
        ("2", "15%"),
        ("3", "30%"),
        ("4", "10%"),
        ("5", "10%"),
        ("6", "17%"),
    ):
        assert f".filtering-table th:nth-child({selector})" in styles
        assert f"width: {width};" in styles
    assert ".filtering-table th:nth-child(6)" in base_styles


def test_routing_flow_range_contract_matches_dashboard_and_visible_selector():
    routing = read("src/webui/routing_flow.js")
    dashboard = read("src/webui/operations_dashboard.js")
    acceptance = read("src/webui/operations_acceptance.js")

    assert 'const ROUTING_RANGE_KEYS = new Set(["10m", "1h", "1d", "1m", "1y"]);' in routing
    assert 'const FLOW_RANGES = new Set(["10m", "1h", "1d", "1m", "1y"]);' in acceptance
    assert "const requestRange = selectedRoutingRange();" in routing
    assert 'String(next.range || "") !== requestRange' in routing
    assert 'String(cached.range || "") !== range' in routing
    assert "delete state.routingFlowSnapshots[nextRange]" not in routing
    assert "refresh({ allowCache: true, forceRender: true });" in routing

    install = dashboard[
        dashboard.index("function installRoutingFlowRanges()"):
        dashboard.index("function syncDashboardChrome()", dashboard.index("function installRoutingFlowRanges()"))
    ]
    assert "const previousValue = select.value;" in install
    assert 'select.dispatchEvent(new Event("change", { bubbles: true }));' in install


def test_routing_flow_layout_can_float_each_layer_toward_connected_neighbors():
    routing = read("src/webui/routing_flow.js")
    layout = routing[
        routing.index("function computeFlowLayout(current, ordered, headerBottom)"):
        routing.index("function positionNode", routing.index("function computeFlowLayout(current, ordered, headerBottom)"))
    ]
    assert "function shiftCentersToTop(" not in routing
    assert "routeCenters = resolveCenters(" in layout
    assert "filterCenters = resolveCenters(" in layout
    assert "destinationCenters = resolveCenters(" in layout
    assert "shiftCentersToTop" not in layout
    assert "Math.max(20, Math.min(gap * .2, 80))" in routing
