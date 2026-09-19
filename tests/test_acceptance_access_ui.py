"""Regression coverage for acceptance-stage Destination/Filtering UI cleanup."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_acceptance_cleanup_keeps_filter_rows_stable_without_owning_status_columns():
    script = (ROOT / "src" / "webui" / "acceptance_cleanup.js").read_text(
        encoding="utf-8"
    )

    assert "integrationOrder" in script
    assert "stabilizeIntegrationOrder" in script
    assert "sourceFromRow" in script
    assert "relocateLegacyVisibilityBadges" in script
    assert 'row.querySelectorAll(".filtering-access-badge, .acceptance-visibility-badge")' in script
    assert 'marker.textContent = "○"' in script
    assert "statusCell.append(visibility)" not in script
    assert "statusCell.replaceChildren" not in script


def test_private_destination_metadata_stays_admin_only_while_filter_metadata_is_retired():
    script = (ROOT / "src" / "webui" / "acceptance_cleanup.js").read_text(
        encoding="utf-8"
    )
    service = (ROOT / "src" / "webui" / "service.py").read_text(encoding="utf-8")
    access = (ROOT / "src" / "api" / "access_acceptance.py").read_text(encoding="utf-8")

    assert "appendPrivateDestinationMetadata" in script
    assert "configuration, credentials, integrations and filtering remain private" in script.lower()
    assert 'document.querySelectorAll(\'[data-action="destination-access"]\')' in script
    assert '"private_resources": []' in access
    assert '"/ui/acceptance_cleanup.js"' in service
    assert '<script src="/ui/acceptance_cleanup.js{version}" defer></script>' in service


def test_private_destination_metadata_is_reused_synchronously_across_destination_renders():
    script = (ROOT / "src" / "webui" / "acceptance_cleanup.js").read_text(
        encoding="utf-8"
    )

    assert "privateDestinationMetadata = []" in script
    assert "privateDestinationMetadataSignature" in script
    assert "privateDestinationSignature" in script
    assert "list.dataset.privateDestinationSignature" in script
    assert "appendPrivateDestinationMetadata(privateDestinationMetadata)" in script
    assert script.index("appendPrivateDestinationMetadata(privateDestinationMetadata)") < script.index(
        "refreshDestinationMetadata();",
        script.index("renderDestinations = function renderDestinationsAcceptance"),
    )


def test_programmatic_main_focus_does_not_draw_workspace_outline():
    script = (ROOT / "src" / "webui" / "acceptance_cleanup.js").read_text(
        encoding="utf-8"
    )

    assert "suppressProgrammaticMainFocusOutline" in script
    assert 'document.getElementById("main-content")' in script
    assert 'main.style.outline = "none"' in script


def test_api_service_uses_owner_private_filtering_with_destination_master_state():
    service = (ROOT / "src" / "api" / "service.py").read_text(encoding="utf-8")
    access = (ROOT / "src" / "api" / "access_acceptance.py").read_text(encoding="utf-8")
    private_actions = (
        ROOT / "src" / "api" / "private_destination_actions.py"
    ).read_text(encoding="utf-8")

    assert "from api.private_destination_actions import PlatformAPI" in service
    assert "from api.access_acceptance import PlatformAPI as AcceptancePlatformAPI" in private_actions
    assert "class PlatformAPI(AcceptancePlatformAPI)" in private_actions
    assert 'return str(owner["role"]) == "admin"' in access
    assert 'return actor.user_id == str(destination["owner_user_id"])' in access
    assert "class AcceptanceDestinationStore" in access
    assert '_MASTER_FILTER_NAMESPACE = "destination_filter_master_enabled"' in access
    assert "destination_filtering_enabled" in access
    assert '"managed_by_admin": managed_by_admin' in access
    assert '"can_change_sharing": bool(actor.is_admin and owned)' in access
    assert '"private_resources": []' in access


def test_ownership_sync_extension_loads_after_routing_flow_and_uses_distinct_columns():
    script = (ROOT / "src" / "webui" / "filtering_ownership_sync.js").read_text(
        encoding="utf-8"
    )
    style = (ROOT / "src" / "webui" / "filtering_ownership_sync.css").read_text(
        encoding="utf-8"
    )
    service = (ROOT / "src" / "webui" / "service.py").read_text(encoding="utf-8")

    assert "policy.can_manage_filters" in script
    assert "policy.can_change_sharing" in script
    assert 'data-filter-sync-action' in script
    assert '"Integrations", "Filters", "Destinations"' in script
    assert "Managed by administrator" in script
    assert "filtering-sharing-cell" in script
    assert "filtering-status-stack" not in script
    assert ".filtering-sharing-cell" in style
    assert ".filtering-overview-list" in style
    assert ".rf-column-heading" in style
    assert "refreshDestinationsState" in script
    assert 'method: "PATCH"' in script and 'body: { shared: !current }' in script
    assert 'method: "PUT"' in script and 'body: { enabled: !current }' in script
    assert "all integration filters are disabled and must be re-enabled individually" in script
    assert "all integration filters were turned off" in script
    assert "saved integration filter states are preserved" not in script.lower()
    assert '"/ui/filtering_ownership_sync.js"' in service
    assert '"/ui/filtering_ownership_sync.css"' in service
    assert service.index('/ui/filtering_ownership_sync.js') > service.index('/ui/routing_flow.js')
