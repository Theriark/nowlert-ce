# Platform output adapters and previews

Nowlert v3.1.1 exposes database-authoritative destinations through a shared
output-adapter layer for Discord, Microsoft Teams, Slack, generic outbound
webhooks, MQTT, and ntfy.

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
| Discord | Components/presentation options | webhook URL |
| Microsoft Teams | presentation uses source image mapping | workflow webhook URL |
| Slack | safe presentation options | Slack webhook URL |
| Webhook | method, timeout, safe headers, JSON template, HMAC flag | URL; optional HMAC key/credential headers |
| MQTT | host, port, topic, QoS, retain, TLS, keepalive, client ID | optional username/password |
| ntfy | server, topic, priority, tags, title/action/timeout options | optional access token or username/password |

Outputs requiring multiple private values store a JSON object inside the
owner-only secret record, never in API-facing metadata.

## Discord

Discord uses source-aware rich presentation and packaged image assets. The
adapter uploads/uses the selected packaged artwork rather than exposing an
internal asset reference to Discord.

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

The default body is the versioned `nowlert.event.v1` envelope. Metadata is
bounded recursively and credential-like keys are redacted.

An optional JSON template may use the supported safe substitutions:

```json
{
  "summary": "${source}: ${title}",
  "host": "${host}",
  "severity": "${severity}",
  "event_id": "${event_id}"
}
```

Supported substitutions include `body`, `category`, `event_id`, `host`,
`severity`, `source`, `status`, and `title`.

Requests receive `X-Nowlert-Idempotency-Key`. When HMAC signing is enabled, the
canonical UTF-8 JSON body is signed with HMAC-SHA256 and sent in
`X-Nowlert-Signature`.

## MQTT

MQTT publishes the normalized event envelope to a bounded topic template. QoS
is limited to 0, 1, or 2; publish topics cannot contain wildcard subscription
characters; TLS is enabled by default; and credentials remain in the secret
store.

## ntfy

ntfy sends normalized title/message plus configured priority/tags and optional
safe action metadata. Hosted and self-hosted HTTPS servers are supported.
Credentials are private and excluded from previews/history.

## Outbound network policy

Webhook, MQTT, and ntfy destinations reject unsafe private/loopback resolution
by default. An administrator may explicitly enable private-network delivery for
an intentional self-hosted target.

Discord, Microsoft Teams, and Slack destination types do not expose that generic
private-network override.

## Preview and test delivery

Preview is credential-free. Test delivery resolves the real destination secret
internally and returns only safe outcome metadata such as success, retryability,
HTTP-like status, and bounded error code/text.

Test outcome can be stored as destination health state and surfaced in the
WebUI/routing flow without storing response bodies or credentials.

See [platform-routing.md](platform-routing.md) and
[platform-api.md](platform-api.md).
