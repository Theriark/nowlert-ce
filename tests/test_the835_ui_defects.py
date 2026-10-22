"""Regression coverage for the Development walk UI defects N1, F1, N2 and N4.

THE-835: the Preview dialog's assigned-routes drawer (invisible Done button and
the Active badge wrapping under the integration icon), the Modern card header
badge that said Information while the strip said Severity: Debug, the Users
list that stayed stale until the whole workspace reload finished, and the
Email Alerts rules table that only scrolled sideways at 768 and 390 px.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from formatters.discord_common import DiscordCardFormatter
from formatters.discord_generic import GenericDiscordFormatter
from models import Notification


ROOT = Path(__file__).resolve().parents[1]
WEBUI = ROOT / "src" / "webui"


def _read(name: str) -> str:
    return (WEBUI / name).read_text(encoding="utf-8")


def _text_content(payload: dict) -> str:
    values = []

    def visit(component):
        if isinstance(component, dict):
            if component.get("type") == 10:
                values.append(component["content"])
            for value in component.values():
                visit(value)
        elif isinstance(component, list):
            for value in component:
                visit(value)

    visit(payload["components"])
    return "\n".join(values)


def _generic_notification(severity: str, status: str = "") -> Notification:
    item = Notification(
        source="nowlert",
        title="Nowlert test alert",
        body="This is a safe sample event generated in the WebUI.",
        category="generic",
        status=status,
        start_time="2026-10-22T19:00:00+00:00",
    )
    item.metadata = {"provider": "Nowlert", "severity": severity}
    return item


# F1: Modern card header badge versus the Severity metric.


def test_modern_header_shows_the_real_severity_when_the_bucket_is_only_informational():
    payload = GenericDiscordFormatter().format_components_v2(
        _generic_notification("debug")
    )
    rendered = _text_content(payload)

    assert "ℹ️ **Debug** •" in rendered
    assert "ℹ️ **Severity:** Debug" in rendered
    assert "**Information**" not in rendered


def test_modern_header_keeps_information_for_information_synonyms():
    for severity in ("information", "info", "Informational"):
        rendered = _text_content(
            GenericDiscordFormatter().format_components_v2(
                _generic_notification(severity)
            )
        )
        assert "ℹ️ **Information** •" in rendered, severity


def test_modern_header_keeps_bucketed_states_for_resolved_critical_and_warning():
    recovered = _text_content(
        GenericDiscordFormatter().format_components_v2(
            _generic_notification("Ok", status="resolved")
        )
    )
    assert "✅ **Resolved** •" in recovered
    assert "✅ **Severity:** Ok" in recovered

    failed = _text_content(
        GenericDiscordFormatter().format_components_v2(
            _generic_notification("error")
        )
    )
    assert "🚨 **Critical** •" in failed
    assert "🚨 **Severity:** Error" in failed

    degraded = _text_content(
        GenericDiscordFormatter().format_components_v2(
            _generic_notification("caution")
        )
    )
    assert "⚠️ **Warning** •" in degraded
    assert "⚠️ **Severity:** Caution" in degraded


def test_header_state_helper_contract():
    helper = DiscordCardFormatter._discord_header_state

    assert helper("Resolved", "ok") == "Resolved"
    assert helper("Critical", "error") == "Critical"
    assert helper("Information", "") == "Information"
    assert helper("Information", None) == "Information"
    assert helper("Information", "info") == "Information"
    assert helper("Information", "debug") == "Debug"
    assert helper("Information", "not_classified") == "Not Classified"


# N1: Preview dialog assigned-routes drawer.


def test_preview_dialog_defines_the_accent_used_by_the_routes_drawer_done_button():
    css = _read("destination_routes.css")
    start = css.index("#preview-dialog.reference-preview-dialog {")
    block = css[start:css.index("}", start)]

    assert "--destination-accent: var(--accent, #f4c542);" in block
    assert "--destination-accent-strong: var(--accent-strong, #d9a629);" in block
    # The Done button keeps painting from those variables.
    assert ".route-assignment-footer .button.primary {" in css
    assert "var(--destination-accent), var(--destination-accent-strong)" in css


def test_route_rows_with_a_state_badge_get_a_third_grid_column():
    css = _read("destination_routes.css")

    assert (
        ".route-assignment-option:has(> .route-assignment-option-state) {\n"
        "  grid-template-columns: auto minmax(0, 1fr) auto;\n"
        "}"
    ) in css
    assert ".route-assignment-option > .route-assignment-option-state {" in css
    # Rows without a badge keep the two-column clamp of destination_editor_fix.css.
    assert "grid-template-columns: auto minmax(0, 1fr);" in _read(
        "destination_editor_fix.css"
    )


# N2: Users list refresh.


def test_user_api_results_update_the_local_user_list_before_the_workspace_reload():
    script = _read("management_consistency.js")

    assert "function applyUserRecord(user)" in script
    assert "function removeUserRecord(id)" in script
    assert "request = async function requestWithUserRecordSync(path, options = {})" in script
    assert 'if (path === "/users" && method === "POST") applyUserRecord(response?.user);' in script
    assert 'else if (userId && method === "PATCH") applyUserRecord(response?.user);' in script
    assert 'else if (userId && method === "DELETE") removeUserRecord(userId);' in script
    # app.js keeps its own flow: the workspace reload still reconciles afterwards.
    app = _read("app.js")
    save = app[app.index("async function saveUser(event)"):app.index("function openPreview(id)")]
    assert "await loadWorkspace();" in save


def test_user_record_sync_renders_the_users_view_immediately():
    script = _read("management_consistency.js")
    helpers = script[script.index("  function applyUserRecord(user)"):script.index("  installChannelCollection();")]
    program = (
        "const assert = require('node:assert');\n"
        "let renders = 0;\n"
        "function renderUsers() { renders += 1; }\n"
        "const state = { currentView: 'users', users: [{ id: 'a', username: 'alpha', enabled: true }] };\n"
        "const calls = [];\n"
        "let request = async (path, options) => { calls.push([path, options?.method || 'GET']); "
        "return options?.method === 'POST' ? { user: { id: 'b', username: 'bravo', enabled: true } } "
        ": options?.method === 'PATCH' ? { user: { id: 'a', username: 'alpha', enabled: false } } : {}; };\n"
        + helpers
        + "(async () => {\n"
        "  await request('/users', { method: 'POST', body: {} });\n"
        "  assert.deepEqual(state.users.map(item => item.id), ['a', 'b']);\n"
        "  assert.equal(renders, 1);\n"
        "  await request('/users/a', { method: 'PATCH', body: { enabled: false } });\n"
        "  assert.equal(state.users[0].enabled, false);\n"
        "  assert.equal(state.users.length, 2);\n"
        "  await request('/users/a/password', { method: 'PUT', body: {} });\n"
        "  await request('/users');\n"
        "  assert.equal(renders, 2);\n"
        "  await request('/users/a', { method: 'DELETE' });\n"
        "  assert.deepEqual(state.users.map(item => item.id), ['b']);\n"
        "  state.currentView = 'dashboard';\n"
        "  await request('/users/b', { method: 'DELETE' });\n"
        "  assert.deepEqual(state.users, []);\n"
        "  assert.equal(renders, 3);\n"
        "  assert.equal(calls.length, 6);\n"
        "})().catch((error) => { console.error(error); process.exit(1); });\n"
    )
    result = subprocess.run(
        ["node", "-e", program],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


# N4: Email Alerts rules table at narrow widths.


def test_rules_table_stacks_into_cards_below_900px():
    script = _read("email_alerts.js")
    table = script[script.index("function emailRenderRuleTable()"):script.index("function emailUpdateRuleRow(")]
    # The CSS labels follow this column order.
    assert '["RULE", "GROUP", "CLASSIFICATION", "MATCH", "CONDITIONS", "PRIORITY", "STATUS", "ACTIONS"]' in table

    css = _read("email_alerts.css")
    narrow = css[css.index("/* Rules table narrow layout"):]
    assert "@media (max-width: 900px)" in narrow
    assert "#view-email-alerts#view-email-alerts .email-table-panel .email-rules-table {\n    display: block;\n    min-width: 0;" in narrow
    assert ".email-rules-table thead {\n    display: none;" in narrow
    for index, label in ((2, "Group"), (3, "Classification"), (4, "Match"), (5, "Conditions"), (6, "Priority")):
        assert f'td:nth-child({index})::before {{ content: "{label}"; }}' in narrow
    assert "td:nth-child(1) {\n    grid-area: 1 / 1 / 2 / 2;" in narrow
    assert "td:nth-child(7) {\n    grid-area: 1 / 2 / 2 / 3;" in narrow
    assert "td:nth-child(5) {\n    grid-area: 4 / 1 / 5 / 3;" in narrow
    assert "td:nth-child(8) {\n    border-top" in narrow
    assert "grid-template-columns: repeat(3, minmax(0, 1fr));" in narrow
