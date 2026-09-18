import time

from storage.mfa import totp_code
from test_route_destination_api import PASSWORD, api, call, login


def _headers_from_session(response):
    cookies = [value for name, value in response.headers if name == "Set-Cookie"]
    session = next(item.split(";", 1)[0] for item in cookies if "session=" in item)
    return {"Cookie": session, "X-CSRF-Token": response.payload["csrf_token"]}


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
