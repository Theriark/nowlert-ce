"""Publish Teams Modern image cards through Nowlert's public health path."""

from __future__ import annotations

from io import BytesIO
import os
from pathlib import Path
import re
import secrets
import time
from urllib.parse import urlsplit, urlunsplit

from PIL import Image

from environment import first_environment
from storage.runtime import state_directory


TEAMS_MODERN_CARD_PUBLIC_PATH = "/api/health"
TEAMS_MODERN_CARD_PUBLIC_PREFIX = "/api/health/teams-modern-card/"
TEAMS_MODERN_CARD_URL_PREFIX = TEAMS_MODERN_CARD_PUBLIC_PREFIX
TEAMS_MODERN_CARD_RETENTION_SECONDS = 90 * 24 * 60 * 60
TEAMS_MODERN_CARD_MAX_DIMENSION = 1024
_CARD_FILENAME = re.compile(r"^[0-9a-f]{48}\.png$")


def teams_modern_public_base(configuration) -> str:
    """Return a credential-free HTTPS origin or an empty string."""

    value = str(
        first_environment(
            "NOWLERT_TEAMS_PUBLIC_BASE_URL",
            default="",
        )
        or ""
    ).strip().rstrip("/")
    if not value:
        value = str(
            configuration.get("webui", "public_url", default="") or ""
        ).strip().rstrip("/")
    if not value:
        return ""

    try:
        parsed = urlsplit(value)
    except ValueError:
        return ""
    if (
        parsed.scheme.casefold() != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        return ""

    return urlunsplit(
        (parsed.scheme, parsed.netloc, "", "", "")
    ).rstrip("/")


def teams_modern_image_directory(configuration) -> Path:
    return state_directory(configuration) / "teams-modern-cards"


def normalize_teams_modern_image(image_bytes: bytes) -> bytes:
    """Keep the exact Modern visual while respecting Teams image bounds."""

    with Image.open(BytesIO(image_bytes)) as source:
        source.load()
        image = source.copy()
    longest = max(image.size)
    if longest > TEAMS_MODERN_CARD_MAX_DIMENSION:
        ratio = TEAMS_MODERN_CARD_MAX_DIMENSION / longest
        size = (
            max(1, round(image.width * ratio)),
            max(1, round(image.height * ratio)),
        )
        image = image.resize(size, Image.Resampling.LANCZOS)

    output = BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()


def _cleanup(directory: Path, now: float) -> None:
    cutoff = now - TEAMS_MODERN_CARD_RETENTION_SECONDS
    try:
        candidates = tuple(directory.glob("*.png"))
    except OSError:
        return
    for candidate in candidates:
        try:
            if candidate.stat().st_mtime < cutoff:
                candidate.unlink(missing_ok=True)
        except OSError:
            continue


def publish_teams_modern_image(configuration, image_bytes: bytes) -> str | None:
    """Persist one immutable rendered card and return its public HTTPS URL."""

    base = teams_modern_public_base(configuration)
    if not base or not image_bytes:
        return None

    try:
        directory = teams_modern_image_directory(configuration)
        directory.mkdir(parents=True, exist_ok=True)
        _cleanup(directory, time.time())

        filename = f"{secrets.token_hex(24)}.png"
        destination = directory / filename
        temporary = directory / f".{filename}.{secrets.token_hex(4)}.tmp"
        temporary.write_bytes(normalize_teams_modern_image(image_bytes))
        os.chmod(temporary, 0o600)
        os.replace(temporary, destination)
    except (OSError, ValueError):
        try:
            temporary.unlink(missing_ok=True)
        except (OSError, UnboundLocalError):
            pass
        return None

    return f"{base}{TEAMS_MODERN_CARD_URL_PREFIX}{filename}"


def load_teams_modern_image(configuration, filename: str) -> bytes | None:
    """Resolve only one bounded unguessable image token from state."""

    value = str(filename or "")
    if not _CARD_FILENAME.fullmatch(value):
        return None

    try:
        path = teams_modern_image_directory(configuration) / value
        stat = path.stat()
        if time.time() - stat.st_mtime > TEAMS_MODERN_CARD_RETENTION_SECONDS:
            path.unlink(missing_ok=True)
            return None
        return path.read_bytes()
    except (OSError, ValueError):
        return None
