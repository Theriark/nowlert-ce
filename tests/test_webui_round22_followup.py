from pathlib import Path

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]


def _read(relative):
    return (ROOT / relative).read_text(encoding="utf-8")


def test_round22_scheduled_backup_save_is_compact_heading_action():
    markup = _read("src/webui/index.html")
    soup = BeautifulSoup(markup, "html.parser")
    panel = soup.find(id="backup-schedule-panel")
    assert panel is not None

    heading = panel.find("div", class_="panel-heading", recursive=False)
    assert heading is not None
    button = heading.find(
        "button",
        attrs={"type": "submit", "form": "backup-settings-form"},
    )
    assert button is not None
    assert button.get_text(" ", strip=True) == "Save"

    form = panel.find(id="backup-settings-form")
    assert form is not None
    assert "Save backup settings" not in form.get_text(" ", strip=True)


def test_round22_profile_returns_to_left_column_with_password_sessions_on_right():
    script = _read("src/webui/reference_acceptance.js")
    style = _read("src/webui/reference_acceptance.css")

    assert 'identity.replaceChildren(heading, body, status, meta);' in script
    assert 'const top = ref("div", "reference-profile-top")' not in script

    marker = "/* 2026-09-18 round-22 compact Profile two-column layout. */"
    assert marker in style
    final = style[style.index(marker):]
    assert "grid-template-columns: minmax(360px, 0.88fr) minmax(520px, 1.12fr) !important;" in final
    assert ".reference-profile-card {" in final
    assert ".reference-password-card {" in final
    assert "grid-template-columns: minmax(0, 1fr) !important;" not in final.split("@media", 1)[0]


def test_round22_mfa_action_uses_main_application_click_dispatcher():
    script = _read("src/webui/reference_acceptance.js")
    app = _read("src/webui/app.js")
    markup = _read("src/webui/index.html")

    assert 'item.dataset.action = "account-mfa";' in script
    assert 'else if (action === "account-mfa") void openMfaDialog();' in app
    assert 'id="mfa-dialog"' in markup
    assert 'id="mfa-enable-form"' in markup
    assert 'id="mfa-disable-form"' in markup


def test_round22_routing_flow_range_options_are_owned_by_routing_flow():
    script = _read("src/webui/routing_flow.js")

    assert "syncRangeOptionsFromDashboard" not in script
    assert 'document.getElementById("history-range")' not in script
    assert 'option value="10m">Last 10 minutes</option>' in script
    assert 'option value="1h">Last 1 hour</option>' in script
    assert 'option value="1d" selected>Last 24 hours</option>' in script
    assert 'option value="1m">Last 1 month</option>' in script
    assert 'option value="1y">Last 1 year</option>' in script
