# Controlled integration delivery validation

On 2 October 2026, four integrations awaiting native-source proof were tested
against the local Nowlert development deployment. Each request used the packaged
mock fixture in the application's native payload format, a temporary source-scoped
token, and the real selected route/destination. Temporary test tokens were revoked.
Titles or event context explicitly identify these callbacks as **SIMULATION**.

| Integration | Conditions exercised | Assigned destination | Receiver | Delivery |
|---|---|---|---|---|
| Portainer | Firing, resolved | Operational | 204 for both | Delivered, HTTP 200 for both |
| UniFi Drive | Backup task failed, completed | Storage | 204 for both | Delivered, HTTP 200 for both |
| Dell iDRAC | Predictive disk failure, recovery | Criticals | 204 for both | Delivered, HTTP 200 for both |
| Supermicro | Thermal warning, recovery | Criticals | 204 for both | Delivered, HTTP 200 for both |

[Token-free delivery records](../examples/integration-validation-2026-10-02.json)
record the observed event status, outcome and destination HTTP response. Portainer,
Dell and Supermicro used run `SIMULATION-20261002T223937Z`; Drive used
`SIMULATION-20261002T224106Z`. Drive's text must retain the native
`Alarm "..." was triggered` shape; an initially malformed simulation was corrected.

These results establish receiver authentication, parsing, routing and destination
delivery for the exercised conditions. They do **not** establish that Portainer,
UNAS, iDRAC or Supermicro emitted the requests. Native device/app test proof remains
outstanding for those four sources. See [the tutorial index](infrastructure-tutorials.md)
for native configuration steps and the existing proof limits.

## Central UniFi noise filter

The Security destination's enabled UniFi Network filter now also blocks:

- `Network Accessed` / `networkaccessed`.
- `Blocked by Firewall` / `blockedbyfirewall`.

The previous block rule remains intact. Two labelled callbacks sent through the
live receiver returned HTTP 204, incremented the filtered count by two, and
produced zero destination deliveries. Clause checks also confirmed that
`Internet Disconnected` and `Internet Restored` did not match this new rule.
Apply equivalent policies to other destinations if they also receive these events.
