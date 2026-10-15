"""Slack crops accessory backgrounds to a square with background-size: cover."""

from pathlib import Path

import pytest
from PIL import Image

from formatters.slack import SlackFormatter
from webui.service import WebUIService


@pytest.mark.parametrize("source", ("qnap", "synology"))
def test_slack_wide_wordmark_survives_square_cover_crop(source):
    formatter = SlackFormatter()
    url = formatter._slack_classic_icon_url(source)
    assert url.endswith(f"/{source}-white-slack.png")
    root = Path(__file__).resolve().parents[1] / "assets" / "icons"
    with Image.open(root / f"{source}-white.png") as original:
        original = original.convert("RGBA")
        with Image.open(root / url.rsplit("/", 1)[1]) as padded:
            padded = padded.convert("RGBA")
            assert padded.width == padded.height
            x = (padded.width - original.width) // 2
            y = (padded.height - original.height) // 2
            assert x > 0 and y > 0
            assert padded.crop((x, y, x + original.width, y + original.height)).tobytes() == original.tobytes()
            assert padded.getpixel((0, 0))[3] == 0
    # Other providers continue using the native wide artwork.
    assert formatter._product_icon_url(source).endswith(f"/{source}-white.png")

    class Configuration:
        def get(self, *_keys, default=None):
            return default

    response = WebUIService(Configuration(), root=root.parents[1]).response(
        f"/ui/source-icons/{source}-white-slack.png"
    )
    assert response.status == 200 and response.content_type == "image/png"
    assert response.body == (root / f"{source}-white-slack.png").read_bytes()
