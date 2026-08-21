# Route Dell iDRAC Redfish events through Nowlert CE

Dell iDRAC can emit Redfish Event Service notifications. Nowlert CE accepts
those events on a dedicated Dell endpoint, normalises the vendor payload into
the shared event model, applies deterministic routing, and delivers a structured
notification to destinations such as Discord or Microsoft Teams.

```text
Dell iDRAC
    |
    | Redfish Event Service
    v
POST /redfish/dell
    |
    | source = dell_idrac
    | normalize + deduplicate
    v
Nowlert route
    |
    v
Discord / Teams / ...
```

Nowlert does not poll the iDRAC API and does not require permanent iDRAC
administrator credentials.

## What you need

- a running Nowlert CE v3.1.2 instance;
- HTTP/HTTPS reachability from iDRAC to the Nowlert HTTP listener or trusted
  reverse proxy;
- a source-scoped Nowlert token that allows `dell_idrac`, unless you deliberately
  use the compatible shared-secret path; and
- a configured Nowlert destination and route.

The dedicated endpoint is:

```text
/redfish/dell
```

For example:

```text
https://nowlert.example.com/redfish/dell
```

## 1. Keep the HTTP listener enabled

The current process/bootstrap configuration includes the HTTP listener:

```yaml
http:
  enabled: true
  host: 0.0.0.0
  port: 8080
  max_body_bytes: 1048576
```

When exposing Nowlert outside a trusted private network, put the WebUI/HTTP
listener behind an appropriate HTTPS reverse proxy and restrict management
network access as needed.

## 2. Create a source-scoped token

Use the Nowlert WebUI to create an Event API/application token scoped for the
Dell iDRAC source. The plaintext token is shown only at creation/rotation and is
stored by Nowlert only as a digest.

The Redfish endpoint accepts either:

```text
Authorization: Bearer <token>
```

or:

```text
X-Nowlert-Token: <token>
```

The token must be authorized for `dell_idrac`. If the token is revoked,
expired, disabled through its owner, out of scope, or over its configured rate
limit, the request is rejected.

## 3. Create the destination

In **Destinations**, create the output that should receive hardware events, for
example a Discord channel or Microsoft Teams webhook.

Keep a dedicated hardware destination if that makes the operational ownership
clearer. Destination credentials remain write-only and are not exposed in
normal platform reads.

## 4. Create a Dell iDRAC Redfish route

In **Routes**, create:

- **Integration:** Dell iDRAC
- **Input:** Redfish
- **Destination:** your hardware destination
- **Enabled:** yes

Start with broad matching for validation. Afterwards, use host/event/severity or
status criteria to restrict delivery if required.

Dedicated Dell iDRAC routes are evaluated before wildcard Redfish fallback
routes. A fallback is considered only when no enabled dedicated route matches.

## 5. Configure the Redfish subscription in iDRAC

Point the iDRAC Redfish Event Service subscription at the public/reachable
Nowlert endpoint:

```text
https://nowlert.example.com/redfish/dell
```

Provide the source token using a supported authentication mechanism. If the
controller cannot set the required header directly, use a trusted
header-injecting reverse proxy between iDRAC and Nowlert rather than storing
permanent iDRAC administrator credentials in Nowlert.

Use a harmless test event first. Vendor firmware can differ in registry and
payload details, so compare the resulting Nowlert card with the original iDRAC
event log before relying on a new firmware/version combination.

## 6. What Nowlert does with the event

The Dell endpoint accepts JSON and routes parsed events through the normal
platform path. For Redfish events Nowlert also:

- records the input type as Redfish;
- applies source-scoped authentication;
- deduplicates repeated events inside the configured window;
- acknowledges duplicates without routing them again; and
- avoids retaining raw payloads or credential values in delivery history.

The current Redfish parser covers common Dell hardware-management categories
including storage, power, thermal, memory, network, security, firmware, chassis
and availability events.

## 7. Verify the result

After a test event:

1. confirm the destination received a Dell iDRAC-specific notification;
2. check **Delivery History** for the intended route and destination;
3. compare the event text/severity with the iDRAC event log; and
4. confirm repeated delivery of the exact same Redfish event does not create an
   unnecessary duplicate notification within the deduplication window.

A public Discord example is included in the repository:

![Nowlert Dell iDRAC Discord notification](../images/v2.5.2-discord-idrac.png)

## Authentication compatibility

Current v3.x platform state is database-authoritative for Event API tokens,
routes and destinations. Older documentation may show token or routing YAML from
v1.x-era releases. Do not recreate those legacy WebUI-managed YAML sections in
a current deployment.

Use the WebUI for the current resources and keep `config.yaml` limited to
listener/bootstrap/security settings.

## Security notes

- Restrict access to the Redfish endpoint to intended management networks where
  possible.
- Prefer HTTPS for traffic crossing untrusted networks.
- Use a source-scoped token instead of a broad shared credential when possible.
- Do not commit token values or destination secrets.
- Do not give Nowlert permanent iDRAC administrative credentials; they are not
  required for event ingestion.

## Run Nowlert CE

Nowlert CE is free, open source and self-hosted.

- Repository: https://github.com/Theriark/nowlert-ce
- Quick start: https://github.com/Theriark/nowlert-ce#-quick-start
