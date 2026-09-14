"""Destination-owned route picker runtime hardening."""

from pathlib import Path

from webui.service import WebUIService


ROOT = Path(__file__).resolve().parents[1]


class Configuration:
    def get(self, *_keys, default=None):
        return default


def test_destination_route_runtime_asset_is_served_and_loaded():
    service = WebUIService(Configuration(), root=ROOT)

    page = service.response("/")
    assert page is not None and page.status == 200
    assert b'<script src="/ui/destination_routes.js" defer></script>' in page.body

    script = service.response("/ui/destination_routes.js")
    assert script is not None and script.status == 200
    assert script.content_type == "text/javascript; charset=utf-8"
    assert script.cache_control == "no-cache"


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
