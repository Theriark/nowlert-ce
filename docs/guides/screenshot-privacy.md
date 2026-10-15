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

## Adding or replacing an image

1. Prefer a fresh capture with synthetic account/device names and documentation
   addresses such as `192.0.2.0/24`; keep raw captures outside the repository.
2. Inspect the full image at readable size, including account chrome, sidebars,
   message previews, URLs, logs, personal folders and profile pictures.
3. If private information remains, omit the image and supply written steps.
   Do not rely on blur, partial masks or a hidden password input.
4. Label synthetic receiver tests, native source tests and API readbacks
   accurately. An image does not establish an untested lifecycle or release.
5. Recheck the final exported file and every reference before publication.

This change does not rewrite Git history or remove old release artifacts,
cached copies, or previously published images. No new capture or release is
claimed accepted by this documentation check.
