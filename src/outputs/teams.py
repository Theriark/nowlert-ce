"""
Nowlert

teams.py

Microsoft Teams output.
"""

from __future__ import annotations

import json

import requests

from urllib.parse import urlsplit

from config import config
from outputs.discord import DiscordOutput
from outputs.teams_modern_image import publish_teams_modern_image
from formatters.teams import TeamsFormatter
from formatters.teams_classic_v1 import (
    TeamsClassicFormatter,
    TeamsClassicXenOrchestraFormatter,
)
from formatters.teams_generic import GenericTeamsFormatter
from formatters.teams_grafana import GrafanaTeamsFormatter
from formatters.teams_hardware import (
    DellIDRACTeamsFormatter,
    HPEILOTeamsFormatter,
    RedfishTeamsFormatter,
    SupermicroTeamsFormatter,
)
from formatters.teams_home_assistant import HomeAssistantTeamsFormatter
from formatters.teams_portainer import PortainerTeamsFormatter
from formatters.teams_proxmox import ProxmoxTeamsFormatter
from formatters.teams_qnap import QNAPTeamsFormatter
from formatters.teams_synology import SynologyTeamsFormatter
from formatters.teams_truenas import TrueNASTeamsFormatter
from formatters.teams_unifi import (
    UniFiDriveTeamsFormatter,
    UniFiNetworkTeamsFormatter,
    UniFiProtectTeamsFormatter,
)
from formatters.teams_zabbix import ZabbixTeamsFormatter
from logger import log
from models import Notification


def valid_teams_webhook(value) -> bool:
    """Return whether value is a complete, credential-free HTTPS URL."""

    webhook = str(value or "").strip()
    lowered = webhook.casefold()

    if not webhook or "paste_here" in lowered or webhook == "<configured>":
        return False

    try:
        parsed = urlsplit(webhook)
        return (
            parsed.scheme.casefold() == "https"
            and bool(parsed.hostname)
            and parsed.username is None
            and parsed.password is None
        )
    except ValueError:
        return False


class TeamsModernImageUnavailable(RuntimeError):
    """The exact Teams Modern rendered image cannot be published."""


class TeamsOutput:
    MAX_PAYLOAD_BYTES = 28 * 1024

    @staticmethod
    def payload_size(payload: dict) -> int:
        """Return the exact conservative JSON byte count used for guarding."""

        return len(
            json.dumps(
                payload,
                allow_nan=False,
            ).encode("utf-8")
        )

    def payload_too_large(self, payload: dict) -> bool:
        return self.payload_size(payload) > self.MAX_PAYLOAD_BYTES

    def __init__(self):

        self.default_formatter = GenericTeamsFormatter()
        self.discord_modern_output = DiscordOutput()

        self.source_formatters = {
            "xo": TeamsFormatter(),
            "grafana": GrafanaTeamsFormatter(),
            "portainer": PortainerTeamsFormatter(),
            "proxmox": ProxmoxTeamsFormatter(),
            "qnap": QNAPTeamsFormatter(),
            "synology": SynologyTeamsFormatter(),
            "truenas": TrueNASTeamsFormatter(),
            "unifi_drive": UniFiDriveTeamsFormatter(),
            "unifi_network": UniFiNetworkTeamsFormatter(),
            "unifi_protect": UniFiProtectTeamsFormatter(),
            "zabbix": ZabbixTeamsFormatter(),
            "redfish": RedfishTeamsFormatter(),
            "supermicro": SupermicroTeamsFormatter(),
            "hpe_ilo": HPEILOTeamsFormatter(),
            "dell_idrac": DellIDRACTeamsFormatter(),
            "home_assistant": HomeAssistantTeamsFormatter(),
        }

        self.classic_source_formatters = {
            "xo": TeamsClassicXenOrchestraFormatter(),
        }
        self.classic_formatter = TeamsClassicFormatter()

    def modern_image_payload(
        self,
        notification: Notification,
    ) -> dict | None:
        """Reuse the exact Discord Modern renderer for Microsoft Teams."""

        try:
            image = self.discord_modern_output.render_modern_image(
                notification
            )
        except Exception:
            log.exception(
                "Failed to render the shared Modern image for Teams."
            )
            return None
        if image is None:
            return None

        image_url = publish_teams_modern_image(config, image)
        if not image_url:
            log.error(
                "Teams Modern image parity is unavailable because no "
                "credential-free HTTPS media origin is configured or the "
                "card-image cache is not writable."
            )
            return None

        title = (
            notification.title
            or notification.subject
            or notification.job_name
            or "Nowlert notification"
        )
        alt_text = self.default_formatter._truncate(
            f"{notification.source or 'Nowlert'}: {title}",
            512,
        )
        return {
            "type": "message",
            "attachments": [
                {
                    "contentType": (
                        "application/vnd.microsoft.card.adaptive"
                    ),
                    "content": {
                        "$schema": (
                            "http://adaptivecards.io/schemas/"
                            "adaptive-card.json"
                        ),
                        "type": "AdaptiveCard",
                        "version": "1.4",
                        "msteams": {"width": "Full"},
                        "body": [
                            {
                                "type": "Image",
                                "url": image_url,
                                "altText": alt_text,
                                "size": "Stretch",
                                "horizontalAlignment": "Center",
                                "spacing": "None",
                            }
                        ],
                    },
                }
            ],
        }

    def modern_payload(
        self,
        notification: Notification,
        formatter=None,
    ) -> tuple[dict, bool]:
        """Return the exact shared Modern image or fail closed."""

        image_payload = self.modern_image_payload(notification)
        if image_payload is None:
            raise TeamsModernImageUnavailable(
                "Microsoft Teams Modern Card requires the shared rendered "
                "image to be published from a credential-free HTTPS origin. "
                "Configure NOWLERT_TEAMS_PUBLIC_BASE_URL or webui.public_url "
                "and ensure the state directory is writable."
            )
        return image_payload, True

    def send(
        self,
        notification: Notification,
        target: str = "default",
    ) -> bool:

        webhook = config.get(
            "outputs",
            "teams",
            target,
            "webhook",
        )

        if not valid_teams_webhook(webhook):

            log.error(
                "Teams webhook for '%s' is missing or invalid; "
                "configure a complete HTTPS URL.",
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
            # Legacy YAML-configured Teams outputs predate platform
            # message_style and keep their native Teams renderer. Platform
            # Modern destinations use modern_payload() and fail closed.
            payload = formatter._sanitize_payload(
                formatter.format(notification)
            )
        except Exception:
            log.exception(
                "Failed to format Teams notification."
            )
            return False

        payload_bytes = self.payload_size(payload)
        if payload_bytes > self.MAX_PAYLOAD_BYTES:
            log.error(
                "Teams payload is %s bytes and exceeds the %s-byte limit.",
                payload_bytes,
                self.MAX_PAYLOAD_BYTES,
            )
            return False

        log.info(
            "Sending %s-byte notification to Microsoft Teams (%s)...",
            payload_bytes,
            target,
        )

        log.info(
            "Teams formatter: %s",
            formatter.__class__.__name__,
        )

        if source.startswith("unifi_"):

            log.info(
                "%s formatter selected",
                formatter.label,
            )

        try:

            response = requests.post(
                webhook,
                json=payload,
                timeout=15,
            )

            if response.status_code >= 400:

                log.error(
                    "Teams returned %s",
                    response.status_code,
                )

                log.error(
                    "Teams response: %s",
                    response.text,
                )

                return False

            if response.status_code == 202:
                log.info(
                    "Teams accepted the notification with HTTP 202; "
                    "channel delivery is not confirmed."
                )
            else:
                log.info(
                    "Teams notification request completed successfully."
                )

            return True

        except Exception:

            log.exception(
                "Failed to send Teams notification."
            )

            return False
