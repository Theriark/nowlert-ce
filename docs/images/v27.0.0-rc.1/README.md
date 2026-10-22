# Development interface captures, v27.0.0-rc.1

Live screenshots of the Nowlert CE development WebUI, taken on 21 October 2026
(Europe/Lisbon) from the Development deployment of the `development` branch at
commit `342698c67fe000a11b02994ed289f0cf45b22166` (running application version
3.1.6 plus the development changes listed in
[Development after v3.1.6](../../releases/post-v3.1.6-development.md)).

Every capture uses the synthetic AI-crew test accounts (`ai-crew-admin-…`,
`ai-crew-user-…`), synthetic destinations and synthetic events. No credential,
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
| `audit-log-overview-admin-1440.png` | Audit log | administrator | 1440 | 15:49 |
| `settings-regional-admin-1440.png` | Settings (Regional, Updates, Housekeeping) | administrator | 1440 | 15:50 |
| `security-profile-admin-1440.png` | Security (Profile, MFA, password, API tokens) | administrator | 1440 | 15:50 |
| `users-search-admin-1440.png` | Users, filtered to the crew accounts | administrator | 1440 | 15:51 |
| `delivery-history-zabbix-admin-1440.png` | Delivery history, Zabbix source filter | administrator | 1440 | 15:53 |
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

The two preview captures were replaced on 21 October 2026 at the times shown;
the other 24 files are unchanged.

## Added on 22 October 2026 (commit 8dc1b2ca)

Five captures were added on 22 October 2026 from the Development deployment of
the `development` branch at commit `8dc1b2cabdbfbbb3f9ec1539ec6fbeb854ab4461`
(still application version 3.1.6), after the merge of pull requests 619 and
620, which fixed the Preview dialog routes drawer, the Discord header badge,
the Users list refresh, the IMAP mailbox edit form and the narrow Email Alerts
rules table. The stylesheets and scripts served by that deployment were
compared byte for byte with the sources of that commit before capturing. Same
synthetic administrator account, same viewports.

| File | Page / state | Role | Width | Captured (Lisbon) |
|---|---|---|---|---|
| `destination-preview-routes-drawer-admin-1440.png` | Preview dialog with the **Manage routes** drawer open: Done button, Active badge beside each route | administrator | 1440 | 22:43 |
| `destination-preview-discord-debug-admin-1440.png` | Preview dialog, Discord destination, severity **Debug**, generic sample source, output scrolled to the context line that reads **Debug** | administrator | 1440 | 22:49 |
| `email-alerts-rules-admin-768.png` | Email Alerts, Rules tab as stacked rule cards | administrator | 768 | 22:49 |
| `email-alerts-rules-admin-390.png` | Email Alerts, Rules tab as stacked rule cards, scrolled to the first full card | administrator | 390 | 22:50 |
| `email-alerts-mailbox-edit-imap-admin-1440.png` | Edit mailbox dialog of the synthetic IMAP mailbox (username and password optional, folder scan unavailable) | administrator | 1440 | 22:51 |

Notes on these five files:

- The Preview dialog has no visible source selector: it sends the sample event
  with the source of the destination's first dedicated route. For the Debug
  capture the preview form's source value was set to the generic Nowlert
  source so that the generic Discord card is shown; an integration with its
  own state label (for example Home Assistant) keeps that label in the header.
- The Edit mailbox capture shows the synthetic mailbox
  `qa@ce-qa-fixture.invalid` with the loopback host `127.0.0.1` and port
  `19993`, which the QA fixture uses because no IMAP server exists in
  Development. The Mailboxes list behind the dialog is hidden by the dialog
  backdrop; the list itself remains uncaptured (see below).
- The 390 px rules capture is scrolled so that one complete rule card is
  visible; the page header stays fixed at the top.

## Names shown in the captures

- The accounts `ai-crew-admin-…` and `ai-crew-user-…` are the synthetic crew
  test accounts.
- The owner label `ITMANAGER` on the shared `CE Development - …` destinations
  is the username of the administrator account of the Development deployment
  that created them; it is a role name, not a personal name. The destination
  subtitles (`#ce-nowlert-development`, `#Dev`, `#test`,
  `ce-nowlert-development`) are the labels typed into the destination editor
  for the crew's development test channels, not webhook addresses.
- The host, database and runbook names in
  `delivery-history-zabbix-admin-1440.png` (`VM-08 | Zabbix Server`, `DB-01`,
  `DB-REPLICA`, `DB-RUNBOOK-REPLICATION-01`) are the synthetic Zabbix sample
  data of the repository's own tests (`tests/test_round44_zabbix_classic_cleanup.py`,
  `tests/test_discord_modern_images.py`), delivered to the Development
  deployment on 15 October 2026 with the tag `site=development`; they are not
  real infrastructure and no address is shown.

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
  message bodies contain a real mailbox address.
- Email Alerts Mailboxes tab: a personal mailbox label (only the Edit mailbox
  dialog of the synthetic IMAP mailbox is captured, with the list hidden
  behind the dialog backdrop).
- Users without a search filter: personal names of other accounts.
- Backups: a private storage address.

These pages are described in writing in the [WebUI guide](../../webui.md).
The historical `v3.1.0-*.png` and `v2.5.2-*.png` captures one folder up are
unchanged and remain labelled as historical.
