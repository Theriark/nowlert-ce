from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "src" / "webui" / "destination_routes.js"
STYLE = ROOT / "src" / "webui" / "destination_routes.css"


def test_destination_editor_builds_provider_routing_and_credentials_sections():
    source = SCRIPT.read_text(encoding="utf-8")

    assert 'id = "destination-editor-main"' in source
    assert 'id = "destination-provider-card"' in source
    assert 'id = "destination-routing-summary"' in source
    assert 'id = "destination-credentials-heading"' in source
    assert 'text: "Manage routes"' in source
    assert '"Shared with users"' in source


def test_route_assignment_is_a_right_hand_drawer_with_search_and_done_action():
    source = SCRIPT.read_text(encoding="utf-8")
    style = STYLE.read_text(encoding="utf-8")

    assert 'className: "route-assignment-drawer"' in source
    assert 'text: "Assigned routes"' in source
    assert 'placeholder: "Search routes..."' in source
    assert 'text: "Done"' in source
    assert 'routeAssignmentOpenDrawer' in source
    assert 'routeAssignmentCloseDrawer' in source
    assert '.route-assignment-drawer' in style
    assert 'grid-template-columns: minmax(0, 1fr) minmax(300px, 360px)' in style


def test_destination_editor_supports_all_output_types_without_backend_contract_changes():
    source = SCRIPT.read_text(encoding="utf-8")

    for output_type in ("discord", "teams", "slack", "webhook", "mqtt", "ntfy"):
        assert f'{output_type}:' in source
    assert 'route_ids: [...routeAssignmentSelection]' not in source
    assert 'saveDestination(event)' in source
    assert 'byId("destination-type")' in source


def test_changing_destination_type_does_not_claim_old_credentials_are_configured():
    source = SCRIPT.read_text(encoding="utf-8")

    assert 'const originalType = byId("destination-original-type")?.value || "";' in source
    assert 'const typeChanged = Boolean(item && originalType && originalType !== type);' in source
    assert 'item && item.secret_configured && !typeChanged' in source
