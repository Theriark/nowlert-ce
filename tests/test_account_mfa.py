import time
import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor

import storage.database as database_module
from storage.database import Database
from storage.migrations import MIGRATIONS
from storage.secrets import SecretStore
from storage.mfa import totp_code
from storage.users import UserStore
from test_route_destination_api import PASSWORD, api, call, login


def _headers_from_session(response):
    cookies = [value for name, value in response.headers if name == "Set-Cookie"]
    session = next(item.split(";", 1)[0] for item in cookies if "session=" in item)
    return {"Cookie": session, "X-CSRF-Token": response.payload["csrf_token"]}


def _enroll(api):
    headers = login(api)
    setup = call(api, "POST", "/api/v2/account/mfa/setup", {}, headers)
    secret = setup.payload["secret"]
    enabled = call(api, "PUT", "/api/v2/account/mfa",
                   {"code": totp_code(secret)}, headers)
    assert enabled.status == 200
    assert ("Cache-Control", "no-store") in enabled.headers
    codes = enabled.payload.get("recovery_codes")
    assert isinstance(codes, list) and len(codes) == 10
    assert len(set(codes)) == 10
    assert all(re.fullmatch(r"(?:[0-9a-f]{4}-){7}[0-9a-f]{4}", code) for code in codes)
    return headers, secret, codes


def _recovery_login(api, code, password=PASSWORD):
    return call(api, "POST", "/api/v2/session", {
        "username": "administrator", "password": password, "otp": code,
    })


def test_recovery_codes_are_hashed_and_single_use_after_password_check(api):
    headers, _secret, codes = _enroll(api)
    with api["database"].connect() as connection:
        stored = connection.execute("SELECT code_hash FROM mfa_recovery_codes").fetchall()
        dump = "\n".join(connection.iterdump())
    assert {row[0] for row in stored} == {
        hashlib.sha256(code.replace("-", "").encode("ascii")).hexdigest()
        for code in codes
    }
    assert all(code not in dump and code.replace("-", "") not in dump for code in codes)
    assert "recovery" not in json.dumps(call(api, "GET", "/api/v2/session", headers=headers).payload)
    assert _recovery_login(api, codes[0], "incorrect password").status == 401
    assert _recovery_login(api, "ffff-ffff-ffff-ffff-ffff-ffff-ffff-ffff").status == 401
    assert _recovery_login(api, codes[0].upper()).status == 200
    replay = _recovery_login(api, codes[0])
    assert replay.status == 401 and replay.payload["code"] == "mfa_invalid"
    assert _recovery_login(api, codes[1]).status == 200


def test_recovery_code_consumption_is_atomic(api):
    _headers, _secret, codes = _enroll(api)
    users = UserStore(api["database"])
    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(
            lambda _: users.consume_mfa_recovery_code(api["admin"].id, codes[0]),
            range(2),
        ))
    assert sorted(outcomes) == [False, True]


def test_recovery_regeneration_requires_password_and_authenticator(api):
    headers, secret, codes = _enroll(api)
    path = "/api/v2/account/mfa/recovery-codes"
    assert call(api, "POST", path, {"password": PASSWORD, "code": totp_code(secret)}).status == 401
    assert call(api, "POST", path, {"password": PASSWORD, "code": totp_code(secret)}, {"Cookie": headers["Cookie"]}).status == 401
    assert call(api, "POST", path, {"password": "wrong", "code": totp_code(secret)}, headers).status == 403
    denied = call(api, "POST", path, {"password": PASSWORD, "code": codes[0]}, headers)
    assert denied.status == 403 and denied.payload["code"] == "mfa_invalid"
    assert _recovery_login(api, codes[0]).status == 200
    response = call(api, "POST", path, {"password": PASSWORD, "code": totp_code(secret)}, headers)
    assert response.status == 200
    assert ("Cache-Control", "no-store") in response.headers
    fresh = response.payload["recovery_codes"]
    assert len(fresh) == 10 and not set(fresh) & set(codes)
    assert _recovery_login(api, codes[1]).status == 401
    assert _recovery_login(api, fresh[0]).status == 200


def test_existing_mfa_users_can_generate_codes_and_recovery_can_disable(api):
    headers = login(api)
    setup = call(api, "POST", "/api/v2/account/mfa/setup", {}, headers)
    secret = setup.payload["secret"]
    users = UserStore(api["database"])
    user = users.get(api["admin"].id)
    users.set_mfa_state(user.id, user.mfa_secret_id, True)
    response = call(api, "POST", "/api/v2/account/mfa/recovery-codes",
                    {"password": PASSWORD, "code": totp_code(secret)}, headers)
    assert response.status == 200
    codes = response.payload["recovery_codes"]
    repeated_enable = call(api, "PUT", "/api/v2/account/mfa", {"code": totp_code(secret)}, headers)
    assert repeated_enable.status == 409
    assert call(api, "DELETE", "/api/v2/account/mfa",
                {"password": "wrong", "code": codes[0]}, headers).status == 403
    disabled = call(api, "DELETE", "/api/v2/account/mfa",
                    {"password": PASSWORD, "code": codes[0]}, headers)
    assert disabled.status == 200 and disabled.payload["user"]["mfa_enabled"] is False
    assert users.consume_mfa_recovery_code(user.id, codes[1]) is False
    with api["database"].connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM mfa_recovery_codes").fetchone()[0] == 0


def test_mfa_recovery_migration_preserves_enrolled_accounts(tmp_path, monkeypatch):
    database = Database(tmp_path / "upgrade.db")
    with monkeypatch.context() as previous:
        previous.setattr(database_module, "MIGRATIONS", MIGRATIONS[:-1])
        previous.setattr(database_module, "LATEST_SCHEMA_VERSION", 16)
        assert database.migrate() == 16
        users = UserStore(database)
        user = users.create("enrolled-user", PASSWORD)
        secret = SecretStore(database).create(user.actor, user.id, "Authenticator", "totp", "SECRET")
        with database.transaction() as connection:
            connection.execute("UPDATE users SET mfa_enabled = 1, mfa_secret_id = ? WHERE id = ?",
                               (secret.id, user.id))
    assert database.migrate() == 17
    assert database.migrate() == 17
    assert users.authenticate("enrolled-user", PASSWORD).mfa_enabled is True
    codes = users.generate_mfa_recovery_codes(user.id, secret.id)
    assert len(codes) == 10
    assert users.consume_mfa_recovery_code(user.id, codes[0]) is True


def test_account_mfa_setup_login_challenge_and_disable(api):
    headers = login(api)
    setup = call(api, "POST", "/api/v2/account/mfa/setup", {}, headers)
    assert setup.status == 200
    assert setup.payload["user"]["mfa_enabled"] is False
    secret = setup.payload["secret"]
    assert setup.payload["provisioning_uri"].startswith("otpauth://totp/")
    assert setup.payload["qr_code"].startswith("data:image/svg+xml;base64,")

    enabled = call(
        api, "PUT", "/api/v2/account/mfa",
        {"code": totp_code(secret)}, headers,
    )
    assert enabled.status == 200
    assert enabled.payload["user"]["mfa_enabled"] is True

    assert call(api, "DELETE", "/api/v2/session", headers=headers).status == 204
    challenge = call(
        api, "POST", "/api/v2/session",
        {"username": "administrator", "password": PASSWORD},
    )
    assert challenge.status == 401
    assert challenge.payload["code"] == "mfa_required"

    invalid = call(
        api, "POST", "/api/v2/session",
        {"username": "administrator", "password": PASSWORD, "otp": "000000"},
    )
    assert invalid.status == 401
    assert invalid.payload["code"] == "mfa_invalid"

    signed_in = call(
        api, "POST", "/api/v2/session",
        {
            "username": "administrator",
            "password": PASSWORD,
            "otp": totp_code(secret, timestamp=time.time()),
        },
    )
    assert signed_in.status == 200
    assert signed_in.payload["user"]["mfa_enabled"] is True
    mfa_headers = _headers_from_session(signed_in)

    disabled = call(
        api, "DELETE", "/api/v2/account/mfa",
        {"password": PASSWORD, "code": totp_code(secret)},
        mfa_headers,
    )
    assert disabled.status == 200
    assert disabled.payload["user"]["mfa_enabled"] is False

    normal_login = call(
        api, "POST", "/api/v2/session",
        {"username": "administrator", "password": PASSWORD},
    )
    assert normal_login.status == 200
