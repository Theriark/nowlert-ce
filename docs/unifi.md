# UniFi integration

For the current UI-based setup, source-scoped tokens and illustrated delivery
checks, use [UniFi Network, Protect and Drive to Discord](guides/unifi-to-discord.md).
The YAML examples below document the older 1.7.0 configuration interface.

Nowlert `1.7.0` provides three independent normalized UniFi sources:

- `unifi_network` receives UniFi Network Alarm Manager JSON webhooks;
- `unifi_protect` receives UniFi Protect Alarm Manager JSON webhooks; and
- `unifi_drive` receives UniFi Drive Alarm Manager JSON webhooks or parses
  delivered UniFi Drive notification email through SMTP.

All three sources use the shared `Notification` model, router, Discord output,
and Microsoft Teams output.

## Native HTTP input

The HTTP input runs alongside SMTP and remains disabled unless explicitly enabled:

```yaml
http:
  enabled: true
  host: "0.0.0.0"
  port: 8080
  max_body_bytes: 1048576
  shared_secret: "REPLACE_WITH_A_RANDOM_SECRET"
```

Supported endpoints:

```text
POST /unifi/network
POST /unifi/protect
POST /unifi/drive
```

Successful parse and dispatch returns HTTP 204. Invalid JSON or an invalid
source envelope returns 400, unknown paths return 404, unsupported methods
return 405, and oversized bodies return 413.

When `shared_secret` is non-empty, every request must include:

```text
X-Nowlert-Token: <secret>
```

Use HTTPS termination, a strong token, and source restrictions. Do not expose
the native listener directly to the public internet.

## Container ports

```yaml
ports:
  - "8025:8025"
  - "18080:8080"
```

Publishing port `8080` does not enable HTTP; `http.enabled` must also be true.

## UniFi Network

Configure Alarm Manager to POST JSON to `/unifi/network`. Network notifications
normalize controller, event, category, severity, client, network or Wi-Fi,
connected-device, duration, RSSI, and event-time context. MAC addresses remain
excluded from visible cards by default.

## UniFi Protect

Configure Alarm Manager to POST JSON to `/unifi/protect`. Protect notifications
use the actual trigger event and trigger device while preserving the configured
rule as `Alarm rule`.

## UniFi Drive webhooks

Configure Alarm Manager to POST JSON to `/unifi/drive`.

The discovered default Drive payload is intentionally small:

```json
{
  "alarm_id": "00000000-0000-4000-8000-000000000001",
  "text": "Alarm \"Nowlert | Drive - Backup Task Partially Completed\" was triggered"
}
```

The alarm ID is internal metadata and is not displayed in Discord or Teams.

Unlike Protect, Drive does not identify the exact condition inside a
multi-trigger alarm. Create one Drive alarm per event and use descriptive names:

```text
Nowlert | Drive - Backup Task Partially Completed
Nowlert | Drive - Backup Task Failed
Nowlert | Drive - Backup Task Completed
Nowlert | Drive - Storage Pool Suspended
```

For names using `Drive - <event>` or `Drive | <event>`, Nowlert uses the final
event segment as the card title and preserves the full name in `Alarm rule`.

## UniFi Drive delivered email

Drive email support remains available. Nowlert does not poll IMAP, Microsoft
Graph, Gmail, or any mailbox and stores no mailbox credentials. Email-based
Drive notifications require an external forwarding rule or SMTP relay.

## Routing and targets

Destinations and routes are managed in the WebUI, not in `config.yaml` (which
refuses `outputs` and `routing` sections). Create the Discord or Microsoft
Teams destination under **Destinations**, with the webhook in the write-only
**Webhook URL** field, then edit it, open **Manage routes** and select the
built-in **UniFi Network HTTP**, **UniFi Protect HTTP** and **UniFi Drive
HTTP** routes you need. The [UniFi to Discord guide](guides/unifi-to-discord.md)
shows the complete flow.

## Reverse proxy

All three paths can use the same production backend:

```text
/unifi/network -> nowlert:8080
/unifi/protect -> nowlert:8080
/unifi/drive   -> nowlert:8080
```

Keep the shared token enabled even on a private Docker network.
