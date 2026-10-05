"""Representative real parser fixtures and established destination regression cases."""
import json
from email import policy
from email.parser import BytesParser
from pathlib import Path

from dispatcher import Dispatcher
from integrations.catalog import integrations
from models import Notification

FIXTURES = Path(__file__).parent / 'fixtures'


def mobile_card_cases():
    dispatcher = Dispatcher()
    cases = []
    # Exercise every valid email and native webhook fixture, including lifecycle variants.
    for path in sorted(FIXTURES.rglob('*')):
        if path.suffix == '.eml':
            notification = dispatcher.parse(BytesParser(policy=policy.default).parsebytes(path.read_bytes()))
            if notification and notification.source != 'generic':
                cases.append((str(path.relative_to(FIXTURES)), notification))
        elif path.suffix == '.json' and path.parent.name != 'tls':
            relative = path.relative_to(FIXTURES)
            first = relative.parts[0]
            application = path.stem if first == 'application_alerts' else {
                'home_assistant': 'home_assistant', 'portainer': 'portainer',
                'proxmox': 'proxmox', 'synology': 'synology',
                'unifi': relative.parts[1] if len(relative.parts) > 2 else '',
                'redfish': path.stem.split('_')[0].replace('hpe', 'hpe').replace('dell', 'dell'),
            }.get(first)
            if application:
                parsed = dispatcher.parse_webhook(application, json.loads(path.read_text()))
                if parsed:
                    for index, notification in enumerate(parsed if isinstance(parsed, list) else [parsed]):
                        cases.append((str(relative) + ':' + str(index), notification))
    # Sources without an on-disk raw fixture reuse the established destination cases.
    from test_round42_final_ee_classic_v1 import xo_success
    from test_round44_zabbix_classic_cleanup import zabbix_notification
    from test_teams_classic_prometheus import prometheus_notification
    from test_generic_fallback_classic import smtp_notification
    cases.extend([('xo:success', xo_success()), ('zabbix:problem', zabbix_notification('problem')),
                  ('zabbix:update', zabbix_notification('update')), ('zabbix:recovery', zabbix_notification('recovery')),
                  ('prometheus:firing', prometheus_notification()), ('prometheus:resolved', prometheus_notification('resolved')),
                  ('generic:smtp', smtp_notification())])
    cases.append(('email:alert', Notification(source='email', category='email', status='information',
        title='Synthetic email alert', body='A controlled email notification.',
        metadata={'subject': 'Synthetic email alert', 'sender_address': 'monitor@example.invalid'})))
    cases.append(('redfish:event', dispatcher.parse_webhook('redfish',
        json.loads((FIXTURES/'redfish/supermicro_thermal.json').read_text()
            .replace('Supermicro', 'Generic').replace('supermicro', 'generic').replace('SMC', 'Generic').replace('smc', 'generic')))[0]))
    supported = {item['source'] for item in integrations()} | {'generic', 'redfish'}
    covered = {item.source for _, item in cases}
    assert supported <= covered, f'Missing source fixtures: {supported - covered}'
    return cases
