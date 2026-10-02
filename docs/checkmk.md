# Checkmk notifications to Nowlert

[Configured-installation tutorial](guides/checkmk-to-nowlert.md) · [All illustrated tutorials](guides/infrastructure-tutorials.md)

Checkmk's native notification system calls a site-local notification script with
host/service context. This integration uses that documented interface, without
polling hosts or running an additional monitoring agent.

## Nowlert setup

1. Upgrade to an image containing Checkmk. CE provides **Checkmk HTTP** as a
   built-in route for new accounts and adds it once on upgrade for previously
   seeded accounts. In EE, create a route with integration **Checkmk**, input
   **HTTP**. Assign the route to your destination and enable both.
2. Create an application token scoped only to `checkmk` in Settings.
3. Your Checkmk site must reach `https://YOUR_NOWLERT/checkmk/events` with a
   certificate it trusts. Requests use `X-Nowlert-Token`, not a token in the URL.

## Checkmk setup

Run these steps as the **Checkmk site user**, inside the site container if used.

1. Copy [tools/checkmk_notification.py](../tools/checkmk_notification.py) to
   `~/local/share/check_mk/notifications/nowlert`, then make it executable:

   ```sh
   chmod 0755 ~/local/share/check_mk/notifications/nowlert
   mkdir -p ~/.config/nowlert
   chmod 0700 ~/.config/nowlert
   touch ~/.config/nowlert/checkmk.json
   chmod 0600 ~/.config/nowlert/checkmk.json
   ```

2. Edit that configuration file privately with:

   ```json
   {"url":"https://YOUR_NOWLERT/checkmk/events","token":"YOUR_CHECKMK_TOKEN"}
   ```

   Keep the script and configuration in persistent site storage. Do not place
   the token in notification rule parameters, screenshots, or the repository.
3. In **Setup → Events → Notifications**, create a notification rule using
   method **Nowlert**. Select a single recipient/contact so one monitoring event
   is not sent repeatedly for every contact. Keep notification bulking disabled;
   this method processes one notification at a time. Keep asynchronous spooling
   enabled. No script parameters are required.
4. Include host and service notifications, all states and all notification types
   you want centralized. Do not restrict the rule to only CRIT or PROBLEM.
   Checkmk still observes its normal notification periods, acknowledgements,
   downtime suppression and host/service contact rules. Those can prevent an
   event from being emitted upstream; Nowlert cannot receive suppressed events.
5. Save; activate only if Checkmk shows pending changes. Use Checkmk's test notification on a disposable
   monitored object. Verify accepted HTTP 204, then inspect Nowlert Delivery
   history and the destination. Acceptance alone is not proof of delivery.

## Central filtering and troubleshooting

Nowlert preserves host name/alias/address, service, native check state, previous
state, notification type and site. Problems map WARN/UNKNOWN to warning and
CRIT/DOWN/UNREACH to critical. Recovery is success; acknowledgement, downtime,
flapping and custom notifications remain independently filterable.

Filter noisy hosts, services or notification types in Nowlert after validating
delivery. Arbitrary notification parameters, contact credentials and the full
process environment are never forwarded.

Check `~/var/log/notify.log` and `~/var/log/mknotifyd.log` for script results.
Exit 0 means accepted; 1 requests retry for temporary connection/429/5xx errors;
2 signals a final configuration/authentication/invalid-payload error. The script
uses a ten-second connection timeout and verifies TLS certificates.

Source: [Checkmk notification scripts and environment variables](https://docs.checkmk.com/latest/en/notifications.html#scripts).
