# Nowlert CE development after v3.1.6

**Release candidate line: v27.0.0.** The `development` branch is tested as
`v27.0.0-rc.N` pre-release tags (`v27.0.0-rc.7` at commit `9823244c` is the
latest at the time of writing). A release candidate is not a stable release:
`src/version.py` still reports `3.1.6`, the current stable release remains
v3.1.6, and no stable v27.0.0 tag or image alias exists. This
note records what the `development` branch contains beyond v3.1.6 so that
operators, testers and documentation reviewers can tell current development
behavior from the released line. When v27.0.0 is released, its numbered
release note and QA checklist replace this note as the current release
material.

## Compatibility

- Database schema: **18**. v3.1.6 shipped schema 9; migrations 10 to 18 run
  automatically on first start of a development image: remove notices,
  destination filtering, independent routes and destination assignments,
  history housekeeping runs, account MFA and routing flow telemetry, Email
  Alerts foundation, email mailbox sharing, one-time MFA recovery codes, and
  source receipt identity.
- Configuration model: **`platform_database_v1`**, unchanged.
- Persistent state path: **`/nowlert/state`**, unchanged.
- A database migrated to schema 18 cannot be used by a v3.1.6 image. Take a
  verified recovery snapshot before upgrading a v3.1.6 installation and keep an
  off-host copy until acceptance passes.

## New since v3.1.6

### Inputs and integrations

- **Email Alerts**: Gmail and Microsoft 365 mailbox connections (private or
  shared), deterministic rules grouped into groups, an Activity view, and
  routing of classified messages through Nowlert.
- New built-in integrations: Prometheus (Alertmanager), Checkmk, Semaphore,
  Sonarr, Radarr, Metabase and GitHub Actions, each with receiver tests and
  Event API token scopes.
- Documented and validated flows for Zabbix, Grafana, Portainer, Home
  Assistant, TrueNAS and UniFi Network/Protect/Drive, with controlled
  integration delivery validation.

### Destinations and presentation

- Destination types offered by the editor: Discord, Microsoft Teams, Slack,
  Email (outbound SMTP), Nowlert Mobile and generic webhook. MQTT and ntfy are
  no longer offered.
- **Message style** per destination: **Modern Card** or **Classic Card** for
  Microsoft Teams, Slack, Nowlert Mobile and generic webhook; Discord keeps its
  Components v2 option. Modern image cards exist for all integrations on
  Discord and Teams; Slack gained Classic and Modern cards; Teams gained
  Classic cards across integrations.
- **Nowlert Mobile** destination connected through a temporary connection code
  approved in the mobile app.
- Destination test sends a Nowlert-owned notification rendered in the
  destination's selected style.
- Discord card header: when an event carries no state of its own, the header
  badge shows the real severity (Debug, Notice, Not Classified) instead of a
  generic Information label; Information and its synonyms, and the Resolved,
  Critical and Warning buckets, are unchanged.

### WebUI

- Routing Flow with pulses and live metrics; Dashboard delivery graph.
- Filtering decoupled from routes; the **Integration behavior** panel
  (formatter filters, device aliases, trusted management clients, Redfish
  deduplication) is shown under **Filtering**.
- Delivery history and Audit log pagination restored, with Audit log filters,
  range and sort applied on the server.
- **Security** page (Profile menu): multi-factor authentication with an
  authenticator app and one-time recovery codes, password change and Event API
  tokens.
- Resilient browser sessions with in-place re-authentication; refreshed
  translation source for the sidebar titles.
- The Notices feature was removed.
- Fixes after the 22 October 2026 Development walk: the Preview dialog's
  assigned routes drawer shows its **Done** button and keeps the
  Active/Disabled badge in its own column; the Users list and counts update
  immediately after create, enable/disable and delete; an IMAP mailbox's name
  and visibility save without a folder scan and a blank username keeps the
  stored one; the Email Alerts rules table becomes stacked cards at 900 px and
  narrower.

### Operations

- Scheduled housekeeping of Delivery history, Audit log and backup-run records.
- Backup listing of NAS targets without scanning archive contents; the Mobile
  coordination lock is excluded from backups.
- Concurrent SMTP routing and bounded concurrent destination delivery.

## Documentation state

- Live captures of this development interface are packaged under
  `docs/images/v27.0.0-rc.1/`: 30 screenshots taken on 21 to 23 October 2026
  from the Development deployment with synthetic accounts and synthetic data, at
  1440, 768 and 390 pixel widths, listed in
  [the folder index](../images/v27.0.0-rc.1/README.md) and embedded in the
  repository README, the Docker Hub README and the [WebUI guide](../webui.md).
  They are the reviewed screenshot set of the `v27.0.0-rc.7` documentation
  package. The v3.1.0 set is historical; the v2.5.2 and v1.9.6 captures show
  the retired product name and remain outdated.
- A release candidate still needs: a version bump with a numbered release note
  and QA checklist, independent visual review of those captures, and the normal
  Development -> Stage -> Finalize CE Release path described in
  [deployment](../deployment.md).

See the [WebUI guide](../webui.md), the [integration setup index](../integrations/README.md)
and the [technical use-case guides](../guides/README.md) for current steps.
