# Supermicro BMC / IPMI

Nowlert v1.9.0 provides a fixture-validated Supermicro candidate through the
explicit `/redfish/supermicro` endpoint and conservative delivered-email
detection. Both paths normalize to the `supermicro` routing key.

Configure the BMC Redfish Event Service subscription URL as:

```text
http://nowlert.example:8080/redfish/supermicro
```

Use `X-Nowlert-Token` when the BMC supports custom subscription headers. If
it cannot send a header, place the endpoint behind a trusted reverse proxy that
injects the token, or use the isolated SMTP compatibility path. Never expose an
unauthenticated Redfish endpoint to an untrusted network.

Create the source-scoped token under **Profile menu → Security → API tokens**
(allowing only Supermicro). Routing is configured in the WebUI, not in
`config.yaml`: create the destination under **Destinations**, then edit it,
open **Manage routes** and select the built-in **Supermicro Redfish** route.
The [hardware Redfish setup guide](guides/hardware-redfish-setup.md) shows the
complete flow.

Thermal, fan, power, memory, storage, security, firmware, network, chassis, and
availability categories share a consistent server-hardware presentation.
SMTP recognition requires both Supermicro/BMC/IPMI identity and hardware-event
language to avoid stealing unrelated mail. Real BMC firmware compatibility is
pending representative hardware validation.

