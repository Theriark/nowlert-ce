# Send Zabbix webhooks to Discord with Nowlert CE

Nowlert CE can accept Zabbix events over the authenticated Event API and route
them to Discord through the same destination/routing model used by the rest of
the platform.

```text
Zabbix
  |
  | HTTPS/HTTP webhook
  v
POST /api/v2/events
  |
  | source = zabbix
  v
Nowlert CE route
  |
  v
Discord
```

The Event API is preferred for a webhook-style integration because tokens are
source-scoped, rate-limited, returned only at creation/rotation, and stored only
as digests.

## 1. Create a source-scoped Event API token

In the Nowlert WebUI, open **API Access / Event API Tokens** and create a token
for the Zabbix integration.

Use a source scope containing:

```text
zabbix
```

Copy the plaintext token when it is shown. Nowlert will not display that value
again.

## 2. Create the Discord destination

In **Destinations**:

1. create a destination;
2. choose **Discord**;
3. enter a clear display name such as `Monitoring - Discord`;
4. store the Discord webhook URL in the write-only secret field;
5. save the destination; and
6. run the built-in destination test.

## 3. Create the Zabbix HTTP route

In **Routes**, create a route with:

- Integration: **Zabbix**;
- Input: **HTTP**;
- Destination: the Discord destination;
- Enabled: yes.

Use host/event/severity/status filters if only a subset of Zabbix events should
reach this destination.

Dedicated Zabbix routes are evaluated before fallback routes. A wildcard
fallback does not fan out a second copy when a dedicated Zabbix route already
matched.

## 4. Send the Nowlert event envelope

The endpoint is:

```text
POST https://nowlert.example.com/api/v2/events
```

Authenticate with:

```http
Authorization: Bearer YOUR_EVENT_API_TOKEN
Content-Type: application/json
```

A representative event is:

```json
{
  "schema": "nowlert.event.v1",
  "source": "zabbix",
  "provider": "Zabbix",
  "category": "monitoring",
  "title": "High CPU load on pve-01",
  "message": "CPU load is above the configured trigger threshold.",
  "severity": "warning",
  "status": "active",
  "host": "pve-01",
  "metadata": {
    "event_id": "123456",
    "trigger": "High CPU load"
  }
}
```

The supported event schema is intentionally bounded. `source`, `title` and
`message` are required. Severity accepts the current Nowlert event levels such
as `information`, `warning`, `error` and `critical`; status accepts values such
as `active`, `firing`, `resolved`, `ok` and `success`.

For a recovery event, send the same event identity/context with for example:

```json
{
  "schema": "nowlert.event.v1",
  "source": "zabbix",
  "provider": "Zabbix",
  "category": "monitoring",
  "title": "High CPU load on pve-01",
  "message": "CPU load returned below the configured trigger threshold.",
  "severity": "success",
  "status": "resolved",
  "host": "pve-01"
}
```

## 5. Map Zabbix macros into the payload

In a Zabbix Webhook media type, map the event values you already use into the
Nowlert envelope. A practical mapping is:

| Nowlert field | Zabbix value |
|---|---|
| `source` | constant `zabbix` |
| `provider` | constant `Zabbix` |
| `title` | trigger/event name |
| `message` | problem or recovery description |
| `host` | affected host name |
| `severity` | mapped Zabbix severity |
| `status` | `active`/`firing` for problems, `resolved` for recovery |
| `metadata.event_id` | Zabbix event ID |

Do not send the Nowlert token inside the JSON body. Keep it in the HTTP
`Authorization` header configured by the webhook/media type.

## 6. Validate with curl before enabling the Zabbix action

A direct request helps separate Nowlert configuration from Zabbix media-type
configuration:

```bash
curl --fail-with-body \
  --header 'Authorization: Bearer REPLACE_WITH_TOKEN' \
  --header 'Content-Type: application/json' \
  --data '{
    "schema":"nowlert.event.v1",
    "source":"zabbix",
    "provider":"Zabbix",
    "category":"monitoring",
    "title":"Nowlert Zabbix test",
    "message":"Synthetic validation event from the Zabbix integration guide.",
    "severity":"warning",
    "status":"active",
    "host":"zabbix-test"
  }' \
  https://nowlert.example.com/api/v2/events
```

Then confirm the event appears in **Delivery History** and reaches Discord.

Current presentation example:

![Nowlert Discord Zabbix notification](../images/v2.5.2-discord-zabbix.png)

The screenshot is an existing packaged presentation example; the current
routing/token model is the v3.1.x database-authoritative platform model
described in this guide.

## Security notes

- Prefer HTTPS through a trusted reverse proxy when Zabbix and Nowlert do not
  communicate entirely inside a trusted private network.
- Scope the token to `zabbix` only.
- Set a sensible token rate limit for the expected event volume.
- Revoke/rotate the token if it is exposed.
- Do not reuse WebUI login credentials as Event API credentials.

## Troubleshooting

### HTTP 401/403

Check the bearer token, token owner state, source scope and token expiry/revoked
state. The token must authorize `zabbix`.

### HTTP 400

Validate the JSON envelope. The schema must be `nowlert.event.v1`, required
strings must be non-empty, and severity/status values must be supported.

### Request is accepted but Discord is empty

Check the Zabbix (HTTP) route filters, destination enabled state and Delivery
History. Test the Discord destination separately.

## Next step

Once the synthetic request works, configure the Zabbix action/media type to
submit real problem and recovery events, then review the first few deliveries
against the source event details.

- <https://github.com/Theriark/nowlert-ce>
