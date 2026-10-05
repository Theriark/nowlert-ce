import json
import pytest

from formatters.mobile_simple_card import render_mobile_simple_card
from formatters.classic_card_v1 import render_classic_card_v1
from mobile_card_cases import mobile_card_cases


@pytest.mark.parametrize('case,notification', mobile_card_cases())
def test_every_integration_preserves_approved_fields(case, notification):
    card = render_mobile_simple_card(notification)
    assert card['source_name'] and card['title']
    assert len(card['title']) <= 256
    assert len(card['fields']) <= 8
    assert all(len(row['value']) <= 1024 for row in card['fields'])
    assert card['fields'], case
    if notification.source != 'checkmk':
        expected = render_classic_card_v1(notification)
        assert len(card['fields']) == min(8, len(expected['fields']))
    assert 'mobile_simple_card_v1' in json.dumps(card)
