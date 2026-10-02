# Sonarr notifications to Nowlert

[Configured-installation tutorial](guides/sonarr-to-nowlert.md) · [All illustrated tutorials](guides/infrastructure-tutorials.md)

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

Assign **Sonarr HTTP** and issue a `sonarr`-scoped token. In Sonarr go to
**Settings → Connect → + → Webhook**. Set the method to POST and URL to:

```text
https://nowlert.example/sonarr/events
```

Add a **Custom Headers** entry with key `X-Nowlert-Token` and value
`YOUR_SONARR_TOKEN`. The configured installation uses header authentication.

Enable all notification triggers offered by your version, including Health
Issue, Health Restored, application updates, grabs/imports/deletions and manual
interaction events. Click **Test**, then save. The payload is Sonarr's native
JSON; no custom script is needed.

Central filter fields include event type, instance, media title, download
client, health type and message. Health Issue severity follows the native level;
Health Restored is successful recovery. Test messages and future event types
with the native envelope are accepted. Nowlert receives only notifications
Sonarr's Connect system emits; it does not inspect the download queue itself.

Source: [Sonarr Webhook implementation](https://github.com/Sonarr/Sonarr/blob/develop/src/NzbDrone.Core/Notifications/Webhook/Webhook.cs).
