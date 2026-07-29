"""
Nowlert

discord.py

Discord output.
"""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import (
    parse_qsl,
    unquote,
    urlencode,
    urlsplit,
    urlunsplit,
)

import requests

from config import config
from environment import compatible_environment
from formatters.discord import DiscordFormatter
from formatters.discord_generic import GenericDiscordFormatter
from formatters.discord_grafana import GrafanaDiscordFormatter
from formatters.discord_hardware import (
    DellIDRACDiscordFormatter,
    HPEILODiscordFormatter,
    RedfishDiscordFormatter,
    SupermicroDiscordFormatter,
)
from formatters.discord_home_assistant import HomeAssistantDiscordFormatter
from formatters.discord_portainer import PortainerDiscordFormatter
from formatters.discord_proxmox import ProxmoxDiscordFormatter
from formatters.discord_qnap import QNAPDiscordFormatter
from formatters.discord_synology import SynologyDiscordFormatter
from formatters.discord_truenas import TrueNASDiscordFormatter
from formatters.discord_unifi import (
    UniFiDriveDiscordFormatter,
    UniFiNetworkDiscordFormatter,
    UniFiProtectDiscordFormatter,
)
from formatters.discord_zabbix import ZabbixDiscordFormatter
from logger import log
from models import Notification


class DiscordOutput:

    ICON_DIR = Path(
        compatible_environment(
            "NOWLERT_DISCORD_ICON_DIR",
            "NOTIFINHO_DISCORD_ICON_DIR",
            default="/notifinho/assets/icons",
        )
    )

    def __init__(self):

        self.default_formatter = GenericDiscordFormatter()

        self.source_formatters = {
            "xo": DiscordFormatter(),
            "grafana": GrafanaDiscordFormatter(),
            "portainer": PortainerDiscordFormatter(),
            "proxmox": ProxmoxDiscordFormatter(),
            "qnap": QNAPDiscordFormatter(),
            "synology": SynologyDiscordFormatter(),
            "truenas": TrueNASDiscordFormatter(),
            "unifi_drive": UniFiDriveDiscordFormatter(),
            "unifi_network": UniFiNetworkDiscordFormatter(),
            "unifi_protect": UniFiProtectDiscordFormatter(),
            "zabbix": ZabbixDiscordFormatter(),
            "redfish": RedfishDiscordFormatter(),
            "supermicro": SupermicroDiscordFormatter(),
            "hpe_ilo": HPEILODiscordFormatter(),
            "dell_idrac": DellIDRACDiscordFormatter(),
            "home_assistant": HomeAssistantDiscordFormatter(),
        }

    def send(
        self,
        notification: Notification,
        target: str = "default",
    ) -> bool:

        webhook = config.get(
            "outputs",
            "discord",
            target,
            "webhook",
        )

        if not webhook:

            log.error(
                "Discord webhook not configured for '%s'.",
                target,
            )

            return False

        source = (
            notification.source
            or ""
        ).lower()

        formatter = self.source_formatters.get(
            source,
            self.default_formatter,
        )

        try:

            if hasattr(formatter, "format_components_v2"):
                payload = formatter.format_components_v2(notification)
            else:
                payload = formatter.format(notification)

            payload = formatter._sanitize_payload(payload)

        except Exception:

            log.exception(
                "Failed to format Discord notification."
            )

            return False

        log.info(
            "Sending notification to Discord (%s)...",
            target,
        )

        log.info(
            "Discord formatter: %s",
            formatter.__class__.__name__,
        )

        if source.startswith("unifi_"):

            log.info(
                "%s formatter selected",
                formatter.label,
            )

        log.info(
            "Webhook ID: %s",
            webhook.split("/")[-2],
        )

        try:

            delivery_webhook = self._delivery_webhook(webhook, payload)
            icon = self._local_icon(payload, formatter)

            if icon is None:
                response = requests.post(
                    delivery_webhook,
                    json=payload,
                    timeout=15,
                )
            else:
                filename, path, thumbnail = icon
                thumbnail["url"] = f"attachment://{filename}"
                payload["attachments"] = [
                    {
                        "id": 0,
                        "filename": filename,
                    }
                ]
                with path.open("rb") as stream:
                    response = requests.post(
                        delivery_webhook,
                        data={
                            "payload_json": json.dumps(payload),
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

            if response.status_code >= 400:

                log.error(
                    "Discord returned %s",
                    response.status_code,
                )

                log.error(
                    "Discord response: %s",
                    response.text,
                )

                return False

            log.info(
                "Discord notification sent successfully."
            )

            return True

        except Exception:

            log.exception(
                "Failed to send Discord notification."
            )

            return False

    @staticmethod
    def _delivery_webhook(webhook, payload, *, wait=False):
        """Enable Components V2 and optional returned-message verification."""

        flags = payload.get("flags", 0) if isinstance(payload, dict) else 0
        if not isinstance(flags, int) or not flags & (1 << 15):
            return webhook
        parts = urlsplit(webhook)
        query = dict(parse_qsl(parts.query, keep_blank_values=True))
        query["with_components"] = "true"
        if wait:
            query["wait"] = "true"
        return urlunsplit((
            parts.scheme,
            parts.netloc,
            parts.path,
            urlencode(query),
            parts.fragment,
        ))

    def _local_icon(self, payload, formatter):
        """Resolve an exact packaged icon and its thumbnail media object."""

        thumbnail = self._thumbnail_media(payload)
        if thumbnail is None:
            return None

        url = str(thumbnail.get("url") or "")
        prefix = "notifinho-asset://"
        if not url.startswith(prefix):
            return None

        relative = url[len(prefix):].lstrip("/")
        allowed = (
            set(formatter.PRODUCT_ICONS.values())
            | set(formatter.DISCORD_PRODUCT_ICONS.values())
        )
        if relative not in allowed:
            return None

        root = self.ICON_DIR.resolve()
        path = (root / relative).resolve()
        try:
            path.relative_to(root)
        except ValueError:
            return None

        if not path.is_file():
            log.warning(
                "Packaged Discord icon is unavailable: %s",
                relative,
            )
            return None

        filename = Path(relative).name
        return filename, path, thumbnail

    @staticmethod
    def _returned_message(response):
        """Return only a decoded Discord message object."""

        try:
            message = response.json()
        except (TypeError, ValueError, AttributeError):
            return None
        return message if isinstance(message, dict) else None

    @staticmethod
    def _component_types(value):
        """Collect only numeric component types from returned message JSON."""

        types = []

        def visit(item):
            if isinstance(item, dict):
                component_type = item.get("type")
                if isinstance(component_type, int):
                    types.append(component_type)
                for child in item.values():
                    visit(child)
            elif isinstance(item, list):
                for child in item:
                    visit(child)

        visit(value)
        return types

    @staticmethod
    def _discord_media_url_kind(value):
        """Classify a media URL without retaining or logging its value."""

        url = str(value or "")
        if url.startswith("attachment://"):
            return "attachment"
        try:
            parts = urlsplit(url)
        except ValueError:
            return "other"
        host = str(parts.hostname or "").casefold()
        if (
            parts.scheme.casefold() == "https"
            and host in {"cdn.discordapp.com", "media.discordapp.net"}
            and parts.path.startswith(
                ("/attachments/", "/ephemeral-attachments/")
            )
        ):
            return "discord_cdn"
        return "other" if url else "none"

    @classmethod
    def _discord_attachment_identity(cls, value):
        """Return an attachment id and filename from a Discord CDN URL."""

        if cls._discord_media_url_kind(value) != "discord_cdn":
            return None
        parts = urlsplit(str(value))
        path = [unquote(item) for item in parts.path.split("/") if item]
        if len(path) < 4:
            return None
        return path[-2], path[-1]

    @classmethod
    def _attachment_inspection(cls, response, filename):
        """Verify and summarize one returned Discord thumbnail attachment."""

        message = cls._returned_message(response)
        attachments = (
            message.get("attachments", [])
            if isinstance(message, dict)
            else []
        )
        if not isinstance(attachments, list):
            attachments = []

        safe_attachments = [
            {
                "id": str(item.get("id") or ""),
                "filename": str(item.get("filename") or ""),
                "content_type": str(item.get("content_type") or ""),
                "url_present": bool(item.get("url")),
                "proxy_url_present": bool(item.get("proxy_url")),
            }
            for item in attachments
            if isinstance(item, dict)
        ]
        media = (
            cls._thumbnail_media(message)
            if isinstance(message, dict)
            else None
        )
        media = media if isinstance(media, dict) else {}
        diagnostics = {
            "response_status": int(
                getattr(response, "status_code", 0) or 0
            ),
            "attachments": safe_attachments,
            "component_types": cls._component_types(
                message.get("components", [])
                if isinstance(message, dict)
                else []
            ),
            "thumbnail_media_keys": sorted(
                str(key) for key in media
            ),
            "media_attachment_id": str(
                media.get("attachment_id") or ""
            ),
            "media_url_kind": cls._discord_media_url_kind(
                media.get("url")
            ),
            "media_proxy_url_kind": cls._discord_media_url_kind(
                media.get("proxy_url")
            ),
        }

        media_url = str(media.get("url") or "")
        media_proxy_url = str(media.get("proxy_url") or "")
        media_url_kind = cls._discord_media_url_kind(media_url)
        media_proxy_url_kind = cls._discord_media_url_kind(
            media_proxy_url
        )
        media_attachment_id = str(media.get("attachment_id") or "")
        media_content_type = str(
            media.get("content_type") or ""
        ).casefold()
        media_identities = {
            identity
            for identity in (
                cls._discord_attachment_identity(media_url),
                cls._discord_attachment_identity(media_proxy_url),
            )
            if identity is not None
        }
        media_identity_verified = any(
            item_id == media_attachment_id
            and item_filename == str(filename)
            for item_id, item_filename in media_identities
        )

        # Components V2 may return the uploaded thumbnail exclusively as an
        # unfurled media item and leave the top-level attachments array empty.
        # In that response shape, fail closed unless Discord supplied a PNG,
        # a Discord-hosted attachment URL, and an attachment id that matches
        # both the CDN path and the exact packaged filename.
        if not attachments:
            return (
                bool(media)
                and media_content_type == "image/png"
                and bool(media_attachment_id)
                and media_identity_verified
            ), diagnostics

        attachment = next(
            (
                item
                for item in attachments
                if isinstance(item, dict)
                and str(item.get("filename") or "") == str(filename)
            ),
            None,
        )
        if attachment is None or not media:
            return False, diagnostics

        attachment_id = str(attachment.get("id") or "")
        content_type = str(
            attachment.get("content_type") or ""
        ).casefold()
        attachment_urls = [
            attachment.get("url"),
            attachment.get("proxy_url"),
        ]
        valid_attachment_urls = [
            url
            for url in attachment_urls
            if cls._discord_media_url_kind(url) == "discord_cdn"
        ]
        if (
            not attachment_id
            or content_type != "image/png"
            or not valid_attachment_urls
        ):
            return False, diagnostics

        if not (
            media_url_kind in {"attachment", "discord_cdn"}
            or media_proxy_url_kind == "discord_cdn"
        ):
            return False, diagnostics

        if attachment_id and media_attachment_id == attachment_id:
            return True, diagnostics

        if media_url == f"attachment://{filename}":
            return True, diagnostics

        attachment_identities = {
            identity
            for identity in (
                cls._discord_attachment_identity(url)
                for url in valid_attachment_urls
            )
            if identity is not None
        }
        linked = any(
            item_id == attachment_id
            and item_filename == str(filename)
            for item_id, item_filename in (
                attachment_identities & media_identities
            )
        )
        return linked, diagnostics

    @classmethod
    def _attachment_verified(cls, response, filename):
        """Confirm Discord retained and linked one uploaded thumbnail."""

        verified, _diagnostics = cls._attachment_inspection(
            response,
            filename,
        )
        return verified

    @classmethod
    def _thumbnail_media(cls, payload):
        """Find legacy embed or Components V2 thumbnail media recursively."""

        if not isinstance(payload, dict):
            return None

        embeds = payload.get("embeds")
        if isinstance(embeds, list) and embeds:
            thumbnail = embeds[0].get("thumbnail")
            if isinstance(thumbnail, dict) and thumbnail.get("url"):
                return thumbnail

        def visit(value):
            if isinstance(value, dict):
                if value.get("type") == 11:
                    media = value.get("media")
                    if isinstance(media, dict) and media.get("url"):
                        return media
                for child in value.values():
                    found = visit(child)
                    if found is not None:
                        return found
            elif isinstance(value, list):
                for child in value:
                    found = visit(child)
                    if found is not None:
                        return found
            return None

        return visit(payload.get("components"))
