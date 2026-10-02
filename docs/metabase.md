# Metabase alerts to Nowlert

[Configured-installation tutorial](guides/metabase-to-nowlert.md) · [All illustrated tutorials](guides/infrastructure-tutorials.md)

## Configure Nowlert first

1. Upgrade to a development image containing this integration. Fresh accounts
   receive its built-in routes; existing accounts seeded by earlier images get
   the new routes on upgrade. Existing assignments and filtering are preserved.
2. Create or edit your destination and assign this application's built-in route.
   Enable the destination and route. Leave source severity/status restrictions
   empty initially so every notification emitted by the application can arrive.
3. For HTTP, issue a source-scoped token in Settings. Give it only this
   application's source and the required event rate. Use HTTPS for callbacks.
4. Configure the application's notification settings as described below.
5. Send its native test and check Nowlert Delivery history, source identity,
   destination result and the actual notification received. A local fixture test
   does not establish that your application is connected.
6. Apply noise suppression in Nowlert Filtering, using event/status and the
   application-specific fields. Keep the upstream notification triggers broad.

Assign **Metabase HTTP** and issue a `metabase`-scoped token. In Metabase open
**Admin → Settings → Webhooks → Add a webhook**. Name it Nowlert and set:

```text
https://nowlert.example/metabase/alerts
```

Choose **Bearer** authentication and paste the scoped token. On each question
whose alert should be centralized, create/edit its alert and select this webhook
as recipient. Keep the desired question conditions/schedule in Metabase; these
conditions generate the alert, while Nowlert decides which destinations receive
it. Use the native test and then exercise a real question alert.

Metabase's empty authenticated connection probe returns HTTP 204 without
creating an event or delivery. A real question-alert test is required to prove
the destination flow. For a private LAN callback, see the illustrated tutorial
for `MB_HTTP_CHANNEL_HOST_STRATEGY: allow-private` and trusted TLS setup.

Nowlert recognizes Metabase's `type: alert`, question metadata and `sent_at`.
Filtering includes question name/ID, alert ID, creator, status and severity.
It reports result-row count but does not retain the base64 chart or raw query
rows in normalized metadata or outbound cards. Test alerts have a null alert ID.

This covers **question alerts**. Metabase's native webhooks are not dashboard
subscriptions or a server/database health monitor.

Source: [Metabase webhooks and native payload](https://www.metabase.com/docs/latest/configuring-metabase/webhooks).
