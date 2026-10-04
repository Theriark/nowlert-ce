# Illustrated infrastructure tutorials

Use these walkthroughs to reproduce the tested infrastructure-to-Discord flows.
The guides contain configuration steps, available screenshots, test procedures, and
troubleshooting. The screenshots were captured from the local deployment;
replace its addresses and channel labels with your own.

| Tutorial | What it demonstrates | Validation |
|---|---|---|
| [UniFi Network, Protect and Drive to Discord](unifi-to-discord.md) | Scoped header tokens, broad Network/Protect alarms, 78 event-specific Drive alarms, and central filtering | Native Network and Protect events delivered, HTTP 200. Native Drive Shared Drive Created delivered to Storage on 3 October, HTTP 200; fault/recovery pairs are not yet native-verified. |
| [Home Assistant to Discord](home-assistant-to-discord.md) | Scoped secret, broad alert automations, native notification test | Native notification and real integration errors delivered, HTTP 200. |
| [TrueNAS to Discord](truenas-to-discord.md) | SMTP transport, Info-level Email service, native alert test | Native TrueNAS test delivered, HTTP 200. |
| [Portainer to Discord](portainer-to-discord.md) | Scoped URL token, native webhook channel, all alert rules, and delivery checks | Native authentication warning and recovery delivered, both HTTP 200; production threshold restored. |
| [Centralized event coverage](centralized-event-coverage.md) | Broad source subscriptions and backup-report policies | Audit lists accepted changes and remaining validation limits. |
| [Xen Orchestra to Discord](xen-orchestra-to-discord.md) | SMTP transport, backup-report recipient, built-in route, Discord destination, and Delivery history | Real backup report delivered. |
| [Hardware Redfish setup](hardware-redfish-setup.md) | Source-scoped token, vendor routes, subscription JSON, and safe test actions for iLO, iDRAC, and Supermicro | iLO4 controller event and iDRAC8 native informational event delivered, HTTP 200. Supermicro native test delivered through the isolated HTTP relay, HTTP 200. |
| [Legacy iLO4 local TLS listener](ilo4-local-tls-listener.md) | Portainer deployment, no-SNI TLS callback, native chunked request, and HTTP 200 acknowledgement | Verified on iLO4 2.81 with the specified development image. |

## Newly configured application tutorials

Start with [shared Nowlert route, token and delivery setup](application-notification-setup.md).
These configurations were verified on 2 October 2026 against the development
image recorded in that guide.

| Tutorial | Native configuration | Validation |
|---|---|---|
| [Checkmk](checkmk-to-nowlert.md) | Site-local script, one recipient, broad notification rule | Real host/service events delivered; saved rule screenshots included. |
| [Semaphore](semaphore-to-nowlert.md) | Native Slack provider, project alerts, success suppression off | Read-only task #30 success and native notification delivered. |
| [Sonarr](sonarr-to-nowlert.md) | Native POST webhook, scoped header, all 13 triggers | Native tests delivered; enabled-trigger screenshot included. |
| [Radarr](radarr-to-nowlert.md) | Native POST webhook, scoped header, all 12 triggers | Native tests delivered; enabled-trigger screenshot included. |
| [Metabase](metabase-to-nowlert.md) | Bearer webhook, real failed-delivery question, hourly alert | Healthy run suppressed; separate native question test delivered to Discord, HTTP 200. |
| [Grafana](grafana-to-nowlert.md) | Native Bearer webhook contact point, resolved notifications enabled, distinct telemetry query-health rule | Controlled Grafana-managed rule firing and recovery delivered, HTTP 200. |
| [Prometheus](prometheus-to-nowlert.md) | Alertmanager webhook, private token file, resolved notifications enabled, configuration-reload health rule | Controlled Prometheus rule firing and recovery delivered through Alertmanager, HTTP 200. |
| [GitHub Actions reference](../github-actions.md) | Public HTTPS callback required | Deferred by the operator; no repository hooks configured. |

## Screenshot coverage

Read [notification lifecycle coverage](notification-lifecycle.md) for the native
problem, recovery and success behavior of each integration and its source limits.

| Page or configuration step | Capture |
|---|---|
| Checkmk saved native notification rule | [All events/method](../images/application-setup/checkmk-all-events.jpg), [recipient](../images/application-setup/checkmk-single-recipient.png), [conditions/save behavior](../images/application-setup/checkmk-sending-conditions.jpg) |
| Sonarr saved connection and all native triggers | [Connections](../images/application-setup/sonarr-all-events.png) |
| Radarr saved connection and all native triggers | [Connections](../images/application-setup/radarr-all-events.jpg) |
| Semaphore native task success and notification log | [Task #30](../images/application-setup/semaphore-native-test.png) |
| Metabase saved webhook, no token value | [Webhook destination](../images/application-setup/metabase-webhook.png) |
| Metabase hourly failure alert and native delivery proof | [Saved alert](../images/application-setup/metabase-delivery-alert.jpg), [native question test](../images/application-setup/metabase-native-question-delivered.png) |
| Gmail API enabled | [API status, account header omitted](../images/email-setup/gmail-api-enabled.jpg) |
| Microsoft delegated mailbox permission | [Mail.Read, address concealed](../images/email-setup/microsoft-mail-read-redacted.png) |
| Both mailbox connections healthy | [Private labels concealed](../images/email-setup/mailboxes-healthy-redacted.png) |
| Real No-IP warning classification | [Email, hostname and mailbox label concealed](../images/email-setup/noip-warning-redacted.png) |
| Home Assistant enabled alert automations | [Automation entities](../images/home-assistant-setup/enabled-automations.png) |
| Home Assistant native notification test | [Action](../images/home-assistant-setup/native-test.png), [delivery proof](../images/home-assistant-setup/native-delivery-proof.png) |
| Home Assistant authenticated receiver acceptance | [HTTP 204 response](../images/home-assistant-setup/transport-response.png) |
| TrueNAS saved Info Email service | [Service](../images/truenas-setup/info-alert-service.png) |
| TrueNAS native alert delivery | [Delivery proof](../images/truenas-setup/delivery-proof.png) |
| iLO resource noise suppressed centrally | [Rule](../images/hardware-setup/ilo-resource-filter.png), [filtered outcomes](../images/hardware-setup/ilo-resource-filter-proof.png) |
| Hardware token scope selection | [Token form](../images/hardware-setup/nowlert-token-scope.png) |
| Issued token list, credential value excluded | [Token list](../images/hardware-setup/nowlert-token-list.png) |
| Configured destination list | [Destinations](../images/hardware-setup/nowlert-destinations.png) |
| Hardware Discord edit form | [Hardware destination](../images/hardware-setup/nowlert-hardware-destination.png) |
| Built-in hardware routes | [Redfish assignments](../images/hardware-setup/nowlert-hardware-routes.png) |
| iLO event subscription | [Redacted API readback](../images/hardware-setup/hpe-subscription-record.png) |
| Dell event subscription | [Redacted API readback](../images/hardware-setup/dell-subscription-record.png) |
| Supermicro event subscription | [Redacted API readback](../images/hardware-setup/supermicro-subscription-record.png) |
| Local Portainer stack | [Running services](../images/hardware-setup/portainer-stack-running.png) |
| TLS listener configuration | [Listener](../images/hardware-setup/portainer-tls-config.png), [forwarding and allowlist](../images/hardware-setup/portainer-tls-forwarding.png) |
| Actual iLO callback acknowledgement | [Access log](../images/hardware-setup/portainer-hpe-callback.png) |
| Actual iLO-to-Discord delivery | [Native image delivery](../images/hardware-setup/hpe-native-image-delivery.png) |
| Xen Orchestra Discord edit form | [Operational destination](../images/hardware-setup/nowlert-xen-destination.png) |
| Xen Orchestra SMTP route | [SMTP assignment](../images/hardware-setup/nowlert-xen-routes.png) |
| Xen Orchestra transport-email | [Host, port, security](../images/hardware-setup/xen-orchestra-transport-email.png), [authentication fields](../images/hardware-setup/xen-orchestra-transport-auth.png) |
| Xen Orchestra backup-reports | [Recipient](../images/hardware-setup/xen-orchestra-backup-reports.png), [test controls](../images/hardware-setup/xen-orchestra-backup-test.png) |
| Actual Xen Orchestra SMTP delivery | [Delivery history](../images/hardware-setup/xen-orchestra-delivery.png) |

Controller subscriptions were configured through authenticated Redfish API
calls, not through their SMTP WebUI forms. Their illustrated records are
explicitly labeled API readbacks. The [token-free source records](../images/hardware-setup/records/)
are included so the captures can be checked against the data.

## Release and marketing notes

For mailbox sources, follow the illustrated [Gmail](gmail-email-alerts.md) and
[Microsoft 365 / Outlook](microsoft-email-alerts.md) tutorials, then the
[shared rules and delivery walkthrough](gmail-microsoft-email-alerts.md).
Both local mailbox connections and background synchronization were verified on
4 October 2026. Real No-IP notices matched the warning rule. Gmail remains in
Google Testing mode; production authorization is outstanding. Native OpenAI
incident/resolution and email-to-destination delivery proof are not yet captured.
Personal addresses and account labels are concealed in the tutorial images.

The native iLO fix was verified in a development image. Before advertising it as
a stable-release feature, promote and test a release containing that fix and
update the version references in the guides. The separate TLS listener remains
deployment configuration; mounting the Nowlert image does not create it.

Verified claims supported by these captures are **Xen Orchestra SMTP to Discord**
and **iLO4 Redfish to Discord on the documented listener and image**. Do not label
a native hardware fault/recovery pair as verified from an informational/test
event alone. Dell and Supermicro controller-native delivery and Drive native
alarm delivery are captured in the linked guides. Portainer's native warning
and matching recovery are also verified. A subscription readback or laptop-generated receiver test
does not establish controller delivery.
