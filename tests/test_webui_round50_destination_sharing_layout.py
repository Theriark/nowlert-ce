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
    consistency = read("src/webui/management_consistency.js")

    start = cleanup.index("function appendPrivateDestinationMetadata(items)")
    end = cleanup.index("async function refreshDestinationMetadata()", start)
    block = cleanup[start:end]
    assert 'badge(item.owner_username, "destination-owner-badge")' in block
    assert 'badge(item.owner_username, "")' not in block
    assert 'badge("View only", "destination-view-only-badge")' in block

    assert "function syncDestinationViewOnlyBadge(card)" in consistency
    assert "syncDestinationViewOnlyBadge(card);" in consistency


def test_destination_metadata_row_uses_equal_dynamic_columns_at_action_height():
    styles = read("src/webui/management_consistency.css")
    cleanup = read("src/webui/acceptance_cleanup.js")

    start = styles.index("#view-destinations .destination-reference-card .resource-meta,")
    end = styles.index("#view-destinations .destination-reference-card .resource-actions", start)
    block = styles[start:end]

    assert "display: grid;" in block
    assert "grid-auto-columns: minmax(0, 1fr);" in block
    assert "grid-auto-flow: column;" in block
    assert "grid-template-columns: none;" in block
    assert "height: 34px;" in block
    assert "min-height: 34px;" in block
    assert "grid-template-columns: repeat(4" not in styles

    actions_start = cleanup.index("#view-destinations .resource-actions .button {")
    actions_end = cleanup.index("}", actions_start)
    actions = cleanup[actions_start:actions_end]
    assert "min-height: 34px;" in actions
