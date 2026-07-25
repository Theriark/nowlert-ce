<p align="center">
  <img src="docs/images/logo.png" width="220" alt="Notifinho logo">
</p>

<h1 align="center">Notifinho</h1>

<p align="center">
  <strong>Infrastructure Notification Engine</strong><br>
  Built for homelabs · ready for enterprise
</p>

<p align="center">
  <a href="https://github.com/FortPT/notifinho/releases">
    <img src="https://img.shields.io/badge/stable-v2.5.2-blue" alt="Stable release v2.5.2">
  </a>
  <img src="https://img.shields.io/badge/python-3.13-blue" alt="Python 3.13">
  <img src="https://img.shields.io/badge/docker-ready-2496ED?logo=docker&logoColor=white" alt="Docker ready">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT license">
</p>

Notifinho receives infrastructure events through **SMTP**, **HTTP**, and
**Redfish**, normalizes them, applies database-backed routes, and delivers rich
notifications to collaboration and automation platforms.

The current stable release is **v2.5.2**. The WebUI is the normal management
surface for destinations, routes, Event API tokens, regional preferences,
backup schedules, integration behavior, aliases, users, and operational
history. `config.yaml` is intentionally limited to listener, bootstrap, and
security settings.

| Property | Value |
|---|---|
| **Status** | Stable – Production Ready |
| **Current Stable Release** | **v2.5.2** |
| **Next Planned Release** | **v2.x** |
| **Python** | 3.13 |
| **License** | MIT |

## Current interface

| Overview | Routing Flow |
|---|---|
| ![Notifinho v2.5.2 Overview](docs/images/v2.5.2-overview.png) | ![Notifinho v2.5.2 Routing Flow](docs/images/v2.5.2-routing-flow.png) |

| Sources | Destinations |
|---|---|
| ![Built-in integrations and inputs](docs/images/v2.5.2-sources.png) | ![Database-backed destinations](docs/images/v2.5.2-destinations.png) |

| Inputs | Settings |
|---|---|
| ![SMTP, HTTP, and Redfish inputs](docs/images/v2.5.2-inputs.png) | ![Regional and integration settings](docs/images/v2.5.2-settings.png) |

## Notifications

| Discord | Microsoft Teams |
|---|---|
| ![Dell iDRAC notification in Discord](docs/images/v2.5.2-discord-idrac.png) | ![Notifinho notification in Microsoft Teams](docs/images/v2.5.2-teams.png) |

Notifinho uses source-aware presentation, severity colours, structured event
details, and packaged vendor assets. Discord-specific padded thumbnails keep
large vendor artwork readable without changing Microsoft Teams sizing.

## Core capabilities

- Authenticated same-origin WebUI and `/api/v2`.
- Local administrator and user accounts with protected browser sessions.
- Database-authoritative destinations, routes, Event API tokens, settings,
  aliases, notices, delivery history, and audit history.
- Write-only destination credentials stored outside SQLite in private files.
- Built-in integration catalogue with integration-level categories.
- Independent **SMTP**, **HTTP**, and **Redfish** input controls.
- Input-aware routing with include/exclude filters for hosts, events,
  severities, and statuses.
- Dedicated routes first; wildcard routes are fallback-only.
- Duplicate delivery suppression when several routes resolve to one destination.
- Discord, Microsoft Teams, Slack, generic webhook, MQTT, and ntfy outputs.
- Destination preview and explicit test delivery.
- Local, host-mounted, NFS, and SMB backup workflows.
- Credential-free export/import and guarded private-state restore.
- English/Portuguese interface, IANA timezone selection, and 12/24-hour time.
- Update checks and an administrator-only, reasoned, audited restart action.

## Built-in integrations

| Integration | Inputs | Default category |
|---|---|---|
| Xen Orchestra | SMTP | Virtualization |
| Zabbix | SMTP, HTTP | Monitoring |
| Grafana | HTTP | Monitoring |
| Portainer | HTTP | Containers |
| Proxmox | HTTP | Virtualization |
| QNAP | SMTP | Storage |
| Synology | HTTP | Storage |
| TrueNAS | SMTP | Storage |
| UniFi Network | HTTP | Networking |
| UniFi Protect | HTTP | Security |
| UniFi Drive | HTTP | Storage |
| Supermicro | Redfish | Hardware |
| HPE iLO | Redfish | Hardware |
| Dell iDRAC | Redfish | Hardware |
| Home Assistant | HTTP | Automation |

Custom events can use a fallback HTTP or Redfish route. Integrations are
packaged with the image and are not discovered, enabled, disabled, or removed
as configuration records. Inputs and routes determine whether events flow.

## Routing model

```text
Integration + Input
        │
        ▼
Dedicated enabled routes
        │
        ├── matching route(s) → enabled destination(s)
        │
        └── no dedicated match → fallback route(s)
```

A disabled source-side input, route, or destination is shown independently in
Routing Flow, making the failing boundary visible. Exclude filters override
include filters. Only one final delivery is produced for the same destination.

See [Routing](docs/platform-routing.md) and
[Integrations and inputs](docs/integrations-and-inputs.md).

## Quick start

Clone the repository, create the persistent directories, and use the hardened
production Compose definition:

```bash
git clone https://github.com/FortPT/notifinho.git
cd notifinho

cp .env.example .env
cp config/config.example.yaml config/config.yaml

mkdir -p logs/emails secrets state external-backups
mkdir -p config
chmod 600 .env config/config.yaml
chmod 700 logs logs/emails secrets state external-backups

# Set NOTIFINHO_UID and NOTIFINHO_GID in .env to:
id -u
id -g

docker compose -f compose.production.yaml config
docker compose -f compose.production.yaml up -d
docker logs -f notifinho
```

The default host ports are:

- `8025/tcp` — SMTP input
- `18080/tcp` — WebUI and HTTP/Redfish input, mapped to container port `8080`

On the first start, copy the short-lived setup token from the container log and
open the WebUI. Choose the first administrator username and password. There is
no default account or password.

For Portainer, use `compose.production.yaml`, replace relative volume paths
with absolute host paths, and keep the `config`, `state`, `secrets`, and `logs`
mounts persistent.

## Configuration authority

### `config.yaml`

The mounted file contains only process-level settings:

- SMTP listener, STARTTLS, and SMTP AUTH bootstrap
- HTTP listener and body limit
- API and platform activation
- persistent state directory
- browser cookie mode
- WebUI public URL and HTTPS enforcement

### Private platform state

SQLite and private secret files store WebUI-managed resources:

- destinations and credential references
- routes, inputs, priorities, and filters
- Event API token hashes and usage metadata
- users, sessions, notices, audit events, and delivery history
- language, timezone, clock format, and backup scheduling
- integration categories, behavior, aliases, and Redfish deduplication

Changing a listener, certificate, binding, or cookie mode requires a container
restart. Ordinary WebUI resource changes take effect through their independent
database stores.

See [Database-authoritative resources](docs/database-authoritative-resources.md)
and [Current configuration model](docs/current-configuration-model.md).

## Security

The production Compose definition runs as a configured non-root UID/GID with:

- a read-only root filesystem
- `cap_drop: ALL`
- `no-new-privileges:true`
- a bounded PID limit
- a private writable state mount
- a `tmpfs` for `/tmp`

Use direct HTTP only on a trusted private network. Public or untrusted access
must terminate TLS at a trusted reverse proxy and use:

```yaml
platform:
  secure_cookies: true

webui:
  public_url: "https://notifinho.example.com"
  enforce_https: true
```

Notifinho never returns stored webhook values, token values, password hashes,
secret paths, or secret digests through the normal read API.

## Backups and upgrades

Back up `config`, `state`, and `secrets` as one matched set before every upgrade.
A rollback across a schema boundary also requires restoring that matched set;
changing only the image is not sufficient.

Upgrading a v2.3/v2.4 installation to v2.5:

1. Create a matched backup.
2. Test a copy in an isolated container.
3. Deploy the v2.5.2 image.
4. Confirm schema 8 and resource counts.
5. Verify token authentication and real destination delivery.
6. Keep the backup until acceptance is complete.

The first successful v2.5 start imports supported YAML-managed resources and
atomically normalizes `config.yaml`.

## Documentation

- [Deployment and Portainer](docs/deployment.md)
- [WebUI](docs/webui.md)
- [Integrations and inputs](docs/integrations-and-inputs.md)
- [Routing and delivery](docs/platform-routing.md)
- [Platform API](docs/platform-api.md)
- [Platform state](docs/platform-state.md)
- [Database-authoritative resources](docs/database-authoritative-resources.md)
- [Current configuration model](docs/current-configuration-model.md)
- [Roadmap](docs/roadmap.md)
- [v2.5.2 release notes](docs/releases/v2.5.2.md)
- [v2.5.2 acceptance checklist](docs/v2.5.2-acceptance-checklist.md)
- [v2.3.3 to v2.5.2 sequence](docs/version-history-2.3.3-to-2.5.2.md)

## Project status

Notifinho v2.5.2 is stable and production-ready. New integrations, destination
adapters, compatibility validation, and operational improvements are tracked
as future v2.x work rather than mixed into the current configuration model.

## License

MIT License. See [LICENSE](LICENSE).

Powered by FortPT.
