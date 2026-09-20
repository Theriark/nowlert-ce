"""Generic fallback parsing and Discord Classic Card coverage."""

from __future__ import annotations

from email.message import EmailMessage

from outputs.discord import DiscordOutput
from parsers.event_api import Parser as EventAPIParser
from parsers.generic import Parser as GenericParser
from parsers.redfish import RedfishParser


FOOTER = {"text": "🦉 Nowlert CE • Classic Card"}


def field_map(embed):
    return {
        field["name"]: field["value"]
        for field in embed.get("fields", [])
    }


def smtp_notification():
    message = EmailMessage()
    message["From"] = "Generic Monitor <alerts@generic.example.invalid>"
    message["To"] = "nowlert-development@example.invalid"
    message["Subject"] = "Synthetic generic SMTP notification"
    message["Date"] = "Thu, 04 Sep 2026 00:20:00 +0100"
    message["Message-ID"] = "<generic-fallback-smtp@example.invalid>"
    message.set_content(
        "A synthetic generic SMTP notification reached Nowlert through "
        "the fallback route.\n"
        "The message does not match any product-specific email parser."
    )
    item = GenericParser().parse(message)
    item.metadata["_input_type"] = "SMTP"
    item.metadata["to"] = "nowlert-development@example.invalid"
    return item


def test_generic_smtp_parser_preserves_useful_message_context():
    item = smtp_notification()

    assert item.source == "generic"
    assert item.category == "email"
    assert item.status == "information"
    assert item.title == "Synthetic generic SMTP notification"
    assert "fallback route" in item.body
    assert "product-specific email parser" in item.body
    assert item.sender == "Generic Monitor <alerts@generic.example.invalid>"
    assert item.metadata["provider"] == "Generic Monitor"
    assert item.metadata["sender_address"] == "alerts@generic.example.invalid"
    assert item.metadata["message_id"] == (
        "<generic-fallback-smtp@example.invalid>"
    )
    assert item.metadata["format"] == "smtp"


def test_generic_smtp_classic_card_shows_body_transport_and_email_identity():
    embed = DiscordOutput().default_formatter.format(
        smtp_notification()
    )["embeds"][0]
    fields = field_map(embed)

    assert embed["footer"] == FOOTER
    assert "fallback route" in embed["description"]
    assert "**Severity:** `information`" in fields["ℹ️ Alert"]
    assert "**Category:** `email`" in fields["ℹ️ Alert"]
    assert "**Input:** `SMTP`" in fields["📍 Source"]
    assert "**Provider:** `Generic Monitor`" in fields["📍 Source"]
    assert "alerts@generic.example.invalid" in fields["✉️ Email"]
    assert "nowlert-development@example.invalid" in fields["✉️ Email"]
    assert "generic-fallback-smtp@example.invalid" in fields["✉️ Email"]
    assert "**Format:** `smtp`" in fields["🧩 Context"]
    assert "⏱️ Timing" in fields


def test_generic_http_classic_card_keeps_event_api_context():
    payload = {
        "schema": "nowlert.event.v1",
        "source": "generic_http",
        "title": "Synthetic HTTP fallback warning",
        "message": (
            "Synthetic service latency exceeded the configured "
            "warning threshold."
        ),
        "severity": "warning",
        "status": "active",
        "category": "service",
        "provider": "Synthetic HTTP Monitor",
        "host": "synthetic-http.example.invalid",
        "timestamp": "2026-09-03T23:20:00Z",
        "metadata": {
            "component": "generic-event-api",
            "environment": "development",
        },
    }
    item = EventAPIParser().parse(payload)
    item.metadata["_input_type"] = "HTTP"

    embed = DiscordOutput().default_formatter.format(item)["embeds"][0]
    fields = field_map(embed)

    assert embed["footer"] == FOOTER
    assert "service latency" in embed["description"]
    assert "**Severity:** `warning`" in fields["⚠️ Alert"]
    assert "**Category:** `service`" in fields["⚠️ Alert"]
    assert "**Input:** `HTTP`" in fields["📍 Source"]
    assert "Synthetic HTTP Monitor" in fields["📍 Source"]
    assert "synthetic-http.example.invalid" in fields["📍 Source"]
    assert "**Environment:** `development`" in fields["🧩 Context"]
    assert "**Component:** `generic-event-api`" in fields["🧩 Context"]
    assert "**Format:** `event-api-v1`" in fields["🧩 Context"]
    assert "⏱️ Timing" in fields


def redfish_notification():
    payload = {
        "@odata.type": "#Event.v1_7_0.Event",
        "Id": "synthetic-generic-redfish-event",
        "Name": "Synthetic Generic Redfish Event",
        "Context": "GENERIC-SRV-01",
        "Events": [
            {
                "EventId": "synthetic-generic-redfish-critical-001",
                "EventTimestamp": "2026-09-03T23:21:00Z",
                "Severity": "Critical",
                "Message": (
                    "Synthetic chassis sensor reported a critical condition"
                ),
                "MessageId": "Resource.1.0.GenericCritical",
                "Resolution": (
                    "Inspect the source system and the reported chassis "
                    "sensor condition."
                ),
                "OriginOfCondition": {
                    "@odata.id": (
                        "/redfish/v1/Chassis/1/Sensors/GenericSensor"
                    ),
                },
            },
        ],
    }
    item = RedfishParser().parse(payload)[0]
    item.metadata["_input_type"] = "Redfish"
    return item


def test_generic_redfish_classic_card_is_operationally_useful():
    formatter = DiscordOutput().source_formatters["redfish"]
    embed = formatter.format(redfish_notification())["embeds"][0]
    fields = field_map(embed)

    assert embed["footer"] == FOOTER
    assert embed["color"] == 0xE74C3C
    assert "critical condition" in embed["description"]
    assert "**Severity:** `critical`" in fields["🚨 Alert"]
    assert "**Category:** `chassis`" in fields["🚨 Alert"]
    assert "**Input:** `Redfish`" in fields["📍 Source"]
    assert "**Provider:** `Redfish`" in fields["📍 Source"]
    assert "**System:** `GENERIC-SRV-01`" in fields["📍 Source"]
    assert "Resource.1.0.GenericCritical" in fields["🏷️ Event"]
    assert "synthetic-generic-redfish-critical-001" in fields["🏷️ Event"]
    assert "/redfish/v1/Chassis/1/Sensors/GenericSensor" in fields["🏷️ Event"]
    assert "reported chassis sensor condition" in (
        fields["🛠️ Recommended Action"]
    )
    assert "⏱️ Timing" in fields


def test_generic_redfish_modern_card_remains_components_v2():
    formatter = DiscordOutput().source_formatters["redfish"]
    payload = formatter.format_components_v2(redfish_notification())

    assert payload["flags"] == 32768
    assert "components" in payload
    assert "embeds" not in payload
    assert "Classic Card" not in repr(payload)
