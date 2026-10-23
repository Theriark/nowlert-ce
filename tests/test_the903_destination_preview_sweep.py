"""THE-903: destination Preview must not fail for any catalogue source.

The Preview dialog sends one Event API sample per assigned route.  This sweep
parses a sample of that shape for every route source through the real Event
API parser and renders it with the real Teams and Discord adapters (Modern and
Classic), so a source whose rendering raises (an HTTP 500 at the endpoint)
fails here instead of on Development.
"""

from __future__ import annotations

import json

import pytest

from dispatcher import Dispatcher
from integrations.catalog import route_options
from outputs.platform import DiscordPlatformAdapter, TeamsPlatformAdapter
from storage.destinations import Destination

SOURCES = sorted({item["source"] for item in route_options() if item["source"] != "*"})
SEVERITIES = ("information", "warning", "critical")


def destination(output_type: str, style: str) -> Destination:
    settings = (
        {"message_style": style}
        if output_type == "teams"
        else {"components_v2": style == "modern"}
    )
    return Destination(
        id="d" * 32,
        owner_user_id="u" * 32,
        name="Preview sweep",
        output_type=output_type,
        settings=settings,
        shared=False,
        enabled=True,
        secret_configured=True,
        created_at=1,
        updated_at=1,
    )


def webui_event(source: str, severity: str) -> dict:
    return {
        "schema": "nowlert.event.v1",
        "source": source,
        "title": f"{source} test alert",
        "message": f"Safe WebUI test: {source} events are routed to this destination.",
        "severity": severity,
        "status": "active",
        "category": "monitoring",
        "provider": source,
        "metadata": {
            "host": "Preview sweep",
            "component": "Destination test",
            "severity": severity,
            "synthetic": True,
            "route_id": "r" * 32,
            "route_name": f"{source} route",
        },
    }


@pytest.fixture(autouse=True)
def public_cards(monkeypatch, tmp_path):
    monkeypatch.setenv("NOWLERT_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("NOWLERT_TEAMS_PUBLIC_BASE_URL", "https://nowlert.example.test")


@pytest.mark.parametrize("severity", SEVERITIES)
@pytest.mark.parametrize("source", SOURCES)
def test_every_route_source_sample_is_accepted_by_the_event_parser(source, severity):
    notification = Dispatcher().parse_webhook("event_api", webui_event(source, severity))
    assert notification is not None
    assert notification.source == source


@pytest.mark.parametrize("style", ("modern", "classic"))
@pytest.mark.parametrize("adapter_type", ("teams", "discord"))
@pytest.mark.parametrize("source", SOURCES)
def test_every_route_source_previews_without_raising(source, adapter_type, style):
    notification = Dispatcher().parse_webhook("event_api", webui_event(source, "warning"))
    adapter = TeamsPlatformAdapter() if adapter_type == "teams" else DiscordPlatformAdapter()

    preview = adapter.preview(destination(adapter_type, style), notification)

    assert preview.output_type == adapter_type
    assert json.dumps(preview.payload)
