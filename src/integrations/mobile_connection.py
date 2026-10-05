"""Server-owned Mobile pairing; credentials stay in the existing secret boundary."""
import fcntl
import json
import os
import re
import time
from urllib.parse import urlsplit

import requests

from outputs.settings import normalize_output_settings, validate_mobile_publish_key


def mobile_origin():
    explicit_environment = os.environ.get("NOWLERT_DEPLOYMENT_ENVIRONMENT")
    aliases = {"dev": "development", "development": "development", "stg": "stage", "stage": "stage", "staging": "stage", "prod": "production", "production": "production"}
    if explicit_environment is not None:
        environment = aliases.get(explicit_environment.strip().lower())
    else:
        environment = aliases.get(os.environ.get("DD_ENV", "production").strip().lower(), "production")
    defaults = {
        "development": "https://nowlert-mb-dev.theriark.dev",
        "stage": "https://nowlert-mb-stg.theriark.dev",
        "production": "https://nowlert-mb.theriark.com",
    }
    if environment not in defaults:
        raise ValueError("Mobile deployment environment is invalid")
    origin = os.environ.get("NOWLERT_MOBILE_ORIGIN", defaults[environment]).rstrip("/")
    parsed = urlsplit(origin)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment:
        raise ValueError("Administrator Mobile origin must be an HTTPS origin")
    return origin


class MobileConnections:
    def __init__(self, secrets):
        self.secrets = secrets

    def _post(self, origin, operation, body):
        try:
            response = requests.post(origin + "/api/v1/integrations/ce/connections" + operation,
                                     json=body, timeout=15, allow_redirects=False,
                                     headers={"User-Agent": "Nowlert-CE/1.0", "Accept": "application/json"})
            if response.status_code in (404, 410):
                raise ValueError("This connection has expired. Connect Nowlert Mobile again.")
            if response.status_code == 429:
                raise ValueError("Mobile is busy. Please try again shortly.")
            if response.status_code >= 300:
                raise ValueError("Could not contact Nowlert Mobile. Please try again.")
            result = response.json()
            if not isinstance(result, dict):
                raise ValueError("Mobile returned an invalid response. Please try again.")
            return result
        except (requests.RequestException, json.JSONDecodeError):
            raise ValueError("Could not contact Nowlert Mobile. Please try again.") from None

    def start(self, actor, name):
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 128:
            raise ValueError("Enter a destination name before connecting.")
        # Remove this owner's expired pending records, including their private files.
        for item in self.secrets.list_for_owner(actor, actor.user_id):
            if item.kind == "mobile-connection" and item.updated_at < time.time() - 3600:
                self.secrets.delete(actor, item.id)
        origin = mobile_origin()
        result = self._post(origin, "", {"name": name.strip()})
        if not isinstance(result.get("device_code"), str) or not 16 <= len(result["device_code"]) <= 4096 or not re.fullmatch(r"[A-Z0-9]{4}-[A-Z0-9]{4}", str(result.get("user_code", ""))):
            raise ValueError("Mobile returned an invalid connection. Please try again.")
        expires_in = result.get("expires_in", 600)
        if isinstance(expires_in, bool) or not isinstance(expires_in, int) or expires_in < 1:
            raise ValueError("Mobile returned an invalid expiry. Please try again.")
        record = {"origin": origin, "device_code": result["device_code"],
                  "expires_at": int(time.time()) + min(600, expires_in)}
        item = self.secrets.create(actor, actor.user_id, "Mobile connection " + os.urandom(12).hex(),
                                   "mobile-connection", json.dumps(record))
        return {"connection_id": item.id, "user_code": result["user_code"],
                "expires_in": record["expires_at"] - int(time.time()), "interval": 3}

    def _load(self, actor, connection_id):
        if not isinstance(connection_id, str) or not re.fullmatch(r"[0-9a-f]{32}", connection_id):
            raise ValueError("Invalid Mobile connection")
        item = self.secrets.metadata(actor, connection_id)
        if item.owner_user_id != actor.user_id or item.kind != "mobile-connection":
            raise PermissionError("This connection belongs to another user")
        record = json.loads(self.secrets.resolve(actor, connection_id))
        if record["expires_at"] < time.time():
            raise ValueError("This connection has expired. Connect Nowlert Mobile again.")
        return record

    def status(self, actor, connection_id):
        record = self._load(actor, connection_id)
        if "saved_destination_id" in record:
            return {"status": "approved", "topic_name": record.get("topic_name", "Nowlert CE")}
        if "grant" in record:
            return {"status": "approved", "topic_name": record["grant"]["topic_name"]}
        result = self._post(record["origin"], "/status", {"device_code": record["device_code"]})
        if result.get("status") not in {"pending", "approved"}:
            raise ValueError("Mobile returned an invalid connection status")
        return {"status": result["status"], **({"topic_name": str(result.get("topic_name", "Nowlert CE"))[:128]} if result["status"] == "approved" else {})}

    def save(self, actor, connection_id, data, destination_id, save):
        # Lock across workers. The private retry record retains a redeemed grant if normal save fails.
        with open(self.secrets.directory / ".mobile-connect.lock", "a") as lock:
            os.chmod(lock.name, 0o600)
            fcntl.flock(lock, fcntl.LOCK_EX)
            record = self._load(actor, connection_id)
            if "saved_destination_id" in record:
                if destination_id is not None and destination_id != record["saved_destination_id"]:
                    raise ValueError("This connection was already saved to another destination")
                return save(record["saved_destination_id"], {k: v for k, v in data.items() if k != "settings"})
            if "destination_id" in record and record["destination_id"] != destination_id:
                raise ValueError("This connection belongs to another destination save")
            if "grant" not in record:
                grant = self._post(record["origin"], "/redeem", {"device_code": record["device_code"]})
                if grant.get("status") != "connected":
                    raise ValueError("Approve this connection in Nowlert Mobile before saving.")
                validate_mobile_publish_key({"api_token": grant.get("secret")})
                normalize_output_settings("nowlert_mobile", {"base_url": record["origin"], "topic_id": grant.get("topic_id")})
                record["destination_id"] = destination_id
                record["grant"] = {"topic_id": grant["topic_id"], "topic_name": str(grant.get("topic_name", "Nowlert CE"))[:128], "secret": grant["secret"]}
                record["expires_at"] = int(time.time()) + 3600
                self.secrets.rotate(actor, connection_id, json.dumps(record))
            grant = record["grant"]
            data = {**data, "settings": {"base_url": record["origin"], "topic_id": grant["topic_id"], "topic_name": grant["topic_name"]}, "secret": {"api_token": grant["secret"]}}
            response = save(destination_id, data)
            if response.status < 300:
                record["saved_destination_id"] = response.payload["destination"]["id"]
                record["topic_name"] = grant["topic_name"]
                del record["grant"]
                del record["device_code"]
                self.secrets.rotate(actor, connection_id, json.dumps(record))
            return response
