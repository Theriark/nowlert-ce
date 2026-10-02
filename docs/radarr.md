# Radarr notifications to Nowlert

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

Assign **Radarr HTTP** and issue a `radarr`-scoped token. In Radarr go to
**Settings → Connect → + → Webhook**. Set POST and this URL:

```text
https://nowlert.example/radarr/events?token=YOUR_RADARR_TOKEN
```

Enable every notification trigger offered by your version, including health
issues/recoveries, updates, grabs/imports, movie additions/deletions and manual
interaction events. Use **Test** and save. Radarr sends its native JSON directly.

Filter centrally by event type, instance, movie title, download client, health
type, message, status and severity. Health Restored is a successful recovery;
future native event types are retained. Queue conditions Radarr does not emit
through Connect are outside this integration's coverage.

Source: [Radarr Webhook implementation](https://github.com/Radarr/Radarr/blob/develop/src/NzbDrone.Core/Notifications/Webhook/Webhook.cs).
