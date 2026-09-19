"""Round-37 regressions for Security role i18n race and Routing Flow value popovers."""

from pathlib import Path

from webui.service import UI_BUILD


ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_security_role_does_not_sync_before_authentication_or_keep_i18n_source():
    script = read("src/webui/reference_acceptance.js")

    start = script.index("function syncAccountReference()")
    end = script.index("function syncAll()", start)
    sync = script[start:end]

    assert "if (!state.user) return;" in sync
    assert 'const roleValue = byId("reference-account-role-value");' in sync
    assert "delete roleValue.dataset.i18nSource;" in sync
    assert 'roleValue.textContent = admin ? "Administrator" : "User";' in sync


def test_routing_value_overflow_uses_browser_top_layer_popover():
    script = read("src/webui/routing_flow.js")
    styles = read("src/webui/routing_flow.css")

    start = script.index("function renderFilterCard")
    end = script.index("function activeFlowGraph", start)
    card = script[start:end]

    assert 'valuePopover.setAttribute("popover", "auto");' in card
    assert "function positionValuePopover()" in card
    assert "valuePopover.showPopover();" in card
    assert "valuePopover.hidePopover();" in card
    assert 'valuePopover.matches(":popover-open")' in card
    assert ".rf-filter-value-popover[popover]" in styles
    assert "position: fixed;" in styles
    assert "inset: auto;" in styles


def test_round37_build_versions_changed_webui_assets():
    assert UI_BUILD == "20260919-r38"
    index = read("src/webui/index.html")
    assert 'name="nowlert-ui-build" content="20260919-r38"' in index
    assert "/ui/app.js?v=20260919-r38" in index
    assert "/ui/qa_patch.css?v=20260919-r38" in index
    assert "/ui/qa_patch.js?v=20260919-r38" in index
