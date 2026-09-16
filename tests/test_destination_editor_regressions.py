"""Destination editor regression fixes for the compact drawer UI."""

from pathlib import Path
import subprocess

from webui.service import WebUIService


ROOT = Path(__file__).resolve().parents[1]
FIX_SCRIPT = ROOT / "src" / "webui" / "destination_editor_fix.js"
ROUTES_SCRIPT = ROOT / "src" / "webui" / "destination_routes.js"
FIX_STYLE = ROOT / "src" / "webui" / "destination_editor_fix.css"


class Configuration:
    def get(self, *_keys, default=None):
        return default


def test_destination_editor_fix_assets_are_served_after_destination_routes():
    service = WebUIService(Configuration(), root=ROOT)

    page = service.response("/")
    assert page is not None and page.status == 200
    html = page.body.decode("utf-8")
    assert html.index('/ui/destination_routes.css') < html.index('/ui/destination_editor_fix.css')
    assert html.index('/ui/destination_routes.js') < html.index('/ui/destination_editor_fix.js')

    stylesheet = service.response("/ui/destination_editor_fix.css")
    assert stylesheet is not None and stylesheet.status == 200
    assert stylesheet.content_type == "text/css; charset=utf-8"

    script = service.response("/ui/destination_editor_fix.js")
    assert script is not None and script.status == 200
    assert script.content_type == "text/javascript; charset=utf-8"


def test_destination_editor_fix_removes_duplicate_message_style_and_duplicate_title_suffix():
    source = FIX_SCRIPT.read_text(encoding="utf-8")

    assert 'querySelectorAll(".destination-message-style")' in source
    assert "controls.slice(1)" in source
    assert 'editing ? `Edit ${name}` : "Add destination"' in source


def test_destination_editor_fix_moves_sharing_to_provider_header():
    source = FIX_SCRIPT.read_text(encoding="utf-8")
    stylesheet = FIX_STYLE.read_text(encoding="utf-8")

    assert 'sharing.id = "destination-provider-sharing"' in source
    assert 'status.textContent = sharedInput.checked ? "Shared" : "Private"' in source
    assert 'sharedInput.checked = !sharedInput.checked' in source
    assert "credentials.append(shared);" not in source
    assert ".destination-shared-native" in stylesheet


def test_destination_editor_fix_restores_amber_accent_and_dark_provider_options():
    stylesheet = FIX_STYLE.read_text(encoding="utf-8")

    assert "--destination-accent: var(--accent, #f4c542);" in stylesheet
    assert "--destination-accent-strong: var(--accent-strong, #d9a629);" in stylesheet
    assert ".destination-provider-type select option" in stylesheet
    assert "#16aef2" not in stylesheet
    assert "#0e97d6" not in stylesheet


def test_destination_editor_fix_restores_provider_selector_and_avoids_modal_fieldset_collisions():
    stylesheet = FIX_STYLE.read_text(encoding="utf-8")

    assert ".destination-provider-type::after" in stylesheet
    assert 'content: "⌄"' in stylesheet
    assert "pointer-events: none" in stylesheet
    assert "fieldset.destination-connection-card" in stylesheet
    assert "fieldset.destination-credentials-card" in stylesheet
    assert "fieldset.route-assignment-drawer" in stylesheet
    assert "grid-row: 1" in stylesheet


def test_destination_editor_fix_keeps_route_drawer_at_top_without_focus_scroll_jump():
    source = FIX_SCRIPT.read_text(encoding="utf-8")

    assert "drawerOptions.scrollTop = 0" in source
    assert "search.focus({ preventScroll: true })" in source


def test_destination_editor_fix_normalizes_route_icons_and_credentials_card():
    stylesheet = FIX_STYLE.read_text(encoding="utf-8")

    assert ".route-assignment-source-icon .source-product-icon" in stylesheet
    assert "box-sizing: border-box" in stylesheet
    assert ".destination-credentials-card .destination-section-icon" in stylesheet
    assert ".destination-credentials-card .qa-credential-state" in stylesheet
    assert "min-inline-size: 0" in stylesheet


def test_destination_editor_fix_removes_marked_helper_copy():
    stylesheet = FIX_STYLE.read_text(encoding="utf-8")

    assert ".destination-connection-card > .field-help" in stylesheet
    assert "#destination-routing-summary .destination-section-copy small" in stylesheet
    assert "#destination-route-summary-detail" in stylesheet
    assert ".destination-credentials-card .destination-section-copy small" in stylesheet
    assert "display: none !important" in stylesheet


def test_destination_editor_fix_drawer_list_fills_available_height_with_compact_rows():
    stylesheet = FIX_STYLE.read_text(encoding="utf-8")

    assert ".route-assignment-options" in stylesheet
    assert "flex: 1 1 0" in stylesheet
    assert "max-height: none" in stylesheet
    assert "align-content: start" in stylesheet
    assert "padding: 4px 6px" in stylesheet


def test_destination_editor_fix_route_icons_have_spacing_without_global_tile_padding():
    stylesheet = FIX_STYLE.read_text(encoding="utf-8")

    assert ".route-assignment-source-icon .source-product-icon" in stylesheet
    assert "padding: 0" in stylesheet
    assert "margin: 0 4px 0 2px" in stylesheet


def test_destination_editor_fix_leaves_routing_summary_state_to_destination_routes():
    fix_source = FIX_SCRIPT.read_text(encoding="utf-8")
    routes_source = ROUTES_SCRIPT.read_text(encoding="utf-8")

    for marker in (
        "function destinationRouteSummaryLabel",
        "function destinationRouteSelectedItems",
        "function destinationRouteVisibleItems",
        "function destinationRouteSelectionForItem",
        "function destinationRouteSummaryModel",
        "function routeAssignmentRefreshSummary",
        'pills.id = "destination-route-summary-pills"',
        "function routeAssignmentSummaryMoreMenu",
        'id: "destination-route-more-toggle"',
        'attributes: { id: "destination-route-more-menu", role: "menu" }',
        "for (const route of model.overflow)",
        "routeAssignmentMoreMenuOpen = !routeAssignmentMoreMenuOpen",
        "routeAssignmentSelection.delete(route.id)",
    ):
        assert marker in routes_source

    for obsolete in (
        "function destinationRouteSummaryLabel",
        "function destinationRouteSelectedItems",
        "function destinationRouteVisibleItems",
        "function destinationRouteSelectionForItem",
        "function refreshRouteAssignmentSummary",
        "routeAssignmentRenderOptionsWithSummary",
        "openDestinationWithFinalEditorPolish",
        "routeAssignmentSelection",
    ):
        assert obsolete not in fix_source
    assert "openDestinationWithVisualPolish" in fix_source


def test_destination_routes_summary_model_runs_in_javascript():
    program = r'''
const assert = require("node:assert/strict");
const helpers = require("./src/webui/destination_routes.js");

assert.equal(helpers.destinationRouteSummaryLabel(0, 4), "No routes assigned");
assert.equal(helpers.destinationRouteSummaryLabel(1, 4), "1 route assigned");
assert.equal(helpers.destinationRouteSummaryLabel(3, 4), "3 routes assigned");
assert.equal(helpers.destinationRouteSummaryLabel(4, 4), "All routes assigned");

const routes = [
  {id:"a", source:"zabbix", enabled:true, destination_ids:[]},
  {id:"b", source:"home_assistant", enabled:true, destination_ids:["destination-1"]},
  {id:"c", source:"xen_orchestra", enabled:false, destination_ids:[]},
  {id:"d", source:"grafana", enabled:true, destination_ids:[]},
  {id:"e", source:"portainer", enabled:true, destination_ids:[]},
];

const synced = helpers.destinationRouteSelectionForItem(
  {id:"destination-1", route_ids:["a", "c", "d", "e"]},
  routes,
);
assert.deepEqual([...synced], ["a", "c", "d", "e", "b"]);

const model = helpers.destinationRouteSummaryModel(routes, new Set(["a", "b", "c", "d"]), 3);
assert.equal(model.label, "4 routes assigned");
assert.deepEqual(model.selectedRoutes.map((item) => item.id), ["a", "b", "c", "d"]);
assert.deepEqual(model.visible.map((item) => item.id), ["a", "b", "c"]);
assert.deepEqual(model.overflow.map((item) => item.id), ["d"]);
assert.equal(model.remainder, 1);
assert.equal(model.showPills, true);

const all = helpers.destinationRouteSummaryModel(routes, new Set(routes.map((item) => item.id)), 3);
assert.equal(all.label, "All routes assigned");
assert.deepEqual(all.overflow.map((item) => item.id), ["d", "e"]);
assert.equal(all.showPills, false);
'''
    result = subprocess.run(
        ["node", "-e", program],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_destination_editor_fix_preserves_visual_route_row_cleanup_without_state_wrappers():
    source = FIX_SCRIPT.read_text(encoding="utf-8")

    assert "destinationPolishBound" in source
    assert "new MutationObserver(normalizeRouteOptionRows)" in source
    assert "routeAssignmentSelection" not in source
    assert "destinationRouteSelectionForItem" not in source


def test_destination_editor_fix_removes_route_secondary_copy_after_each_render():
    source = FIX_SCRIPT.read_text(encoding="utf-8")

    assert 'querySelectorAll(".route-assignment-option-copy small")' in source
    assert "secondary.remove()" in source
    assert "normalizeRouteOptionRows();" in source


def test_destination_editor_fix_centers_route_row_contents_without_label_spacing():
    stylesheet = FIX_STYLE.read_text(encoding="utf-8")

    assert ".route-assignment-option > .route-assignment-option-leading" in stylesheet
    assert ".route-assignment-option > .route-assignment-option-copy" in stylesheet
    assert "align-self: center" in stylesheet
    assert "margin-bottom: 0" in stylesheet
    assert ".route-assignment-option-leading" in stylesheet
    assert "height: 22px" in stylesheet
    assert ".route-assignment-option-copy strong" in stylesheet
    assert "min-height: 22px" in stylesheet


def test_destination_editor_fix_removes_route_status_and_routing_helper_from_dom():
    source = FIX_SCRIPT.read_text(encoding="utf-8")

    assert 'querySelectorAll(".route-assignment-option-state")' in source
    assert "status.remove()" in source
    assert 'document.getElementById("destination-routing-summary")' in source
    assert 'querySelectorAll(".destination-section-copy small")' in source
    assert "helper.remove()" in source


def test_destination_editor_fix_route_search_focus_halo_is_not_clipped():
    stylesheet = FIX_STYLE.read_text(encoding="utf-8")

    assert ".route-assignment-popover" in stylesheet
    assert "overflow: visible" in stylesheet


def test_destination_editor_fix_custom_boxes_show_amber_halo_on_hover_and_focus():
    stylesheet = FIX_STYLE.read_text(encoding="utf-8")

    hover_start = stylesheet.index(
        ".destination-editor-dialog .destination-provider-card:hover"
    )
    focus_start = stylesheet.index(
        ".destination-editor-dialog .destination-provider-card:focus-within"
    )
    hover_block = stylesheet[hover_start:focus_start]

    for selector in (
        ".destination-provider-card:hover",
        ".destination-routing-summary:hover",
        "fieldset.destination-credentials-card:hover",
        ".route-assignment-option:hover",
    ):
        assert selector in hover_block
    assert "border-color: rgba(244, 197, 66, 0.58)" in hover_block
    assert "box-shadow: 0 0 0 3px rgba(244, 197, 66, 0.08)" in hover_block

    focus_block = stylesheet[focus_start:]
    for selector in (
        ".destination-provider-card:focus-within",
        ".destination-routing-summary:focus-within",
        "fieldset.destination-credentials-card:focus-within",
    ):
        assert selector in focus_block
    assert ".route-assignment-option:focus-within" not in focus_block
    assert "border-color: rgba(244, 197, 66, 0.58)" in focus_block
    assert "box-shadow: 0 0 0 3px rgba(244, 197, 66, 0.08)" in focus_block


def test_destination_editor_fix_clamps_route_icons_inside_two_column_rows():
    stylesheet = FIX_STYLE.read_text(encoding="utf-8")

    assert "grid-template-columns: auto minmax(0, 1fr);" in stylesheet
    assert ".route-assignment-option-state" in stylesheet
    assert "overflow: hidden" in stylesheet
    assert "max-height: 18px !important" in stylesheet
    assert "max-width: 22px !important" in stylesheet
