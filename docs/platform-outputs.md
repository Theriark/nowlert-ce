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
| Microsoft Teams | destination label | workflow webhook URL |
| Slack | message-detail option and destination label | Slack webhook URL |
| Webhook | message style and destination label | webhook URL |

## Discord

Discord uses source-aware rich presentation and packaged image assets. Operators
can choose **Modern Card** or **Classic Embed**. The adapter uploads/uses the
selected packaged artwork rather than exposing an internal asset reference to
Discord.

## Microsoft Teams

Microsoft Teams uses Adaptive Card-style payloads and public HTTPS source-image
URLs because Teams clients do not reliably render embedded data-URI artwork.
Published release images pin the default source-image base to immutable release
content.

Serialized Teams payloads are bounded to 28 KiB before transport. HTTP 202 means
the Teams workflow accepted the request; the UI does not claim that the card
was rendered in the destination channel without operator confirmation.

## Slack

Slack previews/delivery use bounded Block Kit-style content with plain-text
fallback and normalized source/severity/host context. Credential sanitization
is applied before payload construction.

## Generic outbound webhook

Generic Webhook is intentionally backend-owned rather than a raw HTTP request
builder. Operators provide a webhook URL, a destination label, and select one of
two Nowlert presentation models:

- **Modern Card** (default) — structured card-style presentation metadata; or
- **Classic Embed** — compact embed-style presentation metadata.

Both modes send the stable, versioned `nowlert.event.v1` envelope. Metadata is
bounded recursively and credential-like keys are redacted. The selected
presentation is included under the envelope's `presentation` object so a generic
receiver can render the event without requiring operators to author JSON
payloads in the WebUI.

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

Test outcome can be stored as destination health state and surfaced in the
WebUI/routing flow without storing response bodies or credentials.

See [platform-routing.md](platform-routing.md) and
[platform-api.md](platform-api.md).
