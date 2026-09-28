"""Regressions from the September 2026 WebUI review."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_main_navigation_keeps_email_tab_query_on_reload():
    script = source("src/webui/app.js")
    navigation = script[script.index("function navigate(view,"):script.index("function renderDashboard()")]

    assert "const targetUrl = new URL(window.location.href);" in navigation
    assert "targetUrl.hash = targetHash;" in navigation
    assert '"", targetUrl);' in navigation


def test_groups_load_without_waiting_for_activity_and_show_pending_state():
    script = source("src/webui/email_alerts.js")
    load = script[script.index("async function emailLoad("):script.index("async function emailRefreshActivity()")]
    render = script[script.index("function emailRender()"):script.index("function emailAlignRulesActionsHeading()")]

    assert 'groups: ["groups", "rules"]' in load
    assert 'activity: ["groups", "rules", "mailboxes", "activity"]' in load
    assert 'request("/email-activity")' not in load
    assert "Loading Email Alert groups" in render


def test_disabling_rule_updates_its_row_without_replacing_page_or_losing_scroll():
    script = source("src/webui/email_alerts.js")
    start = script.index('if (action === "toggle-rule")')
    end = script.index('if (action === "delete-rule")', start)
    toggle = script[start:end]

    assert "emailUpdateRuleRow(id," in toggle
    assert "await emailLoad(true);" not in toggle
    assert 'dataset: { emailRuleId: rule.id }' in script


def test_activity_mutations_invalidate_cached_rules_and_groups():
    script = source("src/webui/email_alerts.js")
    load = script[script.index("async function emailLoad("):script.index("async function emailRefreshActivity()")]
    toggle_start = script.index('if (action === "toggle-rule")')
    toggle_end = script.index('if (action === "delete-rule")', toggle_start)
    toggle = script[toggle_start:toggle_end]

    assert "emailInvalidateOtherTabs();" in load
    assert "emailInvalidateOtherTabs();" in toggle


def test_destination_route_save_reconciles_new_destination_without_refresh():
    script = source("src/webui/dashboard.js")
    start = script.index("saveDestination = async function saveDestinationWithRoutes")
    end = script.index("function routeAssignmentInstallRouteDefinitionUi()", start)
    save = script[start:end]

    assert "state.destinations.push(nextDestination);" in save
    assert "state.routes = state.routes.map((route) =>" in save
    assert "destination_count: destinationIds.size" in save
    assert "if (savedDestination) {" in save


def test_group_fields_opt_out_of_password_manager_autofill():
    script = source("src/webui/email_alerts.js")
    group_form = script[script.index('attributes: { id: "email-group-form"'):script.index('if (!byId("email-rule-dialog"))')]

    assert 'autocomplete: "off"' in group_form


def test_email_preview_separates_security_notice_from_message_body():
    styles = source("src/webui/email_alerts.css")
    preview = styles[styles.index(".email-preview-security {"):styles.index(".email-preview-frame {")]

    assert "margin-bottom:" in preview


def test_destination_route_done_closes_picker_without_saving_destination():
    dashboard = source("src/webui/dashboard.js")
    routes = source("src/webui/destination_routes.js")
    start = dashboard.index("saveDestination = async function saveDestinationWithRoutes")
    end = dashboard.index("function routeAssignmentInstallRouteDefinitionUi()", start)
    save = dashboard[start:end]

    assert 'event.submitter?.value === "routes-done"' not in save
    assert 'type: "button"' in routes[routes.index('attributes: { id: "destination-routes-clear"'):] 
    assert "done.addEventListener(\"click\", routeAssignmentCloseDrawer);" in routes
    assert "await loadWorkspace();" not in save
    assert "route_ids: [...routeAssignmentSelection]" in save


def test_delivery_history_resolves_route_name_with_short_id_fallback():
    script = source("src/webui/destination_overview_acceptance.js")

    assert '(state.routes || []).find((candidate) => String(candidate.id) === String(item.route_id))' in script
    assert 'deliveryTag("Route", route?.name || shortId(item.route_id), "route")' in script


def test_email_tab_loading_uses_a_visible_status_instead_of_an_empty_panel():
    script = source("src/webui/email_alerts.js")
    render = script[script.index("function emailRender()"):script.index("function emailAlignRulesActionsHeading()")]

    assert 'attributes: { role: "status" }' in render
    assert "Loading Email Alert groups…" in render


def test_repeated_rate_limits_are_grouped_into_one_recoverable_workspace_message():
    script = source("src/webui/app.js")
    errors = script[script.index("function renderWorkspaceErrors()"):script.index("function applyLanguage(")]

    assert 'failure.status === 429' in errors
    assert "temporarily rate limited" in errors
    assert 'status: result.reason?.status || 0' in script
