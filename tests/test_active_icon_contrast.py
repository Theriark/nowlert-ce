"""Active vendor marks remain visible on dark notification cards."""
from pathlib import Path
from collections import Counter

import pytest
from PIL import Image

from formatters.presentation import PresentationMixin
from webui.service import WebUIService


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("source", ("github_actions", "qnap", "synology"))
def test_active_icon_has_dark_card_contrast_and_transparent_background(source):
    path = ROOT / "assets/icons" / PresentationMixin.PRODUCT_ICONS[source]
    image = Image.open(path).convert("RGBA")
    opaque = [image.getpixel((x, y)) for y in range(image.height) for x in range(image.width)
              if image.getpixel((x, y))[3] == 255]
    assert opaque
    assert image.getchannel("A").getextrema() == (0, 255)
    def luminance(rgb):
        channels = [value / 255 for value in rgb[:3]]
        linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in channels]
        return sum(value * weight for value, weight in zip(linear, (0.2126, 0.7152, 0.0722)))
    background = luminance((28, 33, 37))
    foreground = [luminance(pixel) for pixel in opaque]
    assert min((max(value, background) + 0.05) / (min(value, background) + 0.05)
               for value in foreground) >= 3


@pytest.mark.parametrize("source", ("github_actions", "qnap", "synology", "supermicro"))
def test_webui_serves_same_icon_used_by_notifications(source):
    class Configuration:
        def get(self, *_keys, default=None):
            return default
    filename = PresentationMixin.PRODUCT_ICONS[source]
    response = WebUIService(Configuration(), root=ROOT).response(f"/ui/source-icons/{filename}")
    assert response is not None and response.status == 200
    assert response.content_type == "image/png"
    assert response.body == (ROOT / "assets/icons" / filename).read_bytes()
    script = (ROOT / "src/webui/app.js").read_text()
    assert f'{source}: "/ui/source-icons/{filename}"' in script


@pytest.mark.parametrize("filename", ("qnap.png", "synology.png", "supermicro.png"))
def test_previous_nas_icon_urls_remain_available(filename):
    class Configuration:
        def get(self, *_keys, default=None):
            return default
    response = WebUIService(Configuration(), root=ROOT).response(f"/ui/source-icons/{filename}")
    assert response.status == 200
    assert response.body == (ROOT / "assets/icons" / filename).read_bytes()


@pytest.mark.parametrize("discord", (False, True))
def test_active_supermicro_wordmark_keeps_official_white_center(discord):
    filename = PresentationMixin.PRODUCT_ICONS["supermicro"]
    if discord:
        filename = PresentationMixin.DISCORD_PRODUCT_ICONS.get("supermicro", filename)
    image = Image.open(ROOT / "assets/icons" / filename).convert("RGBA")
    assert image.getchannel("A").getextrema() == (0, 255)
    logo = image.crop(image.getbbox())
    pixels = [logo.getpixel((x, y)) for y in range(logo.height) for x in range(logo.width)]
    white = sum(pixel == (255, 255, 255, 255) for pixel in pixels)
    assert white / len(pixels) > 0.35, "Official ellipse requires an opaque white center behind navy lettering"
    navy = Counter(pixel[:3] for pixel in pixels
                   if pixel[3] == 255 and pixel[2] > max(pixel[:2]) and pixel[2] < 180).most_common(1)[0][0]
    channels = [value / 255 for value in navy]
    linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in channels]
    luminance = sum(value * weight for value, weight in zip(linear, (0.2126, 0.7152, 0.0722)))
    assert 1.05 / (luminance + 0.05) >= 4.5
