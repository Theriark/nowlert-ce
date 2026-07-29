"""Nowlert environment-variable compatibility regressions."""

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


def test_primary_environment_variable_has_precedence():
    value = compatible_environment(
        "NOWLERT_STATE_DIR",
        "NOTIFINHO_STATE_DIR",
        environment={
            "NOWLERT_STATE_DIR": "/new",
            "NOTIFINHO_STATE_DIR": "/legacy",
        },
    )

    assert value == "/new"


def test_explicit_empty_primary_value_has_precedence():
    value = compatible_environment(
        "NOWLERT_AVAILABLE_VERSION",
        "NOTIFINHO_AVAILABLE_VERSION",
        default="fallback",
        environment={
            "NOWLERT_AVAILABLE_VERSION": "",
            "NOTIFINHO_AVAILABLE_VERSION": "9.9.9",
        },
    )

    assert value == ""


def test_legacy_environment_variable_remains_supported():
    value = compatible_environment(
        "NOWLERT_STATE_DIR",
        "NOTIFINHO_STATE_DIR",
        environment={"NOTIFINHO_STATE_DIR": "/legacy"},
    )

    assert value == "/legacy"


def test_default_is_used_when_neither_variable_exists():
    value = compatible_environment(
        "NOWLERT_STATE_DIR",
        "NOTIFINHO_STATE_DIR",
        default="/default",
        environment={},
    )

    assert value == "/default"


def test_first_environment_preserves_requested_precedence():
    value = first_environment(
        "NOWLERT_ICON_DIR",
        "NOWLERT_DISCORD_ICON_DIR",
        "NOTIFINHO_ICON_DIR",
        environment={
            "NOWLERT_DISCORD_ICON_DIR": "/new-discord",
            "NOTIFINHO_ICON_DIR": "/legacy-general",
        },
    )

    assert value == "/new-discord"


def test_compatible_names_support_both_rebrand_directions():
    assert compatible_environment_names("NOWLERT_SMTP_PASSWORD") == (
        "NOWLERT_SMTP_PASSWORD",
        "NOTIFINHO_SMTP_PASSWORD",
    )
    assert compatible_environment_names("NOTIFINHO_SMTP_PASSWORD") == (
        "NOTIFINHO_SMTP_PASSWORD",
        "NOWLERT_SMTP_PASSWORD",
    )
    assert compatible_environment_names("CUSTOM_PASSWORD") == (
        "CUSTOM_PASSWORD",
    )


def test_legacy_smtp_configuration_accepts_new_variable():
    password = _read_password(
        SMTPPasswordConfiguration("NOTIFINHO_SMTP_PASSWORD"),
        {"NOWLERT_SMTP_PASSWORD": "new-secret"},
    )

    assert password == b"new-secret"


def test_new_smtp_configuration_accepts_legacy_variable():
    password = _read_password(
        SMTPPasswordConfiguration("NOWLERT_SMTP_PASSWORD"),
        {"NOTIFINHO_SMTP_PASSWORD": "legacy-secret"},
    )

    assert password == b"legacy-secret"


def test_configured_smtp_variable_has_precedence():
    password = _read_password(
        SMTPPasswordConfiguration("NOWLERT_SMTP_PASSWORD"),
        {
            "NOWLERT_SMTP_PASSWORD": "new-secret",
            "NOTIFINHO_SMTP_PASSWORD": "legacy-secret",
        },
    )

    assert password == b"new-secret"
