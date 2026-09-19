"""Round-49 regressions for destination ownership presentation and controls."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_destination_cards_use_dynamic_owner_identity_and_owner_scoped_controls():
    app = read("src/webui/app.js")
    consistency = read("src/webui/management_consistency.js")
    editor = read("src/webui/destination_editor_fix.js")
    cleanup = read("src/webui/acceptance_cleanup.js")

    render_start = app.index("function renderDestinations()")
    render_end = app.index("function destinationName(", render_start)
    render = app[render_start:render_end]

    assert "const editable = ownResource(item);" in render
    assert "const canTest = editable || isAdmin() || item.shared;" in render
    assert 'actionButton("Edit", "edit-destination", item.id)' in render
    assert 'actionButton("Send test", "test-destination-card", item.id, "primary")' in render
    assert 'className: "badge destination-owner-badge"' in render
    assert "item.owner_username" in render
    assert "Owner:" not in render

    open_start = app.index('function openDestination(id = "")')
    open_end = app.index("function collectFields(", open_start)
    open_block = app[open_start:open_end]
    assert 'byId("destination-shared-field").hidden = item ? !ownResource(item) : false;' in open_block

    save_start = app.index("async function saveDestination(event)")
    save_end = app.index("function splitList(", save_start)
    save = app[save_start:save_end]
    assert 'if (!byId("destination-shared-field").hidden)' in save
    assert "if (isAdmin()) payload.shared" not in save

    assert "Owner: ${destinationOwnerName(item)}" not in consistency
    assert '|| "User"' not in consistency
    assert '.replace(/^owner:\\s*/i, "")' in consistency
    assert "status.hidden = Boolean(sharedField?.hidden);" in editor
    assert 'badge(item.owner_username, "destination-owner-badge")' in cleanup
    assert 'Owner: ${item.owner_username' not in cleanup
