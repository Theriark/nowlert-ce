# Nowlert CE development after v3.1.6

**Release candidate line: v27.0.0.** The `development` branch is tested as
`v27.0.0-rc.N` pre-release tags. The current release candidate is the latest
GitHub pre-release of `Theriark/nowlert-ce`; its exact version, source commit
and image digest are recorded in that pre-release and in the matching
documentation package, not in this note. A release
candidate is not a stable release: `src/version.py` reports `27.0.0`, the
version the candidates are released as, while the current stable release
remains v3.1.6 and no stable v27.0.0 tag or image alias exists. This note
records what the `development` branch contains beyond
v3.1.6 so that operators, testers and documentation reviewers can tell current
development behavior from the released line. When v27.0.0 is released, its
numbered release note and QA checklist replace this note as the current
release material.

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
- Filtering decoupled from routes; the **Integration behavior** panel under
  **Filtering** holds UniFi Protect device aliases, Home Assistant
  endpoint/component aliases and Redfish deduplication; trusted Dell iDRAC
  management clients moved into each destination's Dell iDRAC filter.
- Delivery history and Audit log pagination restored, with Audit log filters,
  range and sort applied on the server.
- **Security** page (account menu at the bottom of the sidebar): multi-factor authentication with an
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
- Changes of 11 and 12 November 2026 (pull requests 651 to 658): the
  Dashboard delivery chart shows deliveries per period of the chosen range
  (per minute to per month) as stacked Delivered/Retry/Failed columns with
  readable axes, instead of a running total; signing in no longer stalls on
  **Connecting…** or shows **Some workspace data could not be loaded**;
  layout fixes for 13-inch laptops and narrow windows (scrolling sidebar,
  pinned table actions, visible dialog buttons, no overlapping text) and
  clearer wording; the duplicate **Restart Nowlert** button on the Security
  page is removed (the account menu keeps it); the Users page **Recent
  activity** lists sign-ins and account changes; the Event API token
  **Allowed integrations** list takes a plain click per integration.
- Readiness fixes of 28 November 2026: the application reports version
  27.0.0; regular users see Regional settings and Integration behavior
  read-only instead of Save and Edit controls that failed; **Send test** is
  limited to a destination's owner and administrators; a webhook URL must be a
  complete `https://` address; route names are unique across accounts,
  ignoring case; a wrong current password says "The current password is not
  correct." on the field; the Preview dialog explains a destination without
  routes; editing a backup destination clears its old **Last test** time.
- Readiness fixes, round 2 (28 November 2026): Discord, Microsoft Teams and
  Slack URLs are validated like the Generic webhook URL; route names are unique
  for every writer, built-in routes of a later account get numbered names such
  as "Checkmk HTTP (2)" and older duplicates are renamed at start-up; a
  `/#routing-flow` link opens Routing Flow after a full page load; the language
  list shows English and Português once; the Updates card shows its green tick
  only after a successful check; Audit log trends are coloured by good or bad
  news; Scheduled backups show only the day field that applies.
- Readiness fixes, round 3 (28 November 2026): sign-in and account errors read
  as sentences that say what to do; the Delivery history severity filter
  groups equivalent words (Information also finds Info and Informational) and
  keeps each event's own word; the Email Alerts cards count enabled rules per
  classification and enabling or disabling a rule, group or mailbox confirms
  it; the token dialog is titled "Event API token: NAME" and **Remove** appears
  only with a profile picture; the Dell iDRAC logo sits on a light tile in
  Routing Flow; a sidebar label that does not fit wraps instead of being cut
  off; Backup destinations become cards at 900 px and narrower; leaving Email
  Alerts drops `?emailTab=`; the destination URL error ends with one full
  stop; the route picker names each route's owner ("Owner: you"); creating a
  user shows a confirmation; the Security page token section is always headed
  **Event API tokens**; `PUT /api/v2/integration-settings/{xo,zabbix}` refuses
  `show_ids: true`.

### Operations

- Scheduled housekeeping of Delivery history, Audit log and backup-run records.
- Health checks warn about mailboxes that cannot synchronize or repeated
  mailbox synchronization failures, and report the selected backup target and
  schedule instead of "External backup disabled".
- Backup listing of NAS targets without scanning archive contents; the Mobile
  coordination lock is excluded from backups.
- Concurrent SMTP routing and bounded concurrent destination delivery.
- Faster pages: read requests share one database connection and the
  Destinations list builds its route list once; Filtering, Routing Flow and
  Destinations open two to three times faster, backups and the Audit log in
  well under a second. Repeated empty mailbox checks no longer fill the
  Audit log.
- Runtime libraries updated after the Datadog Code Security scan of
  `development`: Pillow 13.0.0, certifi 2026.10.23, ddtrace 4.17.0 and
  opentelemetry-api 1.45.2.

## Documentation state

- Live captures of this development interface are packaged under
  `docs/images/v27.0.0-rc.1/`: screenshots first taken on 21 to 23 October 2026
  from the Development deployment with the crew's Development test accounts
  and test data, at 1440, 768 and 390 pixel widths, listed in
  [the folder index](../images/v27.0.0-rc.1/README.md) and embedded in the
  [WebUI guide](../webui.md). Nowlert CE is a desktop web application: the
  repository README and the Docker Hub README Preview show the 1440 px
  Dashboard, Routing Flow, Destinations and sign-in captures, and the 768 and
  390 px captures are secondary examples of the responsive layout in a narrow
  browser window, not the separate Nowlert Mobile app. Captures whose page
  changed were replaced: eight on 12 November 2026 (the four Dashboard
  captures, Users, both Security captures and Filtering), the 1440 px
  Dashboard and Routing Flow captures on 27 November 2026, and on
  28 November 2026, from Development builds of version 27.0.0 signed in as the
  neutral test administrator `nowlert-admin`, the Settings and Audit log
  captures and then nine more after the round-3 readiness fixes (the three
  Routing Flow captures, the 1440 and 768 px Email Alerts rules captures,
  both Security captures and the Synology- and Zabbix-filtered Delivery
  history captures). The folder index records the date, build and account of
  every file. The v3.1.0 set is historical; the v2.5.2 and v1.9.6 captures
  show the retired product name and remain outdated.
- A release candidate still needs: a version bump with a numbered release note
  and QA checklist, independent visual review of those captures, and the normal
  Development -> Stage -> Finalize CE Release path described in
  [deployment](../deployment.md).

See the [WebUI guide](../webui.md), the [integration setup index](../integrations/README.md)
and the [technical use-case guides](../guides/README.md) for current steps.
