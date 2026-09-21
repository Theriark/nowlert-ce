# Platform output adapters and previews

The platform output layer introduced in Nowlert v3.1.2 exposes database-authoritative
destinations through a shared output-adapter layer for Discord, Microsoft Teams, Slack,
and generic outbound webhooks.

Adapters receive safe public destination metadata, an internally resolved
owner-scoped secret, and the normalized `Notification` model.

## Common contract

Every adapter provides:

- credential-free preview using backend formatters;
- one bounded transport attempt returning a structured result;
- no response-body, raw exception-text, or credential persistence; and
- compatibility with the shared retry/delivery-history service.

Retry policy is intentionally bounded. Retryable transport/server failures may
be retried by the delivery service; terminal client/configuration failures are
not retried indefinitely.

## Destination settings and secrets

Public destination settings and private credentials are separate.
Credential-like values must not be placed in the public settings document.

| Output | Public settings | Owner-scoped secret |
|---|---|---|
| Discord | message style and destination label | webhook URL |
| Microsoft Teams | message style and destination label | workflow webhook URL |
| Slack | message-detail option and destination label | Slack webhook URL |
| Webhook | message style and destination label | webhook URL |

## Discord

Discord uses source-aware rich presentation and packaged image assets. Operators
can choose **Modern Card** or **Classic Card**. The adapter uploads/uses the
selected packaged artwork rather than exposing an internal asset reference to
Discord.

## Delivery concurrency

Nowlert dispatches matched destinations through one bounded delivery scheduler
shared by Modern and Classic presentations. The default limits are 40 active
deliveries process-wide and 8 active deliveries for the same destination.
Excess work is queued fairly by destination so one slow or retrying webhook
cannot occupy the worker pool and block unrelated destinations.

Delivery ordering is intentionally not guaranteed: a later fast notification
may complete before an earlier slow notification. Retry delays and destination
HTTP timeouts are unchanged. In this phase ingress remains synchronous with
its own delivery summary; a durable immediate-ack queue is a separate future
change.

Normal SQLite connections may overlap. Backup/restore and other maintenance
operations retain exclusive database access and block new connections while
maintenance is waiting.

## Microsoft Teams

Microsoft Teams uses native Adaptive Card 1.4 payloads and public HTTPS
source-image URLs because Teams clients do not reliably render embedded
data-URI artwork. Published release images pin the default source-image base to
immutable release content.

Operators can choose **Modern Card** or **Classic Card** per destination.
Modern remains the default and preserves the existing standardized Teams
layout. Existing destinations that do not yet store `message_style` normalize
to Modern automatically.

Classic uses a separate Teams-native renderer so Classic layout changes do not
modify Modern cards. It consumes the approved Classic Card v1 information
contract used by Discord Classic and renders that content as Adaptive Card
elements. Xen Orchestra, Zabbix, Grafana, Portainer, Proxmox, QNAP, Synology,
TrueNAS, UniFi Network/Protect/Drive, Home Assistant, Redfish, Supermicro,
HPE iLO, Dell iDRAC, and generic/Nowlert fallback events all use the Classic
renderer when the destination selects Classic.

Serialized Teams payloads remain bounded to 28 KiB before transport. HTTP 202
means the Teams workflow accepted the request; the UI does not claim that the
card was rendered in the destination channel without operator confirmation.

## Slack

Slack previews/delivery use bounded Block Kit-style content with plain-text
fallback and normalized source/severity/host context. Credential sanitization
is applied before payload construction.

## Generic outbound webhook

Generic Webhook is intentionally backend-owned rather than a raw HTTP request
builder. Operators provide a webhook URL, a destination label, and select one of
two Nowlert presentation models:

- **Modern Card** (default) — structured card-style presentation metadata; or
- **Classic Card** — the same approved source-specific Classic information
  hierarchy used by Discord Classic, encoded as destination-neutral
  `classic_card_v1` JSON.

Both modes send the stable, versioned `nowlert.event.v1` envelope. Metadata is
bounded recursively and credential-like keys are redacted. The selected
presentation is included under the envelope's `presentation` object so a generic
receiver can render the event without requiring operators to author JSON
payloads in the WebUI.

Classic mode does not send a Discord webhook payload. Nowlert renders the
approved Discord Classic presentation first, then converts its title,
description, color, ordered fields, footer, and optional URL/timestamp into the
`presentation` object inside the stable event envelope. Discord-only `embeds`,
attachments, webhook query parameters, and media-upload semantics are not
exposed to generic receivers.

For example:

```json
{
  "schema": "nowlert.event.v1",
  "source": "grafana",
  "presentation": {
    "style": "classic_card_v1",
    "title": "🚨 Database latency — Firing",
    "description": "Database latency is high.",
    "color": 15158332,
    "fields": [
      {
        "title": "🚨 Alert",
        "value": "**Severity:** `critical`",
        "inline": false
      }
    ],
    "footer": "🦉 Nowlert CE • Classic Card"
  }
}
```

Automation consumers should use the stable event-envelope fields for routing and
logic. The `presentation` object is rendering metadata for receivers that want
to reproduce Nowlert's approved card presentation.

Delivery uses a fixed HTTPS `POST` with JSON, a 15-second timeout, and the
`X-Nowlert-Idempotency-Key` header. The WebUI does not expose request methods,
custom headers, payload templates, HMAC keys, or private-network overrides.

Existing destinations created by older versions may retain the former advanced
HTTP settings until they are saved through the simplified editor. This is an
upgrade-compatibility path only; new Generic Webhook destinations use the
backend-owned contract above.

## Outbound network policy

All supported destination types require public HTTPS delivery targets. Generic
Webhook does not expose a private-network override in the simplified editor.

## Preview and test delivery

Preview is credential-free. Test delivery resolves the real destination secret
internally and returns only safe outcome metadata such as success, retryability,
HTTP-like status, and bounded error code/text.

The destination-card **Send test** is a Nowlert-owned synthetic event. It always
uses the Nowlert source/icon and the destination name instead of inheriting an
integration from an attached route. Discord, Teams, and Generic Webhook render
that event using the destination's selected Modern/Classic presentation; Slack
renders it through its current Classic-only presentation.

Test outcome can be stored as destination health state and surfaced in the
WebUI/routing flow without storing response bodies or credentials.

See [platform-routing.md](platform-routing.md) and
[platform-api.md](platform-api.md).
