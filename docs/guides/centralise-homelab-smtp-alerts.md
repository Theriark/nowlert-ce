# Centralise homelab SMTP alerts without mailbox rules

Many infrastructure products can already send email, but routing those messages
through a personal mailbox creates extra moving parts: forwarding rules, mailbox
credentials, provider dependencies and long vendor-specific messages that are
hard to scan quickly.

Nowlert CE can receive SMTP directly from supported infrastructure products,
normalise the event and route it to collaboration destinations such as Discord,
Microsoft Teams or Slack.

```text
SMTP-capable infrastructure
        |
        | direct SMTP
        v
Nowlert CE
        |
        | source detection + normalisation
        | deterministic routing
        v
Discord / Teams / Slack / ...
```

Nowlert does not poll IMAP, Gmail, Microsoft Graph or other mailboxes.

## Where this fits

The current v3.1.2 integration catalogue includes SMTP input for products such
as:

- Xen Orchestra;
- QNAP; and
- TrueNAS.

Other integrations use HTTP or Redfish instead. Nowlert keeps those transports
inside the same routing and destination model after ingestion.

## 1. Enable the SMTP listener

The current process configuration contains listener/bootstrap settings only.
A simple trusted-network listener looks like this:

```yaml
smtp:
  enabled: true
  host: 0.0.0.0
  port: 8025
```

Expose the configured port only to the systems that need to send events. Host
and network firewall allowlists remain important even when TLS/authentication
are enabled.

## 2. Choose the right security boundary

For a trusted private homelab network, the backward-compatible listener can run
without SMTP authentication.

If SMTP crosses an untrusted network, enable **STARTTLS** before enabling SMTP
AUTH. Nowlert supports SMTP AUTH `LOGIN` and `PLAIN` only after STARTTLS, and
TLS 1.2 or newer is required.

A TLS-enabled listener uses mounted certificate material:

```yaml
smtp:
  host: "0.0.0.0"
  port: 8025
  tls:
    enabled: true
    certfile: "/nowlert/config/tls/cert.pem"
    keyfile: "/nowlert/config/tls/key.pem"
```

Do not place SMTP passwords directly in tracked configuration. Use an
environment variable or mounted secret.

See [SMTP security](../smtp-security.md) for the full secure rollout procedure.

## 3. Create destinations in the WebUI

Open **Destinations** and create the collaboration targets you actually use.
Current destination adapters include:

- Discord;
- Microsoft Teams;
- Slack;
- generic webhook;
- MQTT; and
- ntfy.

Destination credentials are stored as owner-scoped write-only secrets rather
than being returned by normal read APIs.

## 4. Create dedicated routes

Create routes from **Routes** using the integration and SMTP input, for example:

```text
Xen Orchestra (SMTP) -> Infrastructure Discord
QNAP (SMTP)           -> Storage Teams
TrueNAS (SMTP)        -> Infrastructure Discord
```

Routes can filter on host, event, severity and status. Dedicated integration
routes are evaluated first. Wildcard routes are fallback-only and run only when
no enabled dedicated route matches.

This is useful for keeping one SMTP listener while still giving each product a
clear routing policy.

## 5. Point each appliance directly at Nowlert

For every SMTP-capable infrastructure product:

1. set the SMTP server to the Nowlert host/IP;
2. use the configured SMTP port (8025 by default);
3. configure STARTTLS/authentication if your deployment requires it; and
4. send a harmless built-in test or normal operational notification.

Do not forward the event through a mailbox first unless the appliance cannot
reach Nowlert directly and you explicitly accept the extra dependency.

## 6. Verify the operational path

For each source, confirm:

- Nowlert detected the expected integration;
- the event matched the intended dedicated route;
- the selected destination received the notification; and
- **Delivery History** records the expected outcome.

Once the basic path is proven, tighten route filters and SMTP network exposure.

## Example: one homelab, several products

A small environment could use:

```text
Xen Orchestra --SMTP--\
QNAP ----------SMTP----> Nowlert CE -> Discord
TrueNAS -------SMTP---/              -> Teams

Zabbix --------HTTP-----------------> same routing/destination model
Dell iDRAC ----Redfish--------------> same routing/destination model
```

The value is not merely centralising transport. Nowlert converts separate
vendor-specific event formats into one deterministic operational routing model.

## Why this is simpler than mailbox forwarding

Direct infrastructure-to-Nowlert delivery avoids:

- personal or shared mailbox credentials;
- mailbox forwarding/rule drift;
- IMAP/Graph/Gmail polling integrations;
- cloud mail-provider availability in the event path; and
- treating a long raw email as the final operational notification.

You retain the source system as the authority for the event while Nowlert
handles normalisation, routing and destination-aware delivery.

## Run Nowlert CE

Nowlert CE is free, open source and self-hosted.

- Repository: https://github.com/Theriark/nowlert-ce
- Quick start: https://github.com/Theriark/nowlert-ce#-quick-start
