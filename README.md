<p align="center">
  <img src="assets/icons/nowlert.png" width="240" alt="Nowlert logo">
</p>

<h1 align="center">Nowlert</h1>

<p align="center">
  <strong>Infrastructure Notification Engine</strong>
</p>

<p align="center">
Built for Homelabs • Ready for Enterprise
</p>

<p align="center">

<a href="https://github.com/Theriark/nowlert/releases">
  <img src="https://img.shields.io/badge/stable-v3.0.0-blue" alt="Stable release v3.0.0">
</a>

<a href="https://www.python.org/">
  <img src="https://img.shields.io/badge/python-3.13-blue" alt="Python">
</a>

<img src="https://img.shields.io/badge/docker-ready-2496ED?logo=docker&logoColor=white" alt="Docker">

<img src="https://img.shields.io/badge/license-MIT-green" alt="License">

<img src="https://img.shields.io/badge/Xen%20Orchestra-supported-orange" alt="Xen Orchestra">

<img src="https://img.shields.io/badge/Zabbix-v1.2.0-D40000?logo=zabbix&logoColor=white" alt="Zabbix">

<img src="https://img.shields.io/badge/QNAP-v1.3.0-008C95" alt="QNAP v1.3.0">

<img src="https://img.shields.io/badge/Grafana-v1.3.0-F46800?logo=grafana&logoColor=white" alt="Grafana v1.3.0">

<img src="https://img.shields.io/badge/TrueNAS-v1.4.0-0095D5" alt="TrueNAS v1.4.0">

<img src="https://img.shields.io/badge/Discord-supported-5865F2?logo=discord&logoColor=white" alt="Discord">

<img src="https://img.shields.io/badge/Microsoft%20Teams-supported-6264A7?logo=microsoftteams&logoColor=white" alt="Microsoft Teams">

</p>

---

# 🚀 Project Status

| Property | Value |
|----------|-------|
| **Status** | 🚀 Stable – Production Ready |
| **Current Stable Release** | **v3.0.0** |
| **Next Planned Release** | **v3.x** |
| **License** | MIT |
| **Python** | 3.13 |

Nowlert 3.0.0 is the product, repository, deployment, and container identity
transition from Notifinho. Existing protocol contracts, environment aliases,
persistent state, internal paths, cookies, schemas, and rollback data remain
compatible.

See the [v3.0.0 release notes](docs/releases/v3.0.0.md) for the repository and
registry transition, compatibility boundaries, upgrade guidance, and rollback
procedure. The operator walkthrough is in the
[v3.0.0 acceptance checklist](docs/v3.0.0-acceptance-checklist.md).

Notifinho v2 adds a self-hosted notification platform with local accounts,
database-authoritative destinations, routes, application tokens, regional
preferences, backup schedules, integration behavior and aliases. Each resource
has its own transaction and error boundary, so one damaged destination, route,
or settings record does not prevent unrelated WebUI pages from loading.
`config.yaml` is now limited to process bootstrap, listener and security
settings. Existing v2.4 YAML resources are imported once into schema 8 and then
removed from the mounted file. First startup emits a short-lived, single-use
setup token so the operator can choose the first administrator credentials in
the browser without a default password or CLI bootstrap. Notifinho consumes
emitted SMTP or webhook notifications; it does not poll infrastructure APIs,
IMAP, Microsoft Graph, Gmail, or other
mailboxes. SMTP transport security remains disabled by default and can be
enabled with STARTTLS and SMTP AUTH; see the
[SMTP security guide](docs/smtp-security.md).

v2.2.0 adds a dismissible notice centre, lifecycle-bound error and update
notices, time-range delivery metrics, a complete routing-flow view, semantic
route ordering, application usage controls, profile pictures, operational
health checks, and scheduled state backups to a host-mounted NFS or SMB share.

v2.3.0 makes those operational workflows immediate and easier to read. It adds
first-login notice enrollment, source categories and real input transports,
animated route flow, channel-aware destination cards, semantic Delivery
History, live Audit Log updates, avatar cropping, an audited restart control,
and separate Inputs and Backups pages. Backup destinations can now be named
Local, NFS, or SMB targets with connectivity/write tests and manual or
scheduled execution; host-mounted shares remain the safest default.

v2.3.2 completes the follow-up production corrections: vendor source icons and
purpose-specific categories, safe removal of inactive sources, accurate
wildcard-route activity, destination-branded test events, a header restart
control, dual HTTP/HTTPS cookie migration, and a directly usable managed-mount
Compose profile including NFSv3 backup behavior in the read-only container.

v2.3.4 completes the final requested polish: Notifinho is slightly larger,
Dell iDRAC, UniFi Network, UniFi Protect, and QNAP are much larger, Synology is
larger, F5 reliably returns to the active page instead of Overview, inactive
source removal accepts the current browser request shape, and the 2.3.3
operations-menu, update-check, destination-test, and regional backup-clock
corrections remain in place.

---

# 📸 Preview

The screenshots below show the current **v2.5.2** WebUI and outbound
notification presentation. They replace the older v1.9.6 examples while
preserving the detailed project documentation that follows.

## Current WebUI

| Overview | Routing Flow |
|---|---|
| ![Notifinho v2.5.2 Overview](docs/images/v2.5.2-overview.png) | ![Notifinho v2.5.2 Routing Flow](docs/images/v2.5.2-routing-flow.png) |

| Sources | Destinations |
|---|---|
| ![Built-in integrations and inputs](docs/images/v2.5.2-sources.png) | ![Database-backed destinations](docs/images/v2.5.2-destinations.png) |

| Inputs | Settings |
|---|---|
| ![SMTP, HTTP, and Redfish inputs](docs/images/v2.5.2-inputs.png) | ![Regional and integration settings](docs/images/v2.5.2-settings.png) |

| Routes | Event API access |
|---|---|
| ![Input-aware routes](docs/images/v2.5.2-routes.png) | ![Scoped Event API tokens](docs/images/v2.5.2-api-access.png) |

## Current notifications

| Discord — Dell iDRAC | Discord — Zabbix |
|---|---|
| ![Dell iDRAC notification in Discord](docs/images/v2.5.2-discord-idrac.png) | ![Zabbix notification in Discord](docs/images/v2.5.2-discord-zabbix.png) |

| Microsoft Teams |
|---|
| ![Notifinho notification in Microsoft Teams](docs/images/v2.5.2-teams.png) |

Notifinho uses source-aware presentation, severity colours, structured event
details, and packaged vendor assets. Discord-specific padded thumbnails keep
large vendor artwork readable without changing Microsoft Teams sizing.

# What is Nowlert?

**Nowlert** is a parser-driven Infrastructure Notification Engine and
self-hosted notification platform. It receives infrastructure events through
**SMTP**, **HTTP**, and **Redfish**, converts vendor-specific payloads into one
shared notification model, applies deterministic database-backed routes, and
delivers rich notifications to collaboration and automation platforms.

Instead of forcing administrators to read long HTML emails or raw webhook
payloads, Nowlert produces concise, actionable notifications containing the
information needed to understand and respond to an event.

Nowlert works alongside existing infrastructure. SMTP-capable products can
send mail directly to its native listener, webhook-capable products can use
authenticated HTTP endpoints, and hardware controllers can submit Redfish Event
Service notifications. It does not poll mailboxes, infrastructure APIs,
Microsoft Graph, Gmail, or IMAP servers.

The modular architecture separates input adapters, source detection, parsers,
the shared notification model, routing, formatters, and outputs. A new source
can therefore be added without changing existing destinations, and a new
output can be introduced without rewriting vendor parsers.

Since v2.5.0, destinations, routes, Event API token hashes, regional settings,
backup scheduling, integration behaviour, aliases, notices, audit events, and
delivery history are authoritative in private SQLite platform state. The
mounted `config.yaml` is intentionally limited to process bootstrap, listener,
and transport-security settings.

# 🦉 Why the name?

**Nowlert** brings together the ideas of **now**, an observant **owl**, and an
actionable **alert**.

The name reflects the product's purpose: receive infrastructure events,
identify what matters, and deliver a clear notification while it is still
useful.

Immediate.

Readable.

Actionable.

---

## 📑 Contents

- [What is Nowlert?](#what-is-nowlert)
- [Why the name?](#-why-the-name)
- [Why Nowlert?](#why-nowlert)
- [Features](#-features)
- [Supported Integrations](#-supported-integrations)
- [Project Goals](#-project-goals)
- [Core Concepts](#-core-concepts)
- [Architecture](#-architecture)
- [Design Principles](#-design-principles)
- [Quick Start](#-quick-start)
- [Configuration](#-configuration)
- [SMTP Configuration](#-smtp-configuration)
- [Example Flow](#-example-flow)
- [Roadmap](#-roadmap)
- [Contributing](#-contributing)
- [License](#license)

# Why Nowlert?

Infrastructure products still report important events through a mixture of
HTML email, vendor-specific webhooks, and hardware event envelopes. Those
messages often contain valuable information, but the important fields are
buried in inconsistent layouts or raw payloads.

Nowlert normalizes those events and presents them in a clean, structured,
consistent format designed for modern collaboration and automation platforms.
It enhances existing monitoring, backup, storage, networking, virtualization,
and hardware-management products rather than replacing them.

## Traditional Email vs. Nowlert

| Traditional/raw event delivery | Nowlert |
|-------------------------------|------------|
| Long HTML emails or raw webhook payloads | Rich structured notification cards |
| Difficult to read on mobile | Mobile-friendly layouts |
| Important data buried in text or JSON | Critical information highlighted |
| Vendor-specific formatting | Consistent source-aware presentation |
| Separate SMTP, HTTP, and hardware flows | One normalized routing model |
| Limited visual feedback | Status colours, packaged icons, and structured sections |
| Destination credentials mixed into configuration | Write-only secrets stored outside SQLite |

---

# ✨ Features

## 📨 SMTP Gateway

- Native SMTP server
- Optional STARTTLS with TLS 1.2 or newer
- Optional SMTP AUTH LOGIN and PLAIN after TLS
- Environment-variable or mounted-secret credentials
- Automatic email reception
- Parser-based architecture
- Configurable routing
- Product detection based on email content
- Zero changes required to monitored software

---

## 🎨 Rich Notifications

- Source-aware Discord embeds
- Microsoft Teams Adaptive Cards
- Mobile-friendly layouts
- Severity colour coding
- Structured information blocks
- Consistent event, device, status, and source-time fields
- Packaged official vendor assets for Discord and public HTTPS source images
  for Microsoft Teams
- Destination-specific icon sizing where platform rendering differs
- 28 KiB Microsoft Teams payload guard and explicit HTTP 202 accepted status
- Preview and explicit test delivery before operational use

---

## 🖥️ WebUI and Platform Management

The v2.5.3 WebUI is the normal management surface for operational resources:

- Local administrator and user accounts
- Protected same-origin browser sessions and CSRF controls
- Administrator notices and lifecycle-bound update/error notices
- Built-in source catalogue with integration categories
- Independent SMTP, HTTP, and Redfish input controls
- Private and shared destinations with write-only credentials
- Input-aware routes, semantic priorities, include/exclude filters, and fallback
  routes
- One-time Event API token creation, rotation, revocation, expiry, and scoped
  source access
- Delivery History and Audit Log views
- Regional language, timezone, and 12/24-hour settings
- Integration behaviour and aliases
- Local, host-mounted, NFS, and SMB backup workflows
- Credential-free export/import and guarded private-state restore
- Administrator-only, reasoned, audited process restart

The backend exposes the same ownership-enforcing resources through the
authenticated `/api/v2` contract. Destination secrets and one-time token values
are never loaded back into normal read forms.

See the [WebUI guide](docs/webui.md),
[current configuration model](docs/current-configuration-model.md), and
[database-authoritative resource guide](docs/database-authoritative-resources.md).

---

## 🖥️ Hardware management and automation

The current backend includes:

- Standard Redfish Event Service envelopes with bounded batch handling and
  duplicate suppression
- Supermicro BMC/IPMI, HPE iLO, and Dell iDRAC vendor normalization
- Authenticated Home Assistant automation events
- Generic source-scoped event submission through the Event API
- Source-scoped application tokens with expiry, rotation, revocation, and rate
  limits
- Masked configuration, safe error boundaries, private audit records, delivery
  history, preview, and destination test delivery
- Environment-, file-, or SHA-256-backed bootstrap credentials where process
  configuration still requires them

Hardware and automation inputs are disabled or enabled independently from
routes and destinations. A disabled input, route, or destination is represented
as a separate boundary in Routing Flow.

See the [API](docs/api.md), [Redfish](docs/redfish.md),
[Home Assistant](docs/home-assistant.md),
[notification presentation contract](docs/presentation-contract.md), and
vendor integration guides.

---

## 💾 Xen Orchestra

Current implementation includes:

- Backup status
- Backup mode
- Start and finish times
- Duration
- Repository
- Transfer size
- Transfer speed
- Success, failure and skipped counters
- VM-level backup results
- VM transfer size
- VM transfer speed
- VM-specific failure reasons
- Optional Job ID and Run ID
- Compact operator-friendly layout

---

## 📊 Zabbix

The v1.2.0 implementation includes:

- Automatic Zabbix email detection
- Problem notifications
- Recovery notifications
- Host name
- Problem name
- Severity
- Event time
- Recovery duration
- Operational data
- Optional problem ID
- Severity-aware colors and icons
- Discord embeds
- Microsoft Teams Adaptive Cards
- Conditional host-based routing
- Secondary webhook destinations for selected hosts

---

## 💽 QNAP QTS / QuTS hero

The v1.3.0 integration, now validated with real QNAP Notification Center
delivery, includes:

- Case-insensitive QNAP Notification Center detection
- Notification Center test messages
- Failed login and security warnings
- Storage pool, volume, RAID, disk, and SMART warnings
- HBS and other backup failures
- Firmware and application update notices
- UPS and power events
- Plain-text, HTML, and multipart email parsing
- QNAP-specific Discord embeds and Microsoft Teams Adaptive Cards
- Synthetic fixtures and a local SMTP replay utility

Run the regression suite with:

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m pytest -q
```

The included fixtures remain anonymized and synthetic so no production data is
stored in the repository. Real QNAP delivery has confirmed the integration;
additional QTS, QuTS hero, localized, and customized templates remain normal
compatibility-hardening work. See the [QNAP integration guide](docs/qnap.md).

---

## 📈 Grafana Alerting

The provisional v1.3.0 integration includes:

- Strong, case-insensitive Grafana email detection
- Test, firing, resolved, pending, No Data, and evaluation-error events
- Grouped notification support with alert counts
- Rule, folder, dashboard, panel, datasource, labels, values, and event times
- Grafana-specific Discord embeds and Microsoft Teams Adaptive Cards
- Dedicated Grafana webhook routing
- Synthetic plain-text, HTML, and multipart fixtures

Grafana support was developed without production email samples. The fixtures
are synthetic and do not prove compatibility with every Grafana release or
custom alert template. See the [Grafana integration guide](docs/grafana.md)
for SMTP/contact-point concepts, replay commands, and known limitations.

---

## TrueNAS 26

The provisional `v1.4.0` integration includes:

- Strong detection using sender/header identity, the `TrueNAS @ hostname`
  marker, and the upstream alert list structure
- Test, new, cleared, current, and grouped alerts
- Storage, SMART, scrub, replication, backup, UPS/power, system, network,
  security, and application/service classification
- TrueNAS-specific Discord embeds and Microsoft Teams Adaptive Cards
- Dedicated TrueNAS targets and source routing
- Synthetic plain-text, HTML, and multipart fixtures

Compatibility remains provisional for broader real-world alert variants and
customized templates. Synthetic fixtures, private test-email/test-alert
replay, and a live Send Test Alert have been validated on VM-04. See the
[TrueNAS integration guide](docs/truenas.md).

---

## ⚡ Designed for Fast Decision Making

Every notification is designed around one principle:

> **Show the right information at the right time, in the clearest possible way.**

Rather than reproducing the original email, Notifinho extracts the relevant information, removes unnecessary noise and presents the result in a format optimized for fast decision making.

---

# 🔌 Supported Integrations

Notifinho separates an **integration** from the **input** that receives its
events. Integrations are packaged with the image; inputs and routes determine
whether their events flow.

## 📥 Built-in integrations and inputs

| Integration | Input(s) | Default category | Compatibility position |
|---|---|---|---|
| Xen Orchestra | SMTP | Virtualization | Stable |
| Zabbix | SMTP, HTTP | Monitoring | Stable |
| Grafana | HTTP | Monitoring | Built-in; template compatibility varies |
| Portainer | HTTP | Containers | Validated where Alerting webhooks are available |
| Proxmox VE | HTTP | Virtualization | Built-in; broader real-system validation remains useful |
| QNAP QTS / QuTS hero | SMTP | Storage | Real Notification Center delivery validated |
| Synology DSM | HTTP | Storage | Webhook flow validated |
| TrueNAS | SMTP | Storage | Real SMTP alert delivery validated |
| UniFi Network | HTTP | Networking | Native authenticated webhook input |
| UniFi Protect | HTTP | Security | Native authenticated webhook input |
| UniFi Drive | HTTP | Storage | Native authenticated webhook input |
| Supermicro BMC / IPMI | Redfish | Hardware | Redfish Event Service integration |
| HPE iLO | Redfish | Hardware | Redfish Event Service integration |
| Dell iDRAC | Redfish | Hardware | Redfish Event Service integration |
| Home Assistant | HTTP | Automation | Authenticated event contract |

The normalized input names shown in the WebUI are **SMTP**, **HTTP**, and
**Redfish**. Zabbix exposes more than one input; routes persist both the
integration and input type. Generic events can use fallback HTTP or Redfish
routes when no dedicated integration route matches.

## 📤 Destinations

| Platform | Availability |
|---|---|
| Discord | Stable |
| Microsoft Teams | Stable |
| Slack | Platform adapter; opt-in when configured |
| Generic outbound webhook | Platform adapter; opt-in when configured |
| MQTT | Platform adapter; opt-in when configured |
| ntfy | Platform adapter; opt-in when configured |

Destinations have an owner, display name, output type, enabled state, optional
shared visibility, non-secret settings, and a write-only credential reference.
Shared destinations remain protected: another user may route to one that an
administrator shared, but cannot reveal or rotate its secret.

See [Integrations and inputs](docs/integrations-and-inputs.md),
[platform outputs](docs/platform-outputs.md), and
[routing and delivery](docs/platform-routing.md).

---

# 🎯 Project Goals

Notifinho was created with a few simple goals in mind:

- Modernize infrastructure notifications.
- Preserve compatibility with existing SMTP-based products.
- Minimize configuration effort.
- Present important information that can be understood in seconds.
- Keep integrations modular and easy to extend.
- Support multiple notification platforms from a single notification model.

Rather than replacing existing monitoring or backup solutions, Notifinho complements them by improving how notifications are delivered.

---

# 🧩 Core Concepts

Notifinho is built around five simple concepts.

Understanding these concepts makes it easy to understand the entire project.

| Concept | Description |
|----------|-------------|
| **Parser** | Understands the email format of a specific product. |
| **Notification Model** | Converts parsed information into a common internal structure. |
| **Router** | Selects one or more output targets, including optional source and host filters. |
| **Output** | Selects the source-specific formatter and delivers its completed payload. |
| **Formatter** | Builds a destination payload without sending web requests. |

Because these components have defined boundaries, a new source can add its own
parser and source-specific formatters without changing existing integrations,
while a new destination can be added without modifying source parsers.

---

# 🏗️ Architecture

```text
Inputs
    |- SMTP listener / raw email capture
    |- authenticated HTTP integration endpoints
    |- authenticated Event API submission
    `- Redfish Event Service envelopes
            |
            v
Input adapter and source normalization
    |- email detection and source-specific parsers
    |- native JSON/webhook adapters
    |- Redfish vendor adapters
    `- generic HTTP and Redfish fallback normalization
            |
            v
Shared Notification model
            |
            v
Database-backed router
    |- integration + input selection
    |- enabled-state checks
    |- deterministic priority ordering
    |- include/exclude filters
    |- dedicated routes first
    `- fallback routes only when no dedicated route matches
            |
            v
Delivery service
    |- destination ownership and visibility checks
    |- internal secret resolution
    |- bounded retry policy
    |- duplicate-destination suppression
    `- safe delivery-history records
            |
            +-> source-aware formatter -> Discord
            +-> source-aware formatter -> Microsoft Teams
            +-> adapter -> Slack
            +-> adapter -> generic webhook
            +-> adapter -> MQTT
            `-> adapter -> ntfy

Control plane
    |- local users, sessions, password changes, and CSRF
    |- destinations, routes, Event API tokens, aliases, and settings
    |- preview, test delivery, audit, and delivery history
    |- export/import and matched private-state backup/restore
    `- responsive same-origin WebUI and authenticated /api/v2
```

Input adapters normalize vendor-specific email, webhook, automation, or
hardware payloads into the output-neutral shared `Notification` model. The
router reads authoritative SQLite resources, not legacy destination/routing
YAML, and resolves dedicated routes before fallback routes.

Formatters only build destination payloads. Outputs and adapters perform
delivery. This separation allows one normalized event to reach multiple
destinations without being parsed again while keeping transport credentials
outside parsers and formatters.

Each database-managed resource has its own transaction and API error boundary.
A damaged destination, route, or settings row is reported with its resource
identifier while unrelated pages and valid resources remain available.

See [platform state](docs/platform-state.md),
[routing and delivery](docs/platform-routing.md),
[platform outputs](docs/platform-outputs.md),
[platform API](docs/platform-api.md), and [WebUI](docs/webui.md).

---

# ⚡ Design Principles

Every design decision in Notifinho follows a few core principles.

### 📖 Readability First

Important information should be visible within seconds.

Operators should never need to read an entire HTML email to understand what happened.

---

### 🔌 Zero Changes to Existing Software

If a product can send SMTP email, it can work with Notifinho.

Existing infrastructure does not need to be modified.

---

### 🧩 Parser-Driven Architecture

Each supported product has its own dedicated parser.

Adding support for a new platform should not impact existing integrations.

---

### 🎨 Output Independence

Parsers know nothing about Discord or Microsoft Teams. Source-specific
formatters understand normalized notification data but do not select routes or
send web requests. Outputs do not parse vendor email; they select a formatter
and deliver its payload. This separation keeps every component focused on a
single responsibility.

---

### 🚀 Built to Grow

Notifinho was designed from the beginning to support additional infrastructure platforms and messaging services without requiring architectural changes.

The current implementation packages Xen Orchestra, Zabbix, Grafana, Portainer,
Proxmox VE, QNAP, Synology, TrueNAS, UniFi Network, UniFi Protect, UniFi Drive,
Supermicro, HPE iLO, Dell iDRAC, and Home Assistant integrations. SMTP, HTTP,
and Redfish inputs feed one routing model. Discord and Microsoft Teams are the
stable collaboration destinations, with Slack, generic webhook, MQTT, and ntfy
available through the platform output layer when configured.

Future v3.x work focuses on additional integrations, destination adapters,
compatibility validation, operational hardening, and carefully scoped platform
features without replacing the current database-authoritative model.

---

# 🚀 Quick Start

Deploying Nowlert takes only a few minutes. The procedure below uses the
versioned, hardened production Compose definition.

## Requirements

- Docker Engine 24 or newer
- Docker Compose v2
- An SMTP-, HTTP-, or Redfish-capable source
- At least one supported destination credential
- Optional trusted reverse proxy for HTTPS publication

## Docker images

The same release source is published to Docker Hub and GitHub Container
Registry:

```bash
docker pull theriark/nowlert:3.0.0
docker pull ghcr.io/theriark/nowlert:3.0.0
```

Use a versioned image for production. The `latest` tag follows the current
stable release but is not an immutable deployment reference.

## 1. Clone the repository

```bash
git clone https://github.com/Theriark/nowlert.git
cd nowlert
```

## 2. Prepare process configuration

```bash
cp .env.example .env
cp config/config.example.yaml config/config.yaml
```

`config.yaml` contains only listener, bootstrap, and transport-security
settings. Destinations, routes, Event API tokens, regional settings, backup
schedules, integration behaviour, aliases, users, notices, audit events, and
delivery history are managed through the WebUI and private platform state.

## 3. Create persistent directories

```bash
mkdir -p logs/emails secrets state external-backups
mkdir -p config
chmod 600 .env config/config.yaml
chmod 700 logs logs/emails secrets state external-backups
```

Keep `config`, `state`, and `secrets` together in backups. They form one matched
configuration set.

## 4. Set the deployment identity

Read the numeric identity of the account that owns the bind mounts:

```bash
id -u
id -g
```

Set those values as `NOWLERT_UID` and `NOWLERT_GID` in `.env`. Existing
`NOTIFINHO_UID` and `NOTIFINHO_GID` values remain accepted as compatibility
aliases. Adjust the published ports only when the defaults conflict with
another service.

## 5. Validate and start

```bash
docker compose -f compose.production.yaml config
docker compose -f compose.production.yaml pull
docker compose -f compose.production.yaml up -d
docker ps --filter name=nowlert
docker logs -f nowlert
```

Default host ports:

| Service | Host port | Container port |
|---|---:|---:|
| SMTP input | `8025/tcp` | `8025/tcp` |
| WebUI, HTTP, and Redfish | `18080/tcp` | `8080/tcp` |

On first start, copy the short-lived, single-use setup token from the container
log and open the WebUI. Choose the first administrator username and password.
Nowlert has no default account or default password.

## Portainer deployment

Use `compose.production.yaml` as the stack definition and replace relative bind
mounts with absolute production paths such as:

```text
/docker/nowlert/config
/docker/nowlert/logs
/docker/nowlert/secrets
/docker/nowlert/state
/docker/nowlert/external-backups
```

Use the `nowlert` container identity for new deployments. Existing
`NOTIFINHO_*` environment aliases and internal `/notifinho` mounts remain
supported for migration and rollback. Do not point production at a development
checkout or release-candidate image.

## HTTP and HTTPS

Direct HTTP is suitable only for a trusted private network. For reverse-proxy
publication, terminate TLS at the proxy and configure:

```yaml
platform:
  secure_cookies: true

webui:
  public_url: "https://notifinho.example.com"
  enforce_https: true
```

SMTP port `8025` is not HTTP and must not be placed behind an HTTP reverse
proxy. Review the [SMTP security guide](docs/smtp-security.md) before enabling
STARTTLS or SMTP AUTH.

See the [deployment guide](docs/deployment.md) and
[v2.5.2 release notes](docs/releases/v2.5.2.md) for upgrade, rollback, managed
backup-mount, and acceptance procedures.

---

# ⚙️ Configuration

Notifinho v2.5.2 uses a normalized process configuration plus private,
database-authoritative platform state.

```text
config/config.yaml          # listener/bootstrap/security settings
state/notifinho.db          # WebUI-managed resources and preferences
secrets/                    # destination credentials and private values
logs/                       # application logs and optional captured email
external-backups/           # optional host-mounted backup target
```

## Configuration authority

### Process-level `config.yaml`

The mounted YAML file contains only settings that must exist before the control
plane starts:

- SMTP listener host, port, STARTTLS, and SMTP AUTH bootstrap
- HTTP listener host, port, body limit, and optional shared secret
- API and platform activation
- platform state directory
- backup retention for process-level private backups
- browser secure-cookie mode
- WebUI activation, canonical public URL, and HTTPS enforcement

A current minimal example is:

```yaml
smtp:
  enabled: true
  host: 0.0.0.0
  port: 8025
  tls:
    enabled: false
    certfile: /notifinho/config/tls/cert.pem
    keyfile: /notifinho/config/tls/key.pem
  auth:
    enabled: false
    username: notifinho
    password_env: NOTIFINHO_SMTP_PASSWORD
    password_file: ""

http:
  enabled: true
  host: 0.0.0.0
  port: 8080
  max_body_bytes: 1048576
  shared_secret: ""

api:
  enabled: true

platform:
  enabled: true
  configuration_model: platform_database_v1
  state_dir: /notifinho/state
  backup_retention: 20
  secure_cookies: false

webui:
  enabled: true
  public_url: ""
  enforce_https: false
```

Listener, certificate, binding, and cookie-mode changes require a container
restart.

### Private platform state

SQLite stores independently managed resources:

- local users, password hashes, sessions, and notices
- Event API token hashes, scopes, expiry, rotation, revocation, and use metadata
- destinations, ownership, sharing, enabled state, and non-secret settings
- integration/input routes, priorities, filters, and fallback behaviour
- regional language, timezone, and clock format
- backup targets, scheduling, and retention preferences
- integration categories, behaviour, aliases, and deduplication settings
- audit events, delivery history, and safe retry records

Credential values remain in owner-only secret files referenced by SQLite.
Normal read APIs do not return stored webhook URLs, passwords, token values,
secret paths, or digests.

## Migration from v2.4

The first successful v2.5 start validates the legacy `unified_yaml_v1`
configuration, imports supported resources into schema 8, and only then
atomically normalizes the mounted file to
`platform.configuration_model: platform_database_v1`.

The migration is one-way. Before upgrading, back up `config`, `state`, and
`secrets` as a matched set. A rollback across the schema boundary requires
restoring that matched set; changing only the image is insufficient.

## Routing

Routes are created and edited in the WebUI. Each route selects:

- one integration and input combination;
- one visible destination;
- an enabled state and numeric priority;
- optional host, event, severity, and status include filters;
- optional host, event, severity, and status exclude filters.

Exclude filters always win. Dedicated integration routes are evaluated first.
Fallback routes run only when no dedicated integration route matches. When
multiple matching routes resolve to the same destination, Notifinho performs
one final delivery through the highest-priority route.

## Logging

Application logs are stored in:

```text
/notifinho/logs/notifinho.log
```

Incoming SMTP messages can optionally be stored under:

```text
/notifinho/logs/emails/
```

These files are for troubleshooting and must not contain long-lived secrets.
Public bug reports should use sanitized fixtures rather than production email,
webhook, token, or destination data.

See [Current configuration model](docs/current-configuration-model.md),
[Database-authoritative resources](docs/database-authoritative-resources.md),
[Platform state](docs/platform-state.md), and
[Routing and delivery](docs/platform-routing.md).

---

# 📬 SMTP Configuration

By default, Notifinho listens on:

| Setting | Value |
|----------|-------|
| Host | `0.0.0.0` |
| Port | `8025` |

Most infrastructure products only require four SMTP settings:

| Setting | Value |
|----------|-------|
| SMTP Server | Notifinho host |
| Port | 8025 |
| Authentication | Disabled |
| TLS | Disabled |

Notifinho identifies the notification type using the email content rather than the recipient address, allowing existing SMTP configurations to be reused without modification.

## Replaying synthetic QNAP mail in development

Production uses SMTP port `8025`. The development Docker Compose mapping
publishes the same container listener on host port `8026`, so fixtures can be
tested without a QNAP device:

```bash
python3 scripts/replay_email.py \
  tests/fixtures/qnap/storage_warning.eml \
  --host 127.0.0.1 \
  --port 8026
```

The host and port shown above are the replay utility defaults, so this shorter
form is equivalent:

```bash
python3 scripts/replay_email.py tests/fixtures/qnap/storage_warning.eml
```

The development SMTP listener does not require authentication. Watch the
Notifinho logs for QNAP detection, parsing, source-specific formatter
selection, and QNAP route matching and delivery. The fixtures are synthetic and do not
guarantee compatibility with every QTS or QuTS hero release. More detail is
available in the [QNAP integration guide](docs/qnap.md).

## Replaying synthetic Grafana mail in development

Reuse the same development SMTP listener and replay utility:

```bash
python3 scripts/replay_email.py \
  tests/fixtures/grafana/alert_firing.eml \
  --host 127.0.0.1 \
  --port 8026
```

Watch the logs for Grafana detection, the structured parse summary,
Grafana route matching, and the `GrafanaDiscordFormatter` selection. A dedicated Grafana route and destination can keep Grafana alerts separate
from the default collaboration destination. These synthetic messages do not guarantee
compatibility with every Grafana template; see [docs/grafana.md](docs/grafana.md).

## Replaying synthetic TrueNAS mail in development

Replay any synthetic TrueNAS fixture through the development listener:

```bash
python3 scripts/replay_email.py \
  tests/fixtures/truenas/grouped_alerts.eml \
  --host 127.0.0.1 \
  --port 8026
```

Watch the logs for TrueNAS detection, the `TRUENAS PARSED` summary,
TrueNAS route matching, and the TrueNAS Discord or Teams formatter selection. The
fixtures are synthetic approximations; see [docs/truenas.md](docs/truenas.md)
for all replay commands and real-sample limitations.

---

# 🔄 Example Flow

The following example shows a Xen Orchestra SMTP backup report using the
current v2.5.2 routing and delivery model:

```text
Xen Orchestra backup report email
              |
              v
SMTP input on port 8025
              |
              v
Source detection and Xen Orchestra parser
              |
              v
Shared Notification model
              |
              v
Dedicated Xen Orchestra (SMTP) routes
              |
              +-- include/exclude filters
              +-- enabled route and destination checks
              `-- deterministic priority ordering
              |
              v
Destination ownership and secret resolution
              |
              v
Xen Orchestra destination formatter
              |
              v
Discord / Microsoft Teams / configured output adapter
              |
              v
Safe Delivery History record
```

For HTTP and Redfish events, the corresponding input adapter replaces the SMTP
parser stage. When no dedicated integration route matches, the router may
evaluate enabled fallback HTTP or Redfish routes. A disabled input, route, or
destination stops the path at that boundary and is shown independently in the
WebUI Routing Flow.

The shared notification model remains output-neutral. A single normalized event
can therefore be delivered to more than one distinct destination without being
parsed again, while duplicate routes to the same destination are suppressed.

---

# 🗺️ Roadmap

The detailed historical milestones below are retained as part of the project
record. The authoritative current v2.x planning summary is maintained in
[docs/roadmap.md](docs/roadmap.md), with issue-level progress tracked in the
[Notifinho Roadmap](https://github.com/users/FortPT/projects/1).

Completed milestones remain documented here so operators and contributors can
understand how the current architecture evolved.

See also the [v2.3.3 to v2.5.2 implementation sequence](docs/version-history-2.3.3-to-2.5.2.md).

## ✅ v1.0.0

- Xen Orchestra parser
- Discord notifications
- SMTP gateway
- Docker deployment
- Parser-driven architecture
- Rich notification formatting
- Docker Hub release
- GitHub Container Registry

---

## ✅ v1.1.1

- Microsoft Teams output
- Microsoft Teams Adaptive Cards
- Multiple output routing
- GitHub Actions
- Automatic container image publishing

---

## ✅ v1.2.0

- Zabbix problem and recovery parser
- Zabbix Discord embed formatter
- Zabbix Microsoft Teams Adaptive Card formatter
- Severity-aware colors and icons
- Source-specific formatter selection
- Conditional host-based routing
- Secondary webhook destinations for selected hosts
- Zabbix routing configuration examples

---

## ✅ v1.3.0 — QNAP and Grafana

Notifinho v1.3.0 introduced provisional QNAP QTS, QuTS hero, and
Grafana Alerting support. See the
[v1.3.0 release notes](docs/releases/v1.3.0.md) for highlights, upgrade
guidance, validation results, and current compatibility limitations.

### Included in v1.3.0

- QNAP detection and parser
- QNAP Discord and Microsoft Teams formatters
- QNAP synthetic fixtures, tests, and documentation
- Grafana detection and parser
- Grafana Discord and Microsoft Teams formatters
- Grafana synthetic fixtures, tests, and documentation
- Dedicated QNAP and Grafana routing examples
- SMTP fixture replay tooling
- Automated GitHub Release creation for stable version tags
- Rerun-safe release updates and manual publication of an existing tag

### Release validation

- 123 automated tests passed.
- 49 Python files passed cache-free syntax validation.
- The GitHub Actions workflow passed `actionlint` and release invariant checks.
- Representative QNAP and Grafana fixtures were parsed, routed, and delivered.
- The production image passed startup, version, and SMTP smoke tests.

### Compatibility hardening

QNAP and Grafana support is intentionally provisional. Validation against
anonymized real QTS, QuTS hero, and Grafana `.eml` samples remains valuable
compatibility-hardening work, but is not a hard blocker for the provisional
v1.3.0 feature set.


---

## ✅ v1.4.0 — TrueNAS

Notifinho v1.4.0 introduced provisional TrueNAS 26 support. See the
[v1.4.0 release notes](docs/releases/v1.4.0.md) for highlights, upgrade
guidance, validation results, and current compatibility limitations.

- Provisional TrueNAS 26 detection and parser
- Pool, disk/SMART, scrub, replication, backup, UPS, system, network,
  security, and application/service classification
- New, cleared, current, test, and grouped alert handling
- Discord and Microsoft Teams cards
- Synthetic fixtures, tests, routing examples, and documentation
- Real TrueNAS 26 test email, test alert, and live Send Test Alert validated on VM-04

---

## ✅ v1.5.0 — Native UniFi support

Notifinho v1.5.0 introduced native UniFi support. See the
[v1.5.0 release notes](docs/releases/v1.5.0.md) for upgrade, rollback,
validation, and compatibility details.

The release includes:

- Native HTTP input for UniFi Network and Protect Alarm Manager webhooks
- Strong-envelope Network client, gateway, switch, access point, connectivity,
  and device-health normalization
- Protect motion, person, vehicle, doorbell, trigger-device, and event-link
  normalization
- Delivered-email parsing for UniFi Drive backup, storage, disk-health, and
  administrative events
- Dedicated Discord and Microsoft Teams formatting
- Independent routing with shared or separate output targets
- Sanitized RFC822 analysis and temporary, opt-in HTTP webhook capture
- Synthetic parsing, listener, authentication, formatting, routing, replay,
  malformed-input, and regression tests
- A documented private-sample review workflow tracked in issue #32

The listener remains disabled until configured. UniFi Drive does not poll a
mailbox; mail must be forwarded or delivered to Notifinho's existing SMTP
input. See [docs/unifi.md](docs/unifi.md) for configuration and security.

---

## ✅ v1.6.0 — SMTP transport security

Notifinho v1.6.0 introduced SMTP transport security. See the
[v1.6.0 release notes](docs/releases/v1.6.0.md) for configuration, upgrade,
rollback, validation, and compatibility details.

The release includes:

- Optional explicit STARTTLS for the SMTP listener
- TLS 1.2 minimum
- SMTP AUTH LOGIN and PLAIN after TLS
- Environment-variable and Docker-secret password sources
- Timing-safe credential comparisons
- Fail-closed configuration validation
- Secure enablement defaults
- Secret-safe logging
- Backward-compatible disabled state
- Focused protocol and regression coverage

---

## ✅ v1.7.0 — Native UniFi Drive webhooks

Notifinho v1.7.0 introduced native UniFi Drive webhooks. See the
[v1.7.0 release notes](docs/releases/v1.7.0.md) for configuration, upgrade,
rollback, validation, and compatibility details.

- Native authenticated `POST /unifi/drive` webhooks
- Shared token authentication with Network and Protect
- Readable titles derived from descriptive Drive alarm names
- Full rule names preserved as `Alarm rule`
- Dedicated Discord and Microsoft Teams presentation
- Existing Drive delivered-email parsing preserved
- Real HTTPS and Discord end-to-end validation

---

## ✅ v1.8.0 — Virtualization, containers, and storage

Notifinho v1.8.0 introduced the v1.8 source integrations. See the
[v1.8.0 release notes](docs/releases/v1.8.0.md) for upgrade, rollback,
validation, and compatibility details. It expands the server-side notification
engine while preserving the current YAML configuration and
Discord/Microsoft Teams delivery model.

- Proxmox VE SMTP and native notification-webhook ingestion
- Backup, replication, node, cluster, storage, and availability events
- Portainer Alerting email and webhook ingestion where supported by the
  deployed Portainer edition, with an explicit compatibility matrix
- Synology DSM email and webhook ingestion
- Source-specific Discord embeds and Microsoft Teams Adaptive Cards
- Safe fixtures, replay tooling, routing examples, integration documentation,
  and real-system validation where representative systems were available
- Grafana compatibility hardening when anonymized real samples are available

Portainer support will consume notifications that Portainer emits; it will not
poll the Portainer API or require permanent administrative credentials.
The private-safe validation workflow is documented in the
[Portainer discovery guide](docs/portainer-discovery.md).
Production ingestion and routing are documented in the
[Portainer integration guide](docs/portainer.md).
The fixture-validated Proxmox candidate and its deferred real-system checklist
are documented in the [Proxmox integration guide](docs/proxmox.md).
The fixture-validated Synology DSM candidate and its deferred real-system
checklist are documented in the
[Synology integration guide](docs/synology.md).

---

## ✅ v1.8.1 — Consistent Discord and Teams presentation

Notifinho v1.8.1 is the presentation and safety patch that preceded v1.9.0.
See the [v1.8.1 release notes](docs/releases/v1.8.1.md) for upgrade, rollback,
validation, and compatibility details.

- Canonical `DD Mon YYYY • HH:MM` timestamps across formatters
- Source badges on Discord and Microsoft Teams cards
- Preserved source/status field icons and existing routing behavior
- TrueNAS wrapped-list extraction and active-alert deduplication
- Final recursive credential redaction on every outbound card
- Cross-source regression coverage for all formatter pairs

---

## ✅ v1.9.0 — Event platform and hardware management

Notifinho v1.9.0 completes the tested backend foundation required by the
user-facing v2.0 release. See the
[v1.9.0 release notes](docs/releases/v1.9.0.md).

- Shared Redfish Event Service listener and normalized hardware event model
- Supermicro BMC/IPMI adapter, including Redfish events and SMTP compatibility
- HPE iLO adapter for Redfish events and AlertMail compatibility
- Dell iDRAC adapter for Redfish events and email-alert compatibility
- Home Assistant event ingestion through authenticated HTTP requests generated
  by automations and `rest_command`
- Generic authenticated event-submission API with source-scoped tokens
- Formal configuration schema and validation API
- Atomic configuration updates, backups, health, logs, preview, and test-send
  API foundations
- API-token authentication, password-hashing helpers, secret masking, rate
  limits, private audit logs, and secure configuration-storage foundations
- Backwards-compatible migration checks for existing YAML configuration

The three server-management products share a Redfish foundation but retain
vendor adapters for their registry identifiers, severities, links, and useful
operator actions.

Hardware compatibility is fixture-validated and remains a synthetic candidate
until representative Supermicro, HPE, and Dell systems complete live delivery
tests. Full browser sessions, user-owned routes/destinations, CSRF protection,
and the responsive WebUI remain explicitly scoped to v2.0.

---

## ✅ v1.9.1 — Generic API and Home Assistant presentation patch

Notifinho v1.9.1 corrects two presentation regressions without changing the
v1.9 configuration schema or endpoint contracts. See the
[v1.9.1 release notes](docs/releases/v1.9.1.md).

- Dedicated generic Discord and Microsoft Teams event formatters replace the
  Xen Orchestra fallback for unknown and authenticated API sources
- Xen Orchestra remains explicitly mapped to its existing formatters
- Home Assistant cards derive concise Event, Service, Device, Entity,
  Endpoint, and Retry information from raw system-log events
- Python paths and verbose internal objects are omitted from cards
- Existing explicit Home Assistant automation fields remain authoritative
- Generic Home Assistant transport examples keep reusable presentation inside
  Notifinho and deployment-specific exclusions in Home Assistant

---

## ✅ v1.9.2 — Home Assistant device aliases and integration errors

Notifinho v1.9.2 improves generic Home Assistant integration errors without
changing the existing event contract. See the
[v1.9.2 release notes](docs/releases/v1.9.2.md).

- Optional endpoint and component aliases keep site-local equipment names in
  Notifinho configuration instead of Home Assistant automations
- Bare IPv4 addresses are extracted into the dedicated Endpoint field
- Tapo/Kasa and Internet Printing Protocol events receive concise summaries
  and canonical service labels
- Structured error codes appear separately in Discord and Microsoft Teams
- Service names are no longer repeated as devices when no real device is known
- Existing Home Assistant payloads and explicit automation fields remain
  compatible

---

## ✅ v1.9.3 — Redfish host identity and deduplication

Notifinho v1.9.3 makes multi-server Redfish cards unambiguous without changing
the endpoint or configuration schema. See the
[v1.9.3 release notes](docs/releases/v1.9.3.md).

- Subscription Context is shown as Host in Discord and Microsoft Teams cards
- Duplicate suppression is scoped by source, host, and Redfish origin
- Empty `MessageArgs` arrays no longer produce bogus recommended actions
- Existing Redfish destinations, routes, tokens, and payloads remain compatible

---

## ✅ v1.9.4 — Shared Teams presentation and source time

Notifinho v1.9.4 gives every Microsoft Teams integration the same information
hierarchy and makes source timestamps deterministic for worldwide deployments.
See the [v1.9.4 release notes](docs/releases/v1.9.4.md).

- Headers show `device • event` with status color and integration image
- Context, message, Severity/Category/Event time metrics, and icon-labelled
  details follow one shared layout
- Source wall-clock timestamps render as `20 Jul 2026 • 18:09`
- Available source times are never replaced with Notifinho receipt time
- Teams and Discord omit visible UTC or offset suffixes
- Existing configuration, routing, endpoints, and secrets remain compatible

---

## ✅ v1.9.6 — Official Teams and Discord presentation

Notifinho v1.9.6 replaces generated initial badges with official vendor assets
for every Teams and Discord integration and closes issues found during the
live v1.9.4 office audit. See the
[v1.9.6 release notes](docs/releases/v1.9.6.md).

- Every Teams and Discord formatter is bound to an exact, official asset
- Discord uses the same device/event, context, metric, and status contract
  while retaining richer source-specific fields
- Asset sources and mechanical transformations are documented
- Xen Orchestra preserves backup names and omits missing Duration/Result facts
- Identifiers such as `PVE-01`, `CPU`, and `VMID` retain their source casing
- UniFi cards remove duplicated state/icons and shorten the last-device label
- Teams and Discord use the Notifinho machine's local clock by default, with
  no visible timezone suffix and no receipt-time substitution
- Trusted Dell session login/logout audit noise can be suppressed by exact
  source IP across REDFISH and IPMI transports
- Placeholder, malformed, and non-HTTPS Teams webhooks fail before delivery
- Existing valid webhooks, routes, endpoints, and secrets remain compatible

---

## ✅ v1.9.7 — Permanent official icon delivery

Notifinho v1.9.7 is a focused packaging and delivery correction. Official
Docker images pin the vendor asset base to their own immutable release commit,
and Discord Components V2 uploads the matching packaged PNG. No layout,
routing, parser, timestamp, configuration, or secret contract changes.

---

## ✅ v2.0.0 — User-facing notification platform

v2.0.0 turns the completed notification engine into a self-service platform
without duplicating parser, formatter, or routing logic in the browser.
Release acceptance, the GitHub Release, and matching Docker Hub and GHCR image
publication completed on 22 July 2026. Roadmap issues #15, #16, #22, and
#49 through #53 are closed as completed. See the
[v2.0.0 release notes](docs/releases/v2.0.0.md) for the acceptance evidence,
upgrade, and rollback guidance.

- Migration-aware SQLite state, local account/lockout services, hashed session
  and CSRF credentials, ownership records, and owner-only secret rotation
- Source-scoped platform token rotation/revocation, private/shared destination
  policy, filterable user routes, bounded retries, audit, and safe history
- Ownership-safe previews and adapters for Discord, Teams, Slack, generic
  webhooks, MQTT, and ntfy, with strict outbound and secret boundaries
- Authenticated `/api/v2` sessions, CSRF, owned-resource management, previews,
  safe history/audit reads, and source-scoped platform event submission
- Responsive same-origin WebUI for the authenticated platform API, including
  accounts, destinations, routes, application tokens, preview/test delivery,
  delivery history, and audit events
- Local administrator and user accounts with clear roles
- User- and application-scoped event endpoints and API tokens
- Private and shared destinations with secrets never returned to the browser
- User-owned routing rules for source, host, event, and severity filters
- Visual route editor, configuration validation, import/export, backup, and
  restore with preview fingerprints and credential-free portable documents
- Preview and test delivery using the real backend formatters
- Searchable delivery history, safe error details, and audit events
- Slack output
- Generic outbound webhook output with customizable headers and JSON templates
- MQTT output for automation and Home Assistant workflows
- ntfy output for a lightweight self-hosted mobile/desktop destination
- Previewed import of supported v1.x Discord/Teams YAML routes and targets
- Production examples for Docker Compose, Portainer stacks, persistent data,
  and Nginx Proxy Manager TLS termination

Telegram and additional destination adapters remain candidates for the v2.x
series after the core v2.0 transports and self-service security model are
stable.

---

## ✅ v2.3.2 — Source identity and managed-mount corrections

v2.3.2 completes the production findings from v2.3.1. Overview and Sources use
the packaged official vendor icons, unknown sources use the Notifinho icon, and
purpose-specific categories replace the old broad visual tags. Enabled All
Sources routes now mark discovered sources Active. Administrators may remove an
inactive source only after confirmation; active exact or wildcard routing
blocks removal and historical deliveries are retained.

Destination-card tests now use the selected destination name and generic
Notifinho identity instead of Home Assistant branding. The audited Restart
action moves from Settings to the top-right header. Session lookup prefers the
cookie matching the configured HTTP/HTTPS mode, preventing an old Secure cookie
from overriding a new dual-access login.

The managed-backup Compose override now includes the exact root capability set
required for existing UID-owned configuration, log, and state mounts.
Application-managed NFS backups use `nolock`, avoiding `rpc.statd` runtime
files inside the read-only container while preserving the backup archive
workflow. See the [v2.3.2 release notes](docs/releases/v2.3.2.md) and
[acceptance checklist](docs/v2.3.2-acceptance-checklist.md).

---

## ✅ v2.3.1 — WebUI corrective release

v2.3.1 closes the post-v2.3.0 WebUI findings: trusted-LAN HTTP login, a profile
dropdown, immediate notices without F5, editable source tags, accurate input
labels, active-resource counts, semantic route animation, blue informational
deliveries, bottom Audit pagination, automatic managed-mount selection, global
12/24-hour backup presentation, and resilient avatar decoding/cropping.

The SQLite schema remains 6. Existing v2.3.0 state and configuration can be
used directly. Remote NFS/SMB auto-mounting still requires the dedicated
managed-backup Compose override because Linux mount capability cannot be added
from inside a running unprivileged container. See the
[v2.3.1 release notes](docs/releases/v2.3.1.md) and
[acceptance checklist](docs/v2.3.1-acceptance-checklist.md).

---

## ✅ v2.3.0 — WebUI operations and managed backup destinations

v2.3.0 completes the requested day-to-day WebUI polish and makes each action
refresh its own component without an F5. The login and header are simpler,
Overview uses categorized sources and real HTTP/SMTP transports, routing flow
is animated with a reduced-motion fallback, destinations expose channel-aware
one-click tests, and Delivery History presents semantic event details and
severity. Users gain the requested read-only operational views; administrators
gain notice lifecycle controls, live Audit pagination, an avatar cropper, and
an audited restart action.

Inputs and Backups are now separate. Backup jobs select named Local, NFS, or
SMB destinations, can test connectivity and write access, and can run manually
or on schedule. Host-mounted remote shares remain the recommended hardened
deployment. An explicit managed-mount override is documented for operators who
accept the additional container privilege and credential boundary. See the
[v2.3.0 release notes](docs/releases/v2.3.0.md) and
[acceptance checklist](docs/v2.3.0-acceptance-checklist.md).

---

## ✅ v2.2.0 — Operational WebUI and scheduled backups

v2.2.0 turns the WebUI into the day-to-day operational surface: administrators
can publish notices, every user can dismiss ordinary notices independently,
and unresolved configuration, routing, backup, or update conditions remain
visible until repaired. Overview metrics have 10-minute through one-year
history ranges, routing flow includes active, disabled, and unhealthy routes,
and Applications, Users, Delivery history, Audit, and Inputs expose direct,
safe controls. Private state backups can run daily, weekly, or monthly and copy
to a host-mounted NFS/SMB directory. See the
[v2.2.0 release notes](docs/releases/v2.2.0.md).

---

## ✅ v2.1.0 — Unified mounted configuration

v2.1.0 replaces the temporary takeover/fallback model with one durable
`config.yaml`. The Overview shows every active signal path, the WebUI provides
administrator CRUD with user read-only visibility, YAML application-token
metadata appears safely, test deliveries report their real outcome, and global
language/timezone/12-or-24-hour preferences apply across the interface and
notification presentation. Existing v2.0.2 imported rows are matched rather
than duplicated during the automatic conversion. See the
[v2.1.0 release notes](docs/releases/v2.1.0.md).

---

## ✅ v2.0.2 — Mounted configuration bridge

v2.0.2 makes existing production configuration visible and safely manageable
from the WebUI. The authenticated administrator sees YAML-managed inputs,
Discord/Teams destinations, routes, credential state, and the active routing
authority without exposing credential values. A previewed takeover creates an
automatic platform-state backup and an atomic `config.yaml` backup, imports
credentials directly inside the server, activates database-managed routing for
legacy SMTP and webhook events, and retains the original YAML routes as an
immediate fallback. Fingerprints, explicit confirmation, collision rejection,
single-authority routing, and interrupted-migration rollback prevent stale or
duplicate activation. See the
[v2.0.2 release notes](docs/releases/v2.0.2.md).

---

## ✅ v2.0.1 — Default WebUI and secure first-run setup

v2.0.1 makes the authenticated platform and same-origin WebUI available by
default on fresh installations and compatible upgrades. First startup creates
a short-lived, single-use setup token and prints it only to container output;
the operator uses that token over HTTPS to choose the first administrator
username and password. There is no shared default password and no
first-visitor-wins registration. Explicit `enabled: false` settings remain
authoritative, existing accounts skip setup, and the original YAML
notification pipeline remains compatible. See the
[v2.0.1 release notes](docs/releases/v2.0.1.md) for deployment, security,
upgrade, acceptance, and schema-aware rollback guidance.

---

The Community edition will continue to provide the complete notification
engine, parsers, formatters, configuration management, user routing, preview,
and test-delivery features for a self-hosted instance.

Advanced commercial functionality may be developed separately without
duplicating or replacing the open-source notification engine.

---

# 🤝 Contributing

Contributions are welcome.

Whether you're fixing a typo, adding a parser or implementing a new output platform, every contribution helps improve the project.

If you'd like to contribute:

1. Fork the repository.
2. Create a feature branch.
3. Commit your changes.
4. Open a Pull Request.

Please keep pull requests focused and include a clear description of the changes.

---

# 📄 License

Nowlert is released under the MIT License.

See the [LICENSE](LICENSE) file for details.

---

# ❤️ Acknowledgements

Special thanks to the open-source community and the projects that inspired Nowlert.

In particular:

- Xen Orchestra
- Discord
- Docker
- Python
- BeautifulSoup
- aiosmtpd

---

──────────────────────────────────────────────

# ⚡ Powered by FortPT

Copyright © 2026 FortPT
