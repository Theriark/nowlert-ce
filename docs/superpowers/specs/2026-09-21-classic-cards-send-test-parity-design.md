# Classic Cards and Send-Test Parity Design

## Goal

Unify destination-card Send test as a Nowlert-owned notification, make it render through each destination's selected presentation, and complete Microsoft Teams Classic coverage for every supported integration plus fallback.

## Send test

Destination-card Send test must always use a synthetic Nowlert event:

- source: `nowlert`
- severity/status: information
- provider: Nowlert
- destination name in the title/body
- component: Destination test
- Nowlert icon/identity

The Send test must not inherit the source attached to a route. Manual preview remains source-selectable.

Stored destination presentation controls rendering:

- Discord Modern -> Components V2 Modern card
- Discord Classic -> Classic embed
- Teams Modern -> current Teams Modern Adaptive Card
- Teams Classic -> Teams Classic Adaptive Card
- Slack -> current Classic-only Slack renderer
- Generic Webhook Modern -> `modern_card`
- Generic Webhook Classic -> `classic_card_v1`

## Classic semantic contract

Discord Classic v1 remains the approved semantic source of truth for source-specific title, description, lifecycle, field names, order, inline intent, omission rules, footer, links, and fallback behavior.

Extract the Discord-embed-to-neutral conversion into a reusable Classic Card v1 helper. Generic Webhook keeps its current exact Discord Classic preview parity and uses the shared converter. Teams consumes the same Classic semantics and renders them natively.

## Teams Classic

Replace the XO-only Classic implementation with one Teams Classic renderer covering:

- Xen Orchestra
- Zabbix
- Grafana
- Portainer
- Proxmox
- QNAP
- Synology
- TrueNAS
- UniFi Network
- UniFi Protect
- UniFi Drive
- Home Assistant
- Redfish
- Supermicro
- HPE iLO
- Dell iDRAC
- generic/unknown/Nowlert fallback

Rendering rules:

- title + lifecycle use a Teams-native header
- source icon comes from the notification source; unknown sources fall back to Nowlert
- consecutive Classic fields with `inline=true` render in Teams ColumnSets, up to three columns
- non-inline fields render as separated full-width sections
- description stays directly under the header
- Classic footer is preserved
- optional URL becomes an Open event action when safe
- empty fields are omitted
- existing sanitization and 28 KiB Teams guard remain

XO must retain the already accepted visual structure: Duration / Transfer Size / Transfer Speed in one row, then Storage, VM sections, and Job ID as full-width sections.

Teams Modern formatter files and behavior must remain unchanged.

## Slack

Slack remains Classic-only in this phase. No Modern/Classic selector is added. The unified Nowlert Send test must render through the existing Slack Classic renderer with the Nowlert icon.

## Generic Webhook

No transport change. Modern and Classic use the same unified Nowlert Send test event, with their existing `modern_card` and `classic_card_v1` contracts.

## Service behavior

`PlatformOutputService._with_message_style()` must support Teams as well as Discord and Generic Webhook so explicit preview/test style overrides are consistent. Destination-card Send test normally relies on the stored destination style.

## Testing

Automated coverage must prove:

- destination-card Send test source is always `nowlert` and is no longer route-aware
- test event includes destination name, output context, Nowlert provider, and Destination test component
- Discord Modern and Classic tests use Nowlert identity
- Teams Modern and Classic tests use Nowlert identity
- Slack test uses Nowlert identity
- Generic Webhook Modern/Classic test presentations carry the same semantic test event
- Teams Classic renders Classic for every supported source and generic fallback
- Teams Classic field order/inline intent is derived from the approved Discord Classic model
- XO Classic accepted ordering remains
- secret sanitization and Teams payload limits remain
- Teams Modern, Discord Modern, Discord Classic, Slack Classic, and Generic Webhook presentation contracts do not regress

## Delivery workflow

Create one feature branch from the current green Development head. Push one atomic implementation candidate, wait for CI, fix only concrete failures, merge to `development` once green, and verify the exact post-merge Development deployment. Visual corrections follow the merged baseline.
