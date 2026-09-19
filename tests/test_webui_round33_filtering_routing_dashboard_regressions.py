"""Round-33 regressions for Filtering, Routing Flow, and Dashboard refresh behavior."""

from pathlib import Path

from webui.service import UI_BUILD


ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_filtering_clears_stale_dashboard_translation_key_before_navigation():
    script = read("src/webui/filtering.js")
    nav = script[
        script.index("function wrapNavigation()"):
        script.index("const previousExpireSession", script.index("function wrapNavigation()"))
    ]

    assert 'if (view === "filtering") {' in nav
    assert 'delete title.dataset.i18nSource;' in nav
    assert nav.index('delete title.dataset.i18nSource;') < nav.index("previousNavigate(view, historyMode)")


def test_filtering_expansion_uses_a_full_width_companion_row():
    script = read("src/webui/filtering.js")
    styles = read("src/webui/filtering.css")
    ownership = read("src/webui/filtering_ownership_sync.js")
    acceptance = read("src/webui/acceptance_cleanup.js")

    assert 'className: "filtering-policy-row"' in script
    assert 'className: "filtering-expanded-row"' in script
    assert 'className: "filtering-expanded-cell"' in script
    assert 'attributes: { colspan: "6" }' in script
    assert 'dataset: { filterOverviewToggle: policy.destination_id }' in script
    assert 'detailRow.hidden = !expanded;' in script
    assert "grid-template-columns: repeat(auto-fit, minmax(220px, 280px));" in styles
    assert '.filtering-expanded-row[hidden] { display: none; }' in styles
    assert '"#filter-table > tr.filtering-policy-row"' in ownership
    assert '"#filter-table > tr.filtering-policy-row"' in acceptance
    assert 'row.nextElementSibling?.matches(".filtering-expanded-row")' in ownership
    assert 'row.nextElementSibling?.matches(".filtering-expanded-row")' in acceptance


def test_routing_range_control_survives_header_reparenting_and_refreshes_immediately():
    script = read("src/webui/routing_flow.js")

    assert 'const routingRangeSelect = section.querySelector("#rf-range");' in script
    assert 'id === "rf-range" ? routingRangeSelect' in script
    assert '$("rf-range").addEventListener("change"' in script
    assert 'changeRoutingRange($("rf-range").value)' in script
    assert "refresh({ allowCache: true, forceRender: true });" in script


def test_dashboard_cache_does_not_restore_range_bound_dynamic_data():
    script = read("src/webui/qa_patch.js")
    start = script.index("const QA_WORKSPACE_CACHE_FIELDS")
    end = script.index("];", start)
    fields = script[start:end]

    for field in ('"deliveries"', '"audit"', '"metrics"', '"historyRange"'):
        assert field not in fields
    assert '"routingFlowSnapshots"' in fields
    assert '"filteringOverview"' in fields


def test_dashboard_restores_saved_range_before_show_app_and_queues_inflight_changes():
    acceptance = read("src/webui/operations_acceptance.js")
    dashboard = read("src/webui/operations_dashboard.js")

    show_start = acceptance.index("showApp = function operationsAcceptanceShowApp")
    show_end = acceptance.index("function resetLiveState", show_start)
    show = acceptance[show_start:show_end]
    assert 'readStoredRangeForSession(session, "dashboard-range")' in show
    assert "state.historyRange = storedDashboardRange;" in show
    assert show.index("state.historyRange = storedDashboardRange;") < show.index("previousShowApp(session)")

    refresh_start = dashboard.index("async function refreshDashboardData")
    refresh_end = dashboard.index("function updateLiveAge", refresh_start)
    refresh = dashboard[refresh_start:refresh_end]
    assert "const requestedRange = state.historyRange;" in refresh
    assert 'request(`/metrics/${requestedRange}`)' in refresh
    assert "if (requestedRange !== state.historyRange)" in refresh
    assert "refreshPending = true;" in refresh
    assert "window.queueMicrotask(() => refreshDashboardData(true));" in refresh


def test_routing_layout_caps_connection_slack_and_filter_cards_use_saved_names():
    script = read("src/webui/routing_flow.js")
    styles = read("src/webui/routing_flow.css")

    resolve_start = script.index("function resolveCenters")
    resolve_end = script.index("function packCentersFromTop", resolve_start)
    resolve = script[resolve_start:resolve_end]
    assert "const maxSlack = Math.max(24, Math.min(48, gap * 3));" in resolve
    assert "Math.min(maxSlack, target - baseCenter)" in resolve
    assert "Math.max(Number.isFinite(target) ? target" not in resolve

    card_start = script.index("function renderFilterCard")
    card_end = script.index("function activeFlowGraph", card_start)
    card = script[card_start:card_end]
    assert 'String(filter?.filter_name || filter?.name || "").trim()' in card
    assert 'configuredName || descriptor.title || "Filter"' in card
    assert 'document.createTextNode("Filter: ")' not in card
    assert ".rf-filter-card-summary" in styles


def test_round33_repaired_bundle_remains_versioned_in_current_build():
    assert UI_BUILD == "20260919-r35"
    index = read("src/webui/index.html")
    assert 'name="nowlert-ui-build" content="20260919-r35"' in index
    assert "/ui/app.js?v=20260919-r35" in index
    assert "/ui/qa_patch.css?v=20260919-r35" in index
    assert "/ui/qa_patch.js?v=20260919-r35" in index
