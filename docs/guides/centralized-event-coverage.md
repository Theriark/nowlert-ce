# Collect supported source events before centralized filtering

Configure sources to emit their broadest supported notification stream, then
apply destination policies in Nowlert **Filtering**. Source-specific limitations
still apply: an alerting subscription is not a universal audit-log export.

## Local configuration audit: 2 October 2026

| Source | Previous restriction | Change and validation |
|---|---|---|
| Home Assistant | Legacy error-only automation was disabled | Added enabled forwarders for warning/error logs, updates, repairs, persistent notifications, and lifecycle. Native notification and real integration errors delivered to Security with HTTP 200. Existing automations preserved. |
| TrueNAS 25.04.2.6 | SMTP used another host and STARTTLS | Saved the reachable Nowlert SMTP host with approved Plain security; set the existing enabled Info Email service recipient. Native Send Test Alert delivered to Storage with HTTP 200. |
| HPE iLO4 | Alert and StatusChange only | PATCH accepted HTTP 200 for all five advertised event types. Subsequent ResourceAdded and ResourceRemoved events appeared as Delivered in Nowlert. Subscription readback is pending a renewed private controller session. |
| Supermicro | Alert and StatusChange only | Earlier PATCH changes were ignored. The approved isolated HTTP subscription was subsequently created and read back with all five types. Its controller-native Send Test Event reached Nowlert and delivered to Criticals, HTTP 200. TLS delivery remains unverified. |
| Dell iDRAC8 | Alert and StatusChange only | This firmware rejects subscription PATCH with HTTP 405. An additional all-five subscription was created with HTTP 201; its response lists all five types. The old subscription was preserved. On 3 October a separate all-five compatibility subscription was read back and a native User Login event delivered to Criticals, HTTP 200. Original subscriptions were preserved. |
| Xen Orchestra backup reports | Theriark VM and configuration/metadata jobs used Skipped and failure | All six existing jobs now show Always, including configuration/metadata. Both restricted jobs were changed and the saved overview was checked. |
| Portainer BE Alerting | Manager disabled, no channels, rules disabled | Enabled the internal manager, configured the authenticated Nowlert channel, and enabled all 13 available rules. No alert silences existed. Delivery verification is described in the Portainer tutorial. |

All three controllers' Event Services advertise exactly:

```json
["StatusChange", "ResourceUpdated", "ResourceAdded", "ResourceRemoved", "Alert"]
```

Use the firmware's advertised event types rather than inventing unsupported
values. Existing routes and destinations were preserved. Dell's additive
subscription overlaps the older subscription for Alert and StatusChange; review
duplicate callbacks before retiring an old subscription during a planned change.

For Xen Orchestra, choose **Always** on every supported backup job and leave
report compaction/success suppression disabled when full reports are needed.
All six saved job conditions are Always; the reporting details of each
job still deserve review. This setting does not export all XO tasks or audit logs.

Portainer thresholds, evaluation periods, Kubernetes-only rules, Alertmanager
grouping/inhibition, and source-side silences can affect the emitted stream.
Enabling every rule does not turn native Alerting into a raw Docker-event feed.

![Newly included iLO resource events delivered](../images/portainer-setup/ilo-expanded-event-delivery.png)

![All six Xen Orchestra jobs report Always](../images/portainer-setup/xen-backup-report-coverage.png)

## Reproduce and verify

1. Read the source's advertised capabilities and current subscriptions/settings.
2. Enable the broadest supported event types or reporting condition.
3. Read the configuration back, then send a safe source-originated test.
4. Confirm receipt and delivery or filtering in Nowlert.
5. Maintain delivery policies centrally; monitor source subscription health too.

Use the [hardware tutorial](hardware-redfish-setup.md),
[Xen Orchestra tutorial](xen-orchestra-to-discord.md), and
[Portainer tutorial](portainer-to-discord.md) for the setup steps.

The [Home Assistant tutorial](home-assistant-to-discord.md) includes portable
alert forwarders; the [TrueNAS tutorial](truenas-to-discord.md) uses Info as the
minimum alert level. These cover native alert streams, not universal telemetry
or audit exports. Only notification/log paths were exercised for Home Assistant;
update, repair, and lifecycle triggers remain configured but not live-tested here.

## Keep broad iLO intake without flooding a destination

After expanding iLO to all advertised event types, ResourceAdded/ResourceRemoved
messages arrived repeatedly with severity Ok. They are native controller events,
not evidence of an agent repeatedly invoking a test action. The precise creating
client was not established; polling software can create transient resources.

The local Criticals destination now blocks only the combination of severity
`ok` and either `iLOEvents.0.9.ResourceAdded` or `iLOEvents.0.9.ResourceRemoved`.
The UI's configured conditions are a block policy, not an allowlist. The source
subscription stays broad; other message IDs, warnings/failures, and other recovery
messages are not matched. Routing Flow showed six subsequent events filtered.
Resource creation/removal with Ok is intentionally suppressed for this destination;
use a separate unfiltered destination if those events are operationally useful.

![Saved narrow iLO block rule](../images/hardware-setup/ilo-resource-filter.png)

![Native iLO events now filtered centrally](../images/hardware-setup/ilo-resource-filter-proof.png)

## Monitoring and native validation follow-up: 3 October 2026

- **Grafana:** reused the built-in route and assigned it to Operational. The
  native Bearer webhook contact point includes resolved notifications. A
  temporary managed rule fired and recovered; both deliveries returned HTTP 200.
- **Prometheus:** reused the built-in route and assigned it to Operational.
  Alertmanager uses a source-scoped token file and `send_resolved: true`. A
  temporary Prometheus rule fired and recovered; both deliveries returned HTTP 200.
- **Duplicate-condition prevention:** Checkmk retains device availability and
  hardware faults. Prometheus owns configuration-reload health; Grafana owns
  telemetry-query availability/staleness. Temporary validation rules were removed.
- **Dell:** a native informational callback reached the approved private
  TLS 1.2 RSA/AES-CBC compatibility listener and delivered with HTTP 200.
- **UniFi Drive:** creating an empty validation share triggered its existing
  native alarm and delivered to Storage with HTTP 200. The test share was deactivated.
- **Supermicro:** the native controller test reached the approved IP-restricted
  HTTP relay and delivered to Criticals, HTTP 200. The saved subscription includes
  all five event types; HTTPS negotiation remains unresolved.
- **Portainer:** a positive-threshold controlled authentication rule test produced
  a native warning and matching recovery, both delivered through Nowlert,
  HTTP 200. The original threshold was restored immediately after capture.
- **Still unverified:** native Dell/Drive/Supermicro real fault-and-recovery pairs
  have not been exercised.

See the [Grafana tutorial](grafana-to-nowlert.md),
[Prometheus tutorial](prometheus-to-nowlert.md),
[hardware validation](hardware-redfish-setup.md#dell-native-validation-3-october-2026),
and [Drive validation](unifi-to-discord.md#drive-native-validation-3-october-2026).

## TV and media-box connectivity noise

The local installation filters these events centrally in Nowlert, while keeping
source collection enabled:

| Integration / destination | Blocked conditions |
|---|---|
| UniFi Network / Security | Client `tv-*` or `box-*`, client connected/disconnected events |
| Checkmk / Criticals | Host `tv-*` or `box-*`, IoT availability or ping services; host availability notifications |
| Zabbix / Criticals | Host `tv-*` or `box-*`, ICMP ping/unavailable/unreachable/offline problem names |
| Home Assistant / Security | TV/box Chromecast socket and webOS system logs; webOS error logs also covered when the sender omits device identity |

Availability recoveries are blocked alongside the expected power-off problems.
This avoids an orphan “recovered” notification when a television is switched on.
Device names must follow the TV-/BOX- convention, or be added explicitly to the
matching rule. The unnamed webOS fallback suppresses that integration's error
logs as a class; it cannot distinguish individual error messages with the current
Home Assistant filter fields. Other Home Assistant components remain unaffected.

Saved-policy readback confirmed enabled filters on both destinations. Thirty
simulated callbacks, including repeated copies, passed through the live receiver:
all thirty were filtered, with zero destination delivery attempts. Seventeen
positive/negative predicate checks confirmed that server connectivity and unrelated
TV/box service faults do not match these new rules. Simulations validate the
filtering pipeline; they do not claim that a device was physically powered off.
