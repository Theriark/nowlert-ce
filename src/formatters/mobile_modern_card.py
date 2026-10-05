"""Native adaptation of the shared Modern Card section profiles."""
import re
from formatters.mobile_simple_card import render_mobile_simple_card, _text
from formatters.modern_sections import MODERN_SECTION_PROFILES
from outputs.platform_common import notification_context


def _name(value):
    return re.sub(r'^[^A-Za-z0-9]+', '', value).strip().casefold()


def render_mobile_modern_card(notification):
    card = render_mobile_simple_card(notification)
    card['layout'] = 'modern'
    card['title'] = _text(notification_context(notification)['title'], 256)
    fields = card['fields']
    if card['source'] == 'checkmk':
        sections = [{'title': 'Source & Context', 'field_indices': list(range(len(fields)))}]
        metadata = notification.metadata or {}
        timing = []
        for label, value in [('Site', metadata.get('site')),
                             ('Previous state', metadata.get('previous_state')),
                             ('Resolved', notification.end_time)]:
            if value:
                timing.append(len(fields))
                fields.append({'title': label, 'value': _text(value, 1024)})
        if timing:
            sections.append({'title': 'Timing', 'field_indices': timing})
    else:
        profile = MODERN_SECTION_PROFILES.get(card['source'], MODERN_SECTION_PROFILES['generic'])
        used = set()
        sections = []
        for title, patterns, _wide in profile:
            indices = [i for i, field in enumerate(fields) if i not in used and any(
                _name(field['title']) == pattern or _name(field['title']).startswith(pattern + ' ')
                for pattern in patterns)]
            if indices:
                used.update(indices)
                sections.append({'title': title, 'field_indices': indices})
        remaining = [i for i in range(len(fields)) if i not in used]
        if remaining:
            sections.append({'title': 'Additional details', 'field_indices': remaining})
    card['sections'] = sections
    return card
