# Development interface captures, v27.0.0-rc.1

**Current set.** The folder keeps the name of the first release candidate; its
contents are the reviewed screenshot set reused unchanged since the
`v27.0.0-rc.7` documentation package. Nowlert CE is a desktop web
application: since 25 October 2026 the Preview of the repository README and
the Docker Hub README shows four of its desktop captures at full width,
`dashboard-live-admin-1440.png`, `routing-flow-live-admin-1440.png`,
`destinations-list-admin-1440.png` and `sign-in-empty-signed-out-1440.png`.
The 768 and 390 px captures are secondary examples of the responsive layout
in a narrow browser window, embedded by the WebUI guide only; they do not show
the Nowlert Mobile app, which is a separate product. The Development build
`66d50b00` ran the same application source as `v27.0.0-rc.7` (`9823244c`);
on 24 October 2026 the Dashboard, Routing Flow and Destinations pages were
compared with it live and showed the same layout and controls, differing only
in live counters and the selected time range. The only application change in
the later commits, up to the source of `v27.0.0-rc.14`, is the Destinations
empty-state fix in `src/webui/app.js` and `src/webui/professional.css`
(THE-1654, PR 641); every other later change is to documentation, CI and
tests.

Live screenshots of the Nowlert CE development WebUI, taken on 21 October 2026
(Europe/Lisbon) from the Development deployment of the `development` branch at
commit `342698c67fe000a11b02994ed289f0cf45b22166` (running application version
3.1.6 plus the development changes listed in
[Development after v3.1.6](../../releases/post-v3.1.6-development.md)).

Every capture uses the crew's Development test accounts (`ai-crew-admin-…`,
`ai-crew-user-…`), the Development test destinations described under "Names
shown in the captures" below and test events. No credential,
token, private address, personal name or customer data is shown; pages that
would have exposed such data were left out (see the end of this file).

File names follow `<page>-<state>-<role>-<width>.png`. Viewports are CSS
pixels at scale 1: 1440×900 (desktop), 768×1024 (tablet) and 390×844 (phone).

| File | Page / state | Role | Width | Captured (Lisbon) |
|---|---|---|---|---|
| `sign-in-empty-signed-out-1440.png` | Sign in, empty form | signed out | 1440 | about 14:40 |
| `sign-in-empty-signed-out-768.png` | Sign in, empty form | signed out | 768 | about 14:40 |
| `sign-in-empty-signed-out-390.png` | Sign in, empty form | signed out | 390 | about 14:40 |
| `dashboard-live-admin-1440.png` | Dashboard, Live, last hour | administrator | 1440 | 15:48 |
| `routing-flow-live-admin-1440.png` | Routing Flow, Live, last 24 hours | administrator | 1440 | 15:48 |
| `destinations-list-admin-1440.png` | Destinations list | administrator | 1440 | 15:48 |
| `filtering-list-admin-1440.png` | Filtering with Integration behavior | administrator | 1440 | 15:49 |
| `email-alerts-rules-admin-1440.png` | Email Alerts, Rules tab | administrator | 1440 | 15:49 |
| `settings-regional-admin-1440.png` | Settings (Regional, Updates, Housekeeping) | administrator | 1440 | 15:50 |
| `security-profile-admin-1440.png` | Security (Profile, MFA, password, API tokens) | administrator | 1440 | 15:50 |
| `users-search-admin-1440.png` | Users, filtered to the crew accounts | administrator | 1440 | 15:51 |
| `email-alerts-groups-admin-1440.png` | Email Alerts, Groups tab | administrator | 1440 | 15:53 |
| `destination-editor-teams-admin-1440.png` | Add destination, Microsoft Teams, Message style | administrator | 1440 | 15:54 |
| `destination-preview-teams-modern-admin-1440.png` | Preview dialog, Teams destination saved as Modern Card, output scrolled to the card body | administrator | 1440 | 20:44 |
| `destination-preview-teams-classic-admin-1440.png` | Preview dialog, Teams destination saved as Classic Card, output scrolled to the card body | administrator | 1440 | 20:41 |
| `destinations-list-admin-768.png` | Destinations list | administrator | 768 | 17:57 |
| `dashboard-live-admin-768.png` | Dashboard, Live | administrator | 768 | 17:57 |
| `routing-flow-live-admin-768.png` | Routing Flow, Live | administrator | 768 | 18:04 |
| `routing-flow-live-admin-390.png` | Routing Flow, Live | administrator | 390 | 18:05 |
| `dashboard-live-admin-390.png` | Dashboard, Live | administrator | 390 | 18:05 |
| `destinations-list-admin-390.png` | Destinations list | administrator | 390 | 18:05 |
| `dashboard-live-user-1440.png` | Dashboard, Live | regular user | 1440 | 18:06 |
| `destinations-list-user-1440.png` | Destinations list (shared destinations of other owners, all view only) | regular user | 1440 | 18:06 |
| `security-profile-user-1440.png` | Security (Profile, MFA, password, API tokens) | regular user | 1440 | 18:07 |

The two preview captures were replaced on 21 October 2026 at the times shown.
The Zabbix-filtered Delivery history capture of 21 October 2026 (15:53) was
withdrawn on 23 October 2026 and is no longer listed, and so is the Audit log
capture; see "Withdrawn and replaced on 23 October 2026" below. The other 22
files of this table are unchanged.

## Added on 22 October 2026 (commit 8dc1b2ca)

Five captures were added on 22 October 2026 from the Development deployment of
the `development` branch at commit `8dc1b2cabdbfbbb3f9ec1539ec6fbeb854ab4461`
(still application version 3.1.6), after the merge of pull requests 619 and
620, which fixed the Preview dialog routes drawer, the Discord header badge,
the Users list refresh, the IMAP mailbox edit form and the narrow Email Alerts
rules table. The stylesheets and scripts served by that deployment were
compared byte for byte with the sources of that commit before capturing. Same
crew administrator account, same viewports.

| File | Page / state | Role | Width | Captured (Lisbon) |
|---|---|---|---|---|
| `destination-preview-routes-drawer-admin-1440.png` | Preview dialog with the **Manage routes** drawer open: Done button, Active badge beside each route | administrator | 1440 | 22:43 |
| `destination-preview-discord-debug-admin-1440.png` | Preview dialog, Discord destination, severity **Debug**, generic sample source, output scrolled to the context line that reads **Debug** | administrator | 1440 | 22:49 |
| `email-alerts-rules-admin-768.png` | Email Alerts, Rules tab as stacked rule cards | administrator | 768 | 22:49 |
| `email-alerts-rules-admin-390.png` | Email Alerts, Rules tab as stacked rule cards, scrolled to the first full card | administrator | 390 | 22:50 |
| `email-alerts-mailbox-edit-imap-admin-1440.png` | Edit mailbox dialog of the IMAP test mailbox of the QA fixture (username and password optional, folder scan unavailable) | administrator | 1440 | 22:51 |

Notes on these five files:

- The Preview dialog has no visible source selector: it sends the sample event
  with the source of the destination's first dedicated route. For the Debug
  capture the preview form's source value was set to the generic Nowlert
  source so that the generic Discord card is shown; an integration with its
  own state label (for example Home Assistant) keeps that label in the header.
- The Edit mailbox capture shows the QA fixture mailbox
  `qa@ce-qa-fixture.invalid` with the loopback host `127.0.0.1` and port
  `19993`, which the QA fixture uses because no IMAP server exists in
  Development. The Mailboxes list behind the dialog is hidden by the dialog
  backdrop; the list itself remains uncaptured (see below).
- The 390 px rules capture is scrolled so that one complete rule card is
  visible; the page header stays fixed at the top.

## Withdrawn and replaced on 23 October 2026 (capture base commit 82c8470a)

The Audit log capture of 21 October 2026 (15:49) was also withdrawn on
23 October 2026 (Jira TOPS-356): its audit rows show the user name of the
Development deployment's administrator account, which is not one of the
crew test accounts, together with truncated internal record identifiers.
It is not replaced; the [WebUI guide](../../webui.md) describes the Audit log
page in writing. Like the Zabbix file below, it remains in the folder as an
empty placeholder until a person with delete access removes it.

The Zabbix-filtered Delivery history capture of 21 October 2026 was withdrawn
on 23 October 2026 (Jira TOPS-351): its sample rows, although taken from the
repository's own test fixture, carried VM-numbered host and database labels
(`VM-08 | Zabbix Server`, `DB-01`, `DB-REPLICA`) that read like internal
infrastructure names. The crew's repository tools overwrite but cannot delete
files, so the withdrawn file remains in the folder as an empty placeholder
until a person with delete access removes it. It was replaced by one capture
from the Development deployment of the `development` branch at commit
`82c8470af473570a87690e76f9ea0431f49e3013` (application version 3.1.6 plus the
development changes, after the merge of pull requests 622 to 626), same
crew administrator account, same viewport, opened at full size before
being added.

The two withdrawn files, `audit-log-overview-admin-1440.png` and
`delivery-history-zabbix-admin-1440.png`, are zero-byte placeholders. No
current document links them, and they are not part of the published
documentation packages.

| File | Page / state | Role | Width | Captured (Lisbon) |
|---|---|---|---|---|
| `delivery-history-synology-admin-1440.png` | Delivery history, **Synology** source filter, **Last 30 days**, newest first, first event selected with its detail pane | administrator | 1440 | 10:48 |

Note on this file: the rows are the Synology sample events of 15 October 2026
for the device `synthetic-dsm-01`, the device name of the repository's
Synology test fixture (storage pool degraded, recovered, Hyper Backup
failure); the detail pane
shows the message, the outcome badges, the transport information (input,
destination `CE Development - Discord`, destination type, response code) and
the timeline. No mailbox, sender, address or token appears. The Email Alerts
rows of this page are still not captured: their subtitles name the connected
mailbox addresses.

## Names shown in the captures

- The accounts `ai-crew-admin-…` and `ai-crew-user-…` are the crew's
  Development test accounts.
- The owner chip on a destination card shows the username of the account that
  owns the destination (`owner_username` in `src/webui/app.js`). Usernames are
  free text typed when an account is created; the only account roles are
  administrator and user, so an owner chip never shows a role.
- The owner label `ITMANAGER` on the shared `CE Development - …` destinations
  is the typed username of the administrator account of the Development
  deployment that created them. It is a generic label, not a role and not a
  personal name; the repository does not record who chose it. The destination
  subtitles (`#ce-nowlert-development`, `#Dev`, `#test`,
  `ce-nowlert-development`) are the labels typed into the destination editor
  for the crew's development test channels, not webhook addresses.
- The owner labels `USER` (on `test 2`) and `CE-QA-20261015` (on the `CE QA …`
  destinations) in the destination captures are, in the same way, the typed
  usernames of the Development accounts that created those destinations: a
  generic account name and the account of the 15 October 2026 QA fixture.
  Neither is a personal name.
- The device name `synthetic-dsm-01` and the storage-pool and backup texts in
  `delivery-history-synology-admin-1440.png` are the Synology sample events
  delivered to the Development deployment on 15 October 2026; they are
  not real infrastructure and no address is shown. The destination column of
  the detail pane names the shared crew destination `CE Development - Discord`
  described above.

## Known limits

- At 768 px the title of the Routing Flow filter card is cut off at the right
  edge of the card without an ellipsis (`routing-flow-live-admin-768.png`).
  The 390 px capture (`routing-flow-live-admin-390.png`) shows the top of the
  page only, with the metric cards in two columns and the first integration
  cards; the filter card is further down the page and is not in the capture.
  This is a presentation limit of the current development interface observed
  live on 21 October 2026, not a documentation error.
- In the Preview dialog, changing the **Message style** selector did not
  change the generated payload in this build: the preview request sends only
  the sample event, and the payload is rendered in the style saved on the
  destination (observed live on 21 October 2026 and matching the preview
  request in `src/webui/app.js`). The preview pair therefore uses two
  destinations saved with different styles, and the selector in each capture
  was set to the style saved on that destination.

## Not captured on purpose

- Delivery history without a source filter and the Email Alerts Activity tab:
  message subtitles and bodies contain real mailbox addresses and real
  message subjects (re-confirmed live on 23 October 2026).
- Email Alerts Mailboxes tab: a personal mailbox label (only the Edit mailbox
  dialog of the QA fixture's IMAP test mailbox is captured, with the list hidden
  behind the dialog backdrop).
- Audit log: audit rows show the user name of the Development deployment's
  administrator account and internal record identifiers.
- Users without a search filter: personal names of other accounts.
- Backups: a private storage address.

These pages are described in writing in the [WebUI guide](../../webui.md).
The historical `v3.1.0-*.png` and `v2.5.2-*.png` captures one folder up are
unchanged and remain labelled as historical.
