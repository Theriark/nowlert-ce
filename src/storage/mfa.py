"""TOTP helpers for local-account multi-factor authentication."""

from __future__ import annotations

import base64
import hashlib
import hmac
import io
import re
import secrets

import qrcode
import qrcode.image.svg
import struct
import time

from urllib.parse import quote


_CODE = re.compile(r"^[0-9]{6}$")


def generate_totp_secret() -> str:
    """Return a 160-bit Base32 secret suitable for authenticator applications."""

    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def totp_code(secret: str, *, timestamp: float | None = None) -> str:
    """Generate the six-digit RFC 6238 code for one timestamp."""

    value = str(secret or "").strip().replace(" ", "").upper()
    if not value:
        raise ValueError("MFA secret is empty")
    padded = value + "=" * ((8 - len(value) % 8) % 8)
    try:
        key = base64.b32decode(padded, casefold=True)
    except Exception as error:
        raise ValueError("MFA secret is invalid") from error
    moment = time.time() if timestamp is None else float(timestamp)
    counter = max(0, int(moment) // 30)
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    number = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return f"{number % 1_000_000:06d}"


def verify_totp(
    secret: str,
    code: str,
    *,
    timestamp: float | None = None,
    window: int = 1,
) -> bool:
    """Verify a code with one adjacent 30-second window in either direction."""

    supplied = str(code or "").strip()
    if _CODE.fullmatch(supplied) is None:
        return False
    moment = time.time() if timestamp is None else float(timestamp)
    for offset in range(-max(0, int(window)), max(0, int(window)) + 1):
        candidate = totp_code(secret, timestamp=moment + offset * 30)
        if hmac.compare_digest(candidate, supplied):
            return True
    return False


def provisioning_uri(username: str, secret: str, *, issuer: str = "Nowlert") -> str:
    """Return a standards-compatible otpauth URI without external dependencies."""

    account = str(username or "account")
    provider = str(issuer or "Nowlert")
    label = quote(f"{provider}:{account}", safe="")
    return (
        f"otpauth://totp/{label}?secret={quote(str(secret), safe='')}"
        f"&issuer={quote(provider, safe='')}&algorithm=SHA1&digits=6&period=30"
    )


def provisioning_qr_data_uri(uri: str) -> str:
    """Render a compact SVG QR data URI for an authenticator provisioning URI."""

    value = str(uri or "").strip()
    if not value.startswith("otpauth://"):
        raise ValueError("MFA provisioning URI is invalid")
    image = qrcode.make(
        value,
        image_factory=qrcode.image.svg.SvgPathImage,
        box_size=6,
        border=2,
    )
    stream = io.BytesIO()
    image.save(stream)
    encoded = base64.b64encode(stream.getvalue()).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"
