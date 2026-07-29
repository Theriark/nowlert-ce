# Nowlert roadmap

## Shipped

### v2.3.3–v2.3.7 — WebUI runtime and icon corrections

- active-page persistence across reloads
- compact operations menu and update checks
- safe inactive-source lifecycle
- source-aware destination tests
- normalized Overview source-card icon boxes
- official DMTF Redfish identity

### v2.4.0 — Integrations and inputs

- built-in integration catalogue
- SMTP, HTTP, and Redfish input model
- input-aware routes
- schema 7 integration categories
- safe destination type changes and rollback

### v2.5.0 — Database-authoritative WebUI resources

- schema 8
- independent stores for destinations, routes, tokens, and settings
- normalized bootstrap-only `config.yaml`
- per-resource failure isolation
- WebUI editors for aliases and integration behavior

### v2.5.1 — Routing and WebUI normalization

- fallback-only wildcard routes
- duplicate delivery suppression
- include/exclude filters
- normalized input labels
- direct destination state controls
- Event API token terminology and scopes
- durable production validation baselines

### v2.5.2 — Flow presentation and packaged assets

- independent Routing Flow status symbols
- destination name plus platform/channel labels
- Discord-specific padded vendor thumbnails
- build-time packaged icon validation
- full-width Settings layout

### v2.5.3–v2.5.5 — Compatibility and destination delivery corrections

- Synology SMTP/HTTP and UniFi Protect payload compatibility
- packaged Discord image attachments and response verification
- persistent schema-9 destination-test health
- Microsoft Teams public HTTPS source icons
- Microsoft Teams 28 KiB pre-send payload guard
- accurate HTTP 202 accepted-versus-delivered wording

### v3.0.0 — Nowlert identity transition

- Nowlert product and WebUI identity
- Theriark repository and container metadata
- `NOWLERT_*` preferred deployment variables with legacy aliases
- Docker Hub and GHCR release coordinates
- compatibility-preserving schema-9 migration
- guarded release publication from `Theriark/nowlert`

## Current maintenance priorities

1. Keep README, Docker Hub, configuration examples, release notes, and
   screenshots synchronized with the stable image.
2. Expand real-system validation for integrations that began as
   fixture-validated candidates.
3. Preserve migration and rollback coverage from schema 6, schema 7, and
   schema 8 to schema 9.
4. Keep the production image non-root, read-only, capability-minimal, and
   reproducible.
5. Add new integrations and outputs only behind explicit contracts, tests, and
   source/destination ownership boundaries.

## Candidate v3.x work

These are candidates, not promises or assigned release dates:

- broader real Proxmox VE compatibility validation
- broader Synology DSM compatibility validation
- Redfish vendor/firmware matrix expansion
- additional destination adapters such as Telegram
- persistent background retry/queue orchestration
- optional operational metrics export
- documentation and screenshot drift automation
- automated Docker Hub content synchronization
- additional UI localization

## Issue and project policy

Create one GitHub issue per independently testable outcome. Each issue should
define:

- problem or goal
- security and compatibility boundary
- acceptance criteria
- real-system versus fixture validation level
- target release only after scope is approved

Completed work remains closed. Do not reopen historical release issues to track
new compatibility findings; create a new issue referencing the original.
