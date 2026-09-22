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
shared by Modern and Classic presentations. The default limits are 50 active
deliveries process-wide and 10 active deliveries for the same destination.
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

Operators can choose **Modern Card** or **Classic Card** per destination.
Existing destinations without `message_style` still normalize to Modern.

Modern no longer has a separate Teams visual design. Nowlert renders the event
with the exact same source-specific image renderer used by Discord Modern, then
places that PNG inside a minimal Adaptive Card 1.4 image wrapper. Xen Orchestra,
Zabbix, Grafana, Portainer, Proxmox, QNAP, Synology, TrueNAS, UniFi
Network/Protect/Drive, Home Assistant, Redfish, Supermicro, HPE iLO, Dell iDRAC,
and generic/Nowlert fallback therefore inherit the same Modern layout changes
automatically.

Teams workflow requests remain JSON-only and bounded to 28 KiB, so the rendered
PNG is referenced by HTTPS rather than embedded in the webhook body. Nowlert
stores each image below `platform.state_dir/teams-modern-cards` and publishes
it from the existing public health path as
`/api/health/teams-modern-card/<unguessable-token>.png`. Plain
`/api/health` continues to return normal health JSON. The public origin comes
from `NOWLERT_TEAMS_PUBLIC_BASE_URL` or, when unset, `webui.public_url`.

The token is 48 hexadecimal characters plus `.png`; unknown, expired,
malformed, and traversal-like tokens return 404. Images are retained for
90 days. This allows the Cloudflare-protected WebUI to remain private while
Teams fetches only the unguessable image through the health path that is
already public for health checks.

Modern is fail-closed. If the exact Discord-rendered image cannot be rendered
or published, delivery returns `teams_modern_image_unavailable` and sends no
Teams request. Nowlert never silently replaces a requested Modern Card with the
native grey Teams layout.

Classic remains a separate Teams-native renderer. It consumes the approved
Classic Card v1 information contract used by Discord Classic and renders that
content as Adaptive Card elements. Modern image parity does not modify Classic.

Serialized Teams JSON payloads remain bounded to 28 KiB before transport.
HTTP 202 means the Teams workflow accepted the request; the UI does not claim
that the card was rendered in the destination channel without operator
confirmation.

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

When the configured Generic Webhook URL is a Discord webhook, delivery bypasses
the destination-neutral JSON transport and is handed to the native Discord
adapter. **Modern Card therefore uses the exact same source-specific Discord
Modern image renderer, layout, typography, lifecycle colors, icons, spacing,
and dynamic vertical sizing as a normal Discord destination.** Classic Card
uses the same native Discord Classic path. Generic Webhook does not maintain a
second Discord-specific card implementation, so later Discord presentation
changes are inherited automatically.

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
