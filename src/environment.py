"""Nowlert environment-variable helpers."""

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
