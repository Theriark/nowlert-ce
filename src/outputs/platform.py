"""Previewable v2 platform adapters for every supported output type."""

from __future__ import annotations

import json
import socket

from dataclasses import dataclass, replace
from urllib.parse import urlsplit

import requests

from formatters.classic_card_v1 import classic_card_v1_from_discord_payload
from formatters.slack import SlackFormatter
from models import Notification
from outputs.discord import DiscordOutput
from outputs.platform_common import (
    decode_secret,
    event_identifier,
    http_delivery_result,
    request_failure,
    safe_event_envelope,
    secret_url,
    validate_outbound_url,
)
from outputs.settings import normalize_output_settings
from outputs.teams import TeamsOutput
from storage.delivery import DeliveryResult
from storage.destinations import Destination


@dataclass(frozen=True)
class OutputPreview:
    output_type: str
    content_type: str
    payload: dict
    metadata: dict


class PlatformOutputAdapter:
    output_type = ""

    def preview(
        self,
        destination: Destination,
        notification: Notification,
    ) -> OutputPreview:
        raise NotImplementedError

    def deliver(
        self,
        destination: Destination,
        secret_value: bytes | None,
        notification: Notification,
    ) -> DeliveryResult:
        raise NotImplementedError

    def __call__(self, destination, secret_value, notification):
        return self.deliver(destination, secret_value, notification)


class _HTTPAdapter(PlatformOutputAdapter):
    def __init__(self, *, http_client=requests, resolver=socket.getaddrinfo):
        self.http_client = http_client
        self.resolver = resolver

    def _url(self, value, settings) -> str:
        return validate_outbound_url(
            value,
            allow_private_network=bool(settings.get("allow_private_network")),
            resolver=self.resolver,
        )

    def _post(self, url, *, payload, timeout, headers=None):
        try:
            response = self.http_client.post(
                url,
                json=payload,
                headers=headers,
                timeout=timeout,
            )
        except requests.RequestException as error:
            return request_failure(error)
        except Exception:
            return DeliveryResult(False, error_code="transport_error")
        return http_delivery_result(response)


class DiscordPlatformAdapter(_HTTPAdapter):
    output_type = "discord"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.output = DiscordOutput()

    def preview(self, destination, notification):
        settings = normalize_output_settings("discord", destination.settings)
        formatter = self.output.source_formatters.get(
            str(notification.source or "").casefold(),
            self.output.default_formatter,
        )
        if settings["components_v2"] and hasattr(formatter, "format_components_v2"):
            payload = formatter.format_components_v2(notification)
        else:
            payload = formatter.format(notification)
        payload = formatter._sanitize_payload(payload)
        return OutputPreview(
            "discord",
            "application/json",
            payload,
            {"formatter": formatter.__class__.__name__},
        )

    def deliver(self, destination, secret_value, notification):
        try:
            settings = normalize_output_settings("discord", destination.settings)
            preview = self.preview(destination, notification)
            url = self._url(
                secret_url(secret_value),
                destination.settings,
            )
            formatter = self.output.source_formatters.get(
                str(notification.source or "").casefold(),
                self.output.default_formatter,
            )
            thumbnail = self.output._thumbnail_media(preview.payload)
            local_reference = (
                isinstance(thumbnail, dict)
                and str(thumbnail.get("url") or "").startswith(
                    "nowlert-asset://"
                )
            )
            icon = self.output._local_icon(
                preview.payload,
                formatter,
            )
            if local_reference and icon is None:
                return DeliveryResult(
                    False,
                    error_code="discord_icon_unavailable",
                    safe_error=(
                        "The packaged Discord notification icon "
                        "is unavailable."
                    ),
                )
            url = self.output._delivery_webhook(
                url,
                preview.payload,
                wait=icon is not None,
            )
        except ValueError:
            return DeliveryResult(
                False,
                error_code="invalid_destination",
            )

        if icon is None:
            return self._post(
                url,
                payload=preview.payload,
                timeout=15,
            )

        filename, path, thumbnail = icon
        thumbnail["url"] = f"attachment://{filename}"
        preview.payload["attachments"] = [
            {
                "id": 0,
                "filename": filename,
            }
        ]

        try:
            with path.open("rb") as stream:
                response = self.http_client.post(
                    url,
                    data={
                        "payload_json": json.dumps(
                            preview.payload,
                            separators=(",", ":"),
                            ensure_ascii=False,
                        ),
                    },
                    files={
                        "files[0]": (
                            filename,
                            stream,
                            "image/png",
                        )
                    },
                    timeout=15,
                )
        except requests.RequestException as error:
            return request_failure(error)
        except OSError:
            return DeliveryResult(
                False,
                error_code="discord_icon_unavailable",
                safe_error=(
                    "The packaged Discord notification icon "
                    "could not be opened."
                ),
            )
        except Exception:
            return DeliveryResult(
                False,
                error_code="transport_error",
            )

        result = http_delivery_result(response)
        if not result.success:
            return result

        if settings["components_v2"] and not self.output._attachment_verified(
            response,
            filename,
        ):
            return DeliveryResult(
                False,
                response_status=int(response.status_code),
                error_code="discord_attachment_unverified",
                safe_error=(
                    "Discord accepted the message but did not "
                    "retain the packaged image attachment."
                ),
            )

        return result


class TeamsPlatformAdapter(_HTTPAdapter):
    output_type = "teams"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.output = TeamsOutput()

    def preview(self, destination, notification):
        settings = normalize_output_settings(
            "teams",
            destination.settings,
        )
        source = str(notification.source or "").casefold()
        modern_formatter = self.output.source_formatters.get(
            source,
            self.output.default_formatter,
        )

        requested_style = settings["message_style"]
        formatter = modern_formatter
        rendered_style = "modern"

        if requested_style == "classic":
            formatter = self.output.classic_source_formatters.get(
                source,
                self.output.classic_formatter,
            )
            rendered_style = "classic"

        payload = formatter._sanitize_payload(
            formatter.format(notification)
        )
        payload_bytes = self.output.payload_size(payload)
        return OutputPreview(
            "teams",
            "application/json",
            payload,
            {
                "formatter": formatter.__class__.__name__,
                "message_style": requested_style,
                "rendered_style": rendered_style,
                "payload_bytes": payload_bytes,
                "payload_limit_bytes": self.output.MAX_PAYLOAD_BYTES,
            },
        )

    def deliver(self, destination, secret_value, notification):
        try:
            preview = self.preview(destination, notification)
            url = self._url(secret_url(secret_value), destination.settings)
        except ValueError:
            return DeliveryResult(False, error_code="invalid_destination")
        payload_bytes = self.output.payload_size(preview.payload)
        if payload_bytes > self.output.MAX_PAYLOAD_BYTES:
            return DeliveryResult(
                False,
                error_code="teams_payload_too_large",
                safe_error=(
                    f"Microsoft Teams payload is {payload_bytes} bytes and "
                    f"exceeds the {self.output.MAX_PAYLOAD_BYTES}-byte limit."
                ),
            )
        return self._post(url, payload=preview.payload, timeout=15)


class SlackPlatformAdapter(_HTTPAdapter):
    output_type = "slack"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.formatter = SlackFormatter()

    def preview(self, destination, notification):
        settings = normalize_output_settings("slack", destination.settings)
        payload = self.formatter.format(
            notification,
            include_metadata=settings["include_metadata"],
        )
        return OutputPreview(
            "slack",
            "application/json",
            payload,
            {"formatter": self.formatter.__class__.__name__},
        )

    def deliver(self, destination, secret_value, notification):
        try:
            preview = self.preview(destination, notification)
            url = self._url(secret_url(secret_value), destination.settings)
            parsed_host = str(urlsplit(url).hostname or "")
            if parsed_host.casefold() not in {"hooks.slack.com", "hooks.slack-gov.com"}:
                raise ValueError("Slack webhook host is invalid")
        except ValueError:
            return DeliveryResult(False, error_code="invalid_destination")
        return self._post(url, payload=preview.payload, timeout=15)


class WebhookPlatformAdapter(_HTTPAdapter):
    output_type = "webhook"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.discord = DiscordPlatformAdapter(
            http_client=self.http_client,
            resolver=self.resolver,
        )
        self.discord_preview = self.discord

    @staticmethod
    def _presentation(payload: dict, style: str) -> dict:
        if style == "classic":
            return {
                "style": "classic_embed",
                "title": payload["title"],
                "description": payload["body"],
                "fields": {
                    "severity": payload["severity"],
                    "status": payload["status"],
                    "source": payload["source"],
                    "category": payload["category"],
                },
            }
        return {
            "style": "modern_card",
            "title": payload["title"],
            "message": payload["body"],
            "facts": [
                {"label": "Severity", "value": payload["severity"]},
                {"label": "Status", "value": payload["status"]},
                {"label": "Source", "value": payload["source"]},
                {"label": "Category", "value": payload["category"]},
            ],
        }

    @staticmethod
    def _classic_card_from_discord_payload(payload: dict) -> dict:
        return classic_card_v1_from_discord_payload(payload)

    def _classic_presentation(self, destination, notification) -> dict:
        discord_destination = self._discord_destination(
            destination,
            "classic",
        )
        preview = self.discord_preview.preview(
            discord_destination,
            notification,
        )
        return self._classic_card_from_discord_payload(
            preview.payload
        )

    @staticmethod
    def _is_discord_webhook(url: str) -> bool:
        host = str(urlsplit(url).hostname or "").casefold()
        return (
            host in {"discord.com", "discordapp.com"}
            or host.endswith(".discord.com")
            or host.endswith(".discordapp.com")
        )

    @staticmethod
    def _discord_destination(destination: Destination, style: str) -> Destination:
        return replace(
            destination,
            output_type="discord",
            settings={"components_v2": style == "modern"},
        )

    def preview(self, destination, notification):
        settings = normalize_output_settings(
            "webhook",
            destination.settings,
            require_complete=True,
        )
        payload = safe_event_envelope(notification)
        if settings["message_style"] == "classic":
            payload["presentation"] = self._classic_presentation(
                destination,
                notification,
            )
        else:
            payload["presentation"] = self._presentation(
                payload,
                settings["message_style"],
            )
        return OutputPreview(
            "webhook",
            "application/json",
            payload,
            {
                "method": "POST",
                "signed": False,
                "message_style": settings["message_style"],
            },
        )

    def deliver(self, destination, secret_value, notification):
        try:
            settings = normalize_output_settings(
                "webhook",
                destination.settings,
                require_complete=True,
            )
            preview = self.preview(destination, notification)
            credentials = decode_secret(secret_value)
            url = self._url(
                credentials.get("url") or credentials.get("value"),
                settings,
            )
        except ValueError:
            return DeliveryResult(False, error_code="invalid_destination")

        if self._is_discord_webhook(url):
            discord_destination = self._discord_destination(
                destination,
                settings["message_style"],
            )
            return self.discord.deliver(
                discord_destination,
                secret_value,
                notification,
            )

        return self._post(
            url,
            payload=preview.payload,
            timeout=15,
            headers={
                "Content-Type": "application/json",
                "X-Nowlert-Idempotency-Key": event_identifier(notification),
            },
        )


class PlatformOutputRegistry:
    def __init__(self, adapters: list[PlatformOutputAdapter] | None = None):
        configured = (
            adapters
            if adapters is not None
            else [
                DiscordPlatformAdapter(),
                TeamsPlatformAdapter(),
                SlackPlatformAdapter(),
                WebhookPlatformAdapter(),
            ]
        )
        self.adapters = {adapter.output_type: adapter for adapter in configured}

    def get(self, output_type: str) -> PlatformOutputAdapter:
        try:
            return self.adapters[str(output_type).casefold()]
        except KeyError as error:
            raise KeyError("output adapter is unavailable") from error

    def delivery_adapters(self) -> dict[str, PlatformOutputAdapter]:
        return dict(self.adapters)
