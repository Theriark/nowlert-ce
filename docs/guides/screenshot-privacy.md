# Screenshot privacy review

On 15 October 2026, the 82 raster captures linked from current documentation
were visually inspected, including sidebars, account labels, message bodies,
configuration editors and browser chrome. The earlier blanket claim that all
captures were sanitized was incorrect. Twelve captures with remaining private
details were withdrawn from the current checkout and all current guide links.
The affected guides now provide written verification steps instead.

A fresh independent review of all 70 retained linked raster captures later on
15 October found one further Protect capture with custom camera/location labels.
That capture was also withdrawn and replaced with written checks, leaving 69
linked rasters. Thirteen captures are now excluded from the current checkout.

## Withdrawn captures

Paths below are relative to `docs/`. They are an exclusion record, not links.

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

The remaining linked captures were retained after visual review. Their dated
validation results are historical observations, not new acceptance or release
claims. The v3.1.0 preview set is explicitly historical; current written steps
describe development. A filename containing `redacted` is never proof of privacy.

## Re-check of 22 October 2026 (NCE-109)

A report of 22 October 2026 (Jira NCE-109) stated that the mailbox list, the
No-IP activity, the Portainer TLS Compose editor, the Dell delivery message and
the Home Assistant captures labelled redacted still exposed a mailbox label,
private addresses or a device label. Those are five of the thirteen captures
withdrawn above. The re-check confirmed on the `development` branch at commit
`eba8c95d39402639270e36153d13f8ff86ce7544`, and on `stage`, that none of the
thirteen withdrawn files exists under `docs/images/` and that no current guide
links them; `tests/test_current_documentation_contract.py` enforces both. The
`v3.1.6` tag and `main` predate the tutorial image folders and do not contain
them either.

The withdrawn files remain in Git history before 15 October 2026 and in any
local checkout, fork or cached page made before that date. History was not
rewritten. A report based on such a copy describes the old state; pull the
current branch before reviewing captures.

No image was edited, added or re-opened during this re-check: the run had no
image tooling, so masking was neither needed for the withdrawn files nor
possible for the retained ones. The review record of each retained capture is
therefore still the inspection dated 15 October 2026, or 21 October 2026 for
the Development WebUI set. The inventory below lists every raster file in the
checkout. `tests/test_screenshot_privacy_inventory.py` fails when a raster is
on disk, or linked from a current guide, without a `retained` row here, when a
`retained` row has no file, when a withdrawn capture reappears, and when a PNG
or JPEG carries EXIF or author/copyright text metadata.

## Open points for the next visual review

These were not resolved on 22 October 2026 because the captures could not be
opened in that run. They are review items, not confirmed exposures.

- The capture `images/unifi-setup/camera-names.png` shows console camera
  aliases by its caption. The Protect alarm capture was withdrawn for
  camera/location labels; confirm that the aliases shown here are generic.
- The eight captures under `images/portainer-setup/`, the TrueNAS delivery
  capture and the remaining Home Assistant delivery capture share browser
  chrome with withdrawn captures; confirm no sidebar label or address is
  readable.
- Re-open every retained capture at full size when image tooling is available
  and update the Record column with the new date.

## Raster inventory

Paths are relative to `docs/`. The Record column gives the date of the last
recorded visual inspection of the file; "unreviewed" means no inspection has
been recorded for that file. Every raster under `docs/images/` needs a row.

| Capture | Status | Record |
|---|---|---|
| `images/logo.png` | retained | product logo, not a capture |
| `images/discord-xen-orchestra-v1.9.6.png` | retained | historical card with the retired product name; not embedded; unreviewed |
| `images/teams-xen-orchestra-v1.9.6.png` | retained | historical card with the retired product name; not embedded; unreviewed |
| `images/v2.5.2-destinations.png` | retained | historical v2.5.2 capture; not embedded; unreviewed |
| `images/v2.5.2-discord-idrac.png` | retained | historical v2.5.2 capture embedded by the Dell iDRAC guide as outdated; reviewed 15 Oct 2026 |
| `images/v2.5.2-discord-zabbix.png` | retained | historical v2.5.2 capture; not embedded; unreviewed |
| `images/v2.5.2-inputs.png` | retained | historical v2.5.2 capture; not embedded; unreviewed |
| `images/v2.5.2-overview.png` | retained | historical v2.5.2 capture; not embedded; unreviewed |
| `images/v2.5.2-routing-flow.png` | retained | historical v2.5.2 capture; not embedded; unreviewed |
| `images/v2.5.2-settings.png` | retained | historical v2.5.2 capture; not embedded; unreviewed |
| `images/v2.5.2-sources.png` | retained | historical v2.5.2 capture; not embedded; unreviewed |
| `images/v2.5.2-teams.png` | retained | historical v2.5.2 capture; not embedded; unreviewed |
| `images/v3.1.0-dashboard.png` | retained | historical v3.1.0 capture; reviewed 15 Oct 2026 |
| `images/v3.1.0-delivery-history.png` | retained | historical v3.1.0 capture; reviewed 15 Oct 2026 |
| `images/v3.1.0-destinations.png` | retained | historical v3.1.0 capture; reviewed 15 Oct 2026 |
| `images/v3.1.0-discord-idrac.png` | retained | historical v3.1.0 capture; not embedded; unreviewed |
| `images/v3.1.0-discord-unifi.png` | retained | historical v3.1.0 capture; not embedded; unreviewed |
| `images/v3.1.0-discord-xen-orchestra.png` | retained | historical v3.1.0 capture; reviewed 15 Oct 2026 |
| `images/v3.1.0-routing-flow.png` | retained | historical v3.1.0 capture; reviewed 15 Oct 2026 |
| `images/v3.1.0-teams-xen-orchestra.png` | retained | historical v3.1.0 capture; reviewed 15 Oct 2026 |
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
| `images/hardware-setup/nowlert-token-list.png` | retained | reviewed 15 and 21 Oct 2026; token value hidden |
| `images/hardware-setup/nowlert-token-scope.png` | retained | reviewed 15 and 21 Oct 2026; pre-issuance scope form |
| `images/hardware-setup/nowlert-xen-destination.png` | retained | reviewed 15 Oct 2026 |
| `images/hardware-setup/nowlert-xen-routes.png` | retained | reviewed 15 Oct 2026 |
| `images/hardware-setup/portainer-hpe-callback.png` | retained | reviewed 15 Oct 2026 |
| `images/hardware-setup/portainer-stack-running.png` | retained | reviewed 15 Oct 2026 |
| `images/hardware-setup/portainer-tls-forwarding.png` | retained | reviewed 15 Oct 2026 |
| `images/hardware-setup/supermicro-subscription-record.png` | retained | rendered token-free API readback with RFC 5737 addresses; reviewed 15 and 21 Oct 2026 |
| `images/hardware-setup/xen-orchestra-backup-reports.png` | retained | reviewed 15 Oct 2026 |
| `images/hardware-setup/xen-orchestra-backup-test.png` | retained | reviewed 15 Oct 2026 |
| `images/hardware-setup/xen-orchestra-delivery.png` | retained | reviewed 15 Oct 2026 |
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
| `images/portainer-setup/token-scope.png` | retained | reviewed 15 and 21 Oct 2026; pre-issuance scope form |
| `images/portainer-setup/webhook-channel.png` | retained | reviewed 15 Oct 2026 |
| `images/truenas-setup/delivery-proof.png` | retained | reviewed 15 Oct 2026 |
| `images/unifi-setup/camera-names.png` | retained | reviewed 15 Oct 2026; open point above |
| `images/unifi-setup/drive-alarms.png` | retained | reviewed 15 Oct 2026 |
| `images/unifi-setup/drive-receiver-delivery.png` | retained | reviewed 15 Oct 2026 |
| `images/unifi-setup/network-alarms.png` | retained | reviewed 15 Oct 2026; labelled outdated pending recapture |
| `images/unifi-setup/network-delivery.png` | retained | reviewed 15 Oct 2026 |
| `images/unifi-setup/protect-delivery.png` | retained | reviewed 15 Oct 2026 |
| `images/unifi-setup/protect-noise-filter.png` | retained | reviewed 15 Oct 2026 |
| `images/v27.0.0-rc.1/audit-log-overview-admin-1440.png` | retained | synthetic Development capture, 21 Oct 2026 |
| `images/v27.0.0-rc.1/dashboard-live-admin-1440.png` | retained | synthetic Development capture, 21 Oct 2026 |
| `images/v27.0.0-rc.1/dashboard-live-admin-390.png` | retained | synthetic Development capture, 21 Oct 2026 |
| `images/v27.0.0-rc.1/dashboard-live-admin-768.png` | retained | synthetic Development capture, 21 Oct 2026 |
| `images/v27.0.0-rc.1/dashboard-live-user-1440.png` | retained | synthetic Development capture, 21 Oct 2026 |
| `images/v27.0.0-rc.1/delivery-history-zabbix-admin-1440.png` | retained | synthetic Development capture, 21 Oct 2026 |
| `images/v27.0.0-rc.1/destination-editor-teams-admin-1440.png` | retained | synthetic Development capture, 21 Oct 2026 |
| `images/v27.0.0-rc.1/destination-preview-teams-classic-admin-1440.png` | retained | synthetic Development capture, 21 Oct 2026 |
| `images/v27.0.0-rc.1/destination-preview-teams-modern-admin-1440.png` | retained | synthetic Development capture, 21 Oct 2026 |
| `images/v27.0.0-rc.1/destinations-list-admin-1440.png` | retained | synthetic Development capture, 21 Oct 2026 |
| `images/v27.0.0-rc.1/destinations-list-admin-390.png` | retained | synthetic Development capture, 21 Oct 2026 |
| `images/v27.0.0-rc.1/destinations-list-admin-768.png` | retained | synthetic Development capture, 21 Oct 2026 |
| `images/v27.0.0-rc.1/destinations-list-user-1440.png` | retained | synthetic Development capture, 21 Oct 2026 |
| `images/v27.0.0-rc.1/email-alerts-groups-admin-1440.png` | retained | synthetic Development capture, 21 Oct 2026 |
| `images/v27.0.0-rc.1/email-alerts-rules-admin-1440.png` | retained | synthetic Development capture, 21 Oct 2026 |
| `images/v27.0.0-rc.1/filtering-list-admin-1440.png` | retained | synthetic Development capture, 21 Oct 2026 |
| `images/v27.0.0-rc.1/routing-flow-live-admin-1440.png` | retained | synthetic Development capture, 21 Oct 2026 |
| `images/v27.0.0-rc.1/routing-flow-live-admin-390.png` | retained | synthetic Development capture, 21 Oct 2026 |
| `images/v27.0.0-rc.1/routing-flow-live-admin-768.png` | retained | synthetic Development capture, 21 Oct 2026 |
| `images/v27.0.0-rc.1/security-profile-admin-1440.png` | retained | synthetic Development capture, 21 Oct 2026 |
| `images/v27.0.0-rc.1/security-profile-user-1440.png` | retained | synthetic Development capture, 21 Oct 2026 |
| `images/v27.0.0-rc.1/settings-regional-admin-1440.png` | retained | synthetic Development capture, 21 Oct 2026 |
| `images/v27.0.0-rc.1/sign-in-empty-signed-out-1440.png` | retained | synthetic Development capture, 21 Oct 2026 |
| `images/v27.0.0-rc.1/sign-in-empty-signed-out-390.png` | retained | synthetic Development capture, 21 Oct 2026 |
| `images/v27.0.0-rc.1/sign-in-empty-signed-out-768.png` | retained | synthetic Development capture, 21 Oct 2026 |
| `images/v27.0.0-rc.1/users-search-admin-1440.png` | retained | synthetic Development capture, 21 Oct 2026 |
| `images/zabbix-setup/action-operations.png` | retained | reviewed 15 Oct 2026 |
| `images/zabbix-setup/media-enabled.png` | retained | reviewed 15 Oct 2026 |
| `images/zabbix-setup/native-problem-accepted.png` | retained | reviewed 15 Oct 2026 |
| `images/zabbix-setup/native-recovery-accepted.png` | retained | reviewed 15 Oct 2026 |
| `images/zabbix-setup/recipient-media.png` | retained | reviewed 15 Oct 2026 |

## Validation records

The JSON and HTML readback records under `images/hardware-setup/records/` and
`images/monitoring-setup/records/` were re-checked on 21 October 2026. Every
address in them is an RFC 5737 documentation address (192.0.2.0/24); the
subscription identifiers and controller contexts are synthetic, and no
authentication value is present. Keep that convention when adding a record,
and never paste a real controller, relay or receiver address into one.

The three packaged captures whose file names mention tokens (the hardware
token list and token scope captures and the Portainer token scope capture)
were visually inspected on 21 October 2026: they show a token name, the issued
token list with the value hidden, or the pre-issuance scope form, and no token
value. A file name that mentions a token is not, by itself, evidence of a
leak; inspect the image.

## Adding or replacing an image

1. Prefer a fresh capture with synthetic account/device names and documentation
   addresses such as `192.0.2.0/24`; keep raw captures outside the repository.
2. Inspect the full image at readable size, including account chrome, sidebars,
   message previews, URLs, logs, personal folders and profile pictures.
3. If private information remains, omit the image and supply written steps.
   Do not rely on blur, partial masks or a hidden password input.
4. Label synthetic receiver tests, native source tests and API readbacks
   accurately. An image does not establish an untested lifecycle or release.
5. Export without metadata: no EXIF segment and no author or copyright text
   chunk. The inventory test rejects both.
6. Add a `retained` row for the file to the inventory above with the review
   date, or a withdrawn bullet when a file is removed. The inventory test
   fails on a raster without a row.
7. Recheck the final exported file and every reference before publication.

This change does not rewrite Git history or remove old release artifacts,
cached copies, or previously published images. No new capture or release is
claimed accepted by this documentation check.
