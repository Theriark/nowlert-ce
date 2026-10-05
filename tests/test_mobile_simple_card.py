import json

from models import Notification
from formatters.mobile_simple_card import render_mobile_simple_card


def checkmk(**metadata):
    return Notification(source='checkmk', category='service', status='test',
        title='Websites / TLS certificate checkmk.local.fortpt.com: OK',
        body='Certificate expires in 84 days', start_time='2026-10-05 18:46:17',
        metadata={'host': 'Websites', 'service': 'TLS certificate checkmk.local.fortpt.com',
                  'native_state': 'OK', 'severity': 'information', 'state': 'test', **metadata})


def test_checkmk_has_distinct_event_and_service_state():
    card = render_mobile_simple_card(checkmk())
    assert card['style'] == 'mobile_simple_card_v1'
    assert card['source_name'] == 'Checkmk'
    assert card['title'] == 'Service notification'
    assert card['status'] == 'test'
    assert card['event_time'] == '2026-10-05 18:46:17'
    assert card['fields'] == [
        {'title': 'Host', 'value': 'Websites'},
        {'title': 'Service', 'value': 'TLS certificate checkmk.local.fortpt.com'},
        {'title': 'Service state', 'value': 'OK'},
    ]


def test_presentation_sanitises_credentials_and_bounds_untrusted_values():
    card = render_mobile_simple_card(checkmk(host='token=hidden', service='x' * 5000))
    assert 'hidden' not in json.dumps(card)
    assert len(card['fields'][1]['value']) <= 1024


def test_host_check_is_not_labelled_as_service():
    card = render_mobile_simple_card(checkmk(service='', native_state='UP'))
    assert card['title'] == 'Host notification'
    assert card['fields'][-1] == {'title': 'Host state', 'value': 'UP'}


def test_parser_normalised_information_preserves_native_test_state():
    item = checkmk()
    item.status = 'information'
    assert render_mobile_simple_card(item)['status'] == 'test'


def test_unifi_numeric_event_time_is_readable_and_explicitly_utc():
    item = Notification(source='unifi_protect', title='Motion', body='Motion detected',
        status='information', start_time='1767323045000', metadata={'severity': 'information'})
    assert render_mobile_simple_card(item)['event_time'] == '2026-01-02T03:04:05+00:00'
