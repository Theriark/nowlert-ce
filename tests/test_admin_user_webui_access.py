"""WebUI regression contract for the Administration and delegated-access redesign."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SHELL = ROOT / "src" / "webui" / "source_ui_retirement.js"
FILTERING = ROOT / "src" / "webui" / "filtering.js"
API = ROOT / "src" / "api" / "filtering.py"
ACCESS = ROOT / "src" / "storage" / "destination_access.py"
BRIDGE = ROOT / "src" / "storage" / "routing_bridge.py"


def test_administration_and_profile_navigation_are_reorganized():
    script = SHELL.read_text(encoding="utf-8")

    assert 'label.textContent = "Administration";' in script
    assert 'const ADMIN_CHILD_VIEWS = new Set(["users", "updates", "data"]);' in script
    assert 'apiAccess.textContent' not in script
    assert 'makeButton("API access", "profile-menu-item")' in script
    assert 'makeButton("Settings", "profile-menu-item")' in script
    assert 'document.querySelector("#profile-menu-button .profile-chevron")?.remove();' in script
    assert 'const tokensNav = primaryNav("tokens");' in script
    assert 'if (tokensNav) tokensNav.remove();' in script
    assert 'if (view === "inputs") view = "dashboard";' in script
    assert 'addDestination.hidden = false;' in script
    assert 'if (addRoute) addRoute.hidden = true;' in script
    assert 'if (auditNav) auditNav.hidden = !admin;' in script
    assert 'if (backupsNav) backupsNav.hidden = !admin;' in script


def test_delegated_destination_access_has_separate_edit_and_filter_permissions():
    shell = SHELL.read_text(encoding="utf-8")
    filtering = FILTERING.read_text(encoding="utf-8")
    api = API.read_text(encoding="utf-8")
    access = ACCESS.read_text(encoding="utf-8")

    for token in ("can_edit_destination", "can_manage_filters"):
        assert token in shell
        assert token in api
        assert token in access
    assert "destination-permissions" in shell
    assert "destination-permissions" in api
    assert 'badge("Read only", "warning")' in shell
    assert "Private names, configuration, credentials, routing, filters and delivery contents are hidden from administrators." in shell
    assert "decorateFiltering" not in shell
    assert "elevateFilteringUntilDialogCloses" not in shell
    assert 'state.user.role = "admin"' not in shell
    assert "policyCanManage" in filtering
    assert "currentDestinationCanManage" in filtering


def test_system_routes_and_private_destination_runtime_are_explicit():
    access = ACCESS.read_text(encoding="utf-8")
    bridge = BRIDGE.read_text(encoding="utf-8")

    assert "class SystemRoutingRouteStore" in access
    assert "enabled=True" in access
    assert "class AccessControlledRouteDestinationStore" in access
    assert "SELECT DISTINCT destinations.owner_user_id" in bridge
    assert "destinations.enabled = 1" in bridge
    assert "routes.enabled = 1" not in bridge
