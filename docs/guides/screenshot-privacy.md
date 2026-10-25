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

Nineteen captures are now excluded from current documentation. On 22 October
2026 the inventory held 105 retained rows, 90 of them linked from current
documents; the five Development captures added later that day brought it to 110
retained rows and 95 linked. On 23 October 2026 the Zabbix row was replaced by
the Synology row (still 110), the unembedded v1.9.6 Teams card was withdrawn
(109 retained rows, 95 linked) and the audit log capture was withdrawn (108
retained rows, 94 linked), and the three token captures were unlinked (108
retained rows, 91 linked). An earlier version of this paragraph gave 105 and
104 retained rows for those states; those numbers were wrong. Counts in this
page are dated observations and the guard test, not this prose, is the
authority.

## Withdrawn captures

Paths below are relative to `docs/`. They are an exclusion record, not links.
A withdrawn path must not exist in the checkout, or may exist only as an empty
placeholder file left where the withdrawing tool could overwrite but not
delete it. `tests/test_screenshot_privacy_inventory.py` and
`tools/validate_current_documentation.py` fail on a withdrawn path with any
content and on any reference to a withdrawn path from a current document.

Withdrawn on 15 October 2026:

- `images/unifi-setup/protect-alarms.png` — private camera/location labels.
- `images/email-setup/mailboxes-healthy-redacted.png` — mailbox account label.
- `images/email-setup/noip-warning-redacted.png` — mailbox account label in activity.
- `images/hardware-setup/portainer-tls-config.png` — private bind address in Compose.
- `images/monitoring-setup/dell-native-delivery.png` — private source address in the message.
- `images/home-assistant-setup/enabled-automations.png` — personal device label in the sidebar.
- `images/home-assistant-setup/native-test.png` — personal device label in the sidebar.
- `images/home-assistant-setup/transport-response.png` — personal device label in the sidebar.
- `images/application-setup/checkmk-single-recipient.png` — local recipient account name.
- `images/application-setup/metabase-delivery-alert.jpg` — personal collection/account label.
- `images/truenas-setup/info-alert-service.png` — appliance hostname in the sidebar.
- `images/portainer-setup/xen-backup-report-coverage.png` — deployment job labels and schedules.
- `images/monitoring-setup/portainer-native-delivery-lifecycle.png` — visible profile portrait.

Withdrawn on 22 October 2026, after the independent review of the inventory
(each had a row recording an inspection on 15 October 2026 and was embedded by
the README or a guide; none is embedded any longer):

- `images/v3.1.0-teams-xen-orchestra.png` — user portrait beside the thread control.
- `images/v3.1.0-discord-xen-orchestra.png` — backup job name, and repository and VM names only partially masked.
- `images/v3.1.0-delivery-history.png` — device-name prefix in a history row title.

The crew's repository tools can create and overwrite files but cannot delete
them, so on 22 October 2026 these three files were overwritten with empty
content to remove their pixels from the branch. A person with delete access
should remove the three empty placeholders; until then the guard accepts them
only while they stay empty.

Withdrawn on 23 October 2026, after the P1 privacy re-check (Jira TOPS-351).
The first was embedded by the WebUI guide and is now replaced there by the
Synology-filtered capture listed in the inventory; the second was not
embedded anywhere:

- `images/v27.0.0-rc.1/delivery-history-zabbix-admin-1440.png` — VM-numbered host and database labels (`VM-08 | Zabbix Server`, `DB-01`, `DB-REPLICA`) in the sample rows and message.
- `images/teams-xen-orchestra-v1.9.6.png` — unmasked backup repository and VM names (`NAS-01 / Critical Backups`, `APP-01`).

They were overwritten with empty content the same way; a person with delete
access should remove the empty placeholders. Git history before each
withdrawal date still contains the images, as it does for the 15 October
withdrawals.

Withdrawn on 23 October 2026, after the independent test of that change (Jira
TOPS-356). It was embedded by the WebUI guide, which now describes the page in
writing:

- `images/v27.0.0-rc.1/audit-log-overview-admin-1440.png` — user name of the Development deployment's administrator account, which is not one of the crew test accounts, and truncated internal record identifiers in the audit rows.

It was overwritten with empty content the same way, so the number of empty
placeholders awaiting deletion by a person is now six.

The two empty placeholders in `images/v27.0.0-rc.1/`,
`audit-log-overview-admin-1440.png` and
`delivery-history-zabbix-admin-1440.png`, are zero-byte files: no current
document links them, and they are not part of the published documentation
packages.

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
them; `tests/test_current_documentation_contract.py` enforces both. The
`v3.1.6` tag and `main` predate the tutorial image folders and do not contain
them either.

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
- Delivery capture `images/hardware-setup/xen-orchestra-delivery.png` (embedded by the Xen
  Orchestra to Discord guide): shows a backup job label that may be a real job
  name. Decide whether it is acceptable.
- Old card `images/discord-xen-orchestra-v1.9.6.png` (not embedded): the card footer
  shows a bot name and an organisation fragment. Decide whether to keep it as
  unembedded history or withdraw it.
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
  stays withdrawn. Any capture that shows a credential, token, private
  address or personal data stays excluded.
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
| `images/discord-xen-orchestra-v1.9.6.png` | retained | historical card with the retired product name; not embedded; opened 22 Oct 2026, open point above |
| `images/v2.5.2-destinations.png` | retained | historical v2.5.2 capture; not embedded; opened 23 Oct 2026 |
| `images/v2.5.2-discord-idrac.png` | retained | historical v2.5.2 capture embedded by the Dell iDRAC guide as outdated; reviewed 15 Oct 2026 |
| `images/v2.5.2-discord-zabbix.png` | retained | historical v2.5.2 capture; not embedded; opened 23 Oct 2026 |
| `images/v2.5.2-inputs.png` | retained | historical v2.5.2 capture; not embedded; opened 23 Oct 2026; bind address `0.0.0.0` only |
| `images/v2.5.2-overview.png` | retained | historical v2.5.2 capture; not embedded; opened 23 Oct 2026 |
| `images/v2.5.2-routing-flow.png` | retained | historical v2.5.2 capture; not embedded; opened 23 Oct 2026 |
| `images/v2.5.2-settings.png` | retained | historical v2.5.2 capture; not embedded; opened 23 Oct 2026; open point above |
| `images/v2.5.2-sources.png` | retained | historical v2.5.2 capture; not embedded; opened 23 Oct 2026 |
| `images/v2.5.2-teams.png` | retained | historical v2.5.2 capture; not embedded; opened 23 Oct 2026 |
| `images/v3.1.0-dashboard.png` | retained | historical v3.1.0 capture; reviewed 15 Oct 2026 |
| `images/v3.1.0-destinations.png` | retained | historical v3.1.0 capture; reviewed 15 Oct 2026 |
| `images/v3.1.0-discord-idrac.png` | retained | historical v3.1.0 capture; not embedded; opened 23 Oct 2026 |
| `images/v3.1.0-discord-unifi.png` | retained | historical v3.1.0 capture; not embedded; opened 23 Oct 2026 |
| `images/v3.1.0-routing-flow.png` | retained | historical v3.1.0 capture; reviewed 15 Oct 2026; open point above |
| `images/application-setup/checkmk-all-events.jpg` | retained | reviewed 15 Oct 2026 |
| `images/application-setup/checkmk-sending-conditions.jpg` | retained | reviewed 15 Oct 2026 |
| `images/application-setup/metabase-native-question-delivered.png` | retained | reviewed 15 Oct 2026 |
| `images/application-setup/metabase-webhook.png` | retained | reviewed 15 Oct 2026; no token value |
| `images/application-setup/radarr-all-events.jpg` | retained | reviewed 15 Oct 2026 |
| `images/application-setup/semaphore-native-test.png` | retained | reviewed 15 Oct 2026 |
| `images/application-setup/sonarr-all-events.png` | retained | reviewed 15 Oct 2026 |
| `images/email-setup/gmail-api-enabled.jpg` | retained | reviewed 15 Oct 2026; account header excluded |
| `images/email-setup/microsoft-mail-read-redacted.png` | retained | reviewed 15 Oct 2026; signed-in address concealed |
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
| `images/hardware-setup/portainer-stack-running.png` | retained | reviewed 15 Oct 2026 |
| `images/hardware-setup/portainer-tls-forwarding.png` | retained | reviewed 15 Oct 2026 |
| `images/hardware-setup/supermicro-subscription-record.png` | retained | rendered token-free API readback with RFC 5737 addresses; reviewed 15 and 21 Oct 2026 |
| `images/hardware-setup/xen-orchestra-backup-reports.png` | retained | reviewed 15 Oct 2026 |
| `images/hardware-setup/xen-orchestra-backup-test.png` | retained | reviewed 15 Oct 2026 |
| `images/hardware-setup/xen-orchestra-delivery.png` | retained | reviewed 15 Oct 2026; open point above |
| `images/hardware-setup/xen-orchestra-transport-auth.png` | retained | reviewed 15 Oct 2026 |
| `images/hardware-setup/xen-orchestra-transport-email.png` | retained | reviewed 15 Oct 2026 |
| `images/home-assistant-setup/native-delivery-proof.png` | retained | reviewed 15 Oct 2026 |
| `images/monitoring-setup/drive-backup-trigger-catalogue.png` | retained | reviewed 15 Oct 2026; console details concealed |
| `images/monitoring-setup/drive-native-delivery.png` | retained | reviewed 15 Oct 2026 |
| `images/monitoring-setup/drive-native-test-share.png` | retained | reviewed 15 Oct 2026 |
| `images/monitoring-setup/grafana-contact.png` | retained | reviewed 15 Oct 2026 |
| `images/monitoring-setup/grafana-native-test.png` | retained | reviewed 15 Oct 2026 |
| `images/monitoring-setup/native-rule-delivery-readback.png` | retained | reviewed 15 Oct 2026 |
| `images/monitoring-setup/portainer-native-active-alert.png` | retained | reviewed 15 Oct 2026 |
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
| `images/truenas-setup/delivery-proof.png` | retained | reviewed 15 Oct 2026 |
| `images/unifi-setup/camera-names.png` | retained | reviewed 15 Oct 2026; aliases confirmed fully masked 22 Oct 2026 |
| `images/unifi-setup/drive-alarms.png` | retained | reviewed 15 Oct 2026 |
| `images/unifi-setup/drive-receiver-delivery.png` | retained | reviewed 15 Oct 2026 |
| `images/unifi-setup/network-alarms.png` | retained | reviewed 15 Oct 2026; labelled outdated pending recapture |
| `images/unifi-setup/network-delivery.png` | retained | reviewed 15 Oct 2026 |
| `images/unifi-setup/protect-delivery.png` | retained | reviewed 15 Oct 2026 |
| `images/unifi-setup/protect-noise-filter.png` | retained | reviewed 15 Oct 2026 |
| `images/v27.0.0-rc.1/dashboard-live-admin-1440.png` | retained | Development capture, 21 Oct 2026; opened at full size 25 Oct 2026; README and Docker Hub Preview |
| `images/v27.0.0-rc.1/dashboard-live-admin-390.png` | retained | Development capture, 21 Oct 2026; opened 24 Oct 2026, no account, owner, destination or channel name; responsive-layout example in the WebUI guide |
| `images/v27.0.0-rc.1/dashboard-live-admin-768.png` | retained | Development capture, 21 Oct 2026 |
| `images/v27.0.0-rc.1/dashboard-live-user-1440.png` | retained | Development capture, 21 Oct 2026 |
| `images/v27.0.0-rc.1/delivery-history-synology-admin-1440.png` | retained | Development capture, 23 Oct 2026; test fixture device `synthetic-dsm-01` only |
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
| `images/v27.0.0-rc.1/filtering-list-admin-1440.png` | retained | Development capture, 21 Oct 2026 |
| `images/v27.0.0-rc.1/routing-flow-live-admin-1440.png` | retained | Development capture, 21 Oct 2026; opened at full size 25 Oct 2026; README and Docker Hub Preview |
| `images/v27.0.0-rc.1/routing-flow-live-admin-390.png` | retained | Development capture, 21 Oct 2026; opened 24 Oct 2026, no account, owner, destination or channel name; responsive-layout example in the WebUI guide |
| `images/v27.0.0-rc.1/routing-flow-live-admin-768.png` | retained | Development capture, 21 Oct 2026 |
| `images/v27.0.0-rc.1/security-profile-admin-1440.png` | retained | Development capture, 21 Oct 2026 |
| `images/v27.0.0-rc.1/security-profile-user-1440.png` | retained | Development capture, 21 Oct 2026 |
| `images/v27.0.0-rc.1/settings-regional-admin-1440.png` | retained | Development capture, 21 Oct 2026 |
| `images/v27.0.0-rc.1/sign-in-empty-signed-out-1440.png` | retained | Development capture, 21 Oct 2026; opened at full size 25 Oct 2026; README and Docker Hub Preview |
| `images/v27.0.0-rc.1/sign-in-empty-signed-out-390.png` | retained | Development capture, 21 Oct 2026; opened 24 Oct 2026, no account, owner, destination or channel name; not embedded since 25 Oct 2026 |
| `images/v27.0.0-rc.1/sign-in-empty-signed-out-768.png` | retained | Development capture, 21 Oct 2026 |
| `images/v27.0.0-rc.1/users-search-admin-1440.png` | retained | Development capture, 21 Oct 2026 |
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
3. If private information remains, omit the image and supply written steps.
   Do not rely on blur, partial masks or a hidden password input.
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
