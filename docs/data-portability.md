# Platform data portability and migration

Nowlert v3.1.2 provides two intentionally different mechanisms:

1. **credential-free portability** for moving safe platform configuration; and
2. **private state backups** for recovery/rollback of the full local platform
   state.

Do not treat a portability export as a disaster-recovery backup.

## Current authority model

Normal v3.1.2 deployments use `platform_database_v1`.

- SQLite is authoritative for WebUI-managed resources.
- `config.yaml` contains process/bootstrap and listener/security settings.
- destination credentials remain in private owner-scoped secret files.

Legacy YAML inventory/import endpoints exist for migration and compatibility,
not as the normal current editing model.

## Safe platform export

The administrator-only portability export produces a versioned
`nowlert.platform.v1` JSON document containing safe resource metadata such as:

- destination owner names, display names, output types, public settings,
  sharing, and enabled state; and
- route owner names, integrations/sources, input types, filters, priorities,
  enabled state, and portable destination references.

The export deliberately excludes:

- password hashes;
- browser session material;
- Event API token values/digests;
- destination credentials;
- secret identifiers and file paths;
- webhook URLs stored as secrets; and
- other private recovery material.

A credential-dependent destination imported from safe JSON remains disabled
until an administrator supplies its credential through the normal write-only
form.

## Preview and fingerprint boundary

Import is preview-first.

The backend validates normalization, ownership, output settings, route filters,
and name collisions, then returns a fingerprint plus bounded actions/warnings.

Apply succeeds only when:

1. preview has no blocking errors;
2. the administrator explicitly confirms the operation; and
3. the submitted document produces the same fingerprint.

Unexpected partial creation is rolled back. Import does not silently overwrite
unrelated existing resources.

## Legacy v1 YAML migration

The compatibility migration path can translate supported legacy output/routing
structures into database-authoritative destinations/routes and owner-scoped
secrets.

Placeholders, unsupported output types, and unsupported match fields are
rejected or skipped with bounded warnings rather than guessed. Credential values
must never be echoed into previews, audit detail, or normal API responses.

This path is for supported upgrades from old installations. A healthy current
v3.1.2 deployment should not be converted back to legacy YAML resource
authority.

## Private state backups

Private state snapshots live below `platform.state_dir/backups` and contain:

- a consistent SQLite snapshot;
- owner-scoped secret files; and
- a SHA-256 integrity manifest.

Directories are private and backup bytes are not downloadable through normal
WebUI/API endpoints.

`platform.backup_retention` defaults to 20 snapshots and accepts a bounded
configured value.

Create a backup before:

- platform upgrades;
- risky account/ownership changes;
- configuration migrations; and
- restore tests.

Also include the complete state bind mount in encrypted off-host backups.
Application-managed snapshots are not a replacement for host-level disaster
recovery.

### Restore

Restore requires the exact backup identifier. Nowlert creates a safety snapshot
first, verifies the selected snapshot, checks SQLite integrity/schema, stages the
replacement, and swaps only after validation.

A successful restore revokes browser sessions. Event API token records and
other private state return to the selected point in time; review/rotate tokens
when that rollback history matters.

### Delete one snapshot

v3.1.1 adds administrator deletion of an individual private state snapshot.

Deletion:

- requires administrator authority and CSRF protection;
- targets the exact backup identifier;
- is separate from restore;
- removes only the selected snapshot; and
- writes an audit event.

Use this for lifecycle cleanup after confirming the snapshot is no longer needed.
It is not an automatic substitute for the configured retention policy.

## API routes

| Method | Route | Purpose |
|---|---|---|
| GET | `/api/v2/portability/export` | credential-free JSON export |
| POST | `/api/v2/portability/preview` | validate/fingerprint platform JSON |
| POST | `/api/v2/portability/import` | apply unchanged confirmed JSON |
| POST | `/api/v2/migrations/v1/preview` | validate/fingerprint legacy YAML |
| POST | `/api/v2/migrations/v1/import` | apply confirmed legacy import |
| GET | `/api/v2/configuration/inventory` | inspect mounted bootstrap/migration metadata without secrets |
| GET | `/api/v2/backups` | list verified private snapshots |
| POST | `/api/v2/backups` | create private snapshot |
| DELETE | `/api/v2/backups/{id}` | permanently delete selected snapshot |
| POST | `/api/v2/backups/{id}/restore` | restore after exact-ID confirmation |

See [platform-api.md](platform-api.md) for the complete authenticated API and
[platform-state.md](platform-state.md) for storage/recovery boundaries.
