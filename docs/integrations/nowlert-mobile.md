# Nowlert Mobile destination

Send CE events to the native Nowlert Mobile app using a topic-scoped publish key.

1. Sign in to Nowlert Mobile, enable notifications and send a test alert.
2. Create a topic in Topics and subscribe the receiving device to it. Copy its UUID.
3. In API tokens, create a publish key scoped to that topic. Copy the key once.
4. In CE Destinations, select **Nowlert Mobile**. Enter the Mobile platform HTTPS
   base URL and topic UUID, then paste the key into **Topic-scoped publish key**.
   Development uses `https://nowlert-mb-dev.theriark.dev`. Use the URL and a separate
   key/topic for the environment where the receiving app is signed in.
5. Save and test the destination. Confirm receipt in the app, then assign the
   destination to a CE route.

The publish key uses CE's existing private credential handling and is never
returned in destination read responses or previews. Leave the field blank while
editing to keep the current key. Public settings contain only the base URL, topic
UUID and optional destination label. Do not put a key in the URL or settings.

Alerts contain bounded, sanitized title/body and CE source, severity, host,
category, status, event identity and matched route. Critical events map to urgent,
warnings/errors to high, and informational/recovery events to default priority.
Alerts from the same destination, source, host and category form a thread.
Retries keep the same idempotency key; separate CE event IDs create separate alerts.
Upstream integrations should provide a stable, unique event ID for each occurrence.

HTTP 202 means the Mobile platform accepted the alert. CE's delivery history shows
**Accepted**; it does not establish device delivery, reading or acknowledgement.
The native app tracks reading and acknowledgement separately. **Acknowledge** does
not modify the originating CE event. No CE deep link is fabricated.

Check the platform URL and publish key for 401/403, and the topic UUID/subscription
if an accepted alert does not appear. 429, network timeouts and server failures
use CE's bounded retry policy. Redirects are refused to protect the publish key.
Provider response bodies and raw exception messages are not persisted. Do not
paste publish keys into tickets or logs.
