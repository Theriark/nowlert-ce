# Current configuration model

Current Nowlert separates **process bootstrap** from **database-authoritative
platform resources**.

The active model is `platform_database_v1`.

## Bootstrap file

`config/config.yaml` controls process-level behavior that must be known before
the management plane is available:

- SMTP binding, STARTTLS, and SMTP AUTH bootstrap;
- HTTP binding and request-size limits;
- API/platform activation;
- persistent state location and retention boundary;
- secure-cookie mode; and
- WebUI activation, canonical URL, and HTTPS enforcement.

Listener, certificate, binding, authentication-bootstrap, and cookie-mode
changes require a container restart.

## Platform state

The persistent `/nowlert/state` mount contains the SQLite database and private
state required by the WebUI.

SQLite is authoritative for:

- local users and sessions;
- destinations and safe credential references;
- routes, integration/input identity, priorities, and filters;
- Event API token hashes, scopes, limits, and usage;
- regional preferences;
- backup schedules and target metadata;
- integration categories, behavior, aliases, and Redfish settings;
- housekeeping policy and run history;
- audit history; and
- delivery history.

Destination secret values remain in private owner-scoped files and are never
returned through normal read APIs.

## Removed legacy YAML resources

Fresh current configurations must not recreate WebUI-managed legacy sections such
as:

- `outputs`;
- `routing`;
- `notifications`;
- `presentation`;
- `home_assistant`;
- `redfish`;
- `api.tokens`;
- `platform.backups`; or
- `webui.language`.

Those structures are relevant only to supported migration paths from older
installations.

## Persistent paths

The supplied production Compose definition uses:

```text
./config           -> /nowlert/config
./state            -> /nowlert/state
./logs             -> /nowlert/logs
./secrets          -> /run/secrets (read-only)
./external-backups -> /nowlert/external-backups
```

The public example configuration uses `/nowlert/state`, matching the production
Compose definition.

A legacy `/nowlert/config/platform-state` directory may still exist on an
installation upgraded from an older release. Do not move or delete it until the
active `platform.state_dir` has been confirmed.

## Backup boundary

Application-managed recovery snapshots now include the complete SQLite state,
Nowlert-managed secret store, and mounted `config/config.yaml` when available.
Because SQLite is snapshotted as a whole, new database-managed resources and
retained Delivery/Audit history automatically remain inside the recovery
boundary instead of requiring table-specific backup code.

A full infrastructure disaster-recovery set must still preserve:

1. the Nowlert recovery snapshot/off-host state copy;
2. externally managed secrets that are mounted read-only from outside Nowlert;
3. the exact image reference/digest; and
4. the deployment definition used with that image.

Portable JSON export is configuration portability, not disaster recovery. It
deliberately omits users, credentials, sessions, token material, history and
other private state.

## Current schema

Current development uses database schema **13** with
`platform_database_v1`. Schema 13 adds bounded operational-history
housekeeping metadata; existing schema-12 state is migrated transactionally.

Take a verified recovery snapshot before upgrading and keep the off-host copy
until acceptance checks pass.
