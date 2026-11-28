"""WebUI corrections from the v27.0.0 readiness check."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def block(source, start, end):
    first = source.index(start)
    return source[first:source.index(end, first)]


def test_users_get_read_only_regional_settings_without_a_save_button():
    script = read("src/webui/source_ui_retirement.js")
    access = block(script, "function syncRegionalSettingsAccess(admin)", "function syncPageOwnership(")

    assert 'document.getElementById("preferences-form")' in access
    assert 'form.querySelectorAll("select, input")) control.disabled = !admin;' in access
    assert "actions.hidden = !admin;" in access
    assert "Only an administrator can change the regional settings." in access
    assert "syncRegionalSettingsAccess(admin);" in block(
        script, "function syncPageOwnership(", "setNavActive(backupsNav"
    )
    assert "#preferences-form [hidden]" in read("src/webui/policy_simplification.css")


def test_integration_behavior_edit_is_offered_only_to_administrators():
    policy = read("src/webui/policy_simplification.js")
    card = block(policy, "function settingCard(source)", "function renderSimpleSettings()")
    app = read("src/webui/app.js")
    legacy = block(app, "function renderIntegrationSettings()", "function integrationSettingSummary(")

    for source in (card, legacy):
        assert "isAdmin()" in source
        assert 'actionButton("Edit", "edit-integration-settings", source)' in source
        assert "Only an administrator can change this." in source


def test_destination_test_button_is_limited_to_owner_or_administrator():
    app = read("src/webui/app.js")
    render = block(app, "function renderDestinations()", "function destinationName(")

    assert "const canTest = editable || isAdmin();" in render
    assert "isAdmin() || item.shared" not in render


def test_wrong_current_password_is_reported_on_the_field():
    app = read("src/webui/app.js")
    change = block(app, "async function changePassword(event)", "async function logout()")

    assert 'error.code === "password_invalid"' in change
    assert "currentField.setCustomValidity(message);" in change
    assert "currentField.reportValidity();" in change
    assert 'currentField.setCustomValidity("")' in change


def test_preview_explains_a_destination_without_routes_inside_the_dialog():
    script = read("src/webui/reference_acceptance.js")
    run = block(script, "async function runReferencePreview(event)", "const destinationId = destination.id;")

    assert "This destination has no routes yet, so there is nothing to preview." in run
    assert 'showValidationError("preview-error", message)' in run
    assert '"No routes are assigned to this destination"' in script


def test_backup_last_test_ignores_a_time_without_an_outcome():
    app = read("src/webui/app.js")
    last_test = block(app, "function backupTargetLastTest(item)", "function badge(")

    assert "if (!item.last_test_at || !item.last_test_outcome) {" in last_test
