# Screenshot privacy review

This page records which raster captures under `docs/images/` are retained,
which were withdrawn, and when each retained file was last opened for
inspection. A recorded inspection date is not a guarantee that a capture is
free of private details: the independent review of 22 October 2026 found
remaining private labels in three captures whose rows recorded an inspection
on 15 October 2026. Read every "reviewed" record as "opened on that date",
never as "verified".

## Review history

- 15 October 2026: the 82 raster captures linked from current documentation at
  that date were opened at readable size, including sidebars, account labels,
  message bodies, configuration editors and browser chrome. The earlier
  blanket claim that all captures were sanitized was incorrect. Twelve
  captures with remaining private details were withdrawn from the checkout
  and from every current guide link; the affected guides provide written
  verification steps instead.
- 15 October 2026, second pass: an independent review of the 70 linked
  captures retained after the first pass found one further Protect capture
  with custom camera/location labels. It was withdrawn as well, leaving 69
  linked rasters at that date.
- 21 October 2026: the Development WebUI set under
  `images/v27.0.0-rc.1/` was added, with its own folder index.
- 22 October 2026: the NCE-109 re-check (below) confirmed the 15 October
  withdrawals on `development` and `stage`, and an independent review of the
  whole inventory (105 of the 108 rasters opened at readable size) found three
  further exposures in captures embedded by the README and guides. Those
  three were withdrawn the same day. The three files that review could not
  open are listed under "Validation records".
- 22 October 2026, later the same day: five further Development captures
  were added to `images/v27.0.0-rc.1/` (Preview dialog routes drawer, Discord
  Debug preview, Email Alerts rules at 768 and 390 px, Edit mailbox dialog of
  the QA fixture's IMAP test mailbox) and inspected at full size before
  being added. The Edit mailbox capture shows the fixture address
  `qa@ce-qa-fixture.invalid` and the loopback host `127.0.0.1`; the list
  behind the dialog is hidden by the backdrop.
- 23 October 2026 (Jira TOPS-351, P1 privacy re-check of the packaged
  Development set): all 31 rasters under `images/v27.0.0-rc.1/` were
  downloaded from `development` at commit `82c8470a` and opened at full size.
  Thirty show only the crew test accounts, test fixture values, the typed
  generic owner label `ITMANAGER` (then wrongly described as a role name; see
  25 October 2026 below) and the crew's test channel labels already described
  in the folder index. One, the Zabbix-filtered Delivery history
  capture, showed VM-numbered host and database labels taken from the
  repository's test fixture (`VM-08 | Zabbix Server`, `DB-01`, `DB-REPLICA`)
  that read like internal infrastructure names; it was withdrawn and replaced
  by a Synology-filtered capture whose rows name only the test fixture device
  `synthetic-dsm-01`. The same check confirmed live on Development that the
  Mailboxes tab, the Activity tab and the unfiltered Delivery history still
  show real connected-mailbox labels, sender addresses and message subjects;
  those pages remain uncaptured and are described in writing.
- 23 October 2026, same re-check, rest of the inventory: every other retained
  raster in the checkout was opened at full size except the three token
  captures, which the crew's tooling still cannot open (see "Validation
  records"). No readable private address, mailbox, sender, token or hostname
  was found; the existing masks cover the labels they were meant to cover.
  One unembedded historical card, the v1.9.6 Teams Xen Orchestra card, showed
  its repository and VM names (`NAS-01 / Critical Backups`, `APP-01`)
  unmasked; it was withdrawn on the same grounds as the v3.1.0 Discord Xen
  Orchestra card of 22 October. The rows below that previously read
  "unreviewed" now record this inspection; the other rows keep their earlier
  record date, but each was also opened on 23 October 2026.
- 23 October 2026, independent test of that change (Jira TOPS-356): the Audit
  log capture of the Development set showed, in its audit rows, the user name
  of the Development deployment's administrator account together with
  truncated internal record identifiers. That account is not one of the
  crew test accounts, the folder index did not list it among the names
  shown, and nothing in the repository establishes it as a test account, so
  the capture was withdrawn rather than described as one. The statement above
  about the other thirty captures of the folder no longer covers it. The Audit log page is described in writing instead.
- 23 October 2026 (Jira TOPS-374): the three token captures that the crew
  cannot open were unlinked from current documentation. The hardware Redfish
  guide, the Portainer guide and the infrastructure tutorials index now
  describe the **Issue Event API token** dialog and the token list in writing
  instead of embedding or linking them, so the documentation package no longer
  references files nobody in the crew has inspected. The three files stay in
  the checkout as retained rows until a person opens them; they must not be
  embedded again before that inspection is recorded.
- 24 October 2026 (Jira TOPS-422 and TOPS-439, review of pull request 635):
  that day the Preview of the README (six captures) and of the Docker Hub
  README (three captures) had been switched to desktop captures of the
  `images/v27.0.0-rc.1/` set. The independent code review found that they
  show the names of the open point below: the administrator account name
  (`ai-crew-admin-…`), the owner labels `ITMANAGER`, `USER` and
  `CE-QA-20261015` and the channel label `#ce-nowlert-development`. All 30
  non-empty captures of the set were opened at full size again. Every desktop
  capture of a signed-in page shows the account name in the sidebar; the
  dialog captures show it only blurred behind the dialog, and blur is not a
  masking method this page accepts. Both Previews now embed only the three
  phone-width captures `sign-in-empty-signed-out-390.png`,
  `dashboard-live-admin-390.png` and `routing-flow-live-admin-390.png`, which
  show none of those names, no destination or channel name and no blurred
  text. The other captures of the set remain embedded by the WebUI guide only.
  No image was edited, masked or recaptured, and the policy question below was
  still open that day.
- 25 October 2026 (Jira TOPS-422 and TOPS-509, product owner correction):
  Nowlert CE is a desktop web application, and the phone-width captures had
  been chosen only because they hide the test-data labels. The product owner
  decided that generic test labels are no reason to replace the desktop
  presentation. Both Previews now show the 1440 px Dashboard, Routing Flow,
  Destinations and sign-in captures at full width; the four were opened at
  full size again that day. The 768 and 390 px captures remain secondary
  examples of the responsive layout in the WebUI guide and do not represent
  the separate Nowlert Mobile app. The same correction removed two
  unsupported statements. The owner label `ITMANAGER` is the typed username of
  the Development administrator account, not a role name: the owner chip
  renders the owner's username, usernames are free text, and the only account
  roles are administrator and user. The crew's accounts, destinations and
  labels are described as Development test data rather than as synthetic,
  because no record shows how each name was chosen. No image was edited,
  masked or recaptured. Credentials, tokens, private addresses and personal
  data stay excluded under the rules of this page.
- 30 October 2026 (Jira TOPS-659, cycle 3 correction after the rejected Stage
  QA of 30 October): the Stage QA finding named three remaining gap classes in
  the tutorial captures, mailbox labels and search text, private addresses in
  configuration and delivery messages, and Home Assistant device and sidebar
  labels. Every raster linked from a current document (88 files) was opened
  again at full size on this date and checked against those three classes;
  none of the retained captures showed one. The seven captures withdrawn on
  15 October 2026 for exactly those classes were the only images that had
  illustrated the mailbox list, the No-IP activity match, the Portainer TLS
  Compose editor, the native Dell delivery and the three Home Assistant
  steps. Their originals were taken from Git history before the withdrawal
  (they are not in the checkout, and stay out of the repository), and a
  sanitized copy of each was made by painting solid rectangles over the
  exposed pixels: the Gmail account label; the activity search text and the
  activity mailbox label; the Compose bind address; the controller address in
  the Dell message, in the list row and in the detail pane; and the personal
  dashboard label in the Home Assistant sidebar. The earlier partial masks in
  those captures were kept. Nothing else in the images was changed, and the
  copies are re-encoded with IHDR, IDAT and IEND chunks only. Each copy was
  opened at full size after masking and is listed below with the suffix
  `-sanitized`; the withdrawn paths remain withdrawn.
- 31 October 2026 (Jira TOPS-677, cycle 3): three Development captures under
  `images/v27.0.0-rc.1/` (Settings, Security as administrator and Security as
  regular user) no longer matched the application and were replaced by new
  captures of the Development deployment at commit `179cbc02`, taken with the
  crew test accounts at 1440 × 900 px and opened at full size before being
  added. They show only the crew account names and roles, dates, the empty
  token list ("No Event API tokens"; the token rows are below the captured
  viewport in any case) and the Development settings values (English,
  Europe/London, 24-hour clock, housekeeping time and retention). No token
  value, address, mailbox, hostname or personal name appears. The other 27
  non-empty captures of that folder were opened again at full size the same
  day; no private detail was found. Two of them show an unrendered emoji
  (an empty box) inside the generated payload text of the Preview dialog;
  that is a capture-browser font limit recorded in the folder index, not a
  privacy finding. The row counts are unchanged (115 retained, 95 linked).
- 31 October 2026 (Jira TOPS-682, cycle 3): the Filtering capture under
  `images/v27.0.0-rc.1/` was replaced by a capture of the Development
  deployment at commit `0c14583c`, taken with the crew administrator account
  at 1440 × 900 px and opened at full size before being added, after the
  review of the `v27.0.0-rc.14` package found that its status badges no
  longer matched the application. It shows the four shared
  `CE Development - …` test destinations, their filter names
  (`CE - Discord Filter 1` and the like), status and sharing badges and the
  three Integration behavior cards with zero aliases; no address, mailbox,
  token, hostname or personal name appears. Ten further captures of that
  folder (the destination editor, the four Preview dialog captures, the Edit
  mailbox dialog, the 768 px Email Alerts rules, the 768 and 390 px Routing
  Flow and the 768 px sign-in page) were compared with the live deployment
  the same day and kept unchanged; see the folder index. The row counts are
  unchanged (115 retained, 95 linked).
- 2 November 2026 (Jira NCE-109, founder instruction after the QA return of
  27 October 2026): removing or emptying an image breaks the tutorials and is
  not what QA asked for; QA asked for private values to be hidden. The crew
  now has a redaction tool that paints solid black rectangles over the given
  pixel boxes, changes nothing else in the picture and drops every metadata
  chunk. With it, the eighteen captures that had been removed from the
  checkout (twelve deleted, six overwritten with empty content) were restored
  from Git history byte for byte and masked, and the Xen Orchestra delivery
  capture, which QA had returned because its Message body still showed a full
  backup job label, was masked in place. Each result was opened at full size
  before being committed. What each still shows is recorded in its retained
  row below; in short: the Checkmk recipient account, the Metabase collection
  label, the Portainer sidebar account corner, the three remaining Xen
  Orchestra job names in the backup overview, the TrueNAS appliance hostname,
  the three location-labelled Protect alarm names, the camera and device
  labels of the v1.9.6 UniFi Discord cards, the NAS label and the personal
  name and portrait of the v1.9.6 QNAP Teams card, the Zabbix host filter
  text of the v2.5.2 routes page, the job, repository and VM names of the five
  Xen Orchestra cards (v1.9.6 Teams, v3.1.0 Discord, the two early cards),
  the user portrait of the v3.1.0 Teams card, the device-name prefix of the
  v3.1.0 Delivery History row, the user column and record identifiers of the
  Audit log capture and the host, database and message text of the
  Zabbix-filtered Delivery history capture are hidden. The v2.5.2 API access
  capture needed no mask (token names only, no values) and was restored
  unchanged. Blur was not used anywhere. The seven captures that already had a
  sanitized copy since 30 October 2026 were left as they are: the sanitized
  copies stay embedded and the original paths stay withdrawn. The guides embed
  the restored captures again where the written checks had replaced them; the
  three v3.1.0 captures stay historical (listed in `docs/README.md`, never in
  the README or the WebUI guide) and the Zabbix-filtered Delivery history
  capture stays unembedded behind its Synology replacement.
- 2 November 2026, independent review of that change (Jira NCE-109): the
  reviewers found the retired product name, its lab name or its bot name
  still readable in six of the restored cards and captures (the two UniFi
  Discord cards, the QNAP Teams card, the v1.9.6 Teams Xen Orchestra card,
  the two early Xen Orchestra cards and the Protect alarm list) and the crew
  administrator account name in the sidebar corner of the two restored
  Development captures. Those were masked the same day with the same tool and
  opened again at full size; the v3.1.0 Teams Xen Orchestra card was reopened
  at full size and needed no further mask. The rows below record the added
  masks.
- 2 November 2026, cycle 3 (Jira NCE-109): the independent privacy check of
  the 19 restored captures found no readable private value; it noted one
  trailing title glyph beside the mask of the v3.1.0 Discord Xen Orchestra
  card, which is now hidden as well. The follow-up review asked for the open
  point of the unembedded v1.9.6 Discord Xen Orchestra card to be decided: its
  bot name, backup job label and footer are hidden and the card stays as
  history. Both captures were opened at full size after masking. Two wording
  errors of this page were corrected: the Audit log capture is restored, not
  withdrawn, and a capture that still shows private information is masked
  with solid black boxes, never removed. No row was added or removed.

Seven captures are now excluded from current documentation. On 22 October
2026 the inventory held 105 retained rows, 90 of them linked from current
documents; the five Development captures added later that day brought it to 110
retained rows and 95 linked. On 23 October 2026 the Zabbix row was replaced by
the Synology row (still 110), the unembedded v1.9.6 Teams card was withdrawn
(109 retained rows, 95 linked) and the audit log capture was withdrawn (108
retained rows, 94 linked), and the three token captures were unlinked (108
retained rows, 91 linked). An earlier version of this paragraph gave 105 and
104 retained rows for those states; those numbers were wrong. On 30 October
2026 the seven sanitized copies were added (115 retained rows, 95 linked). On
2 November 2026 the eighteen restored captures were added back as retained
rows (133 retained rows, 104 linked). Counts in this page are dated
observations and the guard test, not this prose, is the authority.

- 12 November 2026: eight captures of `images/v27.0.0-rc.1/` were replaced by
  captures of the Development build `0011c903` after the delivery chart,
  Security page, Users and layout changes of pull requests 651 to 658 (the
  four Dashboard captures, Users, both Security captures and Filtering).
  Each was opened at full size before being added. The Users capture shows,
  in **Recent activity**, the account name of the Development deployment's
  administrator; two solid black boxes hide it. See the capture index for
  the build, viewports and accounts.

## Withdrawn captures

Paths below are relative to `docs/`. They are an exclusion record, not links.
A withdrawn path must not exist in the checkout, or may exist only as an empty
placeholder file left where the withdrawing tool could overwrite but not
delete it. `tests/test_screenshot_privacy_inventory.py` and
`tools/validate_current_documentation.py` fail on a withdrawn path with any
content and on any reference to a withdrawn path from a current document.

Withdrawn on 15 October 2026 and replaced by a sanitized copy on 30 October
2026 (the original pixels were never masked in place, so the original paths
stay withdrawn and the copies with the suffix `-sanitized` are the retained,
embedded files):

- `images/email-setup/mailboxes-healthy-redacted.png` — mailbox account label.
- `images/email-setup/noip-warning-redacted.png` — mailbox account label in activity.
- `images/hardware-setup/portainer-tls-config.png` — private bind address in Compose.
- `images/monitoring-setup/dell-native-delivery.png` — private source address in the message.
- `images/home-assistant-setup/enabled-automations.png` — personal device label in the sidebar.
- `images/home-assistant-setup/native-test.png` — personal device label in the sidebar.
- `images/home-assistant-setup/transport-response.png` — personal device label in the sidebar.

### Restored with masks on 2 November 2026

The eighteen other captures that had been withdrawn between 15 and 23 October
2026 were put back at their original paths on 2 November 2026 (Jira NCE-109),
restored from Git history byte for byte and then masked with solid black
rectangles where a private value remained; the exposure that had caused each
withdrawal is hidden. They are retained rows again, listed in the inventory
below with the date and a description of the mask. For the record, the
withdrawals they reverse were:

- 15 October 2026: the Protect alarm list (private camera/location labels),
  the Checkmk recipient (local recipient account name), the Metabase alert
  (personal collection label), the TrueNAS alert service (appliance hostname
  in the sidebar), the Xen Orchestra backup overview (deployment job labels)
  and the Portainer delivery lifecycle (visible profile portrait).
- 22 October 2026: the three v3.1.0 captures (user portrait beside the thread
  control; backup job name and partially masked repository and VM names;
  device-name prefix in a history row title). They had been overwritten with
  empty content because the crew's tools could not delete files.
- 23 October 2026: the Zabbix-filtered Delivery history capture (VM-numbered
  host and database labels), the v1.9.6 Teams Xen Orchestra card (unmasked
  repository and VM names) and the Audit log capture (user name of the
  Development administrator account and internal record identifiers). They
  had been overwritten with empty content the same way.
- 4 October 2026, earlier cleanup: six historical cards and pages that no
  guide embedded (the v1.9.6 UniFi Discord cards, the v1.9.6 QNAP Teams card,
  the two early Xen Orchestra cards and the v2.5.2 API access and routes
  pages) had been deleted outright; they are restored as unembedded history.

No empty placeholder remains in `docs/images/`. Git history before each
withdrawal date still contains the unmasked images; history was not rewritten.

The retained captures are listed in the inventory below with the date of their
last recorded inspection. Their dated validation results are historical
observations, not new acceptance or release claims. The v3.1.0 preview set is
explicitly historical; current written steps describe development. A filename
containing `redacted` is never proof of privacy.

## Re-check of 22 October 2026 (NCE-109)

A report of 22 October 2026 (Jira NCE-109) stated that the mailbox list, the
No-IP activity, the Portainer TLS Compose editor, the Dell delivery message and
the Home Assistant captures labelled redacted still exposed a mailbox label,
private addresses or a device label. Those are five of the thirteen captures
withdrawn on 15 October. The re-check confirmed on the `development` branch at
commit `eba8c95d39402639270e36153d13f8ff86ce7544`, and on `stage`, that none of
the thirteen files exists under `docs/images/` and that no current guide links
them; `tests/test_current_documentation_contract.py` enforced both at that
date. Since 2 November 2026 six of the thirteen exist again at their original
paths as masked copies (see "Restored with masks on 2 November 2026"); the
seven that have a sanitized copy stay withdrawn and the test still enforces
their absence. The `v3.1.6` tag and `main` predate the tutorial image folders
and do not contain them either.

The withdrawn files remain in Git history before their withdrawal date and in
any local checkout, fork or cached page made before that date. History was not
rewritten. A report based on such a copy describes the old state; pull the
current branch before reviewing captures.

The re-check run itself had no image tooling and opened no capture. The
independent review later the same day did open the retained captures and found
the three exposures withdrawn above, so the re-check's inventory was corrected
on 22 October. Apart from those three rows, the Record column still gives the
inspection dated 15 October 2026, or 21 October 2026 for the Development WebUI
set; no retained capture was re-inspected by the crew on 22 October. The JSON
and HTML validation records were scanned for private IPv4 addresses and
e-mail addresses on 22 October (none found) but were not re-read in full.

The inventory below lists every raster file in the checkout.
`tests/test_screenshot_privacy_inventory.py` fails when a raster is on disk,
or linked from a current guide, without a `retained` row here, when a
`retained` row has no file, when a withdrawn capture has content or is
referenced by a current document, and when a PNG or JPEG carries EXIF, XMP or
author, artist, creator or copyright text metadata.

## Open points for a person

The independent review of 22 October 2026 cleared two earlier open points:
the camera aliases in `images/unifi-setup/camera-names.png` are fully masked,
and the `images/portainer-setup/` set, the TrueNAS delivery capture and the
remaining Home Assistant delivery capture show no readable private label.

The items below were raised by that review as lower-severity or judgement
calls. The crew has not decided them; they need a person who can open the
images and apply the project's privacy policy. They are review items, not
confirmed exposures.

- Routing flow capture `images/v3.1.0-routing-flow.png` (no longer embedded by
  the README or the Docker Hub README since 24 October 2026; historical only):
  a Zabbix route filter subtitle may carry a residual host-name fragment.
  Decide whether to mask, recapture or withdraw.
- Decided on 2 November 2026: the delivery capture
  `images/hardware-setup/xen-orchestra-delivery.png` (embedded by the Xen
  Orchestra to Discord guide) showed a real backup job label in the Message
  body, which QA returned on 27 October 2026 (Jira NCE-109). The label is now
  masked; the capture stays embedded.
- Decided on 2 November 2026 (Jira NCE-109, cycle 3): the old card
  `images/discord-xen-orchestra-v1.9.6.png` (not embedded) showed a bot name,
  the backup job label in the title and the footer with the retired product
  name and an organisation fragment. Those three are now hidden by solid black
  boxes like the sibling cards; the card stays as unembedded history.
- Blurred captures `images/v2.5.2-settings.png`, `images/zabbix-setup/action-operations.png`,
  `images/zabbix-setup/media-enabled.png` and
  `images/zabbix-setup/recipient-media.png`: parts are blurred and the blurred
  text is unreadable, but blur is not a masking method this page accepts (see
  "Adding or replacing an image"). Decide whether to recapture.
- Decided on 25 October 2026 by the product owner (Jira TOPS-422): the
  `images/v27.0.0-rc.1/` set (embedded by the WebUI guide; since that day the
  README and Docker Hub README Preview embed its 1440 px Dashboard, Routing
  Flow, Destinations and sign-in captures). Its signed-in captures show the
  crew administrator account name, the typed generic owner labels
  `ITMANAGER`, `USER` and `CE-QA-20261015`, test destination and channel
  labels and a timezone. These generic test labels may appear in public
  documentation and are no reason to keep the desktop captures out of the
  Preview. The administrator username also appeared in the audit rows of the
  Audit log capture together with internal record identifiers; that capture
  was withdrawn then and was restored on 2 November 2026 with the user
  column, the record identifiers and the sidebar account name hidden by solid
  black boxes (see the inventory row). Any capture that shows a credential,
  token, private address or personal data stays excluded unless those values
  are hidden the same way.
  `tools/validate_current_documentation.py` and
  `tests/test_current_documentation_contract.py` enforce the list of captures
  the Preview may use.
- Token captures `images/hardware-setup/nowlert-token-list.png`,
  `images/hardware-setup/nowlert-token-scope.png` and
  `images/portainer-setup/token-scope.png`: not viewable by the crew (see
  "Validation records"); unlinked from every current document on 23 October
  2026; a person must open them before they are linked again.
- Every retained row shows only its last recorded inspection date. Re-open any
  capture whose date is considered too old, at full size, and update the
  Record column.

## Raster inventory

Paths are relative to `docs/`. The Record column gives the date of the last
recorded visual inspection of the file and is not a verification claim;
"unreviewed" means no inspection has been recorded for that file. Every
raster under `docs/images/` needs a row.

| Capture | Status | Record |
|---|---|---|
| `images/logo.png` | retained | product logo, not a capture |
| `images/discord-xen-orchestra-v1.9.6.png` | retained | historical card; not embedded; opened 22 Oct 2026; masked 2 Nov 2026, cycle 3 (the bot name in the header, the backup job label in the title and the footer that named the retired product and an organisation; the earlier masks of the repository and VM names kept); still shows the event type, severity, mode, duration, sizes, speeds, times and the version fragment of the footer |
| `images/discord-unifi-v1.9.6.png` | retained | historical cards; not embedded; restored from Git history and masked 2 Nov 2026 (camera label in the title, message and trigger device, drive label in the title and system line; after the independent review the same day also the alarm rule name and both footers that named the retired product and its lab); still shows event types, severities and times |
| `images/teams-qnap-v1.9.6.png` | retained | historical card; not embedded; restored from Git history and masked 2 Nov 2026 (NAS label in the title, the sender name line and the avatar; after the independent review also the footer that named the retired product and its lab); still shows the firmware versions |
| `images/teams-xen-orchestra-v1.9.6.png` | retained | historical card; not embedded; restored from Git history and masked 2 Nov 2026 (job name in the title, repository and the VM name; the earlier partial masks kept; after the independent review also the footer fragment that named the retired product); still shows the result count and times |
| `images/xo-discord.png` | retained | historical card; not embedded; restored from Git history and masked 2 Nov 2026 (job name, repository and the three VM names; after the independent review also the bot name in the header and the footer that named the retired product and its lab); still shows mode, duration, sizes and speeds |
| `images/xo-teams.png` | retained | historical card; not embedded; restored from Git history and masked 2 Nov 2026 (job name, repository and the two VM names; after the independent review also the footer that named the retired product and its lab); still shows mode, duration, sizes, speeds and times |
| `images/v2.5.2-api-access.png` | retained | historical v2.5.2 capture; not embedded; restored from Git history unchanged 2 Nov 2026 (token names and rate limits only, no token value) |
| `images/v2.5.2-destinations.png` | retained | historical v2.5.2 capture; not embedded; opened 23 Oct 2026 |
| `images/v2.5.2-discord-idrac.png` | retained | historical v2.5.2 capture embedded by the Dell iDRAC guide as outdated; reviewed 15 Oct 2026 |
| `images/v2.5.2-discord-zabbix.png` | retained | historical v2.5.2 capture; not embedded; opened 23 Oct 2026 |
| `images/v2.5.2-inputs.png` | retained | historical v2.5.2 capture; not embedded; opened 23 Oct 2026; bind address `0.0.0.0` only |
| `images/v2.5.2-overview.png` | retained | historical v2.5.2 capture; not embedded; opened 23 Oct 2026 |
| `images/v2.5.2-routes.png` | retained | historical v2.5.2 capture; not embedded; restored from Git history and masked 2 Nov 2026 (host filter text of one route); still shows route names, integrations, inputs and status |
| `images/v2.5.2-routing-flow.png` | retained | historical v2.5.2 capture; not embedded; opened 23 Oct 2026 |
| `images/v2.5.2-settings.png` | retained | historical v2.5.2 capture; not embedded; opened 23 Oct 2026; open point above |
| `images/v2.5.2-sources.png` | retained | historical v2.5.2 capture; not embedded; opened 23 Oct 2026 |
| `images/v2.5.2-teams.png` | retained | historical v2.5.2 capture; not embedded; opened 23 Oct 2026 |
| `images/v3.1.0-dashboard.png` | retained | historical v3.1.0 capture; reviewed 15 Oct 2026 |
| `images/v3.1.0-destinations.png` | retained | historical v3.1.0 capture; reviewed 15 Oct 2026 |
| `images/v3.1.0-delivery-history.png` | retained | historical v3.1.0 capture; not embedded; restored from Git history and masked 3 Nov 2026 with five small black boxes over the private values only (the camera name in two row messages, the gateway name in one row title and its location line, and a device and person name in one row message; the earlier large mask was removed); still shows the page header, titles, sources, outcome chips, attempt and transport chips and times |
| `images/v3.1.0-discord-idrac.png` | retained | historical v3.1.0 capture; not embedded; opened 23 Oct 2026 |
| `images/v3.1.0-discord-unifi.png` | retained | historical v3.1.0 capture; not embedded; opened 23 Oct 2026 |
| `images/v3.1.0-discord-xen-orchestra.png` | retained | historical v3.1.0 card embedded by the Xen Orchestra to Discord guide as historical; restored from Git history and masked 2 Nov 2026 (job name in the title and message, repository and the two VM names; the earlier partial masks kept; on 2 Nov 2026, cycle 3, also the trailing title glyph that was left beside the title mask); still shows mode, duration, sizes, speeds, times and the product footer |
| `images/v3.1.0-routing-flow.png` | retained | historical v3.1.0 capture; reviewed 15 Oct 2026; open point above |
| `images/v3.1.0-teams-xen-orchestra.png` | retained | historical v3.1.0 card embedded by the Xen Orchestra to Teams guide as historical; restored from Git history and masked 2 Nov 2026 (user portrait beside the thread control; the earlier sender-name mask kept); still shows the test alert text, severity, category and the product footer |
| `images/application-setup/checkmk-all-events.jpg` | retained | reviewed 15 Oct 2026 |
| `images/application-setup/checkmk-sending-conditions.jpg` | retained | reviewed 15 Oct 2026 |
| `images/application-setup/checkmk-single-recipient.png` | retained | restored from Git history and masked 2 Nov 2026 (the recipient account selector); still shows the rule editor, the Nowlert method and the auto-generated parameter label |
| `images/application-setup/metabase-delivery-alert.jpg` | retained | restored from Git history and masked 2 Nov 2026 (the collection label in the header); still shows the question title, the database label, the SQL text and the Edit alerts dialog |
| `images/application-setup/metabase-native-question-delivered.png` | retained | reviewed 15 Oct 2026 |
| `images/application-setup/metabase-webhook.png` | retained | reviewed 15 Oct 2026; no token value |
| `images/application-setup/radarr-all-events.jpg` | retained | reviewed 15 Oct 2026 |
| `images/application-setup/semaphore-native-test.png` | retained | reviewed 15 Oct 2026 |
| `images/application-setup/sonarr-all-events.png` | retained | reviewed 15 Oct 2026 |
| `images/email-setup/gmail-api-enabled.jpg` | retained | reviewed 15 Oct 2026; opened 30 Oct 2026; account header excluded |
| `images/email-setup/mailboxes-healthy-sanitized.png` | retained | sanitized copy made and opened 30 Oct 2026; both account labels masked |
| `images/email-setup/microsoft-mail-read-redacted.png` | retained | reviewed 15 Oct 2026; opened 30 Oct 2026; signed-in address concealed |
| `images/email-setup/noip-warning-activity-sanitized.png` | retained | sanitized copy made and opened 30 Oct 2026; search text, hostname, sender line and mailbox label masked |
| `images/hardware-setup/dell-subscription-record.png` | retained | rendered token-free API readback with RFC 5737 addresses; reviewed 15 and 21 Oct 2026 |
| `images/hardware-setup/hpe-native-image-delivery.png` | retained | reviewed 15 Oct 2026 |
| `images/hardware-setup/hpe-subscription-record.png` | retained | rendered token-free API readback with RFC 5737 addresses; reviewed 15 and 21 Oct 2026 |
| `images/hardware-setup/ilo-resource-filter-proof.png` | retained | reviewed 15 Oct 2026 |
| `images/hardware-setup/ilo-resource-filter.png` | retained | reviewed 15 Oct 2026 |
| `images/hardware-setup/nowlert-destinations.png` | retained | reviewed 15 Oct 2026 |
| `images/hardware-setup/nowlert-hardware-destination.png` | retained | reviewed 15 Oct 2026; stored webhook hidden |
| `images/hardware-setup/nowlert-hardware-routes.png` | retained | reviewed 15 Oct 2026 |
| `images/hardware-setup/nowlert-token-list.png` | retained | reviewed 15 and 21 Oct 2026 (token value hidden); not viewable by the crew on 22 Oct 2026, needs a person; unlinked 23 Oct 2026 |
| `images/hardware-setup/nowlert-token-scope.png` | retained | reviewed 15 and 21 Oct 2026 (pre-issuance scope form); not viewable by the crew on 22 Oct 2026, needs a person; unlinked 23 Oct 2026 |
| `images/hardware-setup/nowlert-xen-destination.png` | retained | reviewed 15 Oct 2026 |
| `images/hardware-setup/nowlert-xen-routes.png` | retained | reviewed 15 Oct 2026 |
| `images/hardware-setup/portainer-hpe-callback.png` | retained | reviewed 15 Oct 2026 |
| `images/hardware-setup/portainer-stack-running.png` | retained | reviewed 15 Oct 2026; opened 30 Oct 2026 |
| `images/hardware-setup/portainer-tls-config-sanitized.png` | retained | sanitized copy made and opened 30 Oct 2026; bind address, default SNI and site address masked |
| `images/hardware-setup/portainer-tls-forwarding.png` | retained | reviewed 15 Oct 2026; opened 30 Oct 2026 |
| `images/hardware-setup/supermicro-subscription-record.png` | retained | rendered token-free API readback with RFC 5737 addresses; reviewed 15 and 21 Oct 2026 |
| `images/hardware-setup/xen-orchestra-backup-reports.png` | retained | reviewed 15 Oct 2026 |
| `images/hardware-setup/xen-orchestra-backup-test.png` | retained | reviewed 15 Oct 2026 |
| `images/hardware-setup/xen-orchestra-delivery.png` | retained | reviewed 15 Oct 2026; masked 2 Nov 2026 after the QA return of 27 Oct 2026 (the backup job label line of the Message body); still shows the truncated row titles, the SMTP input, the Operational destination, HTTP 200 and the timeline |
| `images/hardware-setup/xen-orchestra-transport-auth.png` | retained | reviewed 15 Oct 2026 |
| `images/hardware-setup/xen-orchestra-transport-email.png` | retained | reviewed 15 Oct 2026 |
| `images/home-assistant-setup/enabled-automations-sanitized.png` | retained | sanitized copy made and opened 30 Oct 2026; personal dashboard label in the sidebar masked |
| `images/home-assistant-setup/native-delivery-proof.png` | retained | reviewed 15 Oct 2026; opened 30 Oct 2026 |
| `images/home-assistant-setup/native-test-sanitized.png` | retained | sanitized copy made and opened 30 Oct 2026; personal dashboard label in the sidebar masked |
| `images/home-assistant-setup/transport-response-sanitized.png` | retained | sanitized copy made and opened 30 Oct 2026; personal dashboard label in the sidebar masked |
| `images/monitoring-setup/dell-native-delivery-sanitized.png` | retained | sanitized copy made and opened 30 Oct 2026; controller address masked in the message, list row and detail pane |
| `images/monitoring-setup/drive-backup-trigger-catalogue.png` | retained | reviewed 15 Oct 2026; opened 30 Oct 2026; console details concealed |
| `images/monitoring-setup/drive-native-delivery.png` | retained | reviewed 15 Oct 2026 |
| `images/monitoring-setup/drive-native-test-share.png` | retained | reviewed 15 Oct 2026 |
| `images/monitoring-setup/grafana-contact.png` | retained | reviewed 15 Oct 2026 |
| `images/monitoring-setup/grafana-native-test.png` | retained | reviewed 15 Oct 2026 |
| `images/monitoring-setup/native-rule-delivery-readback.png` | retained | reviewed 15 Oct 2026 |
| `images/monitoring-setup/portainer-native-active-alert.png` | retained | reviewed 15 Oct 2026 |
| `images/monitoring-setup/portainer-native-delivery-lifecycle.png` | retained | restored from Git history and masked 2 Nov 2026 (the account corner of the sidebar with the profile portrait); still shows the Portainer rows with the loopback address, the simulated callbacks and the detail pane |
| `images/monitoring-setup/portainer-threshold-restored-new.png` | retained | reviewed 15 Oct 2026 |
| `images/monitoring-setup/supermicro-native-delivery.png` | retained | reviewed 15 Oct 2026 |
| `images/monitoring-setup/supermicro-native-test-pair.png` | retained | reviewed 15 Oct 2026 |
| `images/portainer-setup/alert-manager-enabled.png` | retained | reviewed 15 Oct 2026 |
| `images/portainer-setup/all-rules-enabled.png` | retained | reviewed 15 Oct 2026 |
| `images/portainer-setup/ilo-expanded-event-delivery.png` | retained | reviewed 15 Oct 2026 |
| `images/portainer-setup/node-rule-enabled.png` | retained | reviewed 15 Oct 2026 |
| `images/portainer-setup/receiver-routing-proof.png` | retained | reviewed 15 Oct 2026 |
| `images/portainer-setup/route-assignment.png` | retained | reviewed 15 Oct 2026 |
| `images/portainer-setup/token-scope.png` | retained | reviewed 15 and 21 Oct 2026 (pre-issuance scope form); not viewable by the crew on 22 Oct 2026, needs a person; unlinked 23 Oct 2026 |
| `images/portainer-setup/webhook-channel.png` | retained | reviewed 15 Oct 2026 |
| `images/portainer-setup/xen-backup-report-coverage.png` | retained | restored from Git history and masked 2 Nov 2026 (the three job names and identifiers that the earlier large mask left visible); still shows modes, schedule names, states and Report when values |
| `images/truenas-setup/delivery-proof.png` | retained | reviewed 15 Oct 2026 |
| `images/truenas-setup/info-alert-service.png` | retained | restored from Git history and masked 2 Nov 2026 (the appliance hostname above the edition label in the sidebar; the earlier masks of the recipient field and header kept); still shows the alert service list and the Edit Alert Service form |
| `images/unifi-setup/camera-names.png` | retained | reviewed 15 Oct 2026; aliases confirmed fully masked 22 Oct 2026 |
| `images/unifi-setup/drive-alarms.png` | retained | reviewed 15 Oct 2026 |
| `images/unifi-setup/drive-receiver-delivery.png` | retained | reviewed 15 Oct 2026 |
| `images/unifi-setup/network-alarms.png` | retained | reviewed 15 Oct 2026; labelled outdated pending recapture |
| `images/unifi-setup/network-delivery.png` | retained | reviewed 15 Oct 2026 |
| `images/unifi-setup/protect-alarms.png` | retained | restored from Git history and masked 2 Nov 2026 (the three alarm names that carried a location label; after the independent review the same day also the four alarm names that carried the retired product name); still shows the Nowlert alarm rows, categories, actions, hit counts and the detail panel |
| `images/unifi-setup/protect-delivery.png` | retained | reviewed 15 Oct 2026 |
| `images/unifi-setup/protect-noise-filter.png` | retained | reviewed 15 Oct 2026 |
| `images/v27.0.0-rc.1/audit-log-overview-admin-1440.png` | retained | Development capture, 21 Oct 2026; restored from Git history and masked 2 Nov 2026 (the user column of the event list, the record identifier under each resource and, after the independent review the same day, the account name in the sidebar corner); still shows the health checks, counters, action and resource names and the selected event; embedded by the WebUI guide |
| `images/v27.0.0-rc.1/dashboard-live-admin-1440.png` | retained | Development capture, 12 Nov 2026 (replaces the capture of 21 Oct 2026); opened at full size 12 Nov 2026; crew administrator, synthetic test events; README and Docker Hub Preview |
| `images/v27.0.0-rc.1/dashboard-live-admin-390.png` | retained | Development capture, 12 Nov 2026 (replaces the capture of 21 Oct 2026); opened at full size 12 Nov 2026, no account, owner, destination or channel name; responsive-layout example in the WebUI guide |
| `images/v27.0.0-rc.1/dashboard-live-admin-768.png` | retained | Development capture, 12 Nov 2026 (replaces the capture of 21 Oct 2026); opened at full size 12 Nov 2026 |
| `images/v27.0.0-rc.1/dashboard-live-user-1440.png` | retained | Development capture, 12 Nov 2026 (replaces the capture of 21 Oct 2026); opened at full size 12 Nov 2026; crew user account |
| `images/v27.0.0-rc.1/delivery-history-synology-admin-1440.png` | retained | Development capture, 23 Oct 2026; test fixture device `synthetic-dsm-01` only |
| `images/v27.0.0-rc.1/delivery-history-zabbix-admin-1440.png` | retained | Development capture, 21 Oct 2026; restored from Git history and masked 2 Nov 2026 (the row title, the detail header, the whole message body and, after the independent review the same day, the account name in the sidebar corner); still shows the Zabbix filter, badges, transport information and timeline; not embedded, the Synology capture is the reference |
| `images/v27.0.0-rc.1/destination-editor-teams-admin-1440.png` | retained | Development capture, 21 Oct 2026 |
| `images/v27.0.0-rc.1/destination-preview-teams-classic-admin-1440.png` | retained | Development capture, 21 Oct 2026 |
| `images/v27.0.0-rc.1/destination-preview-teams-modern-admin-1440.png` | retained | Development capture, 21 Oct 2026 |
| `images/v27.0.0-rc.1/destination-preview-routes-drawer-admin-1440.png` | retained | Development capture, 22 Oct 2026 |
| `images/v27.0.0-rc.1/destination-preview-discord-debug-admin-1440.png` | retained | Development capture, 22 Oct 2026 |
| `images/v27.0.0-rc.1/destinations-list-admin-1440.png` | retained | Development capture, 21 Oct 2026; opened at full size 25 Oct 2026; README and Docker Hub Preview |
| `images/v27.0.0-rc.1/destinations-list-admin-390.png` | retained | Development capture, 21 Oct 2026 |
| `images/v27.0.0-rc.1/destinations-list-admin-768.png` | retained | Development capture, 21 Oct 2026 |
| `images/v27.0.0-rc.1/destinations-list-user-1440.png` | retained | Development capture, 21 Oct 2026 |
| `images/v27.0.0-rc.1/email-alerts-groups-admin-1440.png` | retained | Development capture, 21 Oct 2026 |
| `images/v27.0.0-rc.1/email-alerts-rules-admin-1440.png` | retained | Development capture, 21 Oct 2026 |
| `images/v27.0.0-rc.1/email-alerts-rules-admin-768.png` | retained | Development capture, 22 Oct 2026 |
| `images/v27.0.0-rc.1/email-alerts-rules-admin-390.png` | retained | Development capture, 22 Oct 2026 |
| `images/v27.0.0-rc.1/email-alerts-mailbox-edit-imap-admin-1440.png` | retained | Development capture, 22 Oct 2026; fixture address and loopback host only |
| `images/v27.0.0-rc.1/filtering-list-admin-1440.png` | retained | Development capture, 12 Nov 2026 (replaces the capture of 31 Oct 2026); shared crew test destinations, their filter names and badges, Integration behavior cards with zero aliases |
| `images/v27.0.0-rc.1/routing-flow-live-admin-1440.png` | retained | Development capture, 21 Oct 2026; opened at full size 25 Oct 2026; README and Docker Hub Preview |
| `images/v27.0.0-rc.1/routing-flow-live-admin-390.png` | retained | Development capture, 21 Oct 2026; opened 24 Oct 2026, no account, owner, destination or channel name; responsive-layout example in the WebUI guide |
| `images/v27.0.0-rc.1/routing-flow-live-admin-768.png` | retained | Development capture, 21 Oct 2026 |
| `images/v27.0.0-rc.1/security-profile-admin-1440.png` | retained | Development capture, 12 Nov 2026 (replaces the capture of 31 Oct 2026); crew administrator account, empty token list, no token value |
| `images/v27.0.0-rc.1/security-profile-user-1440.png` | retained | Development capture, 12 Nov 2026 (replaces the capture of 31 Oct 2026); crew user account, empty token list, no token value |
| `images/v27.0.0-rc.1/settings-regional-admin-1440.png` | retained | Development capture, 31 Oct 2026 (replaces the capture of 21 Oct 2026); Development settings values only |
| `images/v27.0.0-rc.1/sign-in-empty-signed-out-1440.png` | retained | Development capture, 21 Oct 2026; opened at full size 25 Oct 2026; README and Docker Hub Preview |
| `images/v27.0.0-rc.1/sign-in-empty-signed-out-390.png` | retained | Development capture, 21 Oct 2026; opened 24 Oct 2026, no account, owner, destination or channel name; not embedded since 25 Oct 2026 |
| `images/v27.0.0-rc.1/sign-in-empty-signed-out-768.png` | retained | Development capture, 21 Oct 2026 |
| `images/v27.0.0-rc.1/users-search-admin-1440.png` | retained | Development capture, 12 Nov 2026 (replaces the capture of 21 Oct 2026); opened at full size 12 Nov 2026; crew accounts only; two black boxes hide the Development administrator's account name in Recent activity |
| `images/zabbix-setup/action-operations.png` | retained | reviewed 15 Oct 2026 |
| `images/zabbix-setup/media-enabled.png` | retained | reviewed 15 Oct 2026 |
| `images/zabbix-setup/native-recovery-accepted.png` | retained | reviewed 15 Oct 2026 |
| `images/zabbix-setup/native-problem-accepted.png` | retained | reviewed 15 Oct 2026 |
| `images/zabbix-setup/recipient-media.png` | retained | reviewed 15 Oct 2026 |

## Validation records

The JSON and HTML readback records under `images/hardware-setup/records/` and
`images/monitoring-setup/records/` were re-checked on 21 October 2026. Every
address in them is an RFC 5737 documentation address (192.0.2.0/24); the
subscription identifiers and controller contexts are synthetic, and no
authentication value is present. Keep that convention when adding a record,
and never paste a real controller, relay or receiver address into one.

The three packaged captures whose file names mention tokens
(`images/hardware-setup/nowlert-token-list.png`,
`images/hardware-setup/nowlert-token-scope.png` and
`images/portainer-setup/token-scope.png`) have an inspection recorded on
21 October 2026 describing a token name, the issued token list with the value
hidden, or the pre-issuance scope form, and no token value. The independent
review of 22 October 2026 could not open these three files: the crew's run
refused to read them because of their file names, and that rule was not
bypassed. The 21 October record is therefore unconfirmed by that review, and
a person must open the three files and update their rows. Since 23 October
2026 no current document embeds or links them; the guides describe the token
dialog and the token list in writing. A file name that mentions a token is
not, by itself, evidence of a leak; inspect the image.

## Adding or replacing an image

1. Prefer a fresh capture made with the Development test accounts, whose names
   are typed usernames rather than personal names, test device names and
   documentation addresses such as `192.0.2.0/24`; keep raw captures outside
   the repository.
2. Inspect the full image at readable size, including account chrome, sidebars,
   message previews, URLs, logs, personal folders and profile pictures.
3. If private information remains, hide it with solid black boxes (the crew's
   redaction tool paints them and changes nothing else) and keep the image;
   never remove or empty it, because the tutorials depend on it. Reopen the
   result at full size and confirm that no value is still readable. Do not
   rely on blur, on a partial mask that leaves part of a value readable or on
   a hidden password input. Say in the inventory row what the boxes hide.
4. Label synthetic receiver tests, native source tests and API readbacks
   accurately. An image does not establish an untested lifecycle or release.
5. Export without metadata: no EXIF segment, no XMP packet and no author,
   artist, creator or copyright text chunk. The inventory test rejects all of
   them.
6. Add a `retained` row for the file to the inventory above with the review
   date, or a withdrawn bullet when a file is removed. The inventory test
   fails on a raster without a row.
7. Recheck the final exported file and every reference before publication.

This change does not rewrite Git history or remove old release artifacts,
cached copies, or previously published images. No new capture or release is
claimed accepted by this documentation check.
