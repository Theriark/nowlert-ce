# Nowlert Mobile

Add a destination and select **Nowlert Mobile**. Its default name is Nowlert
Mobile; you can change it at any time.

1. Select **Connect Nowlert Mobile** to get a temporary connection code.
2. In the Mobile app, open **Integrations → Connect Nowlert CE**, enter the
   code, review the destination name and approve. The app connects a personal
   **Nowlert CE** topic by default and subscribes you to receive its alerts.
3. CE displays **Connected** with the topic name. Select **Manage routes** to
   choose which routes may deliver to this destination.
4. Select **Add destination** or **Save changes** to save the connection and
   selected routes together.

Codes expire after ten minutes. Select Connect again if a code expires. An
interrupted status check retries automatically. If saving fails, correct the
problem and save again; CE retains the approved connection for one hour after
redeeming it. Merely approving or polling does not create a destination.

When editing a connected destination, its connection and selected routes are
retained. You can rename it, adjust routes, or select Reconnect Nowlert Mobile
to approve a new connection. Existing manually configured Mobile destinations
remain usable and show a connected status without requesting technical fields.

Use the existing destination test action to send a test, then confirm receipt in
the app. Server acceptance is separate from device delivery, read and
acknowledgement. Normal route filtering and delivery history still apply.

## Administrator reference

CE selects the Mobile service on the server using
`NOWLERT_DEPLOYMENT_ENVIRONMENT`: `development`, `stage`, or `production`
(default). If the explicit environment is unset, CE uses the existing server
`DD_ENV` deployment setting. Recognized aliases include `dev`, `stg` and `prod`;
unrecognized tracing environments use production. These select `https://nowlert-mb-dev.theriark.dev`,
`https://nowlert-mb-stg.theriark.dev`, or `https://nowlert-mb.theriark.com`.
The development Compose file selects development explicitly. Set
`NOWLERT_MOBILE_ORIGIN` to override the origin for an installation. It must be a
credential-free HTTPS origin. No browser input or Host header selects it.

Pairing credentials are owner-scoped, short-lived and stored through CE's
existing private secret files outside SQLite. The browser receives only the
temporary human code, CE connection reference and safe approval status. CE
polls `/api/v1/integrations/ce/connections/status` without redeeming; only the
standard destination save redeems the topic-scoped publish credential. Failed
saves retain the redeemed grant in the existing secret store for retries.

The existing destination API continues to accept `nowlert_mobile` settings
`base_url` and `topic_id`, with `secret.api_token` containing a topic-scoped
publish key, for administrator automation. These fields are not part of the
normal destination editor. Do not use a customer or administrative API key.
