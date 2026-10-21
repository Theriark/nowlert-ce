# Integration setup guides

This index provides the stable `docs/integrations/` entry point referenced by
the Nowlert CE README and current documentation.

The product-specific setup notes currently remain in their existing top-level
`docs/` files; this index links to them without moving historical paths or
breaking inbound links. Integrations whose only documentation is an end-to-end
guide link to that guide.

## Hardware / Redfish

- [Redfish Event Service](../redfish.md)
- [Dell iDRAC](../dell-idrac.md)
- [HPE iLO](../hpe-ilo.md)
- [Supermicro](../supermicro.md)
- [Illustrated hardware setup and validation status](../guides/hardware-redfish-setup.md)

## Monitoring

- [Checkmk](../checkmk.md)
- [Grafana](../grafana.md)
- [Prometheus](../prometheus.md)
- [Zabbix](../guides/zabbix-webhook-to-discord.md) (SMTP and HTTP inputs;
  native webhook setup and delivery to Discord)

## Virtualization and containers

- [Xen Orchestra](../guides/xen-orchestra-to-discord.md) (SMTP input; see also
  [Xen Orchestra to Microsoft Teams](../guides/xen-orchestra-to-teams.md))
- [Proxmox](../proxmox.md)
- [Portainer](../portainer.md)

## Storage

- [QNAP](../qnap.md)
- [Synology](../synology.md)
- [TrueNAS](../truenas.md)

## Networking / UniFi

- [UniFi](../unifi.md)

## Automation

- [Home Assistant](../home-assistant.md)

## Email Alerts

Email Alerts connects Gmail and Microsoft 365 mailboxes and routes classified
messages through Nowlert; it is a mailbox connection, not an SMTP listener.

- [Gmail email alerts](../guides/gmail-email-alerts.md)
- [Microsoft 365 / Outlook email alerts](../guides/microsoft-email-alerts.md)
- [Shared email rules and delivery validation](../guides/gmail-microsoft-email-alerts.md)

## Application notifications

- [Semaphore](../semaphore.md)
- [Sonarr](../sonarr.md)
- [Radarr](../radarr.md)
- [Metabase](../metabase.md)
- [GitHub Actions](../github-actions.md)

[Illustrated application setup and validation status](../guides/infrastructure-tutorials.md)

## Destinations with their own setup notes

- [Nowlert Mobile](nowlert-mobile.md): connect the mobile app as a destination
  with a temporary connection code.

## Practical end-to-end use cases

For complete operator-facing flows that include destination and route setup, see
[the technical use-case guide index](../guides/README.md).

The built-in integration catalogue remains authoritative for which normalized
inputs are supported by each integration. See
[Integrations and inputs](../integrations-and-inputs.md).
