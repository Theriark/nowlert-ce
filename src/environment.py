"""Nowlert environment-variable compatibility helpers."""

from __future__ import annotations

import os

from collections.abc import Mapping


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
    legacy: str,
    *,
    default: str | None = None,
    environment: Mapping[str, str] | None = None,
) -> str | None:
    """Prefer a Nowlert variable and fall back to its Notifinho alias."""

    return first_environment(
        primary,
        legacy,
        default=default,
        environment=environment,
    )


def compatible_environment_names(name: str) -> tuple[str, ...]:
    """Return a configured variable followed by its rebrand counterpart."""

    if name.startswith("NOWLERT_"):
        return name, f"NOTIFINHO_{name.removeprefix('NOWLERT_')}"

    if name.startswith("NOTIFINHO_"):
        return name, f"NOWLERT_{name.removeprefix('NOTIFINHO_')}"

    return (name,)
