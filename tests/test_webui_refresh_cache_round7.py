from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_round_seven_restores_requested_view_before_first_paint():
    enhancements = (ROOT / "src" / "webui" / "enhancements.js").read_text(encoding="utf-8")
    headers = (ROOT / "src" / "webui" / "page_headers.js").read_text(encoding="utf-8")
    header_css = (ROOT / "src" / "webui" / "page_headers.css").read_text(encoding="utf-8")

    assert 'navigate(view, "replace")' in enhancements
    assert 'originalNavigate(view, "replace")' not in enhancements
    show_start = enhancements.index("showApp = function enhancedShowApp(session)")
    show_end = enhancements.index("const originalLoadWorkspace = loadWorkspace", show_start)
    show_block = enhancements[show_start:show_end]
    load_start = enhancements.index("loadWorkspace = async function enhancedLoadWorkspace()")
    load_end = enhancements.index("const originalRenderUpdates = renderUpdates", load_start)
    load_block = enhancements[load_start:load_end]
    assert 'window.setTimeout(() => ensureRequestedView(), 0)' not in show_block
    assert 'window.setTimeout(() => ensureRequestedView(), 0)' not in load_block
    assert "syncHeaderMenu();\n    ensureRequestedView();" in show_block

    assert "navigateWithUnifiedPageHeader" in headers
    assert "showAppWithUnifiedPageHeader" in headers
    header_wrapper = headers[
        headers.index("const previousNavigate = navigate;"):
        headers.index("/* Selected Audit Log workbench acceptance. */")
    ]
    assert "syncPageHeader();" in header_wrapper
    assert "scheduleSync();\n    return result;" not in header_wrapper

    guard = header_css[header_css.index("/* 2026-09-18 first-paint guard"):]
    assert '.topbar.page-command-bar[data-page-view="dashboard"]' in guard
    assert '.topbar.page-command-bar[data-page-view="routing-flow"]' in guard
    assert "display: none !important;" in guard


def test_round_seven_workspace_cache_includes_filtering_and_routing_snapshots():
    app = (ROOT / "src" / "webui" / "app.js").read_text(encoding="utf-8")
    patch = (ROOT / "src" / "webui" / "qa_patch.js").read_text(encoding="utf-8")

    assert "filteringOverview: null" in app
    assert "routingFlowSnapshots: {}" in app
    assert '"filteringOverview",' in patch
    assert '"routingFlowSnapshots",' in patch
    assert "state.filteringOverview = null;" in patch
    assert "state.routingFlowSnapshots = {};" in patch


def test_round_seven_filtering_renders_cached_overview_before_network_refresh():
    script = (ROOT / "src" / "webui" / "filtering.js").read_text(encoding="utf-8")

    start = script.index("async function loadOverview()")
    finish = script.index("function filterFieldDescriptor", start)
    block = script[start:finish]
    cached = block.index("const cached = filteringState.overview || state.filteringOverview;")
    render_cached = block.index("renderOverview();", cached)
    network = block.index('const next = await request("/filters");')
    assert cached < render_cached < network
    assert "state.filteringOverview = next;" in block
    assert 'typeof qaSaveWorkspaceCache === "function"' in block
    assert "state.filteringOverview = null;" in script


def test_round_seven_routing_flow_uses_last_snapshot_immediately():
    script = (ROOT / "src" / "webui" / "routing_flow.js").read_text(encoding="utf-8")

    assert "function cachedRoutingFlowSnapshot()" in script
    assert "function hydrateCachedRoutingFlow()" in script
    refresh_start = script.index("async function refresh()")
    refresh = script[refresh_start:script.index("function sync()", refresh_start)]
    assert refresh.index("hydrateCachedRoutingFlow();") < refresh.index("busy=true;")
    assert "state.routingFlowSnapshots = {" in refresh
    assert "[range]: next" in refresh
    assert 'typeof qaSaveWorkspaceCache === "function"' in refresh
    assert "state.routingFlowSnapshots = {};" in script


def test_round_seven_destination_and_users_polish_runs_in_render_cycle():
    script = (ROOT / "src" / "webui" / "management_consistency.js").read_text(encoding="utf-8")

    assert "Array.isArray(state.privateDestinations)" in script
    assert "renderDestinationsWithManagementConsistency" in script
    assert "syncDestinations();" in script
    assert "renderUsersWithManagementConsistency" in script
    assert "syncUsers();" in script


def test_round_seven_settings_does_not_measure_or_clip_updates_card():
    script = (ROOT / "src" / "webui" / "reference_acceptance.js").read_text(encoding="utf-8")
    styles = (ROOT / "src" / "webui" / "reference_acceptance.css").read_text(encoding="utf-8")

    start = script.index("function alignSettingsReferenceCards()")
    finish = script.index("function syncSettingsUpdateState()", start)
    block = script[start:finish]
    assert 'updates.style.height = "";' in block
    assert "getBoundingClientRect" not in block
    assert "targetHeight" not in block

    round_seven = styles[styles.index("/* 2026-09-18 round-seven first-paint and Security token acceptance. */"):]
    assert "align-items: stretch !important;" in round_seven
    assert "height: auto !important;" in round_seven
    assert "overflow: visible !important;" in round_seven


def test_round_seven_security_api_tokens_matches_reference_table():
    script = (ROOT / "src" / "webui" / "reference_acceptance.js").read_text(encoding="utf-8")
    styles = (ROOT / "src" / "webui" / "reference_acceptance.css").read_text(encoding="utf-8")

    assert "const TOKEN_PAGE_SIZE = 6;" in script
    assert "function ensureApiTokenReferenceLayout()" in script
    assert "function syncApiTokensReference()" in script
    assert 'input.placeholder = "Search tokens by name or ID...";' in script
    assert 'const haystack = `${item.name || ""} ${item.id || ""}`.toLowerCase();' in script
    assert "range.textContent = matching.length" in script
    assert "of ${matching.length} API tokens" in script
    assert 'previous.dataset.referenceTokenPage = "previous";' in script
    assert 'next.dataset.referenceTokenPage = "next";' in script
    assert "syncApiTokensReference();" in script

    round_seven = styles[styles.index("/* 2026-09-18 round-seven first-paint and Security token acceptance. */"):]
    assert ".reference-token-search-bar" in round_seven
    assert ".reference-token-footer" in round_seven
    assert ".reference-token-pager button.is-current" in round_seven
    assert ".reference-api-tokens thead" in round_seven
