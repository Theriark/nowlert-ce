"""Conservative lifecycle classification of explicit UniFi event identities.

Detection/activity events have no implied recovery. An alarm name is supplied
by the operator, so callers must use the native event name or trigger key.
"""

import re


def event_lifecycle(value: str) -> tuple[str, str, str] | None:
    key = re.sub(r"[^a-z0-9]", "", value.casefold())
    recovered = {
        "upspowerrestored", "powerrestored", "internetrestored",
        "internetconnected", "internetconnectionrestored", "wanrestored",
        "wanconnected", "deviceonline", "cameraonline", "nvronline",
        "deviceconnected", "cameraconnected", "unifideviceconnected",
        "devicereconnected", "camerareconnected", "devicerecovered",
        "camerarecovered", "deviceissueresolved", "applicationissueresolved",
    }
    failures = {
        "internetdisconnected", "internetconnectionlost", "wandegraded",
        "wandisconnected", "deviceoffline", "cameraoffline", "nvroffline",
        "devicedisconnected", "cameradisconnected", "unifidevicedisconnected",
        "deviceupdatefailed", "cameraupdatefailed", "recordingfailed",
        "fanissuedetected", "macaddresstablecriticallyfull",
    }
    successes = {"deviceupdatecompleted", "cameraupdatecompleted", "updatecompleted"}
    activity = {"networkaccessed", "adminaccess", "deviceadoption", "devicediscovery"}
    warnings = {"deviceissue", "applicationissue", "devicelimitsexceeded"}
    if key in recovered:
        return "success", "information", "resolved"
    if key in successes:
        return "success", "information", "success"
    if key in failures:
        return "failure", "critical", "firing"
    if key in warnings:
        return "warning", "warning", "firing"
    if key in activity:
        return "information", "information", "information"
    return None
