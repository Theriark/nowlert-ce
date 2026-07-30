"""Nowlert environment-variable regressions."""

from __future__ import annotations

from environment import (
    compatible_environment,
    compatible_environment_names,
    first_environment,
)
from inputs.smtp_security import _read_password


class SMTPPasswordConfiguration:
    def __init__(self, password_env: str):
        self.password_env = password_env

    def get(self, *keys, default=None):
        values = {
            ("smtp", "auth", "password_env"): self.password_env,
            ("smtp", "auth", "password_file"): "",
        }
        return values.get(tuple(keys), default)


def test_configured_environment_variable_is_returned():
    value = compatible_environment(
        "NOWLERT_STATE_DIR",
        environment={"NOWLERT_STATE_DIR": "/state"},
    )

    assert value == "/state"


def test_explicit_empty_primary_value_has_precedence():
    value = compatible_environment(
        "NOWLERT_AVAILABLE_VERSION",
        default="fallback",
        environment={"NOWLERT_AVAILABLE_VERSION": ""},
    )

    assert value == ""


def test_default_is_used_when_variable_does_not_exist():
    value = compatible_environment(
        "NOWLERT_STATE_DIR",
        default="/default",
        environment={},
    )

    assert value == "/default"


def test_first_environment_preserves_requested_precedence():
    value = first_environment(
        "NOWLERT_ICON_DIR",
        "NOWLERT_DISCORD_ICON_DIR",
        environment={
            "NOWLERT_DISCORD_ICON_DIR": "/new-discord",
        },
    )

    assert value == "/new-discord"


def test_compatible_names_returns_only_the_configured_name():
    assert compatible_environment_names("NOWLERT_SMTP_PASSWORD") == (
        "NOWLERT_SMTP_PASSWORD",
    )
    assert compatible_environment_names("CUSTOM_PASSWORD") == (
        "CUSTOM_PASSWORD",
    )


def test_smtp_configuration_reads_configured_variable():
    password = _read_password(
        SMTPPasswordConfiguration("NOWLERT_SMTP_PASSWORD"),
        {"NOWLERT_SMTP_PASSWORD": "new-secret"},
    )

    assert password == b"new-secret"
