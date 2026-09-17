from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = ROOT / "src/webui/reference_acceptance.js"
CSS = ROOT / "src/webui/reference_acceptance.css"
SERVICE = ROOT / "src/webui/service.py"
PLATFORM_API = ROOT / "src/api/platform.py"
OUTPUT_SERVICE = ROOT / "src/outputs/service.py"
ENHANCEMENTS = ROOT / "src/webui/enhancements.js"
COMPOSE = ROOT / "compose.managed-backups.yaml"


def test_reference_acceptance_assets_are_registered_and_loaded_after_consistency_layer():
    service = SERVICE.read_text(encoding="utf-8")

    assert '"/ui/reference_acceptance.js"' in service
    assert '"src/webui/reference_acceptance.js"' in service
    assert '"/ui/reference_acceptance.css"' in service
    assert '"src/webui/reference_acceptance.css"' in service
    assert '<link rel="stylesheet" href="/ui/reference_acceptance.css">' in service
    assert '<script src="/ui/reference_acceptance.js" defer></script>' in service
    assert service.rfind("reference_acceptance.css") > service.rfind("management_consistency.css")
    assert service.rfind("reference_acceptance.js") > service.rfind("management_consistency.js")


def test_reference_acceptance_runtime_contract():
    script = JS.read_text(encoding="utf-8")

    assert "function ensurePreviewReferenceLayout()" in script
    assert "function openPreviewRoutes()" in script
    assert '"Assigned routes"' in script
    assert 'placeholder = "Search assigned routes..."' in script
    assert "function ensureUsersReferenceLayout()" in script
    assert "Recent activity" in script
    assert '"Never logged in"' in script
    assert "function ensureSettingsReferenceLayout()" in script
    assert "Regional settings" in script
    assert "Nowlert is up to date" in script
    assert "function ensureAccountReferenceLayout()" in script
    assert "Profile & access" in script
    assert "Password & sessions" in script
    assert "Security posture" in script
    assert 'title.textContent = "API tokens"' in script
    assert 'restart.textContent = "⏻ Restart Nowlert"' in script


def test_reference_acceptance_styles_contract():
    styles = CSS.read_text(encoding="utf-8")

    assert "#view-filtering .filtering-overview-header::after" in styles
    assert "content: none !important;" in styles
    assert '.qa-pagination-row[data-qa-pager="delivery-pagination"]' in styles
    assert '.qa-pagination-row[data-qa-pager="audit-pagination"]' in styles
    assert "grid-template-columns: minmax(145px, .8fr) minmax(330px, 1.7fr) minmax(120px, .62fr) minmax(112px, .58fr)" in styles
    assert ".reference-preview-form" in styles
    assert ".reference-preview-routing" in styles
    assert ".reference-preview-routes-open" in styles
    assert ".reference-users-metrics" in styles
    assert ".reference-settings-grid" in styles
    assert ".reference-account-grid" in styles
    assert "#restart-header-button.reference-account-restart" in styles


def test_managed_backup_override_targets_production_service_name():
    text = COMPOSE.read_text(encoding="utf-8")

    assert "  nowlert-ce:" in text
    assert "\n  nowlert:\n" not in text
    assert 'user: "0:0"' in text
    assert "- DAC_OVERRIDE" in text
    assert "- FOWNER" in text
    assert "- SYS_ADMIN" in text

def test_preview_dialog_matches_editor_shell_and_routes_are_temporary_scenario_choices():
    script = JS.read_text(encoding="utf-8")
    styles = CSS.read_text(encoding="utf-8")

    route_start = script.index("function renderPreviewRouteOptions()")
    route_end = script.index("function closePreviewRoutes()", route_start)
    route_block = script[route_start:route_end]
    drawer_start = script.index("function ensurePreviewDrawer(form)")
    drawer_end = script.index("function ensurePreviewReferenceLayout()", drawer_start)
    drawer_block = script[drawer_start:drawer_end]

    assert "let previewAssignedRouteIds = new Set();" in script
    assert "const assigned = assignedPreviewRoutes();" in route_block
    assert "const visible = assigned.filter" in route_block
    assert 'check.type = "checkbox"' in route_block
    assert "previewRouteSelection.add(route.id)" in route_block
    assert "previewRouteSelection.delete(route.id)" in route_block
    assert '"Select all"' in drawer_block
    assert '"Clear"' in drawer_block
    assert "new Set(previewAssignedRouteIds)" in drawer_block
    assert 'route-assignment-drawer reference-preview-route-drawer' in drawer_block
    assert 'route-assignment-option reference-preview-route-option' in route_block
    assert 'max-width: min(1020px, calc(100vw - 32px)) !important;' in styles
    assert 'min-width: min(610px, calc(100vw - 32px));' in styles
    assert 'width: 360px;' in styles
    assert 'max-width: min(1500px,96vw)' not in styles
    assert 'width: min(510px,42vw)' not in styles


def test_preview_open_resyncs_and_does_not_duplicate_message_counter():
    script = JS.read_text(encoding="utf-8")

    assert 'requestAnimationFrame(syncPreviewReference)' in script
    assert "MutationObserver" in script
    assert 'attributeFilter: ["open"]' in script
    assert 'ref("div", "reference-preview-message-count"' not in script



def test_preview_scenario_uses_integration_severities_and_temporary_style_override():
    script = JS.read_text(encoding="utf-8")
    api = PLATFORM_API.read_text(encoding="utf-8")
    output_service = OUTPUT_SERVICE.read_text(encoding="utf-8")

    assert "function previewSeverityValues(route)" in script
    assert 'routeFilterValuesForSource(route.source, "severities")' in script
    assert "function refreshPreviewSeverityOptions()" in script
    assert "function previewRouteSupportsSeverity(route, severity)" in script
    assert "function runReferencePreview(event)" in script
    assert 'form.removeEventListener("submit", runPreview)' in script
    assert 'body.message_style = messageStyle' in script
    assert "No selected route supports this severity." in script
    assert 'data = self._object(payload, {"event", "message_style"})' in api
    assert "message_style=message_style" in api
    assert "def _with_message_style(" in output_service
    assert 'settings["components_v2"] = style == "modern"' in output_service
    assert 'settings["message_style"] = style' in output_service


def test_preview_compacts_editable_fields_and_renders_only_applicable_outputs():
    script = JS.read_text(encoding="utf-8")
    styles = CSS.read_text(encoding="utf-8")
    enhancements = ENHANCEMENTS.read_text(encoding="utf-8")

    assert '"reference-preview-name"' not in script
    assert '"reference-preview-channel"' not in script
    assert 'textContent = `Preview ${destination.name}`' in script
    assert "window.nowlertSourceTestSample = sourceTestSample;" in enhancements
    assert 'previewScenarioEvent(route, severity, destination)' in script
    assert 'String(byId("preview-message")?.value || "").trim()' in script
    assert '"selected_routes"' not in script
    assert '"skipped_routes"' not in script
    assert 'action === "preview"' in script
    assert '{ preview: output }' in script
    assert '{ result: output }' in script
    assert "reference-preview-route-more-toggle" in script
    assert "reference-preview-route-more-menu" in script
    assert ".reference-preview-route-more-menu" in styles
