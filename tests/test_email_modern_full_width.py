"""Email bodies must use a full-width Modern Card panel."""
import pytest
from formatters.discord_modern_image import GenericFallbackDiscordModernImageRenderer
from models import Notification


@pytest.mark.parametrize('classification,label,status', [('warning','Warning','warning'), ('urgent','Urgent','failure'), ('information','Information','information')])
def test_email_body_uses_full_width_panel(tmp_path, monkeypatch, classification, label, status):
    captured = {}
    renderer = GenericFallbackDiscordModernImageRenderer(tmp_path)
    monkeypatch.setattr(renderer, '_render_standard_card', lambda **content: captured.update(content) or b'card')
    body = 'Long email body with all details retained. ' * 80
    notification = Notification(source='email', title='Email subject', subject='Email subject',
        status=classification, body=body, metadata={'classification': classification,
        'sender': 'notice@example.com', 'mailbox': 'Example mailbox', 'provider': 'gmail'})
    assert renderer.render(notification, {'embeds': [{'title': 'Email subject'}]}) == b'card'
    assert captured['badge'] == label
    assert captured['status'] == status
    assert captured['outcomes'][0]['status'] == status
    assert len(captured['outcomes']) == 1
    assert captured['outcomes'][0]['full_width'] is True
    assert captured['outcomes'][0]['rows'][0]['value'] == body
    assert all(body != row.get('value') for panel in captured['details'] for row in panel['rows'])
    assert captured['details'][0]['rows'][1]['value'] == 'notice@example.com'


def test_information_email_draws_blue_info_badge_without_success_check(tmp_path, monkeypatch):
    from PIL import ImageDraw

    renderer = GenericFallbackDiscordModernImageRenderer(tmp_path)
    status_icons = []
    text_fills = []
    original_icon = renderer._status_icon
    original_text = ImageDraw.ImageDraw.text

    def capture_icon(draw, x, y, size, status, color):
        status_icons.append((status, color))
        return original_icon(draw, x, y, size, status, color)

    def capture_text(self, xy, text, *args, **kwargs):
        if text == 'Information':
            text_fills.append(kwargs['fill'])
        return original_text(self, xy, text, *args, **kwargs)

    monkeypatch.setattr(renderer, '_status_icon', capture_icon)
    monkeypatch.setattr(ImageDraw.ImageDraw, 'text', capture_text)
    item = Notification(source='email', title='Synthetic informational email',
        subject='Synthetic informational email', body='Synthetic informational message.',
        status='information', metadata={'classification': 'information', 'provider': 'gmail'})
    assert renderer.render(item, {'embeds': [{'title': item.title}]})
    assert status_icons[0] == ('information', renderer.ICON_BLUE)
    assert all(status != 'success' for status, _color in status_icons)
    assert text_fills[0] == renderer.ICON_BLUE
