from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_round10_prefetches_startup_requests_before_dom_ready_gate():
    app = (ROOT / "src" / "webui" / "app.js").read_text(encoding="utf-8")

    assert "async function initialize(startupRequests = {})" in app
    initialize = app[
        app.index("async function initialize(startupRequests = {})"):
        app.index("async function loadWorkspace()", app.index("async function initialize(startupRequests = {})"))
    ]
    assert 'const sessionRequest = startupRequests.session || request("/session");' in initialize
    assert 'const status = await (startupRequests.bootstrap || request("/bootstrap"));' in initialize

    tail = app[app.rindex("// Prefetch both startup requests"):]
    assert 'session: request("/session"),' in tail
    assert 'bootstrap: request("/bootstrap"),' in tail
    assert tail.index("const startupRequests = {") < tail.index(
        'document.addEventListener("DOMContentLoaded", startApplication'
    )
    assert "void initialize(startupRequests);" in tail
    assert 'document.addEventListener("DOMContentLoaded", startApplication, { once: true });' in tail


def test_round10_sidebar_final_layer_matches_supplied_reference_contract():
    styles = (ROOT / "src" / "webui" / "qa_patch.css").read_text(encoding="utf-8")

    marker = "/* 2026-09-18 sidebar reference lock."
    start = styles.index(marker)
    end = styles.index("/* NCE-35 final unified pagination row */", start)
    sidebar = styles[start:end]

    assert "grid-template-columns: 208px minmax(0, 1fr) !important;" in sidebar
    assert "grid-template-columns: 106px minmax(0, 1fr) !important;" in sidebar
    assert "> .sidebar-owl-button {" in sidebar
    assert "> .sidebar-edition-expanded {" in sidebar
    assert "> .sidebar-edition-collapsed {" in sidebar
    assert "transform: none !important;" in sidebar
    assert "grid-row: 1 !important;" in sidebar
    assert "grid-row: 2 !important;" in sidebar
    assert "grid-row: 3 !important;" in sidebar
    assert ".app-shell.sidebar-collapsed .nav-item {" in sidebar
    assert "height: 50px !important;" in sidebar
    assert "width: 50px !important;" in sidebar


def test_round10_settings_navigation_icon_has_valid_svg_root():
    markup = (ROOT / "src" / "webui" / "index.html").read_text(encoding="utf-8")

    start = markup.index('id="settings-nav"')
    block = markup[start:markup.index("</button>", start)]
    assert '<span class="nav-icon" aria-hidden="true"><svg viewBox="0 0 24 24">' in block
    assert block.count("<svg") == 1
    assert block.count("</svg>") == 1
