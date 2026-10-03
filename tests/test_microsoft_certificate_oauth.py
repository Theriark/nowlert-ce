"""Verify certificate-backed Microsoft OAuth without a tenant or mailbox."""
import base64
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import NameOID

from inputs.email_mailboxes import Microsoft365MailboxProvider, MailboxConnectionService, MailboxConnectionError, email_oauth_applications


@pytest.fixture
def credentials():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test-only")])
    now = datetime.now(timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
            .public_key(key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(minutes=1))
            .not_valid_after(now + timedelta(days=1)).sign(key, hashes.SHA256()))
    return key, cert, {
        "client_id": "test-client", "tenant_id": "test-tenant",
        "redirect_uri": "https://example.invalid/ui/",
        "certificate": cert.public_bytes(serialization.Encoding.PEM).decode(),
        "private_key": key.private_bytes(serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode(),
        "refresh_token": "test-refresh",
    }


class HTTP:
    def __init__(self):
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs["data"]))
        return SimpleNamespace(status_code=200, json=lambda: {"access_token": "test"})


def decode(value):
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def test_exchange_and_refresh_sign_fresh_valid_assertions(credentials):
    key, cert, settings = credentials
    http = HTTP()
    provider = Microsoft365MailboxProvider(http=http)
    mailbox = SimpleNamespace(settings={})
    provider.exchange_code(mailbox, settings, "test-code")
    provider.refresh_token(mailbox, settings)
    ids = []
    for url, data in http.calls:
        assert "client_secret" not in data
        assert data["client_assertion_type"] == "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"
        header, claims, signature = data["client_assertion"].split(".")
        head = json.loads(decode(header)); body = json.loads(decode(claims))
        assert head["alg"] == "PS256"
        assert decode(head["x5t#S256"]) == cert.fingerprint(hashes.SHA256())
        assert body["aud"] == url
        assert body["iss"] == body["sub"] == "test-client"
        assert 0 < body["exp"] - body["nbf"] <= 300
        ids.append(body["jti"])
        key.public_key().verify(decode(signature), (header + "." + claims).encode(),
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=32), hashes.SHA256())
    assert ids[0] != ids[1]


def test_certificate_application_does_not_require_secret(credentials):
    _, _, settings = credentials
    service = object.__new__(MailboxConnectionService)
    service.clock = lambda: datetime.now(timezone.utc).timestamp()
    service.oauth_applications = {"microsoft_365": settings}
    assert service._oauth_application("microsoft_365")["private_key"] == settings["private_key"].strip()


def test_mismatched_certificate_never_sends_token_request(credentials):
    _, _, settings = credentials
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    settings["private_key"] = other.private_bytes(serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
    http = HTTP()
    with pytest.raises(MailboxConnectionError, match="certificate"):
        Microsoft365MailboxProvider(http=http).exchange_code(SimpleNamespace(settings={}), settings, "code")
    assert not http.calls


@pytest.mark.parametrize("field", ["certificate", "private_key"])
def test_partial_certificate_does_not_fall_back_to_secret(credentials, field):
    _, _, settings = credentials
    del settings[field]
    settings["client_secret"] = "legacy-secret"
    http = HTTP()
    with pytest.raises(MailboxConnectionError, match="certificate"):
        Microsoft365MailboxProvider(http=http).refresh_token(SimpleNamespace(settings={}), settings)
    assert not http.calls


def test_expired_certificate_fails_before_http(credentials):
    _, _, settings = credentials
    http = HTTP()
    provider = Microsoft365MailboxProvider(http=http, clock=lambda: 4_000_000_000)
    with pytest.raises(MailboxConnectionError, match="certificate"):
        provider.exchange_code(SimpleNamespace(settings={}), settings, "code")
    assert not http.calls


@pytest.mark.parametrize("key_size,future", [(1024, False), (2048, True)])
def test_weak_and_not_yet_valid_certificates_are_rejected(key_size, future):
    key = rsa.generate_private_key(public_exponent=65537, key_size=key_size)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "invalid-test")])
    now = datetime.now(timezone.utc)
    start = now + timedelta(days=1) if future else now - timedelta(minutes=1)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
            .public_key(key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(start).not_valid_after(now + timedelta(days=2)).sign(key, hashes.SHA256()))
    settings = {"client_id": "client", "tenant_id": "tenant", "certificate": cert.public_bytes(serialization.Encoding.PEM).decode(),
                "private_key": key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()}
    http = HTTP()
    with pytest.raises(MailboxConnectionError, match="certificate") as failure:
        Microsoft365MailboxProvider(http=http).refresh_token(SimpleNamespace(settings={}), settings)
    assert "BEGIN" not in str(failure.value)
    assert not http.calls


def test_existing_secret_authentication_remains_supported():
    http = HTTP()
    provider = Microsoft365MailboxProvider(http=http)
    settings = {"client_id": "client", "client_secret": "legacy", "tenant_id": "tenant", "redirect_uri": "https://example.invalid/ui/", "refresh_token": "refresh"}
    provider.exchange_code(SimpleNamespace(settings={}), settings, "code")
    provider.refresh_token(SimpleNamespace(settings={}), settings)
    assert all(data["client_secret"] == "legacy" and "client_assertion" not in data for _, data in http.calls)


def test_certificate_credentials_load_from_deployment_files(tmp_path, credentials):
    _, _, settings = credentials
    paths = {}
    for field, name in (("certificate", "CERTIFICATE"), ("private_key", "PRIVATE_KEY")):
        path = tmp_path / (field + ".pem")
        path.write_bytes(settings[field].encode())
        paths[f"NOWLERT_EMAIL_MICROSOFT_{name}_FILE"] = str(path)
    paths["NOWLERT_EMAIL_MICROSOFT_CLIENT_SECRET_FILE"] = str(tmp_path / "unused-secret")
    loaded = email_oauth_applications(environment=paths)["microsoft_365"]
    assert loaded["certificate"] == settings["certificate"].strip()
    assert loaded["private_key"] == settings["private_key"].strip()


def test_empty_certificate_files_never_fall_back_to_secret(tmp_path):
    environment = {"NOWLERT_EMAIL_MICROSOFT_CLIENT_SECRET": "legacy"}
    for name in ("CERTIFICATE", "PRIVATE_KEY"):
        path = tmp_path / name
        path.write_text(" \n")
        environment[f"NOWLERT_EMAIL_MICROSOFT_{name}_FILE"] = str(path)
    loaded = email_oauth_applications(environment=environment)["microsoft_365"]
    loaded["refresh_token"] = "refresh"
    http = HTTP()
    with pytest.raises(MailboxConnectionError, match="certificate"):
        Microsoft365MailboxProvider(http=http).refresh_token(SimpleNamespace(settings={}), loaded)
    assert not http.calls
