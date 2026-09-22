"""Modern cards retain readable, complete content at every integration boundary."""

from io import BytesIO

import pytest
from PIL import Image, ImageDraw

from formatters.discord_modern_image import DiscordModernImageRenderer
from formatters.discord_xo_image import XenOrchestraDiscordImageRenderer
from models import Notification


@pytest.fixture
def painted_text(monkeypatch):
    calls = []
    original = ImageDraw.ImageDraw.text

    def record(self, xy, text, *args, **kwargs):
        font = kwargs.get("font")
        if font is not None:
            calls.append((str(text), font.size, self.textbbox(xy, text, font=font)))
        return original(self, xy, text, *args, **kwargs)

    monkeypatch.setattr(ImageDraw.ImageDraw, "text", record)
    return calls


@pytest.mark.parametrize("source", tuple(DiscordModernImageRenderer.INTEGRATION_NAMES))
def test_long_modern_headers_and_values_are_complete_without_small_type(
    tmp_path, painted_text, source,
):
    renderer = DiscordModernImageRenderer(tmp_path)
    title = "Operational event with extensive context " * 5 + "TITLE-END"
    context = "Production server and storage cluster " * 5 + "CONTEXT-END"
    value = "sensor." + "very_long_identifier_" * 20 + "VALUE-END"
    item = Notification(source=source, status="warning", category="monitoring",
                        metadata={"host": context})
    payload = {"embeds": [{"title": title, "color": 0xF4C131,
                            "description": "A readable operational result.",
                            "fields": [{"name": "Source", "value": "Entity: " + value}]}]}
    with Image.open(BytesIO(renderer.render(item, payload))) as image:
        text = "".join(call[0] for call in painted_text)
        for marker in ("TITLE-END", "CONTEXT-END", "VALUE-END"):
            assert marker in text
        for text, size, box in painted_text:
            if len(text) > 1 and "Nowlert CE" not in text:
                assert size >= 36, (text, size)
            assert box[0] >= 0 and box[2] <= image.width, (text, box)
            assert box[1] >= 0 and box[3] < image.height - 38, (text, box)


def test_modern_card_contracts_again_after_a_long_event(tmp_path):
    renderer = DiscordModernImageRenderer(tmp_path)
    item = Notification(source="portainer", status="success")
    short = {"embeds": [{"title": "Stack updated", "description": "Deployment completed."}]}
    long = {"embeds": [{"title": "Stack updated " * 30,
                        "description": "Full operational details " * 80}]}
    def size(payload):
        with Image.open(BytesIO(renderer.render(item, payload))) as image:
            return image.size
    before = size(short)
    assert size(long)[1] > before[1]
    assert size(short) == before


def test_xo_keeps_success_failure_and_skipped_results_together(tmp_path, painted_text):
    renderer = XenOrchestraDiscordImageRenderer(tmp_path)
    item = Notification(source="xo", status="failure", category="backup",
                        successful_vms=["VM-success"], failed_vms=["VM-failed"],
                        skipped_vms=["VM-skipped"], vm_total=3, vm_success=1,
                        vm_failed=1, vm_skipped=1,
                        vm_details={"VM-failed": {"error": "Connection timeout"},
                                    "VM-skipped": {"error": "Maintenance window"}})
    renderer.render(item)
    text = " ".join(call[0] for call in painted_text)
    for expected in ("VM-success", "VM-failed", "VM-skipped", "Maintenance window"):
        assert expected in text


@pytest.mark.parametrize("status", ("success", "failure", "skipped"))
def test_xo_long_names_and_badges_keep_readable_type(tmp_path, painted_text, status):
    renderer = XenOrchestraDiscordImageRenderer(tmp_path)
    name = "VM-01 | " + "Production database workload " * 8 + "NAME-END"
    item = Notification(source="xo", status=status, category="backup",
                        subject="Backup report " * 8 + "REPORT-END",
                        repository="Storage repository " * 8 + "REPO-END",
                        successful_vms=[name], vm_total=1, vm_success=1,
                        vm_details={name: {"size": "52.06 GiB", "speed": "33.73 MiB/s"}})
    renderer.render(item)
    text = "".join(call[0] for call in painted_text)
    for marker in ("NAME-END", "REPORT-END", "REPO-END"):
        assert marker in text
    assert all(size >= 36 for text, size, _ in painted_text
               if len(text) > 1 and "Nowlert CE" not in text)


def test_single_field_names_and_url_punctuation_survive_rendering(tmp_path, painted_text):
    renderer = DiscordModernImageRenderer(tmp_path)
    item = Notification(source="zabbix", status="warning")
    payload = {"embeds": [{"title": "Operational alert", "fields": [
        {"name": "Runbook", "value": "https://example.com/restart"},
        {"name": "Temperature", "value": "90 C"},
    ]}]}
    renderer.render(item, payload)
    text = " ".join(call[0] for call in painted_text)
    assert "Temperature" in text
    assert "Runbook" in text
    assert "https://example.com/restart" in "".join(call[0] for call in painted_text)


def test_explicit_skipped_state_is_not_hidden_by_classic_information_suffix(tmp_path, painted_text):
    renderer = DiscordModernImageRenderer(tmp_path)
    item = Notification(source="generic", status="skipped", category="backup")
    renderer.render(item, {"embeds": [{"title": "Backup event — Information"}]})
    assert any(text == "Backup Skipped" for text, _, _ in painted_text)
