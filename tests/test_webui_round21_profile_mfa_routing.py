from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative):
    return (ROOT / relative).read_text(encoding="utf-8")


def test_round21_profile_is_named_profile_and_matches_access_reference():
    markup = _read("src/webui/index.html")
    script = _read("src/webui/reference_acceptance.js")
    style = _read("src/webui/reference_acceptance.css")

    assert 'data-view="account"><span aria-hidden="true">◇</span> Profile</button>' in markup
    assert '<h2>Profile</h2><p>Manage your profile information and account access.</p>' in markup
    assert "<h2>Profile</h2>" in script
    assert "reference-profile-top" in script
    assert "reference-access-status" in script
    assert "All systems operational" in script
    assert "reference-account-meta-mfa" in script
    assert 'mfaValue.textContent = enabled ? "Enabled" : "Disabled"' in script
    assert ".reference-profile-top {" in style
    assert "grid-template-columns:minmax(0,1.34fr) minmax(320px,.96fr);" in style
    assert "grid-template-columns:repeat(3,minmax(0,1fr)) !important;" in style


def test_round21_mfa_has_setup_management_and_login_challenge_ui():
    markup = _read("src/webui/index.html")
    app = _read("src/webui/app.js")
    assert 'id="login-mfa-field"' in markup
    assert 'id="login-otp"' in markup
    assert 'id="mfa-dialog"' in markup
    assert 'id="mfa-enable-form"' in markup
    assert 'id="mfa-disable-form"' in markup
    assert 'error.code === "mfa_required"' in app
    assert 'request("/account/mfa/setup"' in app
    assert 'request("/account/mfa", {' in app
    assert 'method: "PUT"' in app
    assert 'method: "DELETE"' in app


def test_round21_backups_have_clearance_and_export_action_fits_card():
    style = _read("src/webui/qa_patch.css")
    marker = "/* 2026-09-18 round-21 profile, backups, and routing metrics. */"
    final = style[style.index(marker):]
    assert "height: 350px !important;" in final
    assert "max-height: 350px !important;" in final
    assert "min-height: 350px !important;" in final
    assert "#backup-data-tools-panel .data-tools-reference-download {" in final
    assert "justify-content: center !important;" in final
    assert "white-space: nowrap !important;" in final
    assert "width: 100% !important;" in final


def test_round21_routing_flow_uses_dashboard_ranges_and_live_filter_metrics():
    script = _read("src/webui/routing_flow.js")
    api = _read("src/api/routing_flow.py")
    storage = _read("src/storage/routing_flow.py")
    filtering = _read("src/storage/filtering.py")
    for value, label in (
        ("10m", "Last 10 minutes"),
        ("1h", "Last 1 hour"),
        ("1d", "Last 24 hours"),
        ("1m", "Last 1 month"),
        ("1y", "Last 1 year"),
    ):
        assert f'value="{value}"' in script
        assert label in script
        assert f'"{value}"' in api
    assert 'range = "1d"' in script
    assert "link.metrics?.received" in script
    assert "link.metrics?.filtered" in script
    assert "routing_flow_events" in storage
    acceptance = _read("src/api/access_acceptance.py")
    assert "record_destination_filter_decision" in acceptance
