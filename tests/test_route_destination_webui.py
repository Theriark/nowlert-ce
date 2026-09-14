"""Static WebUI contract for independent Routes and Destination assignments."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "src" / "webui" / "dashboard.js"
API = ROOT / "src" / "api" / "filtering.py"


def test_destination_editor_owns_route_assignment_ui():
    source = DASHBOARD.read_text(encoding="utf-8")

    assert 'fieldset.id = "destination-routes-fieldset"' in source
    assert 'picker.id = "destination-routes"' in source
    assert 'id: "destination-route-search"' in source
    assert 'action: "destination-routes-select-all"' in source
    assert 'action: "destination-routes-clear"' in source
    assert 'route_ids: [...routeAssignmentSelection]' in source
    assert 'text: "No routes selected"' in source or 'return "No routes selected"' in source


def test_routes_ui_is_traffic_definition_only():
    source = DASHBOARD.read_text(encoding="utf-8")

    assert 'destinationSelect.disabled = true' in source
    assert 'label.hidden = true' in source
    assert '"Optional route filters"' in source
    assert 'fieldset.hidden = true' in source
    assert 'text: "Used by"' in source
    assert '"Unassigned"' in source
    assert 'destination_id:' not in source[source.index("saveRoute = async function saveIndependentRoute"):source.index("renderFlow = function renderAssignmentFlow")]
    assert 'Define which integration and input traffic qualifies for delivery.' in source


def test_dashboard_flow_expands_route_destination_ids():
    source = DASHBOARD.read_text(encoding="utf-8")

    assert 'for (const destinationId of (route.destination_ids || []))' in source
    assert '(candidate.destination_ids || []).includes(id)' in source


def test_api_exposes_many_to_many_assignment_metadata():
    source = API.read_text(encoding="utf-8")

    assert 'data["route_ids"]' in source
    assert 'data["destination_ids"]' in source
    assert 'data["destination_count"]' in source
    assert 'data.pop("destination_id", None)' in source
