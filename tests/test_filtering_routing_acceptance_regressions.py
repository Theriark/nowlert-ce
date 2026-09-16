"""Regression contract for the accepted Filtering and Routing Flow presentation."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_filtering_keeps_status_and_sharing_in_distinct_columns():
    sync = _read("src/webui/filtering_ownership_sync.js")
    cleanup = _read("src/webui/acceptance_cleanup.js")
    style = _read("src/webui/filtering_ownership_sync.css")

    assert "filtering-sharing-cell" in sync
    assert 'heading.textContent = "Sharing"' in sync
    assert "statusCell.replaceChildren" in sync
    assert "sharingCell.replaceChildren" in sync
    assert "filtering-status-stack" not in sync
    assert "filtering-status-stack" not in style
    assert "statusCell.append(visibility)" not in cleanup
    assert "statusCell.replaceChildren" not in cleanup


def test_filtering_sharing_refreshes_destinations_without_browser_reload():
    sync = _read("src/webui/filtering_ownership_sync.js")

    assert "async function refreshDestinationsState()" in sync
    assert 'const payload = await request("/destinations")' in sync
    assert "renderDestinations();" in sync
    assert 'state.currentView === "destinations"' in sync
    assert "window.location.reload" not in sync


def test_legacy_user_filtering_decorator_is_retired():
    shell = _read("src/webui/source_ui_retirement.js")

    assert "decorateFiltering" not in shell
    assert "queueFilteringDecoration" not in shell
    assert "elevateFilteringUntilDialogCloses" not in shell
    assert 'state.user.role = "admin"' not in shell
    assert "row.children[3]" not in shell


def test_filtering_uses_destination_permissions_and_real_read_only_view():
    script = _read("src/webui/filtering.js")

    assert "function policyCanManage(policy)" in script
    assert "function currentDestinationCanManage()" in script
    assert "function canCreateFilter()" in script
    assert '"view-destination-filter"' in script
    assert "openReadOnlyDestinationFilter" in script
    assert "policy.managed_by_admin" in script
    assert 'text: "Read only"' not in script
    assert 'badge("Read only", "warning")' in script
    assert "Read-only view. Filter rules remain private to the destination owner." in script
    assert "!currentDestinationCanManage()" in script


def test_filtering_actions_stay_on_one_line_with_room_for_two_controls():
    style = _read("src/webui/filtering_ownership_sync.css")

    assert ".filtering-table td:last-child" in style
    assert ".filtering-table th:nth-child(5) { width: 17%; }" in style
    assert "flex-wrap: nowrap" in style
    assert "gap: 0.65rem" in style
    assert "white-space: nowrap" in style


def test_routing_flow_keeps_enabled_visible_destinations_without_active_links():
    script = _read("src/webui/routing_flow.js")

    assert "destinations: enabledDestinations," in script
    assert "connectedDestinationIds" not in script
    assert "const hasGraph = current.routes.length > 0 || current.destinations.length > 0;" in script
    assert "graph.hidden = !hasGraph;" in script
    assert "if (!data) return;" in script
