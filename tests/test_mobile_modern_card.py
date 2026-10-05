from dataclasses import replace
import pytest
from test_mobile_simple_card import checkmk
from test_nowlert_mobile_output import adapter, destination, SETTINGS, alert
from test_mobile_connection import pairing
from test_platform_api import platform_api, call
from mobile_card_cases import mobile_card_cases


def presentation(item, style):
    target = destination({**SETTINGS, 'message_style': style})
    return adapter().preview(target, item).payload['content']['metadata']['presentation']


def test_modern_checkmk_preserves_event_and_native_state_in_source_panel():
    card = presentation(checkmk(), 'modern')
    assert card['layout'] == 'modern'
    assert card['status'] == 'test'
    assert card['title'] == checkmk().title
    assert card['sections'][0] == {'title': 'Source & Context', 'field_indices': [0, 1, 2]}
    assert card['fields'][2]['value'] == 'OK'


def test_classic_and_legacy_destinations_keep_identical_presentation_and_identity():
    item = alert()
    classic = adapter().preview(destination({**SETTINGS, 'message_style': 'classic'}), item).payload
    legacy = adapter().preview(destination(), item).payload
    modern = adapter().preview(destination({**SETTINGS, 'message_style': 'modern'}), item).payload
    assert classic == legacy
    assert modern['content']['metadata']['presentation']['layout'] == 'modern'
    assert modern['thread_key'] == legacy['thread_key']
    assert modern['idempotency_key'] == legacy['idempotency_key']
    assert modern['content']['actions'] == legacy['content']['actions']


@pytest.mark.parametrize('case,item', mobile_card_cases(), ids=lambda x: x if isinstance(x, str) else None)
def test_all_modern_integration_fields_are_grouped_once(case, item):
    card = presentation(item, 'modern')
    assert card['layout'] == 'modern'
    indices = [index for section in card['sections'] for index in section['field_indices']]
    assert sorted(indices) == list(range(len(card['fields'])))
    assert len(indices) == len(set(indices))


def test_pairing_style_and_edit_preserve_server_connection_and_secret(platform_api, pairing):
    api, headers, connection_id, calls = pairing
    payload = {'name': 'Modern phone', 'output_type': 'nowlert_mobile',
               'mobile_connection_id': connection_id, 'message_style': 'modern', 'route_ids': []}
    created = call(platform_api, 'POST', '/api/v2/destinations', payload, headers)
    assert created.status == 201
    item = created.payload['destination']
    assert item['settings']['message_style'] == 'modern'
    saved_settings = item['settings']
    changed = call(platform_api, 'PATCH', '/api/v2/destinations/' + item['id'],
                   {'message_style': 'classic'}, headers)
    assert changed.status == 200
    assert changed.payload['destination']['settings'] == {**saved_settings, 'message_style': 'classic'}
    assert changed.payload['destination']['secret_configured']
    assert len([x for x in calls if x[1] == '/redeem']) == 1
    invalid = call(platform_api, 'PATCH', '/api/v2/destinations/' + item['id'],
                   {'message_style': 'invalid'}, headers)
    assert invalid.status == 400

