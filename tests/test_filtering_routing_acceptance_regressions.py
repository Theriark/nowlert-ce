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


def test_filtering_actions_stay_on_one_line_with_room_for_all_controls():
    style = _read("src/webui/filtering_ownership_sync.css")
    base_style = _read("src/webui/filtering.css")

    assert ".filtering-table td:last-child > div" not in style
    assert ".filtering-table .filtering-actions-cell > div" in style
    assert ".filtering-table th:nth-child(6) { width: 24%; }" in base_style
    assert "flex-wrap: nowrap" in style
    assert "gap: 0.5rem" in style
    assert "white-space: nowrap" in style


def test_filtering_approved_actions_are_role_specific_and_icon_labeled():
    sync = _read("src/webui/filtering_ownership_sync.js")

    assert 'rowAction("View", "eye", "secondary", policy, "view-filter", true)' in sync
    assert 'rowAction("Configure", "configure", "primary", policy, "manage-destination")' in sync
    assert 'rowAction("Delete", "delete", "danger", policy, "delete-destination-filter")' in sync
    assert "else if (policy.managed_by_admin)" in sync
    assert 'actions.append(rowAction("View", "eye", "secondary", policy, "view-filter", true));' in sync
    assert 'badge("Read only", "warning")' not in sync
    for icon_name in ("eye", "share", "configure", "delete"):
        assert f"{icon_name}:" in sync


def test_filtering_status_and_sharing_match_approved_control_treatment():
    sync = _read("src/webui/filtering_ownership_sync.js")
    style = _read("src/webui/filtering_ownership_sync.css")

    assert 'node("span", "filtering-status-dot")' in sync
    assert 'item.append(icon("share"), node("span", "", label));' in sync
    assert "filtering-sharing-control" in style
    assert "filtering-row-action-eye" in style
    assert "vertical-align: middle" in style


def test_read_only_filter_modal_has_one_footer_close_action():
    sync = _read("src/webui/filtering_ownership_sync.js")

    assert 'const cancel = footer?.querySelector(\'[data-filter-action="close"]\');' in sync
    assert 'const finish = footer?.querySelector(\'[data-filter-action="finish"]\');' in sync
    assert "if (cancel) cancel.hidden = true;" in sync
    assert 'finish.textContent = "Close";' in sync
    assert "filtering-readonly-view" in sync
    assert "readOnlyDestinationId" in sync


def test_filtering_dialog_patch_is_applied_before_browser_paint():
    sync = _read("src/webui/filtering_ownership_sync.js")

    assert "function scheduleDialogPatch()" in sync
    assert "queueMicrotask" in sync
    assert "new MutationObserver(scheduleDialogPatch)" in sync
    assert "window.setTimeout(patchDialog, 0)" not in sync
    assert 'dialogPatchObserver.observe(dialog, {' in sync
    assert 'dialog.querySelectorAll(":scope > section")' in sync
    assert 'attributeFilter: ["open"]' in sync
    assert 'attributeFilter: ["hidden"]' in sync


def test_filtering_core_table_rerenders_are_redecorated_before_paint():
    sync = _read("src/webui/filtering_ownership_sync.js")

    assert "const previousRequest = request;" in sync
    assert "request = async function filteringOwnershipRequest" in sync
    assert 'if (path === "/filters") latest = response;' in sync
    assert "if (latest) decorate(latest);" in sync
    assert "if (!decorating && state.currentView === FILTER_VIEW) schedule();" not in sync


def test_authenticated_username_is_preserved_in_sidebar_identity():
    sync = _read("src/webui/filtering_ownership_sync.js")

    assert 'authenticatedUsername = String(session?.user?.username || "");' in sync
    assert "function syncProfileIdentity()" in sync
    assert 'document.getElementById("profile-name")' in sync
    assert "profileIdentityObserver = new MutationObserver" in sync
    assert "syncProfileIdentity();" in sync


def test_routing_flow_keeps_enabled_visible_destinations_without_active_links():
    script = _read("src/webui/routing_flow.js")

    assert "destinations: enabledDestinations," in script
    assert "connectedDestinationIds" not in script
    assert "const hasGraph = current.routes.length > 0 || current.destinations.length > 0;" in script
    assert "graph.hidden = !hasGraph;" in script
    assert "if (!data) return;" in script
