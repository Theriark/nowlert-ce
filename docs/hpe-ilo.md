# HPE iLO

Nowlert v1.9.0 provides a fixture-validated HPE iLO candidate through
`POST /redfish/hpe` and conservative HPE iLO AlertMail parsing. Both paths use
the `hpe_ilo` routing key.

Create an iLO Redfish Event Service subscription pointing to:

```text
http://nowlert.example:8080/redfish/hpe
```

Prefer a source-scoped token sent as `X-Nowlert-Token`. Where the installed
iLO release cannot add a header, use a protected reverse proxy or AlertMail to
Nowlert SMTP. Create the source-scoped token under **Security →
Event API tokens** (allowing only HPE iLO). Routing is configured in the WebUI,
independently from other hardware sources: create the destination under
**Destinations**, then edit it, open **Manage routes** and select the built-in
**HPE iLO Redfish** route. The
[hardware Redfish setup guide](guides/hardware-redfish-setup.md) shows the
complete flow.

The adapter preserves safe registry/message identifiers, the affected origin,
severity, category, and recommended action. It does not poll iLO or store iLO
administrator credentials. Live validation across iLO generations remains
pending; compare a test card with the Integrated Management Log before relying
on the integration operationally.

