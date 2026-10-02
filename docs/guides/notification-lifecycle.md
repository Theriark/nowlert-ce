# Problems, recovery and successful operations

Severity describes a problem's importance. State describes its lifecycle.
A recovery is shown as success even when the original problem was critical.
Receipt by Nowlert and delivery to a destination are separate from that state:
an accepted request alone does not prove a Discord or Teams message arrived.

## Native lifecycle support

| Integration | Problems/failures | Recovery or successful operation | Source limitation |
|---|---|---|---|
| Checkmk | Host DOWN/UNREACH/UNREACHABLE; service WARN/WARNING, CRIT/CRITICAL, UNKNOWN | RECOVERY is resolved/success | Acknowledgement, flapping and downtime are separate lifecycle notices; an OK flapping notice is not a recovery. |
| UniFi Network | Explicit disconnection/failure events and vendor severity | Explicit UPS power restored, Internet restored and device reconnection identities | Alarm Manager's installed Internet/Devices selectors do not expose a general “send resolved” checkbox. Nowlert cannot invent events the controller does not send. |
| UniFi Protect | Recognized device/application issues and explicit offline/update-failure identities | Explicit online/reconnection, issue-resolved and update-completed identities | Motion, person, animal and line-crossing detections are point-in-time events, without an implicit resolved counterpart. Unknown keys remain informational. |
| UniFi Drive | Backup failures/partial completion and storage faults | Backup completed | Ordinary file/account activity is informational; not every activity has a recovery. |
| Sonarr / Radarr | HealthIssue, health warnings, ManualInteractionRequired | HealthRestored | Media events are informational activity, not monitoring recoveries. Enable Health Restored on the native webhook. |
| Semaphore | Native ERROR/FAILED task result | Native SUCCESS task result | Stock email notification behavior differs from the native webhook. Keep successful task notifications enabled. |
| GitHub Actions | Failed, timed-out, action-required/startup-failure conclusions | Success conclusion | Local installation is deferred until GitHub has a reachable HTTPS callback. |
| Metabase | Question alert condition matched (`firing`) | No automatic recovery webhook when results become empty | Payload supplies the question/alert, not a generic problem severity. Configure a meaningful question condition rather than manufacturing failure/recovery states. |
| Portainer | Native alert `firing` | Native alert `resolved` | Source must actually send resolved alerts. |
| Home Assistant | Firing/error/warning events | Explicit resolved/cleared/OK state in the forwarder | An isolated log entry has no automatic recovery event. |
| TrueNAS | New problem alerts | Cleared alerts | Configure the native alert service to forward both new and cleared notifications. |
| Dell iDRAC / HPE iLO / Supermicro Redfish | Native critical/warning hardware events | Explicit recovery/normal events | Event capabilities depend on firmware and its Redfish subscription; receiving a test does not prove all native hardware events. |
| Xen Orchestra | Failed/partial backup report | Completed backup report | Completion of one backup is a successful operation, not a recovery for every earlier backup failure. |
| Grafana / Prometheus / Zabbix | Native firing/problem state | Native resolved/recovery state | Enable recovery delivery in the source's notification configuration. |

## Installation audit: 2 October 2026

Checkmk's broad native rule forwards all notification types. Receiver logs showed
HTTP 400 for long-form WARNING and CRITICAL states; those aliases are now accepted
alongside the short forms. Existing history also contained delivered short-form
problems and genuine RECOVERY events. Keep the host/service condition and
notification type when diagnosing apparent OK-only traffic.

UniFi's saved Network and Protect forwarding rules select their native event
groups broadly. The UPS Power Restored rule is saved; at inspection it had zero
hits, so it is not evidence of a live recovery. Native Network Accessed and
Protect Admin Access are routine activity, not failures. Native trigger identity
controls classification; a user-defined alarm called “Recovered” cannot turn a
motion event into a recovery. Additional lifecycle-key tests are synthetic parser
coverage, not claims that this controller has emitted those keys.

The existing central filters for Wi-Fi/client noise, high traffic, threats,
motion/person/vehicle/audio/animals remain in place. Filter problem state or
severity deliberately; avoid blocking an entire source when you still need its
faults and recoveries.

The [Metabase guide](metabase-to-nowlert.md) includes a real saved question that
alerts on failed Nowlert deliveries. Its healthy empty result suppresses alerts.

[Infrastructure tutorials](infrastructure-tutorials.md)
