"""Round-50 regressions for Destination sharing controls and equal metadata rows."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_destination_owner_control_uses_authoritative_ownership_and_shared_viewers_are_view_only():
    app = read("src/webui/app.js")
    consistency = read("src/webui/management_consistency.js")

    own_start = app.index("function ownResource(item)")
    own_end = app.index("function ensureSessionResilienceUi()", own_start)
    own = app[own_start:own_end]
    assert 'typeof item.owned === "boolean"' in own
    assert 'String(item.owner_user_id || "") === String(state.user.id || "")' in own

    render_start = app.index("function renderDestinations()")
    render_end = app.index("function destinationName(", render_start)
    render = app[render_start:render_end]
    assert "const editable = ownResource(item);" in render
    assert 'className: "badge destination-view-only-badge"' in render
    assert 'text: "View only"' in render
    assert "const canTest = editable || isAdmin() || item.shared;" in render

    share_start = consistency.index("function syncDestinationSharingButton(button)")
    share_end = consistency.index("function readOnlyStatus(", share_start)
    share = consistency[share_start:share_end]
    assert "const item = destinationItemForCard(card);" in share
    assert "const owned = item ? ownResource(item) : !button.disabled;" in share
    assert "button.disabled = !owned;" in share
    assert "Shared destination. View only." in share


def test_private_admin_destination_has_one_owner_badge_and_view_only_badge():
    cleanup = read("src/webui/acceptance_cleanup.js")
    destination_css = read("src/webui/destination_overview_acceptance.css")
    consistency = read("src/webui/management_consistency.js")

    start = cleanup.index("function appendPrivateDestinationMetadata(items)")
    end = cleanup.index("async function refreshDestinationMetadata()", start)
    block = cleanup[start:end]
    assert 'badge(item.owner_username, "destination-owner-badge")' in block
    assert 'badge(item.owner_username, "")' not in block
    assert 'badge("View only", "destination-view-only-badge")' in block

    assert "function syncDestinationViewOnlyBadge(card)" in consistency
    assert "syncDestinationViewOnlyBadge(card);" in consistency


def test_destination_metadata_wraps_long_and_five_badge_rows_without_clipping():
    styles = read("src/webui/management_consistency.css")
    destination_css = read("src/webui/destination_overview_acceptance.css")

    start = styles.index("#view-destinations .destination-reference-card .resource-meta,")
    end = styles.index("#view-destinations .destination-reference-card .resource-actions", start)
    block = styles[start:end]

    assert "display: flex;" in block
    assert "flex-wrap: wrap;" in block
    assert "flex: 1 1 max-content;" in block
    assert "max-width: 100%;" in block
    assert "height: auto;" in block
    assert "white-space: normal;" in block
    assert "overflow-wrap: anywhere;" in block
    assert "overflow: hidden;" not in block
    assert "\n  width: 100%;" not in block
    assert "min-height: 34px;" in block
    assert "grid-template-columns: repeat(4" not in styles

    reference = read("src/webui/reference_acceptance.css")
    owner = reference.split("#view-destinations .destination-owner-badge {", 1)[1].split("}", 1)[0]
    assert "height: auto !important;" in owner

    actions_start = destination_css.index("#view-destinations .resource-actions .button {")
    actions_end = destination_css.index("}", actions_start)
    actions = destination_css[actions_start:actions_end]
    assert "min-height: 34px;" in actions
