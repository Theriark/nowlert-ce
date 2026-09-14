"""Register CE HTTP matrix parity without changing legacy shared-secret behavior."""

from __future__ import annotations

from dispatcher import Dispatcher
from inputs import http as _http
from logger import log
from parsers.grafana_webhook import is_envelope, parse_webhook


_GRAFANA_ENDPOINT = "/grafana/alerts"
_GRAFANA_APPLICATION = "grafana"

_MATRIX_SCOPED_SOURCES = {
    "network": "unifi_network",
    "protect": "unifi_protect",
    "drive": "unifi_drive",
    "portainer": "portainer",
    "proxmox": "proxmox",
    "synology": "synology",
    "grafana": "grafana",
}


def install() -> None:
    """Enable application-token auth for CE matrix HTTP sources and Grafana."""
    existing = _http.ENDPOINTS.get(_GRAFANA_ENDPOINT)
    if existing not in {None, _GRAFANA_APPLICATION}:
        raise RuntimeError(f"Grafana endpoint is already owned by {existing!r}")

    _http.ENDPOINTS[_GRAFANA_ENDPOINT] = _GRAFANA_APPLICATION
    _http.SCOPED_SOURCES.update(_MATRIX_SCOPED_SOURCES)

    if getattr(Dispatcher, "_ce_matrix_http_parity", False):
        return

    prior_parse_webhook = Dispatcher.parse_webhook

    def parse_registered_webhook(self, application: str, payload):
        if str(application or "").strip().casefold() != _GRAFANA_APPLICATION:
            return prior_parse_webhook(self, application, payload)
        if not is_envelope(payload):
            return None
        log.info("Detected Grafana Alerting webhook")
        return parse_webhook(payload)

    Dispatcher.parse_webhook = parse_registered_webhook
    Dispatcher._ce_matrix_http_parity = True


__all__ = ["install"]
