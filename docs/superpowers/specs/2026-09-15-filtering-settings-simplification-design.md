# Filtering and Settings Simplification Design

## Goal

Make Nowlert have one authoritative delivery-policy surface: **Filtering** decides whether a normalized notification is delivered, **Settings** controls platform/regional configuration plus deterministic normalization and input-processing behavior, and output formatters deterministically decide presentation.

This change also completes the Administration/profile-menu cleanup found during acceptance.

## Pipeline contract

The intended pipeline is:

`full incoming payload -> deterministic parser/normalizer -> destination Filtering -> deterministic formatter -> Destination`

Nowlert should retain the full payload for parsing/normalization as appropriate, but Filtering exposes stable normalized fields rather than arbitrary vendor-specific raw JSON keys. When a useful source field is missing from Filtering, add it to the normalized schema rather than allowing ad-hoc JSON-path filters.

## Single filtering authority

All rules that answer **"should this destination receive this notification?"** belong to Destination Filtering.

Filtering supports two deterministic actions:

- **ALLOW**: deliver only when the rule conditions match.
- **BLOCK**: do not deliver when the rule conditions match.

Evaluation order for one destination/integration is:

1. If any BLOCK rule matches, do not deliver.
2. Otherwise, if one or more ALLOW rules exist, at least one ALLOW rule must match.
3. Otherwise deliver.

A rule's fields are ANDed together. Multiple rules of the same action are ORed.

The existing destination ownership/delegation model remains unchanged: private destination owners can manage their own filters; shared destinations are read-only to normal users unless Admin grants `can_manage_filters`.

## Dell iDRAC suppression migration

The current trusted-client suppression for successful iDRAC session login/logout events is a delivery filter and must leave Settings/router-global suppression.

The equivalent Filtering rule is a BLOCK rule using normalized Dell fields:

- `message_id`: `USR0030`, `USR0032`
- `source_ip`: configured trusted management-client IP addresses

The behavior becomes destination-specific instead of global. Existing configured trusted IPs must be migrated into destination-owned Dell BLOCK rules where Dell filtering is available, without creating duplicate rules. After migration, the router-level `_notification_suppressed()` path and Dell suppression setting are retired.

## Deterministic presentation settings removed

These are presentation choices, not delivery policies:

- Xen Orchestra `show_ids`
- Zabbix `show_ids`

Remove both settings from the current integration-settings UI and stop using configuration toggles in the XO/Zabbix formatters. The formatters use one deterministic presentation. IDs remain normalized data and remain available to Filtering where already supported.

No Filtering rule should be created for these presentation toggles.

## Settings that remain

Administration -> Settings contains:

### Regional settings

- Language
- Timezone
- Time format

### Aliases & normalization

- UniFi Protect device aliases
- Home Assistant endpoint aliases
- Home Assistant component aliases

These affect normalized/readable identities and are not delivery filters.

### Event processing

- Redfish duplicate-event window

This acts before destination filtering at input-processing time and remains a platform setting.

The old heading **"Notification policies and aliases"** is removed.

## Navigation and profile shell

Admin Administration tabs become:

`Users | Settings | Updates | Data tools`

Settings is removed from the profile dropdown.

The profile dropdown becomes:

`API access | Security | Sign out`

All three rows use the same menu-item DOM structure, spacing, hover/focus treatment, and icon column. API access receives an icon consistent with the existing Security/Sign out rows. The obsolete profile chevron remains removed.

## Compatibility and migration

- Existing database rows containing XO/Zabbix `show_ids` and Dell trusted-client suppression must be safely accepted during migration so startup does not fail.
- After migration, persisted integration settings are rewritten to the smaller supported setting model.
- Existing destination filters remain valid. Legacy single-clause filters are interpreted as ALLOW rules.
- Migration must be idempotent.
- No routes/sources/inputs navigation is reintroduced.

## Acceptance criteria

1. Administration displays `Users | Settings | Updates | Data tools`.
2. Profile menu displays aligned/iconized `API access | Security | Sign out`; Settings is absent.
3. Administration -> Settings contains only Regional settings, Aliases & normalization, and Event processing.
4. XO and Zabbix presentation toggles are gone and their formatters are deterministic.
5. Dell trusted-client suppression is gone from Settings and the router-global suppression path is removed.
6. Filtering can create/edit/remove ALLOW and BLOCK rules.
7. BLOCK wins over ALLOW; ALLOW rules restrict delivery only when at least one ALLOW exists.
8. Existing legacy filters continue to behave as ALLOW filters.
9. Existing Dell trusted IP configuration migrates idempotently into destination-specific Dell BLOCK filters where applicable.
10. Full automated tests, Python/JavaScript syntax validation, YAML/Compose validation, production image build, and Development immutable deployment gates pass before acceptance resumes.
