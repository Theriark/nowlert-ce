"""Outbound Email destination tests."""

from __future__ import annotations

import json
import smtplib
import socket

import pytest

from models import Notification
from outputs.platform import EmailPlatformAdapter
from outputs.settings import normalize_output_settings
from storage.destinations import Destination


class FakeSMTP:
    instances = []

    def __init__(self, host, port, timeout=None, context=None):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.context = context
        self.calls = []
        self.message = None
        self.from_addr = None
        self.to_addrs = None
        self.__class__.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def ehlo(self):
        self.calls.append(("ehlo",))
        return 250, b"ok"

    def starttls(self, context=None):
        self.calls.append(("starttls", context))
        return 220, b"ready"

    def login(self, username, password):
        self.calls.append(("login", username, password))
        return 235, b"authenticated"

    def send_message(self, message, from_addr=None, to_addrs=None):
        self.message = message
        self.from_addr = from_addr
        self.to_addrs = list(to_addrs or [])
        self.calls.append(("send_message",))
        return {}


class TemporarySMTP(FakeSMTP):
    def send_message(self, message, from_addr=None, to_addrs=None):
        raise smtplib.SMTPDataError(451, b"private upstream detail")


class AuthenticationFailureSMTP(FakeSMTP):
    def login(self, username, password):
        raise smtplib.SMTPAuthenticationError(535, b"private auth detail")


def public_resolver(host, port, **_kwargs):
    return [
        (
            socket.AF_INET,
            socket.SOCK_STREAM,
            6,
            "",
            ("8.8.8.8", int(port)),
        )
    ]


def private_resolver(host, port, **_kwargs):
    return [
        (
            socket.AF_INET,
            socket.SOCK_STREAM,
            6,
            "",
            ("10.0.0.10", int(port)),
        )
    ]


def notification():
    return Notification(
        source="grafana",
        category="alert",
        status="firing",
        title="Database latency",
        body="Database latency is above the alert threshold.",
        metadata={
            "event_id": "grafana-42",
            "severity": "critical",
        },
    )


def destination(settings=None):
    return Destination(
        id="email-destination",
        owner_user_id="owner",
        name="Operations email",
        output_type="email",
        settings=settings
        or {
            "server": "smtp.example.com",
            "port": 587,
            "security": "starttls",
            "username": "alerts@example.com",
            "from_address": "alerts@example.com",
            "to": ["noc@example.com"],
            "cc": ["service-owner@example.com"],
            "reply_to": "noreply@example.com",
        },
        shared=False,
        enabled=True,
        secret_configured=True,
        created_at=1,
        updated_at=1,
    )


def test_email_settings_normalize_tls_addresses_and_private_network_policy():
    assert normalize_output_settings(
        "email",
        {
            "server": "SMTP.Example.COM",
            "security": "tls",
            "from_address": "alerts@example.com",
            "to": "noc@example.com, noc@example.com",
            "cc": ["owner@example.com"],
            "reply_to": "noreply@example.com",
            "allow_private_network": True,
        },
    ) == {
        "server": "smtp.example.com",
        "port": 465,
        "security": "tls",
        "username": "",
        "from_address": "alerts@example.com",
        "to": ["noc@example.com"],
        "cc": ["owner@example.com"],
        "reply_to": "noreply@example.com",
        "allow_private_network": True,
    }


@pytest.mark.parametrize(
    "settings",
    [
        {
            "server": "https://smtp.example.com",
            "from_address": "alerts@example.com",
            "to": ["noc@example.com"],
        },
        {
            "server": "smtp.example.com",
            "security": "none",
            "from_address": "alerts@example.com",
            "to": ["noc@example.com"],
        },
        {
            "server": "smtp.example.com",
            "from_address": "alerts@example.com\r\nBcc: other@example.com",
            "to": ["noc@example.com"],
        },
    ],
)
def test_email_settings_reject_invalid_or_insecure_configuration(settings):
    with pytest.raises(ValueError):
        normalize_output_settings("email", settings)


def test_email_adapter_starttls_authentication_and_message_content():
    FakeSMTP.instances.clear()
    tls_context = object()
    adapter = EmailPlatformAdapter(
        smtp_factory=FakeSMTP,
        smtp_ssl_factory=FakeSMTP,
        resolver=public_resolver,
        tls_context_factory=lambda: tls_context,
    )
    secret = json.dumps({"password": "private-password"}).encode()

    preview = adapter.preview(destination(), notification())
    result = adapter.deliver(destination(), secret, notification())

    assert result.success is True
    assert preview.output_type == "email"
    assert preview.payload["to"] == ["noc@example.com"]
    assert "private-password" not in json.dumps(preview.payload)

    client = FakeSMTP.instances[-1]
    assert client.host == "smtp.example.com"
    assert client.port == 587
    assert ("starttls", tls_context) in client.calls
    assert ("login", "alerts@example.com", "private-password") in client.calls
    assert client.from_addr == "alerts@example.com"
    assert client.to_addrs == ["noc@example.com", "service-owner@example.com"]
    assert client.message["Subject"] == "Database latency"
    assert client.message["Reply-To"] == "noreply@example.com"
    assert "Severity: critical" in client.message.get_content()
    assert "Event ID: grafana-42" in client.message.get_content()
    assert "private-password" not in client.message.as_string()


def test_email_adapter_supports_implicit_tls_without_authentication():
    FakeSMTP.instances.clear()
    target = destination(
        {
            "server": "smtp.example.com",
            "security": "tls",
            "from_address": "alerts@example.com",
            "to": ["noc@example.com"],
        }
    )
    adapter = EmailPlatformAdapter(
        smtp_factory=FakeSMTP,
        smtp_ssl_factory=FakeSMTP,
        resolver=public_resolver,
        tls_context_factory=lambda: object(),
    )

    result = adapter.deliver(target, None, notification())

    assert result.success is True
    client = FakeSMTP.instances[-1]
    assert client.port == 465
    assert not any(call[0] == "starttls" for call in client.calls)
    assert not any(call[0] == "login" for call in client.calls)


def test_email_adapter_blocks_private_smtp_resolution_by_default():
    adapter = EmailPlatformAdapter(
        smtp_factory=FakeSMTP,
        smtp_ssl_factory=FakeSMTP,
        resolver=private_resolver,
        tls_context_factory=lambda: object(),
    )

    result = adapter.deliver(
        destination(
            {
                "server": "smtp.internal.example",
                "port": 587,
                "security": "starttls",
                "from_address": "alerts@example.com",
                "to": ["noc@example.com"],
            }
        ),
        None,
        notification(),
    )

    assert result.error_code == "invalid_destination"
    assert result.success is False


def test_email_adapter_maps_temporary_smtp_failure_without_leaking_response():
    adapter = EmailPlatformAdapter(
        smtp_factory=TemporarySMTP,
        smtp_ssl_factory=TemporarySMTP,
        resolver=public_resolver,
        tls_context_factory=lambda: object(),
    )

    result = adapter.deliver(
        destination(),
        b'{"password":"secret"}',
        notification(),
    )

    assert result.success is False
    assert result.retryable is True
    assert result.error_code == "smtp_temporary_failure"
    assert "private upstream detail" not in repr(result)


def test_email_adapter_maps_authentication_failure_as_terminal_and_secret_safe():
    adapter = EmailPlatformAdapter(
        smtp_factory=AuthenticationFailureSMTP,
        smtp_ssl_factory=AuthenticationFailureSMTP,
        resolver=public_resolver,
        tls_context_factory=lambda: object(),
    )

    result = adapter.deliver(
        destination(),
        b'{"password":"secret"}',
        notification(),
    )

    assert result.success is False
    assert result.retryable is False
    assert result.error_code == "smtp_authentication_failed"
    assert "private auth detail" not in repr(result)
