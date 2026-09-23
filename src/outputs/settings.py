"""Validation and normalization for v2 platform destination settings."""

from __future__ import annotations

import ipaddress
import json
import re

from urllib.parse import urlsplit


OUTPUT_TYPES = {"discord", "teams", "slack", "webhook", "email"}
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
        "email": _email,
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
    _unknown(settings, {"message_style"})
    style = str(
        settings.get("message_style", "modern") or ""
    ).strip().casefold()
    if style not in {"modern", "classic"}:
        raise ValueError(
            "teams message_style must be modern or classic"
        )
    return {"message_style": style}


def _slack(settings, _complete):
    _unknown(settings, {"include_metadata", "message_style"})
    style = str(
        settings.get("message_style", "classic") or ""
    ).strip().casefold()
    if style not in {"modern", "classic"}:
        raise ValueError(
            "slack message_style must be modern or classic"
        )
    return {
        "message_style": style,
        "include_metadata": _boolean(
            settings,
            "include_metadata",
            True,
        ),
    }


def _webhook(settings, _complete):
    # The normal editor exposes only message_style. Older releases exposed
    # raw HTTP controls; accept and validate those only so existing records
    # remain deliverable until they are saved through the simplified editor.
    legacy = {
        "allow_private_network",
        "body_template",
        "headers",
        "method",
        "sign_hmac",
        "timeout_seconds",
    }
    _unknown(settings, {"message_style", *legacy})

    style = str(settings.get("message_style", "modern") or "").strip().casefold()
    if style not in {"modern", "classic"}:
        raise ValueError("webhook message_style must be modern or classic")
    result = {"message_style": style}

    if not any(key in settings for key in legacy):
        return result

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

    result.update(
        {
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
    )
    if template is not None:
        result["body_template"] = template
    return result



_EMAIL_LOCAL = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]{1,64}$")
_DOMAIN_LABEL = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")


def _email(settings, _complete):
    _unknown(settings, {
        "server", "port", "security", "username", "from_address",
        "to", "cc", "reply_to", "allow_private_network",
    })
    server = _smtp_host(settings.get("server"))
    security = str(settings.get("security", "starttls") or "").strip().casefold()
    if security not in {"starttls", "tls"}:
        raise ValueError("email security must be starttls or tls")
    port = _integer(settings, "port", 465 if security == "tls" else 587, 1, 65535)
    username = _smtp_username(settings.get("username"))
    from_address = _email_address(settings.get("from_address"), "email from_address")
    to_addresses = _email_addresses(settings.get("to"), "email to", required=True)
    cc_addresses = _email_addresses(settings.get("cc", []), "email cc", required=False)
    if len(to_addresses) + len(cc_addresses) > 100:
        raise ValueError("email destination must not exceed 100 recipients")
    reply_to = ""
    if str(settings.get("reply_to") or "").strip():
        reply_to = _email_address(settings.get("reply_to"), "email reply_to")
    return {
        "server": server, "port": port, "security": security,
        "username": username, "from_address": from_address,
        "to": to_addresses, "cc": cc_addresses, "reply_to": reply_to,
        "allow_private_network": _boolean(settings, "allow_private_network", False),
    }


def _smtp_host(value) -> str:
    text = str(value or "").strip()
    if not text or len(text) > 253 or any(ch.isspace() for ch in text) or any(ch in text for ch in "/?#@"):
        raise ValueError("email server must be a hostname or IP address")
    candidate = text[1:-1] if text.startswith("[") and text.endswith("]") else text
    try:
        return str(ipaddress.ip_address(candidate))
    except ValueError:
        pass
    try:
        ascii_host = candidate.rstrip(".").encode("idna").decode("ascii")
    except UnicodeError as error:
        raise ValueError("email server must be a valid hostname") from error
    labels = ascii_host.split(".")
    if not labels or any(not _DOMAIN_LABEL.fullmatch(label) for label in labels):
        raise ValueError("email server must be a valid hostname")
    return ascii_host.casefold()


def _smtp_username(value) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if len(text) > 320 or "\r" in text or "\n" in text:
        raise ValueError("email username must not exceed 320 characters")
    return text


def _email_addresses(value, field: str, *, required: bool) -> list[str]:
    if value in (None, ""):
        raw = []
    elif isinstance(value, str):
        raw = [item.strip() for item in value.split(",")]
    elif isinstance(value, list):
        raw = [str(item or "").strip() for item in value]
    else:
        raise ValueError(f"{field} must be a list or comma-separated string")
    normalized, seen = [], set()
    for item in raw:
        if not item:
            continue
        address = _email_address(item, field)
        key = address.casefold()
        if key not in seen:
            normalized.append(address)
            seen.add(key)
    if required and not normalized:
        raise ValueError(f"{field} must contain at least one address")
    if len(normalized) > 100:
        raise ValueError(f"{field} must not exceed 100 addresses")
    return normalized


def _email_address(value, field: str) -> str:
    text = str(value or "").strip()
    if not text or len(text) > 320 or "\r" in text or "\n" in text or text.count("@") != 1:
        raise ValueError(f"{field} must be a valid email address")
    local, domain = text.rsplit("@", 1)
    if not _EMAIL_LOCAL.fullmatch(local):
        raise ValueError(f"{field} must be a valid email address")
    try:
        ascii_domain = domain.rstrip(".").encode("idna").decode("ascii")
    except UnicodeError as error:
        raise ValueError(f"{field} must be a valid email address") from error
    labels = ascii_domain.split(".")
    if not ascii_domain or len(ascii_domain) > 253 or any(not _DOMAIN_LABEL.fullmatch(label) for label in labels):
        raise ValueError(f"{field} must be a valid email address")
    return f"{local}@{ascii_domain.casefold()}"


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
