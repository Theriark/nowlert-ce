from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_destination_layout_uses_external_styles_under_the_strict_csp():
    cleanup = read("src/webui/acceptance_cleanup.js")
    destination_css = read("src/webui/destination_overview_acceptance.css")
    route_picker = read("src/webui/destination_routes.js")
    dashboard = read("src/webui/dashboard.js")
    route_css = read("src/webui/destination_routes.css")
    service = read("src/webui/service.py")

    assert "document.createElement(\"style\")" not in cleanup
    assert "document.head.append(style)" not in cleanup
    assert 'document.createElement("style")' not in route_picker
    assert 'document.createElement("style")' not in dashboard
    assert ".destination-route-more-menu" in route_css
    assert ".route-assignment-picker" in route_css
    assert "#view-destinations #destination-list" in destination_css
    assert "#view-destinations .resource-identity strong" in destination_css
    assert "style-src 'self'" in service
    assert "unsafe-inline" not in service
    assert 'UI_BUILD = "20260929-r57"' in service


def test_reference_title_observer_never_calls_a_missing_function():
    reference = read("src/webui/reference_acceptance.js")

    assert "function forceSecurityTitle()" in reference
    assert "requestAnimationFrame(forceSecurityTitle)" in reference


def test_filtering_actions_and_backup_tables_remain_usable_on_tablets():
    filtering = read("src/webui/filtering.css")
    filtering_sync = read("src/webui/filtering_ownership_sync.css")
    visual = read("src/webui/visual_refinement.css")
    backup = read("src/webui/qa_patch.css")

    assert "overflow-x: hidden !important" not in filtering
    assert "overflow-x: hidden !important" not in filtering_sync
    assert "min-width: 1240px !important" in visual
    assert "overflow-x: auto !important" in visual
    assert "min-width: 920px !important" in visual
    assert "overflow-x: clip;" not in backup[backup.rfind(".backup-dashboard-panel .table-scroll"):]


def test_tablet_summary_and_destination_names_can_reflow_without_clipping():
    operations = read("src/webui/operations_acceptance.css")
    destination_css = read("src/webui/destination_overview_acceptance.css")
    acceptance = read("src/webui/operations_acceptance.css")

    tablet_start = operations.index("@media (max-width: 1180px)", operations.index(".ops-config-status.is-review"))
    tablet_rules = operations[tablet_start:operations.index("@media (max-width: 900px)", tablet_start)]
    assert "grid-template-columns: repeat(2, minmax(0, 1fr)) !important" in tablet_rules
    assert "grid-column: 1 / -1" in tablet_rules
    assert "overflow-wrap: anywhere" in destination_css
    assert "@media (max-width: 1180px)" in acceptance
    destination_tablet_rules = acceptance[acceptance.rfind("@media (max-width: 1180px)"):]
    assert "flex-wrap: wrap" in destination_tablet_rules
    assert "white-space: normal" in destination_tablet_rules
    assert "flex: 1 1 100%" in destination_tablet_rules


def test_filtering_tablet_actions_scroll_and_integration_behavior_renders_on_entry():
    visual = read("src/webui/visual_refinement.css")
    policy = read("src/webui/policy_simplification.js")
    management = read("src/webui/management_consistency.js")

    tablet_rules = visual[visual.index("/* Tablet layouts: keep narrow tables scrollable"):]
    assert "#view-filtering .filtering-table-panel > .table-scroll" in tablet_rules
    assert "overflow-y: visible" in tablet_rules
    assert "scrollbar-gutter: stable" in tablet_rules
    assert "white-space: nowrap" in tablet_rules
    assert "min-width: 1240px !important" in tablet_rules
    assert 'view === "settings" || view === "filtering"' in policy
    assert "renderSimpleSettings();" in policy
    assert 'dispatchEvent(new CustomEvent("nowlert:integration-behavior-updated"' in policy
    assert 'addEventListener("nowlert:integration-behavior-updated"' in management


def test_email_group_empty_state_spans_and_centers_the_panel():
    styles = read("src/webui/email_alerts.css")

    assert ".email-groups-grid > .empty-state:not([hidden])" in styles
    assert "grid-column: 1 / -1" in styles
    assert "place-content: center" in styles


def test_generated_form_fields_receive_an_identifier_for_browser_autofill():
    app = read("src/webui/app.js")
    reference = read("src/webui/reference_acceptance.js")
    operations = read("src/webui/operations_acceptance.js")

    assert "function ensureFormFieldIdentity" in app
    assert "ensureFormFieldIdentity(item)" in app
    assert "function observeFormFieldIdentities()" in app
    assert "new MutationObserver((records)" in app
    assert "ensureFormFieldIdentity(node)" in reference
    assert "ensureFormFieldIdentity(item)" in operations


def test_users_keep_filtering_navigation_and_can_add_filters_for_managed_destinations():
    markup = read("src/webui/index.html")
    app = read("src/webui/app.js")
    filtering = read("src/webui/filtering_ownership_sync.js")

    assert 'id="filtering-nav"' in markup
    admin_only = app[app.index('!["users", "inputs", "backups", "data", "audit"]'):]
    assert '"filtering"' not in admin_only[:250]
    assert 'byId("filtering-nav").hidden = false' in app
    assert "item.can_manage_filters" in filtering
    assert "item.owned" not in filtering[filtering.index("function ownedChoices"):filtering.index("function policyFor")]
    assert "async function openOwnerPicker()" in filtering
    assert 'payload = await request("/filters")' in filtering
    assert 'add.dataset.filterSyncAction = "owner-new-filter"' in filtering
