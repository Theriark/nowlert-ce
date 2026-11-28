# Dell iDRAC

Nowlert v1.9.0 provides a fixture-validated Dell iDRAC candidate through
`POST /redfish/dell` and conservative delivered iDRAC email alerts. Both paths
use the `dell_idrac` routing key.

Use this Redfish Event Service destination:

```text
http://nowlert.example:8080/redfish/dell
```

Authenticate with a source-scoped header token where supported. Otherwise use
a trusted token-injecting reverse proxy or the existing SMTP listener. The
adapter recognizes storage, power, thermal, memory, network, security,
firmware, chassis, and availability events and retains safe operator actions.

Destinations, routes and tokens are managed in the WebUI, not in
`config.yaml`. Create a source-scoped Event API token for Dell iDRAC under
**Security → Event API tokens**, create the destination under
**Destinations**, then edit it, open **Manage routes** and select the built-in
**Dell iDRAC Redfish** route. The
[Dell iDRAC Redfish routing guide](guides/dell-idrac-redfish-routing.md) walks
through each step.

Trusted management systems can generate routine `USR0030` and `USR0032`
login/logout audit records over REDFISH, IPMI over LAN, or another management
transport. These successful session records can be handled without delivery
for each destination: open **Filtering**, choose the destination, choose
**Dell iDRAC**, and list the trusted client addresses, one per line, under
**Session audit suppression → Trusted management client IPs**, then save. The
addresses become a block rule of that destination's Dell iDRAC filter, so each
destination keeps its own list.

Older versions kept one global list in the Dell iDRAC integration settings
record (`suppress_ipmi_session_audit_from`). Nowlert moves such a list into a
block rule on every destination that receives Dell iDRAC routes and then deletes
the global record, so do not set it through
`PUT /api/v2/integration-settings/dell_idrac`: the value would not stay.

The filter requires all three signals: a Dell iDRAC notification, message ID
`USR0030` or `USR0032`, and an exact configured source address. Transport text
is deliberately irrelevant. Failed logins, untrusted addresses, and all other
security events continue through normal routing. Suppressed events are logged
as handled so the BMC does not retry them.

Nowlert does not call the iDRAC API, poll Lifecycle Controller data, or need
permanent administrative credentials. Real validation across iDRAC releases
remains pending and should begin with a harmless test alert.
