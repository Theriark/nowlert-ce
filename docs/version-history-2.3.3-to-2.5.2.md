# Nowlert v2.3.3 to v2.5.2 implementation sequence

This is the chronological implementation record for the eight commits between
the v2.3.3 and v2.5.2 tags.

## Starting point: v2.3.3

Platform schema 6 and the unified YAML model were still active.

Implemented:

- retain the active hash-backed WebUI page after F5/reload
- replace the standalone restart control with a three-dot operations menu
- check GitHub releases after startup, every six hours, on stale-tab resume,
  and manually
- use transparent source icons without white tiles
- allow safe inactive-source removal when only a wildcard route covers it
- send destination tests through the best specific source formatter
- respect the selected 12/24-hour backup-time presentation

## v2.3.4 — final WebUI runtime polish

- reapply the requested page after the authenticated workspace renders
- accept `source`, `id`, or `name` in inactive-source removal requests
- finalize requested source icon sizing
- preserve update checks, formatter-aware tests, and regional backup time

## v2.3.5 — source icon and removal corrections

- map `xo` to Xen Orchestra
- package a neutral REST API identity for REST aliases
- enlarge selected source artwork through stable source selectors
- add a body-free source-key DELETE endpoint

## v2.3.6 — icon scope and Redfish identity

- restore non-target icons and normal source-card proportions
- keep enlargement limited to approved source artwork
- use the official DMTF Redfish logo for `redfish`
- retain the neutral REST identity for `restful` and `rest_api`

## v2.3.7 — fixed Overview icon boxes

- normalize desktop source icon boxes to 48 × 48 px
- normalize mobile source icon boxes to 44 × 44 px
- scale only visible artwork inside the fixed box
- explicitly avoid changing outbound notification rendering

## v2.4.0 — integration/input model, schema 7

- replace runtime-discovered source records with a built-in integration catalogue
- separate integrations from SMTP, HTTP, and Redfish inputs
- move integration category overrides to SQLite
- remove source status/removal/internal identifiers from Sources
- use integration/input route choices
- preserve parser-compatible source keys and add `input_type`
- infer legacy Zabbix routes as SMTP
- remove the test-only Home Lab Generic route
- reject duplicate destination names before mutation
- enable the output parent group when enabling a child destination
- allow destination type changes while preserving destination ID, routes, and history
- roll back configuration and synchronization after failed mutations
- preserve `config.yaml` ownership and mode during atomic replacement

## v2.5.0 — database-authoritative resources, schema 8

- make SQLite authoritative for destinations and routes
- migrate destination credentials to private secret records
- migrate Event API token hashes without rotating token values
- move regional settings, backup scheduling, integration behavior, categories,
  aliases, and Redfish deduplication into isolated settings records
- normalize `config.yaml` to process bootstrap, listener, and security settings
- remove legacy WebUI-managed YAML sections after successful import
- isolate malformed destination, route, and settings records
- return reference-coded safe API errors
- add WebUI editors for Xen Orchestra, Zabbix, Dell iDRAC, UniFi Protect,
  Home Assistant, and Redfish settings
- require matched config/state/secrets backups for rollback

## v2.5.1 — fallback routing and WebUI normalization

- evaluate dedicated routes before wildcard routes
- use wildcard routes only when no dedicated route matches
- deliver only once to a destination even when several routes match it
- add include/exclude filters for hosts, events, severities, and statuses
- migrate Xen Orchestra success/skipped/failure selection into route status filters
- standardize visible input labels to SMTP, HTTP, and Redfish
- keep one Zabbix integration with SMTP and HTTP
- label wildcard choices as Fallback
- make Enabled/Disabled and Shared/Private badges direct controls
- remove the positive Credentials set badge
- rename Applications to Event API tokens
- populate token scopes from the built-in integration catalogue
- separate integration-settings card content and spacing
- add independent input/route/destination flow health
- keep durable production validation baselines

## v2.5.2 — final routing labels and notification assets

- show disabled flow as a yellow typographic prohibition symbol
- show the configured destination name as the destination heading
- show `Platform · channel` on the secondary line
- add padded Discord variants for Xen Orchestra, Grafana, TrueNAS, Portainer,
  Home Assistant, Supermicro, and Zabbix
- keep original Microsoft Teams artwork sizing
- normalize Xen Orchestra aliases
- validate every referenced WebUI and notification asset during Docker build
- keep immutable release-addressed icon URLs
- make Settings use the full workspace width

## Final stable state

- version: 2.5.2
- platform schema: 8
- configuration model: `platform_database_v1`
- visible inputs: SMTP, HTTP, Redfish
- WebUI-managed resources: SQLite plus private secret files
- bootstrap authority: normalized `config.yaml`
- routing: dedicated-first, fallback-only wildcard, destination deduplication
- Docker validation: complete test suite plus in-image asset validation
