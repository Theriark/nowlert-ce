"""Round-45 regressions for Filtering first-paint state and Routing Flow cache invalidation."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_filtering_base_renderer_uses_master_state_and_active_count_on_first_paint():
    script = read("src/webui/filtering.js")

    summary_start = script.index("function policyFilterSummary(policy)")
    summary_end = script.index("function policyFilterDetailRow", summary_start)
    summary = script[summary_start:summary_end]

    assert "policy.filtering_enabled" in summary
    assert "policy.configured_count" in summary
    assert "policy.active_count" in summary
    assert "configured · disabled" in summary
    assert "configured · " in summary and " active" in summary

    status_start = script.index("function policyStatusBadge")
    status_end = script.index("function renderOverview", status_start)
    status = script[status_start:status_end]

    assert "policy.filtering_enabled" in status
    assert '"Disabled"' in status
    assert '"Active"' in status


def test_filtering_authoritative_refresh_replaces_cached_overview_and_destination_toggle_invalidates_it():
    filtering = read("src/webui/filtering.js")
    ownership = read("src/webui/filtering_ownership_sync.js")
    app = read("src/webui/app.js")

    assert 'document.addEventListener("nowlert:filtering-overview-updated"' in filtering
    assert "filteringState.overview = payload;" in filtering
    assert "state.filteringOverview = payload;" in filtering

    assert 'document.addEventListener("nowlert:filtering-state-invalidated"' in filtering
    assert "filteringState.overview = null;" in filtering
    assert "state.filteringOverview = null;" in filtering

    refresh_start = ownership.index("async function refresh()")
    refresh_end = ownership.index("async function refreshDestinationsState", refresh_start)
    refresh = ownership[refresh_start:refresh_end]
    assert 'new CustomEvent("nowlert:filtering-overview-updated"' in refresh

    toggle_start = app.index('} else if (action === "toggle-destination")')
    toggle_end = app.index('} else if (action === "toggle-destination-shared")', toggle_start)
    toggle = app[toggle_start:toggle_end]
    assert 'new CustomEvent("nowlert:filtering-state-invalidated")' in toggle
    assert 'new CustomEvent("nowlert:routing-topology-changed")' in toggle


def test_routing_affecting_filter_mutations_invalidate_and_background_warm_the_flow_snapshot():
    filtering = read("src/webui/filtering.js")
    ownership = read("src/webui/filtering_ownership_sync.js")
    routing = read("src/webui/routing_flow.js")

    assert filtering.count('new CustomEvent("nowlert:routing-topology-changed")') >= 4

    toggle_start = ownership.index("async function toggleFiltering(button)")
    toggle_end = ownership.index("async function toggleSharing", toggle_start)
    toggle = ownership[toggle_start:toggle_end]
    assert 'new CustomEvent("nowlert:routing-topology-changed")' in toggle

    assert "function scheduleRoutingFlowWarmup" in routing
    assert "async function warmRoutingFlowSnapshot" in routing
    assert 'document.addEventListener("nowlert:routing-topology-changed"' in routing

    listener_start = routing.index('document.addEventListener("nowlert:routing-topology-changed"')
    listener_end = routing.index("});", listener_start) + 3
    listener = routing[listener_start:listener_end]
    assert "state.routingFlowSnapshots = {};" in listener
    assert "clearPrivateData();" in listener
    assert "scheduleRoutingFlowWarmup" in listener

    warm_start = routing.index("async function warmRoutingFlowSnapshot")
    warm_end = routing.index("function scheduleRoutingFlowWarmup", warm_start)
    warm = routing[warm_start:warm_end]
    assert "/routing-flow/" in warm
    assert 'cache:"no-store"' in warm or 'cache: "no-store"' in warm
    assert "state.routingFlowSnapshots" in warm
    assert "qaSaveWorkspaceCache" in warm
