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


def test_filtering_actions_heading_aligns_with_first_row_action():
    style = _read("src/webui/filtering_ownership_sync.css")

    assert ".filtering-table th:last-child" in style
    assert "text-indent: clamp(0rem, calc(100% - 14rem), 25rem)" in style


def test_email_rules_actions_heading_aligns_with_edit_button():
    style = _read("src/webui/email_alerts.css")

    assert "#view-email-alerts#view-email-alerts .email-rules-table th:last-child" in style
    assert "text-indent: clamp(3.25rem, calc(100% - 21rem), 13.5rem)" in style


def test_audit_log_event_details_stretch_to_match_event_list():
    style = _read("src/webui/visual_refinement.css")
    alignment = style.split("/* Keep the detail inspector level with the full event-list panel", 1)[1]
    alignment = alignment.split("/* Put the three Audit pulses", 1)[0]

    assert "align-items: stretch !important" in alignment
    assert "align-self: stretch !important" in alignment
    assert "height: auto !important" in alignment
    assert "overflow: auto !important" in alignment
