# Current configuration model

Nowlert v3.1.2 separates **process bootstrap** from **database-authoritative
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
- notices;
- audit history; and
- delivery history.

Destination secret values remain in private owner-scoped files and are never
returned through normal read APIs.

## Removed legacy YAML resources

Fresh v3.1.2 configurations must not recreate WebUI-managed legacy sections such
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

A complete recovery set keeps these together:

1. mounted `config`;
2. mounted `state`;
3. mounted external `secrets`, when used;
4. the exact image reference/digest; and
5. the deployment definition used with that image.

Portable JSON export is useful for migration but is not a disaster-recovery
backup because it deliberately omits credentials, passwords, sessions, token
values, and other private state.

## v3.1.1 -> v3.1.2

v3.1.2 keeps database schema 9 and `platform_database_v1`. No database migration
is required. This release changes documentation, dependencies, and release
safety, not the configuration authority model.

Take a matched backup before upgrading and keep it until the v3.1.2 acceptance
checks pass.
