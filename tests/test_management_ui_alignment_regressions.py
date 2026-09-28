"""Regression coverage for management-page controls and panel alignment."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_destination_editor_uses_the_list_badge_states_and_icons():
    script = _read("src/webui/destination_editor_fix.js")
    routes = _read("src/webui/destination_routes.js")
    style = _read("src/webui/destination_editor_fix.css")

    assert 'status.className = "button small destination-provider-status"' in routes
    assert 'status.classList.toggle("is-active", enabled.checked)' in routes
    assert 'status.classList.toggle("is-disabled", !enabled.checked)' in routes
    assert 'destination-provider-sharing is-${shared ? "shared" : "private"}' in script
    assert 'status.replaceChildren(' in routes
    assert 'status.replaceChildren(icon, label)' in script
    assert ".destination-provider-sharing.is-shared" in style
    assert ".destination-provider-sharing.is-private" in style
    assert ".destination-provider-status.is-active" in style
    assert ".destination-provider-status.is-disabled" in style
    assert ".button.destination-provider-sharing," in style
    assert "border-radius: 999px" in style
    assert "font-size: 0.58rem" in style
    assert "min-height: 0" in style
    assert "padding: 3px 6px" in style


def test_filtering_actions_heading_aligns_with_first_row_action():
    script = _read("src/webui/filtering.js")
    sync = _read("src/webui/filtering_ownership_sync.js")
    style = _read("src/webui/filtering_ownership_sync.css")

    assert "function syncFilteringActionsHeading()" in sync
    assert 'querySelector(".filtering-actions-cell button")' in sync
    assert "--filtering-actions-heading-offset" in sync
    assert "text-indent: var(--filtering-actions-heading-offset" in style


def test_email_rules_actions_heading_aligns_with_edit_button():
    script = _read("src/webui/email_alerts.js")
    style = _read("src/webui/email_alerts.css")

    assert 'className: "email-rule-actions-heading"' in script
    assert "function emailAlignRulesActionsHeading()" in script
    assert 'querySelector(".email-rule-actions-heading")' in script
    assert 'querySelector(".email-rule-action-edit")' in script
    assert "--email-rule-actions-heading-left" in script
    assert ".email-rule-actions-heading" in style


def test_audit_log_event_details_stretch_to_match_event_list():
    style = _read("src/webui/visual_refinement.css")
    alignment = style.split("/* Keep the detail inspector level with the full event-list panel", 1)[1]
    alignment = alignment.split("/* Put the three Audit pulses", 1)[0]

    assert "align-items: stretch !important" in alignment
    assert "align-self: stretch !important" in alignment
    assert "height: auto !important" in alignment
    assert "overflow: auto !important" in alignment
    assert "align-content: start !important" in alignment
    assert "grid-auto-rows: max-content !important" in alignment
