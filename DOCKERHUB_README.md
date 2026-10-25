<p align="center">
  <img src="https://raw.githubusercontent.com/Theriark/nowlert-ce/main/docs/images/logo.png" width="210" alt="Nowlert logo">
</p>

<h1 align="center">Nowlert CE</h1>

<p align="center">
  <strong>Infrastructure reports. Nowlert delivers.</strong><br>
  Community Edition · free & open source · self-hosted
</p>

Nowlert CE receives infrastructure signals over **SMTP**, **HTTP**, and
**Redfish**, normalizes vendor-specific events, applies deterministic routing,
and delivers clear operational notifications to Discord, Microsoft Teams,
Slack, generic webhooks, MQTT, and ntfy.

The current stable release is **v3.1.6**. The versioned Docker Hub image is:

```text
theriark/nowlert-ce:3.1.6
```

The next version, v27.0.0, is in release-candidate testing (`v27.0.0-rc.N`
pre-release tags in the source repository). Release candidates are
not stable releases; use the `3.1.6` tag above for a stable deployment.
Development builds still report version 3.1.6 until v27.0.0 is released.

## v3.1.6 highlights

- Stage remains the final runtime acceptance gate for CE releases.
- Release chain remains Development → Stage → main → Release.
- Continuous Integration now owns the Development build, immutable-image
  verification, and Development deployment after a green `development` push.
- Finalize CE Release now owns stable GHCR/Docker Hub alias publication.
- The active workflow set is exactly Continuous Integration, Promote CE to
  Stage, and Finalize CE Release.
- The approved Development digest is promoted and published without rebuild.
- The published release retained the `platform_database_v1` configuration model.

v3.1.6 was a release-automation maintenance patch. These highlights describe
the published release, not newer development changes.

Current development uses database schema **18** with `platform_database_v1`.
Read the current configuration and migration guide before upgrading development
images; this does not claim that development changes have been published.

## Preview

The current WebUI of the v27.0.0 release-candidate line on a phone screen,
captured on 21 October 2026 from the Development deployment with synthetic
test data (part of the reviewed screenshot set of the `v27.0.0-rc.7`
documentation package):

| Sign in | Dashboard | Routing Flow |
|---|---|---|
| ![Nowlert sign-in page on a 390 px phone screen](https://raw.githubusercontent.com/Theriark/nowlert-ce/development/docs/images/v27.0.0-rc.1/sign-in-empty-signed-out-390.png) | ![Nowlert Dashboard on a 390 px phone screen with integration, destination and route counts](https://raw.githubusercontent.com/Theriark/nowlert-ce/development/docs/images/v27.0.0-rc.1/dashboard-live-admin-390.png) | ![Nowlert Routing Flow on a 390 px phone screen with delivery counters and integration cards](https://raw.githubusercontent.com/Theriark/nowlert-ce/development/docs/images/v27.0.0-rc.1/routing-flow-live-admin-390.png) |

The Preview shows only captures in which no account name, owner label,
destination or channel name of the Development test data is visible. The
repository's WebUI guide shows the desktop pages, and its documentation index
lists the older captures that are kept only as history.

## Quick start

```bash
git clone https://github.com/Theriark/nowlert-ce.git
cd nowlert-ce

cp .env.example .env
cp config/config.example.yaml config/config.yaml
mkdir -p logs/emails secrets state external-backups
chmod 600 .env config/config.yaml
chmod 700 logs logs/emails secrets state external-backups

docker compose -f compose.production.yaml config
docker compose -f compose.production.yaml pull
docker compose -f compose.production.yaml up -d
docker logs -f nowlert-ce
```

Set `NOWLERT_UID` and `NOWLERT_GID` in `.env` to the numeric identity that owns
the mounted directories.

On first start, the container prints a short-lived, single-use setup token.
Open the WebUI and choose the first administrator username/password. No default
password exists.

## Ports

- `8025/tcp` — SMTP input
- `8080/tcp` — WebUI + HTTP/Redfish service inside the container
- supplied Compose maps host port `18080` to container port `8080` by default

## Persistent mounts

| Container path | Purpose |
|---|---|
| `/nowlert/config` | bootstrap `config.yaml` and optional TLS material |
| `/nowlert/state` | SQLite state, owner-scoped secrets, private state backups |
| `/nowlert/logs` | application logs and optional retained event material |
| `/run/secrets` | externally managed read-only secrets |
| `/nowlert/external-backups` | bounded external backup target |

Back up `config`, `state`, and external `secrets` as one matched set before an
upgrade or rollback.

## Configuration model

`config.yaml` is intentionally small and controls process/bootstrap concerns:
listeners, transport security, state location, and WebUI publication.

Destinations, routes, Event API tokens, preferences, backup schedules,
integration behavior, aliases, users, notices, audit events, and delivery
history are database-authoritative in private platform state.

Do not add the legacy WebUI-managed `outputs`, `routing`, `api.tokens`,
`notifications`, `presentation`, `home_assistant`, `redfish`,
`platform.backups`, or `webui.language` sections to a fresh configuration,
whether for the v3.1.6 release or a current development build.

## Built-in integrations

Current development and the v27.0.0 release candidates include the same 22
integrations as the repository README:

Xen Orchestra, Zabbix, Grafana, Prometheus, Checkmk, Portainer, Semaphore,
Sonarr, Radarr, Metabase, GitHub Actions, Proxmox, QNAP, Synology, TrueNAS,
UniFi Network, UniFi Protect, UniFi Drive, Supermicro, HPE iLO, Dell iDRAC, and
Home Assistant.

The stable `3.1.6` image includes 15 of them. Prometheus, Checkmk, Semaphore,
Sonarr, Radarr, Metabase, and GitHub Actions were added after v3.1.6 and are
not in the `3.1.6` image.

Normalized inputs are SMTP, HTTP, and Redfish. The built-in catalogue defines
which input(s) and route criteria apply to each integration.

## Routing model

Nowlert evaluates enabled dedicated integration routes before wildcard fallback
routes. Fallback routes run only when no dedicated route matches, and duplicate
delivery to the same destination is suppressed.

The v3.1.6 route editor behavior is unchanged from v3.1.5: host/event patterns
plus included severities and statuses are supported, and unselected
severity/status values are implicitly excluded.

## Security

The production Compose definition uses:

- configurable non-root UID/GID;
- read-only root filesystem;
- dropped Linux capabilities;
- `no-new-privileges`;
- private persistent state; and
- bounded writable mounts/temp storage.

Use direct HTTP only on a trusted private network. For public/untrusted access,
terminate TLS at a trusted reverse proxy, set `webui.public_url`, enable WebUI
HTTPS enforcement, and enable secure cookies.

SMTP STARTTLS and SMTP AUTH are optional and disabled by default.

## Upgrade and rollback

Before upgrading:

1. back up `config`, `state`, and external `secrets` as one matched set;
2. record the currently running image/digest;
3. deploy the versioned v3.1.6 image;
4. verify `/api/health`, login, routes, destinations, history, and backups; and
5. keep the matched backup until acceptance passes.

Current development migrates supported older databases to schema 18. Take a
verified recovery snapshot before upgrading and retain the original image for rollback.

## Immutable release provenance

Theriark's CE release workflow builds the candidate inside Continuous
Integration on `development`, promotes the exact immutable digest to Stage,
advances `main` only to the Stage-approved source commit, publishes stable GHCR
and Docker Hub aliases from that approved digest, and creates the release tag on
that same source.

Stage is the final live runtime acceptance gate. The stable image is **not
rebuilt from the release tag**.

## Documentation

Repository: https://github.com/Theriark/nowlert-ce

Current documentation includes:

- deployment and immutable release flow;
- WebUI guide;
- integration/input catalogue;
- routing/delivery model;
- platform API/state model;
- data portability and private backups;
- integration-specific setup guides;
- practical end-to-end use-case guides; and
- release notes/QA checklists.

MIT License · Powered by Theriark
