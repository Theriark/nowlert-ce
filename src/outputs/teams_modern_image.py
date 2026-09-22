"""Publish Teams Modern image cards through Nowlert's public WebUI."""

from __future__ import annotations

from io import BytesIO
import os
from pathlib import Path
import re
import secrets
import time
from urllib.parse import urlsplit

from PIL import Image

from storage.runtime import state_directory


TEAMS_MODERN_CARD_ROUTE_PREFIX = "/ui/teams-modern-cards/"
TEAMS_MODERN_CARD_RETENTION_SECONDS = 90 * 24 * 60 * 60
TEAMS_MODERN_CARD_MAX_DIMENSION = 1024
_CARD_FILENAME = re.compile(r"^[0-9a-f]{48}\.png$")


def teams_modern_public_base(configuration) -> str:
    """Return a credential-free HTTPS public base URL or an empty string."""

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
    return value


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


def publish_teams_modern_image(
    configuration,
    image_bytes: bytes,
) -> str | None:
    """Persist one immutable rendered card and return its public HTTPS URL."""

    base = teams_modern_public_base(configuration)
    if not base or not image_bytes:
        return None

    try:
        directory = teams_modern_image_directory(configuration)
        directory.mkdir(parents=True, exist_ok=True)
        now = time.time()
        _cleanup(directory, now)

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

    return f"{base}{TEAMS_MODERN_CARD_ROUTE_PREFIX}{filename}"


def load_teams_modern_image(
    configuration,
    route: str,
) -> bytes | None:
    """Resolve only a bounded unguessable card-image route from state."""

    value = str(route or "")
    if not value.startswith(TEAMS_MODERN_CARD_ROUTE_PREFIX):
        return None
    filename = value[len(TEAMS_MODERN_CARD_ROUTE_PREFIX):]
    if not _CARD_FILENAME.fullmatch(filename):
        return None

    try:
        path = teams_modern_image_directory(configuration) / filename
        stat = path.stat()
        if (
            time.time() - stat.st_mtime
            > TEAMS_MODERN_CARD_RETENTION_SECONDS
        ):
            path.unlink(missing_ok=True)
            return None
        return path.read_bytes()
    except (OSError, ValueError):
        return None
