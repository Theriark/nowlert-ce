"""Destination-owned route picker runtime hardening."""

from pathlib import Path

from webui.service import UI_BUILD, WebUIService


ROOT = Path(__file__).resolve().parents[1]


class Configuration:
    def get(self, *_keys, default=None):
        return default


def test_destination_route_runtime_assets_are_served_and_loaded():
    service = WebUIService(Configuration(), root=ROOT)

    page = service.response("/")
    assert page is not None and page.status == 200
    assert f'<link rel="stylesheet" href="/ui/destination_routes.css?v={UI_BUILD}">'.encode() in page.body
    assert f'<script src="/ui/destination_routes.js?v={UI_BUILD}" defer></script>'.encode() in page.body

    stylesheet = service.response("/ui/destination_routes.css")
    assert stylesheet is not None and stylesheet.status == 200
    assert stylesheet.content_type == "text/css; charset=utf-8"
    assert stylesheet.cache_control == "no-cache"

    script = service.response("/ui/destination_routes.js")
    assert script is not None and script.status == 200
    assert script.content_type == "text/javascript; charset=utf-8"
    assert script.cache_control == "no-cache"


def test_destination_route_picker_styles_are_external_and_scrollable():
    stylesheet = (ROOT / "src" / "webui" / "destination_routes.css").read_text(
        encoding="utf-8"
    )
    script = (ROOT / "src" / "webui" / "destination_routes.js").read_text(
        encoding="utf-8"
    )

    assert ".route-assignment-toggle" in stylesheet
    assert "max-height: 19rem" in stylesheet
    assert "overflow: auto" in stylesheet
    assert "grid-template-columns: auto minmax(0, 1fr) auto" in stylesheet
    assert "width: auto" in stylesheet
    assert "height: auto" in stylesheet
    assert (
        "routeAssignmentInstallStyles = function routeAssignmentUseExternalStyles() {};"
        in script
    )


def test_destination_route_picker_uses_stable_dom_anchor_and_idempotent_binding():
    source = (ROOT / "src" / "webui" / "destination_routes.js").read_text(
        encoding="utf-8"
    )

    assert 'byId("destination-secrets")' in source
    assert '.closest("fieldset")' in source
    assert 'fieldset.id = "destination-routes-fieldset"' in source
    assert 'picker.id = "destination-routes"' in source
    assert 'attributes: { id: "destination-routes-select-all" }' in source
    assert 'attributes: { id: "destination-routes-clear" }' in source
    assert 'picker.dataset.routeAssignmentBound' in source
    assert 'textContent.trim() === "Write-only credentials"' not in source


def test_route_assignment_submit_uses_current_destination_and_route_handlers():
    source = (ROOT / "src" / "webui" / "destination_routes.js").read_text(
        encoding="utf-8"
    )

    assert "event.stopImmediatePropagation();" in source
    assert '"destination-form",\n      (event) => saveDestination(event),' in source
    assert '"route-form",\n      (event) => saveRoute(event),' in source
    assert 'form.dataset.routeAssignmentSubmitBound = "true"' in source
    assert "      true,\n    );" in source
