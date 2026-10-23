"""THE-874 F1: a destination's credential record must not outlive the destination."""

from __future__ import annotations

import pytest

import api.platform as platform_module

from api.security import hash_password
from api.service import APIService
from dispatcher import Dispatcher
from storage.database import Database
from storage.destinations import DestinationStore
from storage.secrets import SecretStore
from storage.users import UserStore


PASSWORD = "correct horse battery staple"
OWNER_PASSWORD = "owner secure password"


class Configuration:
    def __init__(self, data):
        self.data = data

    def get(self, *keys, default=None):
        value = self.data
        for key in keys:
            if not isinstance(value, dict) or key not in value:
                return default
            value = value[key]
        return value


class Router:
    def route(self, _notification):
        raise AssertionError("v2 platform ingestion must not use the YAML router")


def fast_hash(password: str) -> str:
    return hash_password(password, salt=b"\x07" * 16, iterations=1_000)


@pytest.fixture
def platform_api(tmp_path, monkeypatch):
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()

    def users(database_value):
        return UserStore(database_value, password_hasher=fast_hash)

    monkeypatch.setattr(platform_module, "UserStore", users)
    seed_users = users(database)
    admin = seed_users.bootstrap_admin("administrator", PASSWORD)
    owner = seed_users.create("owner-user", OWNER_PASSWORD)
    config = Configuration({
        "api": {"enabled": True},
        "platform": {
            "enabled": True,
            "state_dir": str(tmp_path / "state"),
            "secure_cookies": False,
        },
    })
    service = APIService(
        Dispatcher(),
        Router(),
        config,
        platform_database=database,
    )
    return {"database": database, "admin": admin, "owner": owner, "service": service}


def call(platform, method, path, payload=None, headers=None, client="127.0.0.1"):
    return platform["service"].handle_http(
        method, path, payload, headers or {}, client
    )


def login(platform, username="administrator", password=PASSWORD, client="127.0.0.1"):
    response = call(
        platform,
        "POST",
        "/api/v2/session",
        {"username": username, "password": password},
        client=client,
    )
    assert response.status == 200
    cookies = [value for name, value in response.headers if name == "Set-Cookie"]
    session = next(item.split(";", 1)[0] for item in cookies if "session=" in item)
    return {"Cookie": session, "X-CSRF-Token": response.payload["csrf_token"]}


def create_destination(platform, headers):
    response = call(
        platform,
        "POST",
        "/api/v2/destinations",
        {
            "name": "Synthetic webhook",
            "output_type": "webhook",
            "settings": {"method": "POST"},
            "shared": False,
            "secret": {"url": "https://example.invalid/events"},
        },
        headers,
    )
    assert response.status == 201
    return response.payload["destination"]


def secret_records(platform):
    with platform["database"].connect() as connection:
        return connection.execute("SELECT COUNT(*) FROM secret_records").fetchone()[0]


def secret_files(platform):
    return sorted((platform["database"].path.parent / "secrets").glob("*.v*"))


def test_deleting_a_destination_removes_its_secret_record_and_file(platform_api):
    headers = login(platform_api)
    destination = create_destination(platform_api, headers)
    assert secret_records(platform_api) == 1
    assert len(secret_files(platform_api)) == 1

    deleted = call(
        platform_api,
        "DELETE",
        f"/api/v2/destinations/{destination['id']}",
        headers=headers,
    )

    assert deleted.status == 204
    assert secret_records(platform_api) == 0
    assert secret_files(platform_api) == []


def test_secret_shared_with_another_consumer_survives_destination_delete(platform_api):
    headers = login(platform_api)
    first = create_destination(platform_api, headers)
    database = platform_api["database"]
    admin = platform_api["admin"]
    with database.connect() as connection:
        secret_id = connection.execute(
            "SELECT secret_id FROM destinations WHERE id = ?", (first["id"],)
        ).fetchone()[0]
    DestinationStore(database).create(
        admin.actor,
        admin.id,
        "Second webhook",
        "webhook",
        secret_id=secret_id,
        settings={"method": "POST"},
    )

    assert SecretStore(database).delete_if_unreferenced(admin.actor, secret_id) is False
    deleted = call(
        platform_api, "DELETE", f"/api/v2/destinations/{first['id']}", headers=headers
    )

    assert deleted.status == 204
    assert secret_records(platform_api) == 1
    assert len(secret_files(platform_api)) == 1


def test_user_with_an_orphaned_destination_secret_can_be_deleted(platform_api):
    admin_headers = login(platform_api)
    owner = platform_api["owner"]
    # State left behind by releases that kept the secret on destination delete.
    SecretStore(platform_api["database"]).create(
        platform_api["admin"].actor, owner.id, "orphan", "webhook-credentials", "x"
    )
    assert secret_records(platform_api) == 1

    deleted = call(
        platform_api, "DELETE", f"/api/v2/users/{owner.id}", headers=admin_headers
    )

    assert deleted.status == 204
    assert secret_records(platform_api) == 0
    assert secret_files(platform_api) == []


def test_user_still_owning_a_referenced_secret_cannot_be_deleted(platform_api):
    admin_headers = login(platform_api)
    owner = platform_api["owner"]
    owner_headers = login(
        platform_api, "owner-user", OWNER_PASSWORD, client="127.0.0.9"
    )
    create_destination(platform_api, owner_headers)

    deleted = call(
        platform_api, "DELETE", f"/api/v2/users/{owner.id}", headers=admin_headers
    )

    assert deleted.status == 409
    assert secret_records(platform_api) == 1
