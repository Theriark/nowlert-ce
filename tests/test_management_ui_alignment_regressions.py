"""Regression coverage for management-page controls and panel alignment."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_destination_editor_uses_the_list_badge_states_and_icons():
    script = _read("src/webui/destination_editor_fix.js")
    routes = _read("src/webui/destination_routes.js")
    style = _read("src/webui/destination_editor_fix.css")

    assert 'status.className = "button small destination-provider-status"' in routes
    assert 'status.classList.toggle("is-active", enabled.checked)' in routes
    assert 'status.classList.toggle("is-disabled", !enabled.checked)' in routes
    assert 'destination-provider-sharing is-${shared ? "shared" : "private"}' in script
    assert 'status.replaceChildren(' in routes
    assert 'status.replaceChildren(icon, label)' in script
    assert ".destination-provider-sharing.is-shared" in style
    assert ".destination-provider-sharing.is-private" in style
    assert ".destination-provider-status.is-active" in style
    assert ".destination-provider-status.is-disabled" in style
    assert ".button.destination-provider-sharing," in style
    assert "border-radius: 999px" in style
    assert "font-size: 0.58rem" in style
    assert "min-height: 0" in style
    assert "padding: 3px 6px" in style


def test_destination_route_active_matches_the_provider_active_green_treatment():
    style = _read("src/webui/destination_editor_fix.css")

    active_rule = style.split(".destination-route-pill-status.enabled", 1)[1].split("}", 1)[0]
    provider_active_rule = style.split(".destination-provider-status.is-active", 1)[1].split("}", 1)[0]
    for declaration in (
        "background: rgba(77, 211, 126, 0.12)",
        "border-color: rgba(77, 211, 126, 0.28)",
        "color: #8fe47b",
    ):
        assert declaration in active_rule
        assert declaration in provider_active_rule


def test_management_ui_fixes_receive_a_fresh_asset_cache_key():
    service = _read("src/webui/service.py")

    assert 'UI_BUILD = "20260929-r60"' in service


def test_user_role_can_manage_owned_routes_and_filtering_survives_refresh():
    app = _read("src/webui/app.js")
    filtering = _read("src/webui/filtering.js")
    route_editor = _read("src/webui/destination_routes.js")
    cache = _read("src/webui/qa_patch.js")

    assert 'filtering: "Filtering"' in app
    assert 'byId("add-route-button").hidden = !isAdmin()' not in app
    assert "const canManage = isAdmin() || ownResource(item);" in app
    assert 'payload.route_ids = window.nowlertDestinationRouteIds()' in app
    assert 'if (state.currentView === "filtering") navigate("filtering", "replace")' in filtering
    assert "window.nowlertDestinationRouteIds" in route_editor
    assert 'text: "+ Add route"' in route_editor
    assert 'QA_WORKSPACE_CACHE_KEY = "nowlert.workspace-cache.v2"' in cache


def test_users_can_see_and_assign_routes_they_can_access_to_managed_destinations():
    route_editor = _read("src/webui/destination_routes.js")
    picker = route_editor.split(
        "routeAssignmentRenderOptions = function routeAssignmentRenderDrawerOptions()",
        1,
    )[1].split("const destinationEditorBaseRenderDestinationFields", 1)[0]

    assert "if (!isAdmin() && !ownResource(item)) return false;" not in picker
    assert "state.routes || []" in picker
    assert "routeAssignmentSelection = new Set((state.routes || []).map((item) => item.id));" in route_editor
    assert "routeAssignmentSelection.clear();" in route_editor


def test_backup_data_tools_are_not_clipped_by_fixed_height():
    styles = _read("src/webui/qa_patch.css")
    desktop_backup_rules = styles.split("/* 2026-09-18 round-20", 1)[1]
    final_data_tools_rules = styles.split("/* Keep every data-tool card", 1)[1]

    assert "#backup-schedule-panel,\n  #backup-data-tools-panel" not in desktop_backup_rules
    assert "#backup-data-tools-panel {\n  height: auto !important" in final_data_tools_rules


def test_filtering_actions_heading_aligns_with_first_row_action():
    script = _read("src/webui/filtering.js")
    sync = _read("src/webui/filtering_ownership_sync.js")
    style = _read("src/webui/filtering_ownership_sync.css")

    assert "function syncFilteringActionsHeading()" in sync
    assert 'querySelector(".filtering-actions-cell button")' in sync
    assert "--filtering-actions-heading-offset" in sync
    assert "text-indent: var(--filtering-actions-heading-offset" in style
    assert 'removeProperty("--filtering-actions-heading-offset")' in sync
    assert 'addEventListener("nowlert:view-changed"' in sync


def test_workspace_refresh_only_renders_the_visible_view_and_destination_cards_keep_identity():
    app = _read("src/webui/app.js")
    destination_render = app.split("function renderDestinations()", 1)[1].split(
        "function destinationName(", 1
    )[0]
    load_workspace = app.split("async function loadWorkspace()", 1)[1].split(
        "function renderAll()", 1
    )[0]

    assert "renderCurrentView();" in load_workspace
    assert "renderAll();" not in load_workspace
    assert "function renderCurrentView(" in app
    assert "data-destination-id" in destination_render
    assert "existingCards" in destination_render
    assert "container.replaceChildren();\n  if (!state.destinations.length)" not in destination_render
    assert 'new CustomEvent("nowlert:view-changed"' in app


def test_email_rules_actions_heading_aligns_with_edit_button():
    script = _read("src/webui/email_alerts.js")
    style = _read("src/webui/email_alerts.css")

    assert 'className: "email-rule-actions-heading"' in script
    assert "function emailAlignRulesActionsHeading()" in script
    assert 'querySelector(".email-rule-actions-heading")' in script
    assert 'querySelector(".email-rule-action-edit")' in script
    assert "--email-rule-actions-heading-left" in script
    assert ".email-rule-actions-heading" in style


def test_audit_log_event_details_stretch_to_match_event_list():
    style = _read("src/webui/visual_refinement.css")
    alignment = style.split("/* Keep the detail inspector level with the full event-list panel", 1)[1]
    alignment = alignment.split("/* Put the three Audit pulses", 1)[0]

    assert "align-items: stretch !important" in alignment
    assert "align-self: stretch !important" in alignment
    assert "height: auto !important" in alignment
    assert "overflow: auto !important" in alignment
    assert "align-content: start !important" in alignment
    assert "grid-auto-rows: max-content !important" in alignment


def test_destination_assigned_integration_icons_share_title_row_and_align_right():
    app = _read("src/webui/app.js")
    route_model = _read("src/webui/destination_routes.js")
    style = _read("src/webui/operations_acceptance.css")
    destination_render = app.split("function renderDestinations()", 1)[1].split(
        "function destinationName(", 1
    )[0]
    heading = destination_render.split('className: "resource-heading"', 1)[1].split(
        "meta,", 1
    )[0]

    assert 'className: "destination-assigned-route-icons"' in destination_render
    assert "routeIcons," in heading
    assert "destinationRouteSourcesForItem(" in destination_render
    assert "state.routes || []" in destination_render
    assert "function destinationRouteSourcesForItem(" in route_model
    assert ".destination-assigned-route-icons" in style
    assert "margin-left: auto" in style
