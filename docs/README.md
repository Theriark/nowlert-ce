# Nowlert CE documentation

This directory contains current operator/developer guidance plus historical
release records.

## Current documentation

Use these guides for the current v3.1.6 release line and for the development
build that follows it. v3.1.6 is the last stable release. The development
build is the v27.0.0 release-candidate line (`v27.0.0-rc.N` pre-release tags,
not a stable release); it still reports application version 3.1.6 and already
differs from the v3.1.6 release (database schema 18, Email Alerts, Nowlert
Mobile, multi-factor authentication and more).
[Development after v3.1.6](releases/post-v3.1.6-development.md) lists those
differences.

| Guide | Purpose |
|---|---|
| [Current configuration model](current-configuration-model.md) | What belongs in `config.yaml` versus database-authoritative platform state |
| [Deployment](deployment.md) | Docker/Compose operation, immutable promotion flow, upgrade and rollback |
| [WebUI](webui.md) | Current pages, permissions, route assignment, Email Alerts, history, security, users and backups |
| [Integrations and inputs](integrations-and-inputs.md) | Built-in integration catalogue and SMTP/HTTP/Redfish/Email Alerts input model |
| [Integration setup index](integrations/README.md) | Stable index for product-specific setup notes, including Email Alerts and Nowlert Mobile |
| [Nowlert Mobile](integrations/nowlert-mobile.md) | Connecting the mobile app as a destination |
| [Technical use-case guides](guides/README.md) | Practical end-to-end SMTP/HTTP/Redfish/Email Alerts flows to real destinations |
| [Platform routing](platform-routing.md) | Tokens, destinations, routes, fallback behavior, delivery and audit rules |
| [Platform outputs](platform-outputs.md) | Destination adapters and safe output contracts |
| [Platform API](platform-api.md) | `/api/v2` authentication, endpoints, CSRF and event ingestion |
| [Platform state](platform-state.md) | SQLite schema, local accounts, secrets, backup layout and recovery |
| [Data portability](data-portability.md) | Credential-free export/import, private backups, restore and deletion |
| [SMTP security](smtp-security.md) | STARTTLS, SMTP AUTH and trusted-network boundaries |
| [Security hardening](security-hardening.md) | Dependency, container, error-message and exact-candidate scan controls |
| [Presentation contract](presentation-contract.md) | Normalized notification presentation rules |
| [Roadmap](roadmap.md) | Shipped milestones and current maintenance priorities |

## Integration guides

Integration-specific setup is indexed under [`integrations/`](integrations/).
The existing product-specific guide files remain at their established top-level
`docs/` paths so historical and inbound links continue to work.

The built-in catalogue is authoritative for which normalized inputs are
available to each integration. A guide may contain product-specific endpoint or
payload examples, but routing always uses the shared integration + input model.

## Practical use-case guides

The [`guides/`](guides/) collection contains current end-to-end operator flows,
including Xen Orchestra to Discord/Teams, direct homelab SMTP ingestion, Dell
iDRAC/Redfish routing, Zabbix, Grafana, Prometheus, Checkmk, UniFi, Portainer,
Home Assistant, TrueNAS, native application notifications and Gmail/Microsoft
365 Email Alerts.

## Release documentation

Current release material:

- [v3.1.6 release notes](releases/v3.1.6.md)
- [v3.1.6 QA checklist](releases/validation/v3.1.6-qa-checklist.md)
- [Development after v3.1.6](releases/post-v3.1.6-development.md): what the
  `development` branch adds beyond v3.1.6 as the v27.0.0 release-candidate
  line; no stable v27.0.0 release exists yet.

Historical notes under `releases/` and historical acceptance/QA checklists are
version snapshots. They are intentionally preserved even when a newer release
changes current documentation.

Release checklists are grouped in the [validation archive](releases/validation/README.md)
to keep the operator documentation easy to browse. They record release QA;
they do not enable integrations or change runtime behavior.

## Screenshots

Current captures of the development WebUI live under
[`images/v27.0.0-rc.1/`](images/v27.0.0-rc.1/README.md) (the folder keeps the
name of the first release candidate; its contents are the reviewed screenshot
set reused unchanged since the `v27.0.0-rc.7` documentation package). They
were taken on 21 to 23 October 2026 from the Development deployment of the
`development` branch (application version 3.1.6 plus the development changes;
the later commits up to `48ce8d3d`, the application source of `v27.0.0-rc.12`,
changed no application file) with the crew's Development test accounts, test
destinations and test events, at 1440, 768 and 390 pixel widths, for an
administrator and for a regular user. File names
follow `<page>-<state>-<role>-<width>.png`; the folder index lists every file
with its page, role, viewport and capture time, and names the pages that were
left out because they would show a mailbox identity, personal names or a
private address. The [WebUI guide](webui.md) embeds these captures. Nowlert
CE is a desktop web application, so the Preview of the repository README and
the Docker Hub README shows the 1440 px Dashboard, Routing Flow, Destinations
and sign-in captures at full width. The 768 and 390 px captures are secondary
examples of the responsive layout in a narrow browser window; they do not
show the Nowlert Mobile app, which is a separate product (see the
[screenshot privacy review](guides/screenshot-privacy.md)).

Every other raster under `images/` that shows the Nowlert WebUI or a delivered
card is an older capture and is labeled as such where it is used.

## Historical screenshots

The captures below show earlier interfaces. They are kept as history only;
no current document uses them to illustrate the current WebUI.

Historical v3.1.0 screenshots live under `images/` as versioned examples of
the v3.1.0 interface. They do not describe the current development UI and are
no longer embedded by the README or the WebUI guide:

- `v3.1.0-dashboard.png`
- `v3.1.0-routing-flow.png`
- `v3.1.0-destinations.png`

Three further v3.1.0 captures (the Delivery History page and the Discord and
Microsoft Teams Xen Orchestra cards) were withdrawn on 22 October 2026 because
they still showed deployment labels; the
[screenshot privacy review](guides/screenshot-privacy.md) records them.

`v3.1.0-discord-idrac.png` and `v3.1.0-discord-unifi.png` are further v3.1.0
captures that current guides do not embed.

The following captures predate the Nowlert name (they show the retired product
name) and are outdated. They are retained only for history and must not be
used to illustrate current behavior:

- `v2.5.2-destinations.png`, `v2.5.2-discord-idrac.png`,
  `v2.5.2-discord-zabbix.png`, `v2.5.2-inputs.png`, `v2.5.2-overview.png`,
  `v2.5.2-routing-flow.png`, `v2.5.2-settings.png`, `v2.5.2-sources.png`,
  `v2.5.2-teams.png`
- `discord-xen-orchestra-v1.9.6.png`

The v1.9.6 Teams Xen Orchestra card was withdrawn on 23 October 2026 (see the
[screenshot privacy review](guides/screenshot-privacy.md)).

Only the Dell iDRAC Redfish guide still embeds one of them
(`v2.5.2-discord-idrac.png`), explicitly labeled as outdated pending recapture.

## Screenshot rules

Additional packaged screenshots may be referenced by individual practical
guides when they accurately demonstrate an existing integration/destination
presentation. Their validation dates are historical observations, not claims
about the current build.

Every raster under `images/` has a row in the
[screenshot privacy review](guides/screenshot-privacy.md) that records its
status and the date of its last visual inspection; captures that showed
private details were withdrawn from the checkout and are listed there.
`tests/test_screenshot_privacy_inventory.py` fails when a raster is missing
from that inventory or carries EXIF or author metadata.

Capture replacement images from test accounts and test data in the current
development UI.
Never publish captures that show passwords, destination
URLs, API tokens, setup tokens, private hostnames, email addresses, or other
secret/personal material. See the
[screenshot privacy review](guides/screenshot-privacy.md).

## Documentation validation

Run:

```bash
python tools/validate_current_documentation.py
python -m pytest -q tests/test_comprehensive_readme.py \
  tests/test_current_documentation_contract.py \
  tests/test_screenshot_privacy_inventory.py \
  tests/test_v252_documentation_refresh.py \
  tests/test_v310_release_docs.py \
  tests/test_v311_release_docs.py \
  tests/test_v316_release_docs.py
```

Before tagging, verify release metadata, runtime version and Compose defaults
against the accepted release candidate. Label development-only behavior and
historical screenshots separately; documentation checks do not approve a release.
