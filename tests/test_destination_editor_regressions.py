"""Destination editor regression fixes for the compact drawer UI."""

from pathlib import Path
import subprocess

from webui.service import WebUIService


ROOT = Path(__file__).resolve().parents[1]
FIX_SCRIPT = ROOT / "src" / "webui" / "destination_editor_fix.js"
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


def test_destination_editor_fix_removes_provider_chevron_and_modal_fieldset_collisions():
    stylesheet = FIX_STYLE.read_text(encoding="utf-8")

    assert ".destination-provider-type::after" in stylesheet
    assert "content: none" in stylesheet
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


def test_destination_editor_fix_routing_summary_uses_assignment_set_and_resyncs_after_render():
    source = FIX_SCRIPT.read_text(encoding="utf-8")

    assert "function refreshRouteAssignmentSummary" in source
    assert "destinationRouteSelectedItems(routes, routeAssignmentSelection)" in source
    assert "routeAssignmentRenderOptions = function routeAssignmentRenderOptionsWithSummary" in source
    assert "refreshRouteAssignmentSummary();" in source


def test_destination_editor_fix_preserves_schema12_destination_assignment_state():
    source = FIX_SCRIPT.read_text(encoding="utf-8")

    assert "route.destination_id === destinationId" not in source
    assert "function syncRouteAssignmentSelection(destinationId)" not in source
    assert "syncRouteAssignmentSelection(destinationId);" not in source
    assert "destinationRouteSelectionForItem" in source
    assert "Array.isArray(item.route_ids)" in source
    assert "Array.isArray(route.destination_ids)" in source
    assert "routeAssignmentSelection = destinationRouteSelectionForItem" in source
    assert "routeAssignmentRenderOptions();" in source


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


def test_destination_editor_fix_summary_behavior_runs_in_javascript():
    program = r'''
const assert = require("node:assert/strict");
const helpers = require("./src/webui/destination_editor_fix.js");
assert.equal(helpers.destinationRouteSummaryLabel(0, 17), "No routes assigned");
assert.equal(helpers.destinationRouteSummaryLabel(1, 17), "1 route assigned");
assert.equal(helpers.destinationRouteSummaryLabel(15, 17), "15 routes assigned");
assert.equal(helpers.destinationRouteSummaryLabel(17, 17), "All routes assigned");
const routes = [{id:"a"}, {id:"b"}, {id:"c"}, {id:"d"}];
const selected = helpers.destinationRouteSelectedItems(routes, new Set(["a", "c", "d"]));
assert.deepEqual(selected.map((item) => item.id), ["a", "c", "d"]);
assert.deepEqual(helpers.destinationRouteVisibleItems(selected, 2), {
  visible: [routes[0], routes[2]], remainder: 1,
});
const synced = helpers.destinationRouteSelectionForItem(
  {id:"destination-1", route_ids:["a"]},
  [
    {id:"a", destination_ids:[]},
    {id:"b", destination_ids:["destination-1"]},
    {id:"c", destination_ids:["destination-2"]},
  ],
);
assert.deepEqual([...synced], ["a", "b"]);
'''
    result = subprocess.run(
        ["node", "-e", program],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_destination_editor_fix_summary_shows_only_selected_clickable_pills():
    source = FIX_SCRIPT.read_text(encoding="utf-8")
    stylesheet = FIX_STYLE.read_text(encoding="utf-8")

    assert 'pills.id = "destination-route-summary-pills"' in source
    assert 'button.className = "destination-route-pill"' in source
    assert "routeAssignmentSelection.delete(route.id)" in source
    assert "ROUTE_SUMMARY_VISIBLE_PILLS = 3" in source
    assert 'remainder.textContent = `+${compact.remainder} more`' in source
    assert ".destination-route-summary-pills" in stylesheet
    assert ".destination-route-pill-status.enabled" in stylesheet
    assert ".destination-route-pill-more" in stylesheet


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
        ".route-assignment-option:focus-within",
    ):
        assert selector in focus_block
    assert "border-color: rgba(244, 197, 66, 0.58)" in focus_block
    assert "box-shadow: 0 0 0 3px rgba(244, 197, 66, 0.08)" in focus_block


def test_destination_editor_fix_clamps_route_icons_inside_two_column_rows():
    stylesheet = FIX_STYLE.read_text(encoding="utf-8")

    assert "grid-template-columns: auto minmax(0, 1fr);" in stylesheet
    assert ".route-assignment-option-state" in stylesheet
    assert "overflow: hidden" in stylesheet
    assert "max-height: 18px !important" in stylesheet
    assert "max-width: 22px !important" in stylesheet
