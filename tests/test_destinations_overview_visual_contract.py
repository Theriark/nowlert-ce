"""Regression coverage for the approved Destinations overview remake."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "src" / "webui" / "acceptance_cleanup.js"


def test_destinations_overview_uses_compact_four_column_card_treatment():
    script = SCRIPT.read_text(encoding="utf-8")

    assert "installDestinationOverviewStyles" in script
    assert "nowlert-destinations-overview-styles" in script
    assert "#view-destinations #destination-list {" in script
    assert "grid-template-columns: repeat(4, minmax(0, 1fr));" in script
    assert "radial-gradient(circle at 82% 4%" in script
    assert "min-height: 0 !important;" in script
    assert "#view-destinations .resource-icon" in script
    assert "#view-destinations .resource-meta .status-button::before" in script
    assert "#view-destinations .resource-actions" in script
    assert '[data-action="preview-destination"]::before' in script
    assert '[data-action="test-destination-card"]::before' in script
    assert '[data-action="edit-destination"]::before' in script
    assert '[data-action="delete-destination"]::before' in script


def test_destinations_overview_keeps_private_metadata_card_read_only():
    script = SCRIPT.read_text(encoding="utf-8")
    start = script.index("function appendPrivateDestinationMetadata")
    end = script.index("async function refreshDestinationMetadata", start)
    private_block = script[start:end]

    assert "acceptance-private-destination" in private_block
    assert 'badge("Private", "warning")' in private_block
    assert 'badge("Metadata only", "")' in private_block
    assert "resource-actions" not in private_block
    assert "actionButton(" not in private_block
