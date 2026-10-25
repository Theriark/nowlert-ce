# Integrations and inputs

Nowlert distinguishes an **integration** from the **input** that receives an
event.

Integrations are packaged with the image and provide source detection, parsing,
presentation metadata, and supported route criteria. Inputs are the normalized
transport types: **SMTP**, **HTTP**, **Redfish**, and **Email Alerts** (messages
read from connected mailboxes, not an SMTP listener).

The table follows the built-in catalogue of current development and the v27.0.0
release candidates. The stable `3.1.6` image includes 15 of the 22 vendor
integrations and has no Email Alerts input: Prometheus, Checkmk, Semaphore,
Sonarr, Radarr, Metabase, and GitHub Actions were added after v3.1.6.

| Integration | Source key | Inputs | Default category |
|---|---|---|---|
| Xen Orchestra | `xo` | SMTP | Virtualization |
| Zabbix | `zabbix` | SMTP, HTTP | Monitoring |
| Grafana | `grafana` | HTTP | Monitoring |
| Prometheus | `prometheus` | HTTP | Monitoring |
| Checkmk | `checkmk` | HTTP | Monitoring |
| Portainer | `portainer` | HTTP | Containers |
| Semaphore | `semaphore` | SMTP, HTTP | Automation |
| Sonarr | `sonarr` | HTTP | Automation |
| Radarr | `radarr` | HTTP | Automation |
| Metabase | `metabase` | HTTP | Monitoring |
| GitHub Actions | `github_actions` | HTTP | Automation |
| Proxmox | `proxmox` | HTTP | Virtualization |
| QNAP | `qnap` | SMTP | Storage |
| Synology | `synology` | SMTP, HTTP | Storage |
| TrueNAS | `truenas` | SMTP | Storage |
| UniFi Network | `unifi_network` | HTTP | Networking |
| UniFi Protect | `unifi_protect` | HTTP | Security |
| UniFi Drive | `unifi_drive` | HTTP | Storage |
| Supermicro | `supermicro` | Redfish | Hardware |
| HPE iLO | `hpe_ilo` | Redfish | Hardware |
| Dell iDRAC | `dell_idrac` | Redfish | Hardware |
| Home Assistant | `home_assistant` | HTTP | Automation |
| Email Alerts | `email` | Email Alerts | Generic |

The WebUI uses display names; operators do not need to type parser identifiers.

## Route choices

Route forms combine integration and input, for example:

```text
Zabbix (SMTP)
Zabbix (HTTP)
Dell iDRAC (Redfish)
Email Alerts (Email Alerts)
Fallback (SMTP)
Fallback (HTTP)
Fallback (Redfish)
```

A route persists both source/integration identity and input type.

The route editor scopes severity/status choices to the selected
integration/input contract. This avoids showing irrelevant criteria and makes
the saved route representation match what the integration can emit.

## Fallback behavior

Wildcard routes are true fallbacks:

1. evaluate enabled dedicated integration routes;
2. apply their filters;
3. deliver dedicated matches;
4. evaluate fallback routes only if no dedicated route matched; and
5. suppress repeated delivery to the same destination.

## Route criteria

The current WebUI exposes:

- host include/exclude patterns;
- event include/exclude patterns;
- included severities; and
- included statuses.

Unselected severity/status values are implicitly excluded. The UI does not show
redundant excluded-severity or excluded-status controls.

Selecting the full list is preserved and displayed as configured on the Routes
page.

## Categories

Categories are presentation metadata stored in SQLite:

- Virtualization
- Monitoring
- Storage
- Networking
- Hardware
- Automation
- Containers
- Security
- Generic

Changing a category does not change parser identity, supported inputs, or route
matching.

See [platform-routing.md](platform-routing.md) for the full matching model and
[`integrations/`](integrations/) for product-specific setup notes.

Checkmk host/service notifications: HTTP `/checkmk/events`, application source scope `checkmk`; see [setup guide](checkmk.md).
