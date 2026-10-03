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
| Checkmk saved native notification rule | [All events/method](../images/application-setup/checkmk-all-events.jpg), [recipient](../images/application-setup/checkmk-single-recipient.jpg), [conditions/save behavior](../images/application-setup/checkmk-sending-conditions.jpg) |
| Sonarr saved connection and all native triggers | [Connections](../images/application-setup/sonarr-all-events.jpg) |
| Radarr saved connection and all native triggers | [Connections](../images/application-setup/radarr-all-events.jpg) |
| Semaphore native task success and notification log | [Task #30](../images/application-setup/semaphore-native-test.jpg) |
| Metabase saved webhook, no token value | [Webhook destination](../images/application-setup/metabase-webhook.jpg) |
| Metabase hourly failure alert and native delivery proof | [Saved alert](../images/application-setup/metabase-delivery-alert.jpg), [native question test](../images/application-setup/metabase-native-question-delivered.jpg) |
| Home Assistant enabled alert automations | [Automation entities](../images/home-assistant-setup/enabled-automations.jpg) |
| Home Assistant native notification test | [Action](../images/home-assistant-setup/native-test.jpg), [delivery proof](../images/home-assistant-setup/native-delivery-proof.jpg) |
| Home Assistant authenticated receiver acceptance | [HTTP 204 response](../images/home-assistant-setup/transport-response.jpg) |
| TrueNAS saved Info Email service | [Service](../images/truenas-setup/info-alert-service.jpg) |
| TrueNAS native alert delivery | [Delivery proof](../images/truenas-setup/delivery-proof.jpg) |
| iLO resource noise suppressed centrally | [Rule](../images/hardware-setup/ilo-resource-filter.jpg), [filtered outcomes](../images/hardware-setup/ilo-resource-filter-proof.jpg) |
| Hardware token scope selection | [Token form](../images/hardware-setup/nowlert-token-scope.png) |
| Issued token list, credential value excluded | [Token list](../images/hardware-setup/nowlert-token-list.png) |
| Configured destination list | [Destinations](../images/hardware-setup/nowlert-destinations.jpg) |
| Hardware Discord edit form | [Hardware destination](../images/hardware-setup/nowlert-hardware-destination.jpg) |
| Built-in hardware routes | [Redfish assignments](../images/hardware-setup/nowlert-hardware-routes.jpg) |
| iLO event subscription | [Redacted API readback](../images/hardware-setup/hpe-subscription-record.jpg) |
| Dell event subscription | [Redacted API readback](../images/hardware-setup/dell-subscription-record.jpg) |
| Supermicro event subscription | [Redacted API readback](../images/hardware-setup/supermicro-subscription-record.jpg) |
| Local Portainer stack | [Running services](../images/hardware-setup/portainer-stack-running.jpg) |
| TLS listener configuration | [Listener](../images/hardware-setup/portainer-tls-config.jpg), [forwarding and allowlist](../images/hardware-setup/portainer-tls-forwarding.jpg) |
| Actual iLO callback acknowledgement | [Access log](../images/hardware-setup/portainer-hpe-callback.jpg) |
| Actual iLO-to-Discord delivery | [Native image delivery](../images/hardware-setup/hpe-native-image-delivery.png) |
| Xen Orchestra Discord edit form | [Operational destination](../images/hardware-setup/nowlert-xen-destination.jpg) |
| Xen Orchestra SMTP route | [SMTP assignment](../images/hardware-setup/nowlert-xen-routes.jpg) |
| Xen Orchestra transport-email | [Host, port, security](../images/hardware-setup/xen-orchestra-transport-email.jpg), [authentication fields](../images/hardware-setup/xen-orchestra-transport-auth.jpg) |
| Xen Orchestra backup-reports | [Recipient](../images/hardware-setup/xen-orchestra-backup-reports.jpg), [test controls](../images/hardware-setup/xen-orchestra-backup-test.jpg) |
| Actual Xen Orchestra SMTP delivery | [Delivery history](../images/hardware-setup/xen-orchestra-delivery.png) |

Controller subscriptions were configured through authenticated Redfish API
calls, not through their SMTP WebUI forms. Their illustrated records are
explicitly labeled API readbacks. The [token-free source records](../images/hardware-setup/records/)
are included so the captures can be checked against the data.

## Release and marketing notes

For mailbox-based sources, see [Gmail and Microsoft Email Alerts](gmail-microsoft-email-alerts.md).
The local No-IP and OpenAI status groups are prepared; provider application
registration, mailbox consent, sender-specific rules and native delivery remain
pending. Do not advertise these two mailbox connections as configured yet.

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
