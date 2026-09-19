"""Round-36 regressions for authoritative account role and Routing Flow popover activation."""

from pathlib import Path

from webui.service import UI_BUILD


ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_security_account_role_uses_same_live_admin_authority_as_profile():
    script = read("src/webui/reference_acceptance.js")

    assert "referenceAuthenticatedRole" not in script
    sync_start = script.index("function syncAccountReference()")
    sync_end = script.index("function syncAll()", sync_start)
    sync = script[sync_start:sync_end]
    assert 'const admin = typeof isAdmin === "function" && isAdmin();' in sync
    assert 'roleValue.textContent = admin ? "Administrator" : "User";' in sync


def test_routing_flow_nodes_do_not_nest_overflow_buttons_inside_a_button():
    script = read("src/webui/routing_flow.js")

    start = script.index("function createNode(kind, identity, label)")
    end = script.index("function renderMetrics()", start)
    block = script[start:end]

    assert 'const node = el("div", `rf-node rf-${kind}`);' in block
    assert 'node.setAttribute("role", "button");' in block
    assert 'node.tabIndex = 0;' in block
    assert 'event.target.closest("button, a, input, select, textarea")' in block
    assert 'event.key === "Enter" || event.key === " "' in block
    assert 'const node = button("", () => showDetails(kind, identity)' not in block


def test_routing_filter_overflow_toggle_owns_its_menu_and_explicit_open_state():
    script = read("src/webui/routing_flow.js")

    card_start = script.index("function renderFilterCard")
    card_end = script.index("function activeFlowGraph", card_start)
    card = script[card_start:card_end]

    assert 'valuePopover.id = `rf-filter-values-${filter.id}`;' in card
    assert 'valueToggle.setAttribute("aria-controls", valuePopover.id);' in card
    assert 'valuePopover.setAttribute("popover", "auto");' in card
    assert 'valuePopover.showPopover();' in card


def test_round36_build_versions_the_changed_webui_bundle():
    assert UI_BUILD == "20260919-r39"
    index = read("src/webui/index.html")
    assert 'name="nowlert-ui-build" content="20260919-r39"' in index
    assert "/ui/app.js?v=20260919-r39" in index
    assert "/ui/qa_patch.css?v=20260919-r39" in index
    assert "/ui/qa_patch.js?v=20260919-r39" in index
