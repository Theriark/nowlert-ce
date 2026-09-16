"""Validation and normalization for v2 platform destination settings."""

from __future__ import annotations

import json
import re

from urllib.parse import urlsplit


OUTPUT_TYPES = {"discord", "teams", "slack", "webhook"}
_HEADER = re.compile(r"^[A-Za-z0-9!#$%&'*+.^_`|~-]{1,64}$")
_FORBIDDEN_HEADERS = {
    "authorization",
    "connection",
    "content-length",
    "cookie",
    "host",
    "proxy-authorization",
    "te",
    "transfer-encoding",
    "upgrade",
}


def normalize_output_settings(
    output_type: str,
    settings: dict | None,
    *,
    require_complete: bool = False,
) -> dict:
    """Return bounded canonical settings or raise a non-secret validation error."""

    kind = str(output_type or "").strip().casefold()
    if kind not in OUTPUT_TYPES:
        raise ValueError("unsupported destination output type")
    if settings is None:
        settings = {}
    if not isinstance(settings, dict):
        raise ValueError("destination settings must be an object")

    common = {}
    if "channel_name" in settings:
        channel_name = str(settings.get("channel_name") or "").strip()
        if not channel_name or len(channel_name) > 120:
            raise ValueError("destination channel name must contain 1 to 120 characters")
        common["channel_name"] = channel_name
    specific = {key: value for key, value in settings.items() if key != "channel_name"}
    validators = {
        "discord": _discord,
        "teams": _teams,
        "slack": _slack,
        "webhook": _webhook,
    }
    normalized = {**validators[kind](specific, require_complete), **common}
    encoded = json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    if len(encoded.encode("utf-8")) > 16 * 1024:
        raise ValueError("destination settings must not exceed 16384 bytes")
    return normalized


def validate_public_https_url(value, field: str) -> str:
    """Validate the structural, credential-free part of an outbound URL."""

    text = str(value or "").strip()
    try:
        parsed = urlsplit(text)
    except ValueError as error:
        raise ValueError(f"{field} must be a valid HTTPS URL") from error
    if (
        parsed.scheme.casefold() != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise ValueError(f"{field} must be a credential-free HTTPS URL")
    if len(text) > 2048:
        raise ValueError(f"{field} must not exceed 2048 characters")
    return text


def _discord(settings, _complete):
    _unknown(settings, {"components_v2"})
    return {"components_v2": _boolean(settings, "components_v2", True)}


def _teams(settings, _complete):
    _unknown(settings, set())
    return {}


def _slack(settings, _complete):
    _unknown(settings, {"include_metadata"})
    return {"include_metadata": _boolean(settings, "include_metadata", True)}


def _webhook(settings, _complete):
    allowed = {
        "allow_private_network",
        "body_template",
        "headers",
        "method",
        "sign_hmac",
        "timeout_seconds",
    }
    _unknown(settings, allowed)
    method = str(settings.get("method", "POST")).strip().upper()
    if method not in {"POST", "PUT", "PATCH"}:
        raise ValueError("webhook method must be POST, PUT, or PATCH")
    headers = settings.get("headers", {})
    if not isinstance(headers, dict) or len(headers) > 32:
        raise ValueError("webhook headers must be an object with at most 32 entries")
    normalized_headers = {}
    for key, value in headers.items():
        name = str(key or "").strip()
        lowered = name.casefold()
        if not _HEADER.fullmatch(name) or lowered in _FORBIDDEN_HEADERS:
            raise ValueError(f"webhook header is not allowed: {name[:64]}")
        text = str(value or "").strip()
        if not text or "\r" in text or "\n" in text or len(text) > 512:
            raise ValueError(f"webhook header {name} has an invalid value")
        normalized_headers[name] = text
    template = settings.get("body_template")
    if template is not None:
        if not isinstance(template, dict):
            raise ValueError("webhook body_template must be an object")
        _bounded_template(template)
    result = {
        "method": method,
        "headers": normalized_headers,
        "timeout_seconds": _integer(settings, "timeout_seconds", 15, 1, 30),
        "sign_hmac": _boolean(settings, "sign_hmac", False),
        "allow_private_network": _boolean(
            settings,
            "allow_private_network",
            False,
        ),
    }
    if template is not None:
        result["body_template"] = template
    return result


def _unknown(settings, allowed):
    unknown = sorted(str(key) for key in set(settings) - allowed)
    if unknown:
        raise ValueError(f"unsupported destination setting: {unknown[0]}")


def _boolean(settings, key, default):
    value = settings.get(key, default)
    if not isinstance(value, bool):
        raise ValueError(f"destination setting {key} must be true or false")
    return value


def _integer(settings, key, default, minimum, maximum):
    value = settings.get(key, default)
    if isinstance(value, bool):
        raise ValueError(f"destination setting {key} must be an integer")
    try:
        number = int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"destination setting {key} must be an integer") from error
    if not minimum <= number <= maximum:
        raise ValueError(
            f"destination setting {key} must be between {minimum} and {maximum}"
        )
    return number


def _bounded_template(value, depth=0):
    if depth > 6:
        raise ValueError("webhook body_template must not exceed six levels")
    if isinstance(value, dict):
        if len(value) > 64:
            raise ValueError("webhook body_template contains too many keys")
        for key, item in value.items():
            if not str(key) or len(str(key)) > 128:
                raise ValueError("webhook body_template contains an invalid key")
            _bounded_template(item, depth + 1)
    elif isinstance(value, list):
        if len(value) > 128:
            raise ValueError("webhook body_template contains too many items")
        for item in value:
            _bounded_template(item, depth + 1)
    elif isinstance(value, str):
        if len(value) > 4096:
            raise ValueError("webhook body_template text is too long")
    elif value is not None and not isinstance(value, (bool, int, float)):
        raise ValueError("webhook body_template must contain JSON values")
