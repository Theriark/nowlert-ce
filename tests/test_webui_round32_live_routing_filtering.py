"""Round-32 live WebUI delivery and ownership regressions."""

from pathlib import Path

from test_webui import enabled_config
from webui.service import UI_BUILD, WebUIService


ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_served_html_versions_every_runtime_webui_extension():
    service = WebUIService(enabled_config(), root=ROOT)
    response = service.response("/")
    assert response is not None and response.status == 200
    markup = response.body.decode("utf-8")

    assert UI_BUILD == "20260919-r35"
    assert f'name="nowlert-ui-build" content="{UI_BUILD}"' in markup
    for asset in (
        "/ui/filtering.css",
        "/ui/routing_flow.css",
        "/ui/filtering_ownership_sync.css",
        "/ui/operations_dashboard.css",
        "/ui/operations_acceptance.css",
        "/ui/filtering.js",
        "/ui/routing_flow.js",
        "/ui/filtering_ownership_sync.js",
        "/ui/operations_dashboard.js",
        "/ui/operations_acceptance.js",
        "/ui/management_consistency.js",
    ):
        assert f"{asset}?v={UI_BUILD}" in markup


def test_filtering_core_owns_name_sharing_and_final_six_column_geometry():
    filtering = read("src/webui/filtering.js")
    styles = read("src/webui/filtering.css")
    ownership = read("src/webui/filtering_ownership_sync.js")
    ownership_styles = read("src/webui/filtering_ownership_sync.css")
    management = read("src/webui/management_consistency.js")

    assert '<th>Name</th><th>Filters</th><th>Status</th><th data-filter-sync-column="sharing">Sharing</th><th>Actions</th>' in filtering
    assert 'className: "filtering-sharing-cell"' in filtering
    assert 'const nameHeading = headerRow.children[1];' in ownership
    assert 'nameHeading.textContent !== "Name"' in ownership
    assert "syncFilteringTableHeading" not in management

    for selector, width in (
        ("1", "17%"),
        ("2", "18%"),
        ("3", "21%"),
        ("4", "9%"),
        ("5", "11%"),
        ("6", "24%"),
    ):
        assert f".filtering-table th:nth-child({selector}) {{ width: {width}; }}" in styles
    assert "overflow-x: hidden !important;" in styles
    assert ".filtering-table th:nth-child(6) { width: 17%; }" not in ownership_styles


def test_routing_range_has_one_owner_and_preserves_range_specific_cache():
    routing = read("src/webui/routing_flow.js")
    dashboard = read("src/webui/operations_dashboard.js")
    acceptance = read("src/webui/operations_acceptance.js")

    assert "syncRangeOptionsFromDashboard" not in routing
    assert "installRoutingFlowRanges" not in dashboard
    assert 'const ROUTING_RANGE_KEYS = new Set(["10m", "1h", "1d", "1m", "1y"]);' in routing
    assert "const requestRange = selectedRoutingRange();" in routing
    assert 'String(cached.range || "") !== range' in routing
    assert 'String(next.range || "") !== requestRange' in routing
    assert "delete state.routingFlowSnapshots[nextRange]" not in routing
    assert "refresh({ allowCache: true, forceRender: true });" in routing
    assert 'byId("rf-range")?.value || "15m"' not in acceptance


def test_routing_layout_reorders_integrations_filters_and_destinations_each_pass():
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


def test_development_acceptance_checks_the_live_changed_assets():
    workflow = read(".github/workflows/ci.yml")

    assert "from webui.service import UI_BUILD" in workflow
    assert "/ui/routing_flow.js?v=${UI_BUILD}" in workflow
    assert "/ui/filtering.js?v=${UI_BUILD}" in workflow
    assert "/ui/filtering_ownership_sync.css?v=${UI_BUILD}" in workflow
    assert "function sortLayerByDesired(items, desired)" in workflow
    assert 'data-filter-sync-column="sharing">Sharing</th><th>Actions</th>' in workflow
    assert "verify_live_bundle()" in workflow
    assert "for attempt in \\$(seq 1 12)" not in workflow
    assert "for attempt in $(seq 1 12)" in workflow
    assert 'WAIT: deployment is still converging' in workflow
