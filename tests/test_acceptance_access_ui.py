"""Regression coverage for acceptance-stage Destination/Filtering UI cleanup."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_acceptance_cleanup_keeps_filter_rows_stable_and_private_badges_out_of_names():
    script = (ROOT / "src" / "webui" / "acceptance_cleanup.js").read_text(
        encoding="utf-8"
    )

    assert "integrationOrder" in script
    assert "stabilizeIntegrationOrder" in script
    assert "sourceFromRow" in script
    assert "relocateLegacyVisibilityBadges" in script
    assert 'statusCell.append(visibility)' in script
    assert 'destinationCell?.querySelectorAll(".filtering-access-badge")' in script
    assert 'marker.textContent = "○"' in script
    assert 'badge(activeCount ? "Active" : "Disabled"' in script


def test_acceptance_cleanup_exposes_only_private_metadata_to_admin():
    script = (ROOT / "src" / "webui" / "acceptance_cleanup.js").read_text(
        encoding="utf-8"
    )
    service = (ROOT / "src" / "webui" / "service.py").read_text(encoding="utf-8")

    assert "appendPrivateDestinationMetadata" in script
    assert "appendPrivateFilterMetadata" in script
    assert "Metadata only" in script
    assert "configuration, credentials, integrations and filtering remain private" in script.lower()
    assert 'document.querySelectorAll(\'[data-action="destination-access"]\')' in script
    assert '"/ui/acceptance_cleanup.js"' in service
    assert '<script src="/ui/acceptance_cleanup.js" defer></script>' in service


def test_api_service_uses_acceptance_access_model():
    service = (ROOT / "src" / "api" / "service.py").read_text(encoding="utf-8")
    access = (ROOT / "src" / "api" / "access_acceptance.py").read_text(encoding="utf-8")

    assert "from api.access_acceptance import PlatformAPI" in service
    assert 'return str(owner["role"]) == "admin"' in access
    assert 'return actor.user_id == str(destination["owner_user_id"])' in access
    assert "class AcceptanceDestinationStore" in access
    assert 'policy["integrations"] = configured' in access
    assert '"private_resources": self.destination_access.private_filter_metadata(actor)' in access
