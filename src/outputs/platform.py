"""Previewable v2 platform adapters for every supported output type."""

from __future__ import annotations

import json
import socket

from dataclasses import dataclass, replace
from urllib.parse import urlsplit

import requests

from config import config
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
from outputs.teams import TeamsModernImageUnavailable, TeamsOutput
from outputs.teams_modern_image import (
    publish_teams_modern_image as publish_modern_card_image,
)
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
            source = str(notification.source or "").casefold()
            url = self._url(
                secret_url(secret_value),
                destination.settings,
            )

            if settings["components_v2"]:
                formatter = self.output.source_formatters.get(
                    source,
                    self.output.default_formatter,
                )
                image = self.output.render_modern_image(
                    notification,
                    formatter,
                )
                if image is not None:
                    filename = (
                        self.output.modern_image_filename(
                            source
                        )
                    )
                    url = self.output._delivery_webhook(
                        url,
                        {},
                        wait=True,
                    )
                    try:
                        response = self.http_client.post(
                            url,
                            data={
                                "payload_json": json.dumps(
                                    self.output.modern_image_payload(
                                        source,
                                        filename,
                                    ),
                                    separators=(",", ":"),
                                    ensure_ascii=False,
                                ),
                            },
                            files={
                                "files[0]": (
                                    filename,
                                    image,
                                    "image/png",
                                )
                            },
                            timeout=15,
                        )
                    except requests.RequestException as error:
                        return request_failure(error)
                    except Exception:
                        return DeliveryResult(
                            False,
                            error_code="transport_error",
                        )
                    result = http_delivery_result(response)
                    if not result.success:
                        return result
                    if not self.output._image_attachment_verified(
                        response,
                        filename,
                    ):
                        return DeliveryResult(
                            False,
                            response_status=int(
                                response.status_code
                            ),
                            error_code=(
                                "discord_attachment_unverified"
                            ),
                            safe_error=(
                                "Discord accepted the message "
                                "but did not retain the "
                                "rendered image attachment."
                            ),
                        )
                    return result

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
        modern_image = False
        formatter_name = formatter.__class__.__name__

        if requested_style == "classic":
            formatter = self.output.classic_source_formatters.get(
                source,
                self.output.classic_formatter,
            )
            formatter_name = formatter.__class__.__name__
            rendered_style = "classic"
            payload = formatter._sanitize_payload(
                formatter.format(notification)
            )
        else:
            try:
                payload, modern_image = self.output.modern_payload(
                    notification,
                    formatter,
                )
                formatter_name = "DiscordModernImageRenderer"
            except TeamsModernImageUnavailable as error:
                payload = {
                    "error": "teams_modern_image_unavailable",
                    "message": str(error),
                }
                payload_bytes = self.output.payload_size(payload)
                return OutputPreview(
                    "teams",
                    "application/json",
                    payload,
                    {
                        "formatter": "DiscordModernImageRenderer",
                        "message_style": requested_style,
                        "modern_image": False,
                        "rendered_style": rendered_style,
                        "payload_bytes": payload_bytes,
                        "payload_limit_bytes": self.output.MAX_PAYLOAD_BYTES,
                        "error_code": "teams_modern_image_unavailable",
                        "safe_error": str(error),
                    },
                )

        payload_bytes = self.output.payload_size(payload)
        return OutputPreview(
            "teams",
            "application/json",
            payload,
            {
                "formatter": formatter_name,
                "message_style": requested_style,
                "modern_image": modern_image,
                "rendered_style": rendered_style,
                "payload_bytes": payload_bytes,
                "payload_limit_bytes": self.output.MAX_PAYLOAD_BYTES,
            },
        )

    def deliver(self, destination, secret_value, notification):
        try:
            preview = self.preview(destination, notification)
        except ValueError:
            return DeliveryResult(False, error_code="invalid_destination")

        error_code = str(preview.metadata.get("error_code") or "")
        if error_code:
            return DeliveryResult(
                False,
                error_code=error_code,
                safe_error=str(preview.metadata.get("safe_error") or ""),
            )

        try:
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
        self.discord_modern_output = DiscordOutput()

    def _modern_image_payload(self, notification):
        """Reuse the exact Discord Modern rendered card in Slack."""

        try:
            image = self.discord_modern_output.render_modern_image(
                notification
            )
        except Exception:
            return None
        if image is None:
            return None

        image_url = publish_modern_card_image(config, image)
        if not image_url:
            return None

        title = (
            notification.title
            or notification.subject
            or notification.job_name
            or "Nowlert notification"
        )
        alt_text = self.formatter._truncate(
            f"{notification.source or 'Nowlert'}: {title}",
            200,
        )
        return self.formatter._sanitize_payload(
            {
                "text": alt_text,
                "blocks": [
                    {
                        "type": "image",
                        "image_url": image_url,
                        "alt_text": alt_text,
                    }
                ],
            }
        )

    def preview(self, destination, notification):
        settings = normalize_output_settings(
            "slack",
            destination.settings,
        )
        requested_style = settings["message_style"]

        if requested_style == "classic":
            payload = self.formatter.format(
                notification,
                include_metadata=settings["include_metadata"],
            )
            return OutputPreview(
                "slack",
                "application/json",
                payload,
                {
                    "formatter": self.formatter.__class__.__name__,
                    "message_style": "classic",
                    "modern_image": False,
                    "rendered_style": "classic",
                },
            )

        payload = self._modern_image_payload(notification)
        if payload is None:
            safe_error = (
                "Slack Modern Card requires the shared rendered image "
                "to be published from the public Nowlert media endpoint."
            )
            return OutputPreview(
                "slack",
                "application/json",
                {
                    "error": "slack_modern_image_unavailable",
                    "message": safe_error,
                },
                {
                    "formatter": "DiscordModernImageRenderer",
                    "message_style": "modern",
                    "modern_image": False,
                    "rendered_style": "modern",
                    "error_code": "slack_modern_image_unavailable",
                    "safe_error": safe_error,
                },
            )

        return OutputPreview(
            "slack",
            "application/json",
            payload,
            {
                "formatter": "DiscordModernImageRenderer",
                "message_style": "modern",
                "modern_image": True,
                "rendered_style": "modern",
            },
        )

    def deliver(self, destination, secret_value, notification):
        try:
            preview = self.preview(destination, notification)
        except ValueError:
            return DeliveryResult(False, error_code="invalid_destination")

        error_code = str(preview.metadata.get("error_code") or "")
        if error_code:
            return DeliveryResult(
                False,
                error_code=error_code,
                safe_error=str(preview.metadata.get("safe_error") or ""),
            )

        try:
            url = self._url(secret_url(secret_value), destination.settings)
            parsed_host = str(urlsplit(url).hostname or "")
            if parsed_host.casefold() not in {
                "hooks.slack.com",
                "hooks.slack-gov.com",
            }:
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
    def _modern_accent(color) -> tuple[str, str]:
        try:
            value = int(color) & 0xFFFFFF
        except (TypeError, ValueError):
            value = 0x3498DB
        tone = {
            0xE74C3C: "failure",
            0xED4245: "failure",
            0xF1C40F: "warning",
            0xF39C12: "warning",
            0x2ECC71: "success",
            0x57F287: "success",
        }.get(value, "information")
        return tone, f"#{value:06X}"

    @staticmethod
    def _modern_section(title: str, icon: str, fields: list[dict]) -> dict | None:
        items = [
            {
                "title": str(field.get("title") or ""),
                "value": str(field.get("value") or ""),
            }
            for field in fields
            if str(field.get("title") or "").strip()
            or str(field.get("value") or "").strip()
        ]
        if not items:
            return None
        return {
            "title": title,
            "icon": icon,
            "items": items,
        }

    @classmethod
    def _prometheus_modern_presentation(
        cls,
        payload: dict,
        classic: dict,
    ) -> dict:
        """Expose the standardized Prometheus card hierarchy to webhooks."""

        presentation = cls._presentation(payload, "modern")
        metadata = payload.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}

        tone, accent = cls._modern_accent(classic.get("color"))
        state = str(
            metadata.get("state")
            or payload.get("status")
            or "information"
        ).replace("_", " ").strip()
        badge_label = state.title() or "Information"
        event_time = (
            payload.get("end_time")
            if state.casefold() in {"resolved", "recovered", "success"}
            and payload.get("end_time")
            else payload.get("start_time")
        )

        grouped = {
            "target": [],
            "prometheus": [],
            "timing": [],
            "alerts": [],
            "other": [],
        }
        for field in classic.get("fields", []):
            if not isinstance(field, dict):
                continue
            title = str(field.get("title") or "")
            normalized = title.casefold()
            if "alert" in normalized and "alerts" not in normalized:
                # Severity already has a dedicated summary cell.
                continue
            if "target" in normalized:
                grouped["target"].append(field)
            elif "prometheus" in normalized or "labels" in normalized:
                grouped["prometheus"].append(field)
            elif "timing" in normalized or "links" in normalized:
                grouped["timing"].append(field)
            elif "alerts" in normalized:
                grouped["alerts"].append(field)
            else:
                grouped["other"].append(field)

        sections = []
        for key, title, icon in (
            ("target", "Target", "target"),
            ("prometheus", "Prometheus", "chart"),
            ("timing", "Timing & Links", "clock"),
            ("alerts", "Alert details", "alert"),
            ("other", "Additional details", "list"),
        ):
            section = cls._modern_section(
                title,
                icon,
                grouped[key],
            )
            if section is not None:
                if key == "alerts":
                    section["accent"] = accent
                    section["tone"] = tone
                sections.append(section)

        description = str(classic.get("description") or payload.get("body") or "")
        if description:
            sections.append(
                {
                    "title": "Event Details",
                    "icon": "alert",
                    "accent": accent,
                    "tone": tone,
                    "items": [{"title": "", "value": description}],
                }
            )

        presentation.update(
            {
                "visual_system": "nowlert_standard_v1",
                "integration": "Prometheus",
                "accent": accent,
                "badge": {
                    "label": badge_label,
                    "tone": tone,
                    "icon": "status",
                },
                "summary": [
                    {
                        "label": "Severity",
                        "value": payload.get("severity") or "information",
                        "icon": "status",
                    },
                    {
                        "label": "Category",
                        "value": payload.get("category") or "monitoring",
                        "icon": "sync",
                    },
                    {
                        "label": "Event time",
                        "value": event_time or "",
                        "icon": "clock",
                    },
                ],
                "sections": sections,
                "footer": "Nowlert CE • Modern Card",
            }
        )
        return presentation

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
            if str(notification.source or "").strip().casefold() == "prometheus":
                classic = self._classic_presentation(
                    destination,
                    notification,
                )
                payload["presentation"] = self._prometheus_modern_presentation(
                    payload,
                    classic,
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
