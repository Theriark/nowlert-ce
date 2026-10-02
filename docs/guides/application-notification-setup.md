# Prepare Nowlert for application notifications

Use this shared setup before following the application tutorials. The local
configuration was checked on 2 October 2026 using development image
`ghcr.io/theriark/nowlert-ce:sha-e86c536b65f8cecf3428d72a7e4b9dc1d727965d`.
Use this image or a later image containing these integrations and the Metabase
connection-probe fix. These tests do not establish stable-release availability.

## Assign the built-in routes

1. Open **Destinations**, then create or edit the destination that should receive
   the application notifications.
2. Select **Manage routes**, search for the application's built-in HTTP route,
   and check its box. Select **Done**, then **Save changes** (or **Add destination**
   when creating a destination). Done applies the selection to the form; saving
   persists it. No extra route needs to be created.
3. Enable the destination and selected route. Start without severity/status
   restrictions. An unassigned route must not deliver to that destination.
4. In **Settings**, create an application token scoped only to that source.
   The local setup uses 300 requests/minute per application; choose a rate that
   fits your event volume. The token needs no administrator permissions.
5. Use a callback HTTPS address reachable from the application host/container,
   with a trusted certificate. Browser access alone does not prove reachability
   from that application's network.

| Application | Built-in route | Token scope | Local destination |
|---|---|---|---|
| Checkmk | Checkmk HTTP | `checkmk` | Criticals |
| Semaphore | Semaphore HTTP | `semaphore` | Operational |
| Sonarr | Sonarr HTTP | `sonarr` | Operational |
| Radarr | Radarr HTTP | `radarr` | Operational |
| Metabase | Metabase HTTP | `metabase` | Operational |

Destination names are examples; use your own. Keep tokens in application secret
settings or protected configuration files. Every token in these guides is a
placeholder. Screenshots exclude token values and passwords.

## Check delivery, then filter centrally

Run the application's native test. In Nowlert **Delivery history**, match its
time, source, and intended destination; inspect the result and verify the message
at the destination. A 2xx receiver response proves acceptance, not final delivery.
Metabase's empty connection test is the exception: it creates no event or delivery.

Keep native source triggers broad. Use Nowlert **Filtering** to suppress noise
for the destination, based on event type, status, and application fields. This
collects supported native notifications, not every log line, metric, or action.
Source schedules, conditions, acknowledgements and downtime can still suppress
events before they reach Nowlert.

For a route check, unassign only the application route on a test destination,
save, and repeat a distinguishable native test. Confirm it no longer delivers
there, then restore the intended assignment. Do not change production routing
solely to take a tutorial screenshot.

## Troubleshooting

| Symptom | Check |
|---|---|
| Route missing | Running image version, signed-in account, completed image upgrade |
| Test times out | DNS and HTTPS reachability from the app host/container, proxy and listener |
| HTTP 401 | Token scope, token validity, authentication header/provider setting |
| HTTP 429 | Token rate and application retries |
| Accepted but no destination message | Saved assignment, enabled route/destination, central filter outcome, destination response |
| Duplicate messages | Duplicate upstream notification rules, recipients, retries, or overlapping route assignments |

[Tutorial index](infrastructure-tutorials.md)
