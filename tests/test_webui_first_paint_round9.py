from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_round9_app_waits_until_all_deferred_layers_exist_before_startup():
    app = (ROOT / "src" / "webui" / "app.js").read_text(encoding="utf-8")

    tail = app[app.rindex("bindEvents();"):]
    assert 'document.addEventListener("DOMContentLoaded", startApplication, { once: true });' in tail
    assert 'window.addEventListener("load", startApplication, { once: true });' in tail
    assert "let applicationStarted = false;" in tail
    assert tail.rstrip().endswith('if (document.readyState === "complete") startApplication();')
    assert "\nbindEvents();\ninitialize();\n" not in app


def test_round9_ownership_sync_never_replays_old_security_title_after_paint():
    script = (ROOT / "src" / "webui" / "source_ui_retirement.js").read_text(encoding="utf-8")

    account = script[script.index('if (view === "account")'):script.index('} else if (view === "backups")')]
    assert '"Security"' in account
    assert '"Account security"' not in account

    start = script.index("function scheduleFinalOwnershipSync()")
    finish = script.index("function syncAccessShell()", start)
    block = script[start:finish]
    assert "window.queueMicrotask" in block
    assert "requestAnimationFrame" not in block


def test_round9_structural_acceptance_syncs_do_not_wait_for_a_painted_frame():
    reference = (ROOT / "src" / "webui" / "reference_acceptance.js").read_text(encoding="utf-8")
    consistency = (ROOT / "src" / "webui" / "management_consistency.js").read_text(encoding="utf-8")

    ref_start = reference.index("function scheduleSync()")
    ref_end = reference.index("if (typeof openPreview", ref_start)
    ref_block = reference[ref_start:ref_end]
    assert "window.queueMicrotask(syncAll);" in ref_block
    assert "setTimeout(syncAll, 60)" not in ref_block

    con_start = consistency.index("function scheduleSync()")
    con_end = consistency.index("installChannelCollection()", con_start)
    con_block = consistency[con_start:con_end]
    assert "window.queueMicrotask(syncConsistency);" in con_block
    assert "requestAnimationFrame(syncConsistency)" not in con_block


def test_round9_sidebar_is_canonical_and_collapses_from_the_owl():
    markup = (ROOT / "src" / "webui" / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "src" / "webui" / "app.js").read_text(encoding="utf-8")
    styles = (ROOT / "src" / "webui" / "styles.css").read_text(encoding="utf-8")

    assert 'id="sidebar-collapse-button"' in markup
    assert 'data-view="routing-flow"' in markup
    assert 'data-view="filtering"' in markup
    assert "COMMUNITY EDITION" in markup
    assert "sidebar-edition-collapsed" in markup
    assert ">CE<" in markup
    assert 'data-view="sources"' not in markup
    assert 'data-view="routes"' not in markup
    assert 'data-view="tokens"' not in markup
    assert 'data-view="updates"' not in markup

    assert "function setSidebarCollapsed(collapsed)" in app
    assert 'shell.classList.toggle("sidebar-collapsed", Boolean(collapsed));' in app
    assert 'byId("sidebar-collapse-button")?.addEventListener("click"' in app
    assert "localStorage" not in app
    assert "sessionStorage" not in app

    assert ".app-shell.sidebar-collapsed" in styles
    assert ".sidebar-owl-button" in styles
    assert ".app-shell.sidebar-collapsed .nav-label" in styles


def test_round9_routing_flow_reuses_static_navigation_and_cached_status():
    routing = (ROOT / "src" / "webui" / "routing_flow.js").read_text(encoding="utf-8")
    operations = (ROOT / "src" / "webui" / "operations_acceptance.js").read_text(encoding="utf-8")

    assert "let nav = document.querySelector('#primary-nav [data-view=\"routing-flow\"]');" in routing
    assert "if (!nav) {" in routing
    assert "function cachedRoutingFlowTimestamp()" in operations
    assert "state.routingFlowSnapshots && state.routingFlowSnapshots[range]" in operations
    assert "flowLastSuccess = cachedAt;" in operations
