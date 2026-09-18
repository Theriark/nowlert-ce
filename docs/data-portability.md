# Platform data portability, history, and recovery

Current Nowlert deployments intentionally separate three responsibilities:

1. **Data Tools** move credential-free user-created configuration.
2. **Housekeeping** controls how long operational history is retained locally.
3. **Recovery backups** capture the complete application state for rollback and disaster recovery.

Do not treat a Data Tools export as a recovery backup.

## Current authority model

The active configuration model is `platform_database_v1`.

- SQLite is authoritative for WebUI-managed resources and operational history.
- `config/config.yaml` contains process/bootstrap and listener/security settings.
- destination and managed backup-target credentials remain in private secret files.

## Data Tools: safe user configuration

The administrator-only export produces a versioned `nowlert.platform.v2` JSON
document containing safe user-created configuration:

- destination owner/name/output/public settings, sharing and enabled state;
- reusable route owner/name/source/input/priority/enabled state;
- destination-to-route assignments; and
- destination-owned filtering policies and their enabled state.

The v2 export does **not** back up route-owned filter JSON. Filtering is now
owned by Destinations; the portable document follows that current model.

The export deliberately excludes:

- users, password hashes, and browser sessions;
- Event API token values/digests;
- destination and backup-target credentials;
- secret identifiers and file paths;
- delivery history and audit history;
- backup archives and recovery-only private material.

Credential-dependent destinations imported from safe JSON remain disabled until
an administrator supplies their credential through the normal write-only form.

The importer remains compatible with `nowlert.platform.v1` documents. Legacy
v1 route-filter fields are accepted only for backward compatibility; new v2
exports no longer use that route-owned filtering shape.

## Preview and fingerprint boundary

Import is preview-first. The backend validates the bounded JSON document,
ownership, names, public destination settings, route assignments, filtering
payloads and collisions, then returns a fingerprint plus warnings.

Apply succeeds only when preview has no blocking errors, the administrator
explicitly confirms the operation, and the submitted document still produces
the same fingerprint. Partial creation is rolled back.

## Housekeeping

Delivery History and Audit Log are persisted in SQLite for administrator
inspection. They are not transient browser data.

Default retention is:

- Delivery History: **90 days**;
- Audit Log: **365 days**; and
- completed backup-run records: **180 days**.

The WebUI offers recommended fixed retention choices for each category and a
`Keep forever` option. Housekeeping is either **Enabled** or **Disabled**; there
is no manual run control. When enabled it runs once per local calendar day at
the configured time. The persisted `daily:YYYY-MM-DD` housekeeping run key
prevents a container restart or image update from running cleanup twice on the
same day. If Nowlert was offline at the configured time, it catches up once when
it starts later that day.

Cleanup deletes in bounded batches, removes expired/revoked browser sessions
after a short grace period, records each run, and writes a secret-free audit
event. Snapshot retention remains controlled separately by the backup retention
setting.

## Complete recovery backups

Recovery snapshots live below `platform.state_dir/backups`. New snapshots use
the `nowlert.state-backup.v2` manifest and contain:

- a consistent SQLite snapshot, including users, settings, destinations,
  reusable routes/assignments, filtering, API-token records, Delivery History,
  Audit Log, backup settings and housekeeping settings/history;
- Nowlert-managed owner-scoped secret files;
- the mounted bootstrap `config/config.yaml`, when available;
- the running Nowlert version and database schema metadata; and
- a SHA-256 integrity manifest covering every included file.

Older `nowlert.state-backup.v1` state-only snapshots remain readable. When an
older supported database schema is restored, Nowlert upgrades the staged copy to
the current schema before it replaces live state.

Raw application logs, the deployment definition, container image bytes, and
externally managed orchestrator secrets such as read-only `/run/secrets` are
not copied into the application snapshot. Keep those deployment-level
dependencies under normal host/infrastructure backup control.

## Local, NFS, and SMB restore

Scheduled/manual backups can be mirrored to configured Local, NFS, or SMB
destinations under `nowlert-state-backups/`.

The Backups page can discover verified snapshots on those targets. External
restore never swaps live state directly from a network filesystem. Nowlert:

1. makes the configured target ready;
2. copies the selected snapshot to private local staging;
3. verifies the manifest, SHA-256 digests and SQLite integrity;
4. creates a safety snapshot of the currently running instance;
5. upgrades the staged database if required;
6. atomically restores the database, managed secret store and included
   `config.yaml`;
7. revokes browser sessions; and
8. restarts Nowlert so restored bootstrap/runtime state is authoritative.

If staging or validation fails, live state is left untouched.

## API routes

| Method | Route | Purpose |
|---|---|---|
| GET | `/api/v2/portability/export` | credential-free v2 user configuration |
| POST | `/api/v2/portability/preview` | validate/fingerprint portable JSON |
| POST | `/api/v2/portability/import` | apply unchanged confirmed portable JSON |
| GET/PUT | `/api/v2/housekeeping` | inspect/update retention settings and status |
| GET | `/api/v2/backups` | list local verified recovery snapshots |
| POST | `/api/v2/backups` | create a local recovery snapshot |
| DELETE | `/api/v2/backups/{id}` | permanently delete one local snapshot |
| POST | `/api/v2/backups/{id}/restore` | restore a local snapshot and restart |
| GET | `/api/v2/backup-targets/{id}/backups` | discover verified snapshots on one Local/NFS/SMB target |
| POST | `/api/v2/backup-targets/{id}/backups/{backup}/restore` | stage, verify, restore and restart from external storage |
| POST | `/api/v2/migrations/v1/preview` | preview supported legacy YAML migration |
| POST | `/api/v2/migrations/v1/import` | apply supported legacy YAML migration |

See [platform-api.md](platform-api.md) for the complete authenticated API and
[current-configuration-model.md](current-configuration-model.md) for the
storage/authority boundary.
