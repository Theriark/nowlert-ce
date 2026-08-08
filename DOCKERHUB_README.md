<p align="center">
  <img src="https://raw.githubusercontent.com/Theriark/nowlert-ce/main/docs/images/logo.png" width="210" alt="Nowlert logo">
</p>

<h1 align="center">Nowlert</h1>

<p align="center">
  <strong>Infrastructure Notification Engine</strong><br>
  Built for homelabs · ready for enterprise
</p>

Nowlert receives infrastructure events over **SMTP**, **HTTP**, and
**Redfish**, normalizes them, applies database-backed routes, and sends rich
notifications to Discord, Microsoft Teams, Slack, generic webhooks, MQTT, and
ntfy.

The current stable release is **v3.1.0**. The corresponding image is **`theriark/nowlert-ce:3.1.0`**.

## Highlights

- Authenticated same-origin WebUI and `/api/v2`
- Database-authoritative destinations, routes, Event API tokens, settings, and aliases
- Built-in integration catalogue with standardized SMTP, HTTP, and Redfish inputs
- Dedicated-first routing with fallback-only wildcard routes
- Include/exclude filters and duplicate-delivery suppression
- Source-aware Discord and Microsoft Teams cards
- Packaged Discord icons and commit-pinned HTTPS Microsoft Teams icons
- 28 KiB Microsoft Teams payload guard with accurate HTTP 202 wording
- Local users, private/shared destinations, audit history, and delivery history
- Scheduled local, NFS, or SMB private-state backups
- Hardened production Compose deployment

## Preview

![Nowlert v3.1.0 Dashboard](https://raw.githubusercontent.com/Theriark/nowlert-ce/main/docs/images/v3.1.0-dashboard.png)

![Nowlert v3.1.0 Routing Flow](https://raw.githubusercontent.com/Theriark/nowlert-ce/main/docs/images/v3.1.0-routing-flow.png)

![Nowlert v3.1.0 Discord Xen Orchestra](https://raw.githubusercontent.com/Theriark/nowlert-ce/main/docs/images/v3.1.0-discord-xen-orchestra.png)

![Nowlert v3.1.0 Microsoft Teams Xen Orchestra](https://raw.githubusercontent.com/Theriark/nowlert-ce/main/docs/images/v3.1.0-teams-xen-orchestra.png)

## Quick start

```bash
git clone https://github.com/Theriark/nowlert-ce.git
cd nowlert-ce

cp .env.example .env
cp config/config.example.yaml config/config.yaml

mkdir -p logs/emails secrets state external-backups
mkdir -p config
chmod 600 .env config/config.yaml
chmod 700 logs logs/emails secrets state external-backups

docker compose -f compose.production.yaml config
docker compose -f compose.production.yaml up -d
docker logs -f nowlert-ce
```

Set `NOWLERT_UID` and `NOWLERT_GID` in `.env` to the numeric identity that
owns the mounted directories.

On first start, the container log prints a short-lived, single-use setup token.
Open the WebUI and choose the first administrator credentials. No default
password exists.

## Ports

- `8025/tcp` — SMTP input
- `8080/tcp` — WebUI and HTTP/Redfish input inside the container
- the supplied Compose file maps host port `18080` to container port `8080`

## Persistent mounts

| Container path | Purpose |
|---|---|
| `/nowlert/config` | Bootstrap `config.yaml` and optional TLS files |
| `/nowlert/state` | SQLite state, private database backups, and managed secrets |
| `/nowlert/logs` | Application and optional retained-email logs |
| `/run/secrets` | Read-only externally managed secrets |
| `/nowlert/external-backups` | Host-mounted external backup target |

Keep `config`, `state`, and `secrets` together when backing up or rolling back.

## Current configuration model

`config.yaml` contains only listener, bootstrap, and security settings.
Destinations, routes, Event API tokens, regional preferences, backup schedules,
integration behavior, aliases, users, notices, and history are managed from the
WebUI and stored in private platform state.

Do not add the legacy `outputs`, `routing`, `notifications`,
`presentation`, `home_assistant`, `redfish`, `api.tokens`,
`platform.backups`, or `webui.language` sections to a fresh v3.1
configuration.

The first successful v3.1 start can import a supported v2.4 YAML installation,
preserve IDs and credentials, and atomically normalize the mounted file.

## Built-in integrations

Xen Orchestra, Zabbix, Grafana, Portainer, Proxmox, QNAP, Synology, TrueNAS,
UniFi Network, UniFi Protect, UniFi Drive, Supermicro, HPE iLO, Dell iDRAC, and
Home Assistant.

Zabbix supports SMTP and HTTP. Hardware management integrations use Redfish.
The Sources page lists the complete catalogue even before an integration has
sent an event.

## Security

The production Compose file uses a non-root UID/GID, read-only root filesystem,
dropped capabilities, `no-new-privileges`, a PID limit, and private persistent
state.

Direct HTTP is appropriate only on a trusted private network. For public or
untrusted access, terminate TLS at a trusted reverse proxy, set a canonical
HTTPS `webui.public_url`, enable HTTPS enforcement, and enable secure cookies.

SMTP STARTTLS and SMTP AUTH are optional and disabled by default.

## Upgrade and rollback

Before upgrading:

1. Back up `config`, `state`, and `secrets` as one matched set.
2. Test the new image against a copy of production.
3. Deploy the versioned image, not only `latest`.
4. Verify schema, resource counts, token use, and real delivery.
5. Keep the backup until acceptance passes.

Rollback across a schema boundary requires restoring the matched pre-upgrade
backup before starting the older image.

## Documentation

Repository: https://github.com/Theriark/nowlert-ce

- deployment and Portainer guide
- WebUI guide
- integration and input catalogue
- routing and delivery model
- platform API and state model
- release notes and acceptance checklists
- v2.3.3 → v2.5.2 implementation sequence

![Nowlert v2.5.2 Discord card](https://raw.githubusercontent.com/Theriark/nowlert-ce/main/docs/images/v2.5.2-discord-zabbix.png)

MIT License · Powered by Theriark
