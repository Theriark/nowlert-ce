#!/usr/bin/env python3
# Nowlert
"""Checkmk notification method. Install as local/share/check_mk/notifications/nowlert."""
from __future__ import annotations

import json
import os
from pathlib import Path
import stat
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

FIELDS = (
    "WHAT", "HOSTNAME", "HOSTALIAS", "HOSTADDRESS", "HOSTSTATE", "LASTHOSTSTATE",
    "HOSTOUTPUT", "SERVICEDESC", "SERVICESTATE", "LASTSERVICESTATE", "SERVICEOUTPUT",
    "NOTIFICATIONTYPE", "SHORTDATETIME",
)


def notification_payload(environment):
    context = {key: environment.get("NOTIFY_" + key, "") for key in FIELDS}
    context["SITE"] = environment.get("OMD_SITE", "")
    return {"checkmk": context}


def send(environment, config_path=None):
    path = Path(config_path or Path.home() / ".config/nowlert/checkmk.json")
    try:
        if path.stat().st_mode & (stat.S_IRWXG | stat.S_IRWXO):
            raise ValueError("configuration permissions must be 0600")
        settings = json.loads(path.read_text(encoding="utf-8"))
        url = str(settings.get("url", ""))
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path != "/checkmk/events":
            raise ValueError("url must be https://HOST/checkmk/events without credentials or query parameters")
        token = str(settings.get("token", "")).strip()
        if not token:
            raise ValueError("missing checkmk-scoped token")
        payload = notification_payload(environment)
        context = payload["checkmk"]
        if context["WHAT"] not in {"HOST", "SERVICE"} or not context["HOSTNAME"] or not context["NOTIFICATIONTYPE"]:
            raise ValueError("missing Checkmk notification context")
    except (OSError, ValueError, TypeError, AttributeError):
        print("Nowlert configuration or notification context is invalid; check the local configuration and its permissions")
        return 2
    request = Request(url, data=json.dumps(payload).encode("utf-8"), headers={
        "Content-Type": "application/json", "X-Nowlert-Token": token,
        "User-Agent": "nowlert-checkmk-notification/1",
    }, method="POST")
    try:
        with urlopen(request, timeout=10) as response:
            if not 200 <= response.status < 300:
                print("Nowlert did not accept the notification")
                return 1
        print("Nowlert accepted the notification; check Delivery history for destination delivery")
        return 0
    except HTTPError as error:
        print(f"Nowlert returned HTTP {error.code}")
        return 1 if error.code in {408, 429} or error.code >= 500 else 2
    except (URLError, TimeoutError, OSError):
        print("Nowlert connection failed; the notification spooler may retry")
        return 1


if __name__ == "__main__":
    raise SystemExit(send(os.environ))
