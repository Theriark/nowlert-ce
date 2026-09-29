from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_operations_dashboard_matches_approved_information_architecture():
    script = _read("src/webui/operations_dashboard.js")
    for text in (
        "Monitor your alert delivery pipeline and system health",
        "Integrations",
        "Destinations",
        "Routes",
        "Success Rate",
        "Failures",
        "Delivery Performance",
        "Recent Activity",
        "Top Integrations",
        "Top Destinations",
        "System Health",
        "Configuration",
        "API Tokens",
        "Active Filters",
        "Shared Destinations",
        "Audit Issues",
    ):
        assert text in script
    assert "Do not call the legacy renderer" in script
    assert "renderFlow();" not in script


def test_operations_dashboard_has_two_synchronized_dashboard_range_controls():
    script = _read("src/webui/operations_dashboard.js")
    assert 'id="history-range"' not in script
    assert 'id="ops-dashboard-range"' in script
    assert 'state.historyRange = value;' in script
    assert 'syncRangeControls();' in script


def test_dashboard_audit_health_uses_the_same_recent_page_as_workspace_load():
    dashboard = _read("src/webui/operations_dashboard.js")
    acceptance = _read("src/webui/operations_acceptance.js")

    assert 'request("/audit-events/page/1/size/25", { dashboardFeed: true })' in dashboard
    assert 'if (value === "/audit-events" || value.startsWith("/audit-events/page/")) return "audit";' in acceptance


def test_dashboard_does_not_report_storage_warning_before_health_data_exists():
    dashboard = _read("src/webui/operations_dashboard.js")

    assert 'status: storageCheck ? normalizedHealthStatus(storageCheck.status) : "unknown"' in dashboard
    assert 'item.status === "unknown" ? "Checking"' in dashboard


def test_routing_flow_keeps_backend_3h_6h_but_ui_owns_supported_windows():
    api = _read("src/api/routing_flow.py")
    dashboard = _read("src/webui/operations_dashboard.js")
    flow = _read("src/webui/routing_flow.js")
    assert '"3h": 10800' in api
    assert '"6h": 21600' in api
    assert '["3h", "Last 3 hours"]' not in dashboard
    assert '["6h", "Last 6 hours"]' not in dashboard
    assert "installRoutingFlowRanges" not in dashboard
    for label in (
        "Last 10 minutes",
        "Last 1 hour",
        "Last 24 hours",
        "Last 1 month",
        "Last 1 year",
    ):
        assert label in flow


def test_dashboard_visually_retires_legacy_dashboard_routing_flow():
    script = _read("src/webui/operations_dashboard.js")
    css = _read("src/webui/operations_dashboard.css")
    assert 'section.innerHTML = dashboardMarkup();' in script
    assert ".dashboard-flow-panel" in css
    assert "#dashboard-flow" in css
    assert "display: none !important" in css


def test_operations_dashboard_assets_are_packaged_after_existing_extensions():
    service = _read("src/webui/service.py")
    assert '"/ui/operations_dashboard.js"' in service
    assert '"src/webui/operations_dashboard.js"' in service
    assert '"/ui/operations_dashboard.css"' in service
    assert '"src/webui/operations_dashboard.css"' in service
    assert '<link rel="stylesheet" href="/ui/operations_dashboard.css{version}">' in service
    assert '<script src="/ui/operations_dashboard.js{version}" defer></script>' in service
    assert service.index('/ui/filtering_ownership_sync.js') < service.index('/ui/operations_dashboard.js')


def test_selected_visual_reference_layout_is_encoded_in_css():
    css = _read("src/webui/operations_dashboard.css")
    assert "grid-template-columns: repeat(5, minmax(0, 1fr));" in css
    assert "grid-template-columns: minmax(0, 1.56fr) minmax(430px, .94fr);" in css
    assert "grid-template-columns: repeat(3, minmax(0, 1fr));" in css
    assert "grid-template-columns: 180px repeat(4, minmax(0, 1fr));" in css
    assert ".ops-chart-outcome-line" in css
    assert ".ops-chart-delivery-pulse" in css
    assert "ops-chart-line-core 2s ease-in-out infinite" in css
    assert "@media (prefers-reduced-motion: reduce)" in css


def test_dashboard_delivery_chart_is_cumulative_pulsing_and_has_no_replay_or_dots():
    script = _read("src/webui/operations_dashboard.js")
    css = _read("src/webui/operations_dashboard.css")
    assert "window.NowlertDeliveryChart" in script
    assert "chartModel.buildCumulativeSeries(buckets, bucketSeconds)" in script
    assert "chartModel.buildStepPath(points" in script
    assert "ops-chart-delivery-pulse" in script
    assert "ops-chart-replay" not in script
    assert "ops-chart-outcome-point" not in script
    assert "ops-chart-bar" not in script
    assert "ops-chart-outcome-line" in css
    assert "ops-chart-line-core 2s ease-in-out infinite" in css
    assert "prefers-reduced-motion: reduce" in css
