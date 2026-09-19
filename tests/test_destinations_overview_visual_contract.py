"""Regression coverage for the approved Destinations overview remake."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "src" / "webui" / "acceptance_cleanup.js"
STYLE = ROOT / "src" / "webui" / "operations_acceptance.css"
SERVICE = ROOT / "src" / "webui" / "service.py"


def test_destinations_overview_is_delivered_as_csp_safe_static_css():
    style = STYLE.read_text(encoding="utf-8")
    service = SERVICE.read_text(encoding="utf-8")
    start = style.index("/* Destinations overview: compact operational cards")
    destination_css = style[start:]

    assert 'style-src \'self\'' in service
    assert "'unsafe-inline'" not in service
    assert '"/ui/operations_acceptance.css"' in service
    assert 'href="/ui/operations_acceptance.css{version}"' in service
    assert "#view-destinations #destination-list {" in destination_css
    assert "grid-template-columns: repeat(4, minmax(0, 1fr));" in destination_css
    assert "@media (max-width: 980px)" in destination_css
    assert "@media (max-width: 1280px)" not in destination_css
    assert "#view-destinations .resource-icon" in destination_css
    assert "#view-destinations .resource-meta .status-button::before" in destination_css
    assert "#view-destinations .resource-actions" in destination_css
    assert '[data-action="preview-destination"]::before' in destination_css
    assert '[data-action="test-destination-card"]::before' in destination_css
    assert '[data-action="edit-destination"]::before' in destination_css
    assert '[data-action="delete-destination"]::before' in destination_css


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
