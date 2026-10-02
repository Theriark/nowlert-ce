# Illustrated infrastructure tutorials

Use these walkthroughs to reproduce the tested infrastructure-to-Discord flows.
Each guide contains the configuration steps, screenshots, test procedure, and
troubleshooting. The screenshots were captured from the local deployment;
replace its addresses and channel labels with your own.

| Tutorial | What it demonstrates | Validation |
|---|---|---|
| [UniFi Network, Protect and Drive to Discord](unifi-to-discord.md) | Scoped header tokens, broad Network/Protect alarms, 78 event-specific Drive alarms, and central filtering | Native Network and Protect events delivered, HTTP 200. Drive receiver test delivered; native UNAS emission remains unverified. |
| [Home Assistant to Discord](home-assistant-to-discord.md) | Scoped secret, broad alert automations, native notification test | Native notification and real integration errors delivered, HTTP 200. |
| [TrueNAS to Discord](truenas-to-discord.md) | SMTP transport, Info-level Email service, native alert test | Native TrueNAS test delivered, HTTP 200. |
| [Portainer to Discord](portainer-to-discord.md) | Scoped URL token, native webhook channel, all alert rules, and delivery checks | Configuration saved; delivery verification described in the guide. |
| [Centralized event coverage](centralized-event-coverage.md) | Broad source subscriptions and backup-report policies | Audit lists accepted changes and remaining validation limits. |
| [Xen Orchestra to Discord](xen-orchestra-to-discord.md) | SMTP transport, backup-report recipient, built-in route, Discord destination, and Delivery history | Real backup report delivered. |
| [Hardware Redfish setup](hardware-redfish-setup.md) | Source-scoped token, vendor routes, subscription JSON, and safe test actions for iLO, iDRAC, and Supermicro | iLO4 controller event delivered; iDRAC8 and Supermicro delivery remains unverified. |
| [Legacy iLO4 local TLS listener](ilo4-local-tls-listener.md) | Portainer deployment, no-SNI TLS callback, native chunked request, and HTTP 200 acknowledgement | Verified on iLO4 2.81 with the specified development image. |

## Screenshot coverage

| Page or configuration step | Capture |
|---|---|
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

The native iLO fix was verified in a development image. Before advertising it as
a stable-release feature, promote and test a release containing that fix and
update the version references in the guides. The separate TLS listener remains
deployment configuration; mounting the Nowlert image does not create it.

Verified claims supported by these captures are **Xen Orchestra SMTP to Discord**
and **iLO4 Redfish to Discord on the documented listener and image**. Do not label
the older iDRAC8 or Supermicro setup as end-to-end verified until their controller
callback tests pass. A subscription readback or a laptop-generated receiver test
does not establish controller delivery.
