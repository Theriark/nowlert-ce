"""Round-35 WebUI regressions for Routing Flow, Filtering F5, Dashboard stability, and account role."""

from pathlib import Path

from webui.service import UI_BUILD


ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_routing_filter_value_overflow_shows_six_and_renders_above_sibling_nodes():
    script = read("src/webui/routing_flow.js")
    styles = read("src/webui/routing_flow.css")

    card_start = script.index("function renderFilterCard")
    card_end = script.index("function activeFlowGraph", card_start)
    card = script[card_start:card_end]

    assert "const visibleValueLimit = 6;" in card
    assert 'const label = el("span", "rf-filter-value-popover-label", friendlyName(value));' in card
    assert "item.append(label);" in card
    assert '.rf-filter-card:has(.rf-filter-value-overflow[aria-expanded="true"])' in styles
    assert ".rf-filter-value-popover-label" in styles
    assert "color: #dcebf3 !important;" in styles


def test_filtering_first_paint_runs_final_decorators_synchronously_after_base_render():
    filtering = read("src/webui/filtering.js")
    ownership = read("src/webui/filtering_ownership_sync.js")
    cleanup = read("src/webui/acceptance_cleanup.js")

    assert 'new CustomEvent("nowlert:filtering-rendered", { detail: payload })' in filtering
    render_start = filtering.index("function renderOverview()")
    render_end = filtering.index("function actionButtonForFilter", render_start)
    render = filtering[render_start:render_end]
    assert 'document.dispatchEvent(new CustomEvent("nowlert:filtering-rendered", { detail: payload }));' in render

    assert 'document.addEventListener("nowlert:filtering-rendered", event => {' in ownership
    assert "decorate(event.detail);" in ownership
    assert 'document.addEventListener("nowlert:filtering-rendered", event => {' in cleanup
    assert "applyFilteringAcceptance(event.detail);" in cleanup


def test_dashboard_uses_dedicated_delivery_feed_and_only_marks_dashboard_refresh_as_live():
    dashboard = read("src/webui/operations_dashboard.js")
    acceptance = read("src/webui/operations_acceptance.js")

    assert "let dashboardDeliveries = [];" in dashboard
    assert "for (const item of dashboardDeliveries)" in dashboard
    assert "dashboardDeliveries = snapshot.deliveries;" in dashboard
    assert "dashboardDeliveries = jobs[1].value.deliveries || [];" in dashboard
    assert 'request("/deliveries", { dashboardFeed: true })' in dashboard
    assert 'request(\`/metrics/\${requestedRange}\`, { dashboardFeed: true })' in dashboard
    assert 'request("/filters", { dashboardFeed: true })' in dashboard
    assert 'request("/audit-events", { dashboardFeed: true })' in dashboard

    assert 'data-live-contract="data-feed"' in dashboard
    assert 'id="ops-feed-state">Connecting</strong>' in dashboard
    assert 'id="ops-feed-age">Waiting for dashboard data</small>' in dashboard

    assert "if (!options.dashboardFeed)" in acceptance
    assert "return previousRequest(path, options);" in acceptance


def test_account_reference_role_uses_authenticated_session_role():
    script = read("src/webui/reference_acceptance.js")

    assert 'let referenceAuthenticatedRole = "";' in script
    assert 'const role = referenceAuthenticatedRole || String(user.role || "");' in script
    assert 'role === "admin" ? "Administrator" : "User"' in script
    show_start = script.index("showApp = function showAppWithReferenceAcceptance")
    show_end = script.index("const pageTitle =", show_start)
    show = script[show_start:show_end]
    assert 'referenceAuthenticatedRole = String(session?.user?.role || "");' in show
    assert show.index('referenceAuthenticatedRole = String(session?.user?.role || "");') < show.index("base(session)")


def test_round35_build_versions_the_changed_webui_bundle():
    assert UI_BUILD == "20260919-r35"
    index = read("src/webui/index.html")
    assert 'name="nowlert-ui-build" content="20260919-r35"' in index
    assert "/ui/app.js?v=20260919-r35" in index
    assert "/ui/qa_patch.css?v=20260919-r35" in index
    assert "/ui/qa_patch.js?v=20260919-r35" in index
