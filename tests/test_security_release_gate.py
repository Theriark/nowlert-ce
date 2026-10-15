"""Release security invariants found in the Development Datadog review."""

from pathlib import Path
import re

from packaging.version import Version
import pytest

from storage.mfa import totp_code
from storage.destinations import DestinationStore
from storage.routes import RouteStore
from storage.settings import SettingsRecordError
from test_unified_configuration import migrated


ROOT = Path(__file__).resolve().parents[1]


def test_urllib3_includes_the_three_2026_advisory_fixes():
    requirements = (ROOT / "requirements.txt").read_text()
    version = re.search(r"^urllib3==([^\s]+)$", requirements, re.MULTILINE)
    assert version is not None
    assert Version(version[1]) >= Version("2.8.0")


def test_docker_workflow_actions_use_immutable_commit_pins():
    for path in (ROOT / ".github" / "workflows").glob("*.yml"):
        for action in re.findall(r"uses:\s+(docker/[^\s#]+)", path.read_text()):
            assert re.fullmatch(r"docker/[\w-]+@[0-9a-f]{40}", action), (path.name, action)


def test_no_private_tls_key_is_committed_as_a_fixture():
    assert not list((ROOT / "tests" / "fixtures").rglob("key.pem"))


@pytest.mark.parametrize("store_class, decoder", [
    (DestinationStore, "_destination"), (RouteStore, "_route"),
])
def test_resource_metadata_never_contains_internal_exceptions(migrated, monkeypatch, store_class, decoder):
    assert migrated["service"].synchronize().ready
    store = store_class(migrated["database"])

    def broken(*args, **kwargs):
        raise RuntimeError("synthetic-private-diagnostic /private/server/path")

    monkeypatch.setattr(store, decoder, broken)
    items, errors = store.list_visible_safe(migrated["admin"])
    assert not items and errors
    assert "synthetic-private-diagnostic" not in str(errors)
    assert "/private/server/path" not in str(errors)
    assert errors[0]["resource_id"] and errors[0]["code"]


def test_integration_metadata_never_contains_internal_exceptions(migrated, monkeypatch):
    service = migrated["service"]
    assert service.synchronize().ready
    monkeypatch.setattr(service, "synchronize", lambda: None)
    original = service.settings.get

    def broken(namespace, key, default=None):
        if key == "zabbix":
            raise SettingsRecordError(namespace, key, "synthetic-private-diagnostic")
        return original(namespace, key, default)

    monkeypatch.setattr(service.settings, "get", broken)
    assert "synthetic-private-diagnostic" not in str(service.integration_settings()["errors"])
    _value, error = service.settings.get_safe("integration", "zabbix", {})
    assert error and "synthetic-private-diagnostic" not in str(error)


@pytest.mark.parametrize("timestamp, expected", [
    (59, "287082"), (1111111109, "081804"), (1111111111, "050471"),
    (1234567890, "005924"), (2000000000, "279037"), (20000000000, "353130"),
])
def test_totp_preserves_rfc6238_sha1_authenticator_compatibility(timestamp, expected):
    # RFC6238 SHA1 vector uses the public ASCII seed 12345678901234567890.
    assert totp_code("GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ", timestamp=timestamp) == expected
