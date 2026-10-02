"""Dense native check output must remain readable at Discord display scale."""
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from models import Notification
from formatters.discord_modern_image import CheckmkDiscordModernImageRenderer
from outputs.discord import DiscordOutput

ROOT = Path(__file__).resolve().parents[1]
ERROR = (
    "[mgmt_snmp] SNMP Error: Timeout: No Response from monitored host (Exit-Code: 1)(!!), "
    "[piggyback] Successfully processed from source VM-01, Successfully processed from source VM-06, "
    "Missing monitoring data for plugins, "
    + ", ".join("mgmt_dell_idrac_" + plugin + "(!)" for plugin in
                ("fans", "power", "power_unit", "amperage_current", "amperage_power", "cpu",
                 "mem", "netdev", "pci", "status", "temp", "if64", "snmp_info", "uptime"))
    + ", execution time 12.7 sec"
)

def notification(state="firing", severity="critical", body=ERROR):
    return Notification(source="checkmk", category="monitoring", status={"firing": "failure", "resolved": "success"}.get(state, "information"),
                        title="ALFA / Check_MK: CRITICAL" if state == "firing" else "ALFA / Check_MK: OK",
                        body=body, start_time="2026-10-02 19:04:05",
                        metadata={"host": "ALFA", "service": "Check_MK", "native_state": "CRITICAL" if state == "firing" else "OK",
                                  "notification_type": {"firing": "PROBLEM", "resolved": "RECOVERY"}.get(state, "FLAPPINGSTOP"),
                                  "previous_state": "OK", "site": "fortpt", "state": state, "severity": severity})

@pytest.mark.parametrize("state,severity,body", [
    ("firing", "critical", ERROR),
    ("resolved", "information", "[mgmt_snmp] Success, execution time 14.7 sec"),
    ("flappingstop", "information", "[mgmt_snmp] Success, execution time 18.6 sec"),
])
def test_checkmk_output_has_full_width_without_downscaling(monkeypatch, state, severity, body):
    output = DiscordOutput()
    renderer = CheckmkDiscordModernImageRenderer(ROOT / "assets/icons")
    output.checkmk_modern_image_renderer = renderer
    captured = []
    plan = renderer._zabbix_content_plan

    def capture(*args):
        panels, bottom = plan(*args)
        captured.extend(panels)
        return panels, bottom

    monkeypatch.setattr(renderer, "_zabbix_content_plan", capture)
    data = output.render_modern_image(notification(state, severity, body))
    assert data is not None
    image = Image.open(BytesIO(data))
    assert image.size == (renderer.WIDTH, renderer.BASE_HEIGHT)
    result = captured[-1]
    assert result["width"] == renderer.WIDTH - 2 * renderer.CARD_SIDE_PADDING
    assert result["rows"][0]["value"] == body
    assert {panel["title"] for panel in captured} == {
        "Source & Context", "Timing", "RESULT" if state == "resolved" else "EVENT DETAILS",
    }
