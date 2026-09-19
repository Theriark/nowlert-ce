"""Regression coverage for the final Destinations overview acceptance fixes."""

from pathlib import Path

import pytest

from api.private_destination_actions import PlatformAPI
from dispatcher import Dispatcher
from outputs.platform import OutputPreview, PlatformOutputAdapter, PlatformOutputRegistry
from storage.database import Database
from storage.delivery import DeliveryResult
from storage.users import UserStore


ROOT = Path(__file__).resolve().parents[1]


class Configuration:
    def __init__(self, state_dir):
        self.data = {
            "api": {"enabled": True},
            "platform": {"enabled": True, "state_dir": str(state_dir)},
        }

    def get(self, *keys, default=None):
        value = self.data
        for key in keys:
            if not isinstance(value, dict) or key not in value:
                return default
            value = value[key]
        return value


class FakeWebhookAdapter(PlatformOutputAdapter):
    output_type = "webhook"

    def __init__(self):
        self.deliveries = []

    def preview(self, destination, notification):
        return OutputPreview(
            "webhook",
            "application/json",
            {"title": notification.title, "destination": destination.name},
            {"presentation": "safe"},
        )

    def deliver(self, destination, secret_value, notification):
        self.deliveries.append((destination.id, secret_value, notification.title))
        return DeliveryResult(True, response_status=200)


def _event():
    return {
        "schema": "nowlert.event.v1",
        "source": "nowlert",
        "title": "Private destination test",
        "message": "Bounded administrator operation.",
        "severity": "information",
        "status": "active",
    }


def test_private_destination_admin_can_preview_and_test_without_read_access(tmp_path):
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    users = UserStore(database)
    admin = users.bootstrap_admin("administrator", "correct horse battery staple")
    owner = users.create("private-owner", "private owner secure password")
    another = users.create("another-user", "another user secure password")
    adapter = FakeWebhookAdapter()
    platform = PlatformAPI(
        database,
        Dispatcher(),
        Configuration(tmp_path / "state"),
        registry=PlatformOutputRegistry([adapter]),
    )
    private = platform.destinations.create(
        owner.actor,
        owner.id,
        "Private webhook",
        "webhook",
        settings={"method": "POST"},
        shared=False,
    )

    with pytest.raises(PermissionError):
        platform._destination_resource("GET", None, admin.actor, private.id, None)
    with pytest.raises(PermissionError):
        platform._destination_resource(
            "POST", {"event": _event()}, another.actor, private.id, "preview"
        )

    preview = platform._destination_resource(
        "POST", {"event": _event()}, admin.actor, private.id, "preview"
    )
    tested = platform._destination_resource(
        "POST", {"event": _event()}, admin.actor, private.id, "test"
    )

    assert preview.status == 200
    assert preview.payload["preview"]["output_type"] == "webhook"
    assert preview.payload["preview"]["payload"]["destination"] == "Private webhook"
    assert tested.status == 200
    assert tested.payload["result"]["success"] is True
    assert "destination" not in tested.payload
    assert adapter.deliveries == [(private.id, None, "Private destination test")]


def test_destination_overview_statuses_fill_row_and_private_card_has_only_safe_actions():
    css = (ROOT / "src/webui/destination_overview_acceptance.css").read_text(
        encoding="utf-8"
    )
    script = (ROOT / "src/webui/destination_overview_acceptance.js").read_text(
        encoding="utf-8"
    )
    webui_service = (ROOT / "src/webui/service.py").read_text(encoding="utf-8")
    api_service = (ROOT / "src/api/service.py").read_text(encoding="utf-8")

    assert "flex: 1 1 0;" in css
    assert "justify-content: center;" in css
    assert ".acceptance-private-actions" in css
    assert "repeat(2, minmax(0, 1fr))" in css

    assert 'actionButton("Preview", "preview-private-destination"' in script
    assert 'actionButton("Send test", "test-private-destination-card"' in script
    assert "edit-private-destination" not in script
    assert "delete-private-destination" not in script
    assert 'card.querySelector(".field-help")?.remove();' in script
    assert 'form.addEventListener("submit", runPrivatePreview, true)' in script

    assert '"/ui/destination_overview_acceptance.js"' in webui_service
    assert '"/ui/destination_overview_acceptance.css"' in webui_service
    assert '<script src="/ui/destination_overview_acceptance.js{version}" defer></script>' in webui_service
    assert '<link rel="stylesheet" href="/ui/destination_overview_acceptance.css{version}">' in webui_service
    assert "from api.private_destination_actions import PlatformAPI" in api_service
