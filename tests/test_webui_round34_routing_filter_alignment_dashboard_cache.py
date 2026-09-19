"""Round-34 WebUI regressions for compact Routing Flow filters, Filtering alignment, and Dashboard F5 cache."""

from pathlib import Path

from webui.service import UI_BUILD


ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_routing_filter_card_shows_rule_values_in_one_row_with_plus_n_popover():
    script = read("src/webui/routing_flow.js")
    styles = read("src/webui/routing_flow.css")

    card_start = script.index("function renderFilterCard")
    card_end = script.index("function activeFlowGraph", card_start)
    card = script[card_start:card_end]

    assert "function filterCardValues(filter)" in script
    assert "const filterValues = filterCardValues(filter);" in card
    assert 'dataset.filterValue = "1";' in card
    assert '"rf-filter-value-overflow-wrap"' in card
    assert '"rf-filter-value-overflow"' in card
    assert '"rf-filter-value-popover"' in card
    assert 'toggle.textContent = `+${hiddenValues.length}`;' in card
    assert 'popover.hidden = !valueMenuOpen;' in card

    assert ".rf-filter-value-overflow-wrap" in styles
    assert ".rf-filter-value-popover" in styles
    assert ".rf-filter-value-popover-item" in styles
    assert ".rf-filter-card-tags" in styles
    assert "flex-wrap: nowrap !important;" in styles


def test_filtering_expanded_cards_align_from_the_left_and_are_not_treated_as_actions():
    styles = read("src/webui/filtering.css")
    ownership = read("src/webui/filtering_ownership_sync.css")

    assert "grid-template-columns: repeat(auto-fit, minmax(220px, 280px));" in styles
    assert "justify-content: start;" in styles
    assert ".filtering-table td:last-child > div" not in ownership
    assert ".filtering-table .filtering-actions-cell > div" in ownership


def test_dashboard_has_range_aware_first_paint_snapshot_for_f5():
    script = read("src/webui/operations_dashboard.js")

    assert 'const DASHBOARD_SNAPSHOT_SCHEMA = 1;' in script
    assert "function dashboardSnapshotKey(session, range)" in script
    assert "function restoreDashboardSnapshot(session, range)" in script
    assert "function saveDashboardSnapshot(range)" in script
    assert "snapshot.range !== range" in script
    assert "state.deliveries = snapshot.deliveries;" in script
    assert "state.metrics = snapshot.metrics;" in script
    assert "state.audit = snapshot.audit;" in script
    assert "filterSnapshot = snapshot.filters;" in script

    refresh_start = script.index("async function refreshDashboardData")
    refresh_end = script.index("function updateLiveAge", refresh_start)
    refresh = script[refresh_start:refresh_end]
    assert "saveDashboardSnapshot(requestedRange);" in refresh

    assert "const previousShowApp = showApp;" in script
    show_start = script.index("showApp = function operationsDashboardShowApp")
    show_end = script.index("const previousExpireSession", show_start)
    show = script[show_start:show_end]
    assert "restoreDashboardSnapshot(session, state.historyRange);" in show
    assert show.index("restoreDashboardSnapshot(session, state.historyRange);") < show.index("previousShowApp(session)")


def test_round34_build_versions_the_changed_webui_bundle():
    assert UI_BUILD == "20260919-r34"
    index = read("src/webui/index.html")
    assert 'name="nowlert-ui-build" content="20260919-r34"' in index
    assert "/ui/app.js?v=20260919-r34" in index
    assert "/ui/qa_patch.css?v=20260919-r34" in index
    assert "/ui/qa_patch.js?v=20260919-r34" in index
