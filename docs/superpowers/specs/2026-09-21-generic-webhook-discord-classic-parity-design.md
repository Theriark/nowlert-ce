# Generic Webhook Classic Presentation Parity Design

## Goal

Make Generic Webhook **Classic Card** reuse the approved Discord Classic source-specific presentation rules instead of maintaining its current minimal generic presentation.

The result must preserve a stable, destination-neutral `nowlert.event.v1` webhook contract while giving webhook consumers the same Classic information hierarchy already approved for Discord.

## Approved direction

Discord Classic remains the visual source of truth for Classic presentation.

Generic Webhook must not send Discord API payloads directly. Instead, the approved Discord Classic presentation is converted into a neutral Nowlert Classic presentation object embedded under the normal Generic Webhook event envelope.

Conceptually:

```text
Normalized Notification
        |
        v
Approved Discord Classic renderer
        |
        v
Discord classic embed model
        |
        +--> Discord destination -> Discord webhook payload
        |
        +--> Generic Webhook Classic -> neutral nowlert classic_card_v1 presentation
```

This avoids rebuilding and maintaining a second set of source-specific Classic cards for Generic Webhook.

## Classic presentation contract

When a Generic Webhook destination uses `message_style=classic`, the normal versioned `nowlert.event.v1` envelope remains authoritative for event data.

Its `presentation` object becomes a neutral representation derived from the approved Discord Classic embed:

```json
{
  "style": "classic_card_v1",
  "title": "string",
  "description": "string",
  "color": 15158332,
  "fields": [
    {
      "title": "string",
      "value": "string",
      "inline": true
    }
  ],
  "footer": "Nowlert CE • Classic Card",
  "timestamp": "optional string",
  "url": "optional string",
  "source_icon": "optional source identity"
}
```

The exact field content, ordering, grouping, lifecycle wording, and compactness rules come from the approved Discord Classic renderer.

The Generic Webhook payload must not expose Discord-only envelope keys such as `embeds`, `attachments`, Discord webhook query parameters, or multipart upload semantics.

## Source parity

Classic parity applies to every source currently covered by the Discord Classic renderer:

- Xen Orchestra
- Zabbix
- Grafana
- Portainer
- Proxmox
- QNAP
- Synology
- TrueNAS
- UniFi Network
- UniFi Protect
- UniFi Drive
- Home Assistant
- Redfish
- Supermicro
- HPE iLO
- Dell iDRAC
- generic/fallback notifications

If the Discord Classic renderer changes later, Generic Webhook Classic must inherit the same presentation automatically rather than requiring a second source-specific implementation.

## Modern presentation

Generic Webhook **Modern Card** remains unchanged in this change.

This design only replaces the current minimal Generic Webhook Classic presentation with Discord Classic parity.

## Delivery behavior

Generic Webhook transport behavior remains unchanged:

- stable `nowlert.event.v1` envelope;
- public HTTPS destination;
- fixed JSON POST for newly configured destinations;
- existing retry/delivery-history behavior;
- existing idempotency key behavior;
- credential redaction and bounded metadata;
- existing Discord-URL compatibility routing remains supported.

The presentation refactor must not change routing, ownership, authentication, secrets, retry policy, or destination health semantics.

## Implementation boundary

The implementation should introduce one reusable conversion boundary rather than copy Discord source renderers.

Expected shape:

1. Generate the already-approved Discord Classic payload for the notification.
2. Read the first Classic embed produced by that renderer.
3. Convert the embed into a destination-neutral `classic_card_v1` object.
4. Store that object in Generic Webhook `presentation`.
5. Leave Discord delivery using its existing payload unchanged.

If implementation work reveals that calling the existing renderer directly would create an unsafe circular dependency or require Discord transport state, extract the presentation-only Classic rendering function into a shared formatter module while preserving its current output byte-for-byte for Discord.

Do not duplicate source-specific Classic rendering logic into a new webhook-only formatter.

## Compatibility

Existing Generic Webhook consumers continue to receive the same top-level `nowlert.event.v1` event envelope.

The intentional contract change is limited to `presentation` when `message_style=classic`:

- old: minimal `classic_embed` with title, description, and four generic fields;
- new: `classic_card_v1` containing the full approved source-specific Classic presentation.

Modern webhook presentation remains unchanged.

The change must be documented as an additive presentation improvement, not as a new event schema version.

## Testing

Tests must prove:

1. Generic Webhook Classic uses the approved source-specific Discord Classic field geometry for representative sources.
2. Xen Orchestra Classic parity is preserved.
3. A complex source such as TrueNAS or Grafana includes its source-specific Classic fields rather than the old four generic fields.
4. Hardware sources use the existing Supermicro/HPE/Dell Classic presentation.
5. Generic fallback still produces a valid Classic presentation.
6. Generic Webhook output contains no Discord-only top-level payload structure such as `embeds` or `attachments`.
7. Discord Classic output remains unchanged.
8. Generic Webhook Modern output remains unchanged.
9. Existing Generic Webhook transport and destination tests remain green.

Implementation must follow test-first development: add failing parity tests before changing production code.

## Repository scope

Expected files include:

- `src/outputs/platform.py`
- `src/formatters/discord_classic_v1.py` or a new shared Classic presentation module if extraction is required
- Generic Webhook/Discord platform output tests
- `docs/platform-outputs.md`
- release/changelog documentation if required by the repository's existing validation rules

No unrelated formatter, Slack, Teams, parser, routing, WebUI layout, or deployment behavior should change.

## Non-goals

- Do not send raw Discord webhook payloads to arbitrary Generic Webhook receivers.
- Do not rebuild a separate set of Generic Webhook Classic cards.
- Do not change Discord Classic card content or visual geometry.
- Do not change Slack Classic.
- Do not redesign Generic Webhook Modern.
- Do not add custom methods, arbitrary headers, body templates, HMAC controls, or private-network options to the normal WebUI editor in this change.
- Do not change the `nowlert.event.v1` top-level event schema.
