# Integrations and inputs

Nowlert distinguishes an **integration** from the **input** that receives an
event.

Integrations are packaged with the image, always available, and cannot be
disabled or removed as configuration records. Inputs are the three normalized
transport types: **SMTP**, **HTTP**, and **Redfish**.

| Integration | Source key | Inputs | Default category |
|---|---|---|---|
| Xen Orchestra | `xo` | SMTP | Virtualization |
| Zabbix | `zabbix` | SMTP, HTTP | Monitoring |
| Grafana | `grafana` | HTTP | Monitoring |
| Portainer | `portainer` | HTTP | Containers |
| Proxmox | `proxmox` | HTTP | Virtualization |
| QNAP | `qnap` | SMTP | Storage |
| Synology | `synology` | HTTP | Storage |
| TrueNAS | `truenas` | SMTP | Storage |
| UniFi Network | `unifi_network` | HTTP | Networking |
| UniFi Protect | `unifi_protect` | HTTP | Security |
| UniFi Drive | `unifi_drive` | HTTP | Storage |
| Supermicro | `supermicro` | Redfish | Hardware |
| HPE iLO | `hpe_ilo` | Redfish | Hardware |
| Dell iDRAC | `dell_idrac` | Redfish | Hardware |
| Home Assistant | `home_assistant` | HTTP | Automation |

The WebUI shows display names and never requires administrators to type parser
identifiers.

## Route choices

Route forms combine the integration and input:

```text
Zabbix (SMTP)
Zabbix (HTTP)
Dell iDRAC (Redfish)
Fallback (HTTP)
Fallback (Redfish)
```

A route persists both the source key and the input type. Existing Zabbix routes
from v2.3 are conservatively inferred as SMTP during migration.

## Fallback behavior

Since v2.5.1, wildcard routes are true fallbacks:

1. evaluate enabled dedicated integration routes
2. apply include/exclude filters
3. deliver dedicated matches
4. evaluate fallback routes only when no dedicated route matches
5. suppress repeated delivery to the same destination

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

Changing a category does not change parser identity or routing behavior.
