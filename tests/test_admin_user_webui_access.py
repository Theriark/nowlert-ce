"""WebUI regression contract for management navigation and delegated access."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SHELL = ROOT / "src" / "webui" / "source_ui_retirement.js"
FILTERING = ROOT / "src" / "webui" / "filtering.js"
API = ROOT / "src" / "api" / "filtering.py"
ACCESS = ROOT / "src" / "storage" / "destination_access.py"
BRIDGE = ROOT / "src" / "storage" / "routing_bridge.py"


def test_management_navigation_is_regrouped():
    script = SHELL.read_text(encoding="utf-8")

    assert 'account: {' in script
    assert 'tabs: [["account", "Security"], ["tokens", "API access"]]' in script
    assert 'settings: {' in script
    assert 'tabs: [["settings", "Settings"], ["updates", "Updates"]]' in script
    assert 'backups: {' in script
    assert 'tabs: [["backups", "Backups"], ["data", "Data tools"]]' in script
    assert 'document.getElementById("administration-nav")?.remove();' in script
    assert 'document.getElementById("profile-api-access")?.remove();' in script
    assert 'makeButton("Settings", "profile-menu-item")' in script
    assert 'document.querySelector("#profile-menu-button .profile-chevron")?.remove();' in script
    assert 'primaryNav("tokens")?.remove();' in script
    assert 'backupsNav.after(usersNav);' in script
    assert 'button.dataset.sectionTab = target;' in script
    assert 'if (view === "inputs") view = "dashboard";' in script
    assert 'addDestination.hidden = false;' in script
    assert 'if (addRoute) addRoute.hidden = true;' in script
    assert 'if (auditNav) auditNav.hidden = !admin;' in script
    assert 'if (backupsNav) backupsNav.hidden = !admin;' in script
    assert 'if (usersNav) usersNav.hidden = !admin;' in script


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
