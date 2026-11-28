# Home Assistant

For the current WebUI setup, broad alert automations, screenshots, and a verified
native notification test, see [Home Assistant to Discord](guides/home-assistant-to-discord.md).

Home Assistant automations can submit authenticated events to
`POST /home-assistant/events`. The request must follow the
`nowlert.home_assistant.v1` schema and use either the global HTTP secret or a
source-scoped Event API token.

Tokens, destinations and routes are managed in the WebUI, not in
`config.yaml` (which refuses `api.tokens` and `routing`):

1. Under **Profile menu → Security → API tokens**, create an application token
   that allows only **Home Assistant**. The value is shown once.
2. Under **Destinations**, create the destination, edit it, open **Manage
   routes** and select the built-in **Home Assistant HTTP** route.

Store the scoped token in `secrets.yaml`:

```yaml
nowlert_home_assistant_token: "PASTE_SOURCE_SCOPED_TOKEN_HERE"
```

Define one reusable transport in Home Assistant. It forwards event data; card
presentation remains Nowlert's responsibility:

```yaml
rest_command:
  nowlert_event:
    url: "https://nowlert.local.example/home-assistant/events"
    method: POST
    headers:
      X-Nowlert-Token: !secret nowlert_home_assistant_token
      Content-Type: application/json
    payload: >-
      {
        "schema": "nowlert.home_assistant.v1",
        "event_type": {{ event_type | default("automation", true) | string | to_json }},
        "component": {{ component | default("", true) | string | to_json }},
        "title": {{ title | default("Home Assistant event", true) | string | to_json }},
        "message": {{ message | default("No details were provided.", true) | to_json }},
        "severity": {{ severity | default("information", true) | string | to_json }},
        "status": {{ status | default("active", true) | string | to_json }},
        "category": {{ category | default("automation", true) | string | to_json }},
        "entity_id": {{ entity_id | default("", true) | string | to_json }},
        "device": {{ device | default("", true) | string | to_json }},
        "area": {{ area | default("", true) | string | to_json }},
        "tags": {{ tags | default([], true) | to_json }},
        "link": {{ link | default("", true) | string | to_json }},
        "timestamp": {{ utcnow().isoformat().replace("+00:00", "Z") | to_json }}
      }
```

Optional aliases can identify equipment when a raw Home Assistant error only
contains an address or integration name. Keep these deployment-specific names
in Nowlert instead of duplicating them across automations. An administrator
edits them under **Filtering → Integration behavior → Home Assistant → Edit**:
for example the endpoint `192.0.2.10` as device "Building hub" (optionally with
the service "Building automation" when the built-in integration label is not
appropriate), and the component `homeassistant.components.ipp.coordinator` as
device "Office printer" with endpoint `192.0.2.20`.

Endpoint aliases match both a bare address and the host portion of an
`address:port` endpoint. Component aliases use the exact component string sent
by the Home Assistant automation. Explicit device and service fields in a
purpose-built event still take priority.

The following generic automation forwards Home Assistant errors without
embedding presentation rules for individual integrations:

```yaml
alias: "Nowlert - General errors"
description: Forwards selected Home Assistant errors to Nowlert

triggers:
  - trigger: event
    event_type: system_log_event
    event_data:
      level: ERROR

conditions:
  - condition: template
    value_template: >-
      {% set details = (
        (trigger.event.data.name | default('', true) | string)
        ~ ' '
        ~ (trigger.event.data.source | default('', true) | string)
        ~ ' '
        ~ (trigger.event.data.message | default('', true) | string)
      ) | lower %}
      {{ 'nowlert' not in details and 'rest_command' not in details }}

actions:
  - variables:
      event_message: >-
        {% set messages = trigger.event.data.message | default([], true) %}
        {% if messages is string %}
          {{ messages }}
        {% elif messages | count > 0 %}
          {{ messages[0] }}
        {% else %}
          No error details were provided.
        {% endif %}

  - action: rest_command.nowlert_event
    data:
      event_type: system_log
      component: "{{ trigger.event.data.name | default('homeassistant', true) }}"
      title: Home Assistant error
      message: "{{ event_message }}"
      severity: error
      status: active
      category: system_error
      entity_id: ""
      device: ""
      area: ""
      tags:
        - home-assistant
        - error

mode: queued
max: 20
```

The parser derives a concise event summary, service, real device, entity,
endpoint, error code, and retry interval when those details are present.
Discord and Teams formatters present them as separate fields. A service is not
repeated as a device when no actual device is known. Internal Python paths,
method names, and verbose object representations are not placed on the card.
Explicit device, entity, area, and title values still take priority for
purpose-built automations.

Keep deployment-specific exclusions in the Home Assistant condition rather
than in Nowlert's generic parser. For example, a site may suppress a known
lab-only integration by adding another `and '<integration>' not in details`
clause. Those exclusions should not be copied into the shared example.

Tokens must remain in Home Assistant secrets or another protected mechanism.
Titles, messages, entity IDs, tags, links, and payload sizes are bounded. Links
must be HTTP(S) and cannot contain embedded credentials. Verify a harmless
automation before enabling operational alerts.
