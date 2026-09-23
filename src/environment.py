"""Nowlert environment-variable helpers."""

from __future__ import annotations

import os
import stat

from collections.abc import Mapping
from pathlib import Path


def first_environment(
    *names: str,
    default: str | None = None,
    environment: Mapping[str, str] | None = None,
) -> str | None:
    """Return the first explicitly configured environment variable."""

    source = os.environ if environment is None else environment

    for name in names:
        if name in source:
            return source[name]

    return default


def compatible_environment(
    primary: str,
    alternate: str | None = None,
    *,
    default: str | None = None,
    environment: Mapping[str, str] | None = None,
) -> str | None:
    """Return the configured Nowlert variable.

    ``alternate`` remains optional for callers that support two current
    Nowlert settings, while duplicate names are collapsed.
    """

    return first_environment(
        primary,
        *(name for name in (alternate,) if name and name != primary),
        default=default,
        environment=environment,
    )


def compatible_environment_names(name: str) -> tuple[str, ...]:
    """Return the configured environment variable name."""
    return (name,)



def secret_environment(
    name: str,
    *,
    default_file: str | os.PathLike[str] | None = None,
    default: str | None = None,
    environment: Mapping[str, str] | None = None,
    maximum_bytes: int = 64 * 1024,
) -> str | None:
    """Read a mounted secret file before falling back to an environment value."""

    source = os.environ if environment is None else environment
    file_variable = f"{name}_FILE"
    explicit_file = str(source.get(file_variable) or "").strip()

    if explicit_file:
        return _read_secret_file(explicit_file, label=file_variable, maximum_bytes=maximum_bytes)

    if default_file:
        path = Path(default_file)
        if path.exists():
            return _read_secret_file(path, label=str(path), maximum_bytes=maximum_bytes)

    return first_environment(name, default=default, environment=source)


def _read_secret_file(
    value: str | os.PathLike[str],
    *,
    label: str,
    maximum_bytes: int,
) -> str:
    path = Path(value)
    if path.is_symlink():
        raise ValueError(f"{label} must not reference a symbolic link")

    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except FileNotFoundError as error:
        raise ValueError(f"{label} secret file does not exist") from error
    except OSError as error:
        raise ValueError(f"{label} secret file could not be opened") from error

    try:
        details = os.fstat(descriptor)
        if not stat.S_ISREG(details.st_mode):
            raise ValueError(f"{label} must reference a regular file")
        with os.fdopen(descriptor, "rb") as stream:
            descriptor = -1
            payload = stream.read(max(1, int(maximum_bytes)) + 1)
    finally:
        if descriptor >= 0:
            os.close(descriptor)

    if len(payload) > max(1, int(maximum_bytes)):
        raise ValueError(f"{label} secret file is too large")
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(f"{label} secret file must contain UTF-8 text") from error
    if "\x00" in text:
        raise ValueError(f"{label} secret file contains an invalid NUL byte")
    return text.rstrip("\r\n")
