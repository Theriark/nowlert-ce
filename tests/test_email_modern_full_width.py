"""Email bodies must use a full-width Modern Card panel."""
import pytest
from formatters.discord_modern_image import GenericFallbackDiscordModernImageRenderer
from models import Notification


@pytest.mark.parametrize('classification,label', [('warning','Warning'), ('urgent','Urgent'), ('information','Information')])
def test_email_body_uses_full_width_panel(tmp_path, monkeypatch, classification, label):
    captured = {}
    renderer = GenericFallbackDiscordModernImageRenderer(tmp_path)
    monkeypatch.setattr(renderer, '_render_standard_card', lambda **content: captured.update(content) or b'card')
    body = 'Long email body with all details retained. ' * 80
    notification = Notification(source='email', title='Email subject', subject='Email subject',
        status=classification, body=body, metadata={'classification': classification,
        'sender': 'notice@example.com', 'mailbox': 'Example mailbox', 'provider': 'gmail'})
    assert renderer.render(notification, {'embeds': [{'title': 'Email subject'}]}) == b'card'
    assert captured['badge'] == label
    assert len(captured['outcomes']) == 1
    assert captured['outcomes'][0]['full_width'] is True
    assert captured['outcomes'][0]['rows'][0]['value'] == body
    assert all(body != row.get('value') for panel in captured['details'] for row in panel['rows'])
    assert captured['details'][0]['rows'][1]['value'] == 'notice@example.com'
