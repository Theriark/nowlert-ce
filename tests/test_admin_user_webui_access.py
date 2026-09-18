"""WebUI regression contract for management navigation and delegated access."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SHELL = ROOT / "src" / "webui" / "source_ui_retirement.js"
FILTERING = ROOT / "src" / "webui" / "filtering.js"
API = ROOT / "src" / "api" / "filtering.py"
ACCESS = ROOT / "src" / "storage" / "destination_access.py"
BRIDGE = ROOT / "src" / "storage" / "routing_bridge.py"


def test_management_navigation_places_tools_inside_their_parent_pages():
    script = SHELL.read_text(encoding="utf-8")

    assert "SECTION_GROUPS" not in script
    assert "installSectionTabs" not in script
    assert 'document.getElementById("administration-nav")?.remove();' in script
    assert 'document.getElementById("profile-api-access")?.remove();' in script
    assert 'document.getElementById("profile-settings")?.remove();' in script
    assert 'document.querySelector("#profile-menu-button .profile-chevron")?.remove();' in script
    assert 'primaryNav("tokens")?.remove();' in script
    assert 'primaryNav("updates")?.remove();' in script

    assert "function embedAccountApiTokens()" in script
    assert 'container.id = "account-api-tokens";' in script
    assert 'accountGrid.after(container);' in script
    assert 'prepareEmbeddedToolbar(toolbar, "API tokens");' in script
    assert 'if (view === "tokens") view = "account";' in script

    assert "function embedBackupDataTools()" in script
    assert 'container.id = "backup-data-tools";' in script
    assert 'scheduleCard.after(container);' in script
    assert 'prepareEmbeddedToolbar(toolbar, "Data tools");' in script
    assert 'if (view === "data") view = "backups";' in script

    assert 'settingsNav.hidden = false;' in script
    assert 'usersNav.after(settingsNav);' in script
    assert 'settingsNav.after(updatesNav);' not in script
    assert "syncUsersAction" not in script
    assert 'document.querySelector(".topbar-actions")' not in script

    assert 'if (view === "inputs") view = "dashboard";' in script
    assert 'addDestination.hidden = false;' in script
    assert 'if (addRoute) addRoute.hidden = true;' in script
    assert 'if (auditNav) auditNav.hidden = !admin;' in script
    assert 'if (backupsNav) backupsNav.hidden = !admin;' in script
    assert 'if (usersNav) usersNav.hidden = !admin;' in script


def test_settings_embeds_updates_and_filtering_owns_deterministic_processing():
    script = SHELL.read_text(encoding="utf-8")

    assert "function embedSettingsUpdates()" in script
    assert 'container.id = "settings-updates";' in script
    assert 'prepareEmbeddedToolbar(toolbar, "Updates");' in script
    assert 'action.className = "button secondary";' in script
    assert 'action.textContent = "Check for updates";' in script
    assert 'updatesSection.setAttribute("aria-hidden", "true");' in script

    assert "function embedFilteringDeterministicProcessing()" in script
    assert 'panel.id = "filtering-deterministic-processing";' in script
    assert 'filteringTable.after(panel);' in script

    assert 'setPageCopy("Settings", "Configure regional preferences and updates.");' in script
    assert 'if (view === "updates") view = "settings";' in script
    assert 'if (state.currentView === "updates") navigate("settings", "replace");' in script


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
