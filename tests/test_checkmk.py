"""Native Checkmk context, lifecycle, intake, and notification-script contracts."""
import importlib.util
import json
from pathlib import Path
from urllib.error import HTTPError, URLError

import pytest

from dispatcher import Dispatcher
from parsers.application_alerts import Parser

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('checkmk_notification', ROOT / 'tools/checkmk_notification.py')
SCRIPT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SCRIPT)


def context(**changes):
    payload = json.loads((ROOT / 'tests/fixtures/application_alerts/checkmk.json').read_text())
    payload['checkmk'].update(changes)
    return payload


@pytest.mark.parametrize('what,state,status', [
    ('HOST','DOWN','failure'), ('HOST','UNREACH','failure'), ('HOST','UP','information'),
    ('SERVICE','WARN','warning'), ('SERVICE','CRIT','failure'),
    ('SERVICE','UNKNOWN','warning'), ('SERVICE','OK','information'),
])
def test_native_host_service_states(what,state,status):
    item = Parser('checkmk').parse(context(WHAT=what, **{what+'STATE':state}))[0]
    assert item.status == status
    assert item.metadata['native_state'] == state
    assert item.metadata['host'] == 'synthetic-server-01'
    assert item.metadata['service'] == ('CPU load' if what == 'SERVICE' else '')


@pytest.mark.parametrize('kind,state', [
    ('RECOVERY','resolved'), ('CUSTOM','test'), ('ACKNOWLEDGEMENT (operator)','acknowledgement'),
    ('FLAPPINGSTART','flappingstart'), ('FLAPPINGSTOP','flappingstop'),
    ('DOWNTIMESTART','downtimestart'), ('DOWNTIMEEND','downtimeend'),
    ('DOWNTIMECANCELLED','downtimecancelled'), ('ALERTHANDLER (restart)','alerthandler'),
    ('FUTURE_NATIVE_TYPE','future_native_type'),
])
def test_lifecycle_notifications_are_preserved(kind,state):
    item = Dispatcher().parse_webhook('checkmk',context(NOTIFICATIONTYPE=kind))[0]
    assert item.metadata['state'] == state
    assert item.metadata['notification_type'] == kind
    assert item.status == ('success' if kind == 'RECOVERY' else 'information')


@pytest.mark.parametrize('changes', [{'WHAT':'INVALID'}, {'HOSTNAME':''}, {'SERVICEDESC':''}, {'SERVICESTATE':'INVALID'}, {'NOTIFICATIONTYPE':''}, {'WHAT':[]}])
def test_invalid_context_is_not_routed(changes):
    assert Dispatcher().parse_webhook('checkmk', context(**changes)) is None


def test_script_only_forwards_notification_fields():
    value = SCRIPT.notification_payload({'NOTIFY_WHAT':'HOST','NOTIFY_HOSTNAME':'example',
        'NOTIFY_PARAMETER_1':'secret-token','NOTIFY_CONTACTEMAIL':'private@example.invalid',
        'OTHER_PASSWORD':'secret','OMD_SITE':'example-site'})
    assert value['checkmk']['SITE'] == 'example-site'
    assert 'secret' not in json.dumps(value) and 'private' not in json.dumps(value)


@pytest.mark.parametrize('failure,expected', [(None,0), (URLError('private-url'),1),
    (HTTPError('private-url',401,'private-token',None,None),2),
    (HTTPError('private-url',429,'private-token',None,None),1),
    (HTTPError('private-url',503,'private-token',None,None),1)])
def test_script_acknowledgement_retry_and_secret_redaction(tmp_path,monkeypatch,capsys,failure,expected):
    p=tmp_path/'settings.json'; p.write_text(json.dumps({'url':'https://example.invalid/checkmk/events','token':'private-token'}))
    monkeypatch.setattr(Path,'stat',lambda self: type('Permissions',(),{'st_mode':0o600})())
    calls=[]
    class Response:
        status=204
        def __enter__(self): return self
        def __exit__(self,*args): pass
    def connect(request,timeout):
        calls.append((request,timeout))
        if failure: raise failure
        return Response()
    monkeypatch.setattr(SCRIPT,'urlopen',connect)
    assert SCRIPT.send({'NOTIFY_WHAT':'SERVICE','NOTIFY_HOSTNAME':'example','NOTIFY_NOTIFICATIONTYPE':'PROBLEM'},p)==expected
    assert calls[0][1]==10 and calls[0][0].get_header('X-nowlert-token')=='private-token'
    output=capsys.readouterr().out
    assert 'private-token' not in output and 'private-url' not in output
