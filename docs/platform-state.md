# Platform state and local accounts

Nowlert v3.1.1 stores its management-plane state in SQLite plus owner-scoped
private secret files. PostgreSQL, Redis, and separate management services are
not required for a normal single-instance deployment.

The current configuration model is `platform_database_v1`: SQLite is
authoritative for WebUI-managed resources, while `config.yaml` is limited to
process/bootstrap and listener/security settings.

## Storage layout

A production state mount is organized below `/nowlert/state`:

```text
/nowlert/state/
|- nowlert.db
|- secrets/
|  `- generated-identifier.v1
|- backups/
|  `- state-YYYYMMDDTHHMMSSZ-identifier/
`- schema-backups/
   `- nowlert-schema-N-before-M-TIMESTAMP.db
```

Directories containing private state are mode `0700`; database, manifest, and
secret files are mode `0600`. Secret filenames are generated rather than based
on user input.

Normal metadata operations do not return secret values or secret filesystem
paths.

## Schema 9

v3.1.1 keeps database schema **9**. It is the same schema used by v3.1.0, so no
database migration is required for this patch release.

The current schema covers:

- local users and browser sessions;
- hashed Event API tokens;
- owner-scoped secret records;
- private/shared destinations;
- routes and integration/input identity;
- settings records and integration categories;
- notices;
- delivery history;
- audit events;
- backup target metadata; and
- destination-test health state.

A database created by a newer unsupported schema is rejected instead of being
silently downgraded.

## Account security

Passwords use salted PBKDF2-SHA256 records. The database never stores plaintext
passwords, browser session tokens, CSRF values, or Event API token plaintext.

Local account protection includes:

- normalized case-insensitive usernames;
- persistent failed-login counters;
- lockout after repeated failed attempts;
- equivalent password verification work for unknown usernames;
- session revocation after password reset or account disable;
- protection against losing the last enabled administrator;
- absolute and idle session expiry; and
- secure cookie support for reverse-proxied HTTPS deployments.

### Administrator user deletion

v3.1.1 adds permanent user deletion to the administrator workflow.

The operation is not a blind row delete. The API enforces administrative
permissions and account/ownership constraints, rejects deletion of the current
administrator account, and records a `user.delete` audit event when successful.

The WebUI requires an explicit destructive-action confirmation.

## First-run setup

When no users exist, startup creates a random setup token, stores only its
digest, and prints the plaintext token once to container output.

The token is short-lived and single-use. The operator uses it in the WebUI to
choose the first administrator username/password. No default administrator
credential is shipped.

## Production preparation

Create the state directory with the same numeric UID/GID used by the container:

```bash
mkdir -p state
chmod 700 state
```

The production Compose file mounts `NOWLERT_STATE_DIR` at `/nowlert/state`.
Recommended configuration:

```yaml
platform:
  enabled: true
  state_dir: "/nowlert/state"
  backup_retention: 20
  configuration_model: "platform_database_v1"
  secure_cookies: false
```

For untrusted browser access, use a TLS reverse proxy and set
`secure_cookies: true` together with WebUI HTTPS enforcement.

## Trusted recovery CLI

Normal first-run setup and account management use the WebUI/API. A host-trusted
CLI remains available for isolated recovery:

```bash
python3 tools/manage_users.py --state-dir /tmp/nowlert-state init
python3 tools/manage_users.py --state-dir /tmp/nowlert-state \
  create-admin --username administrator
python3 tools/manage_users.py --state-dir /tmp/nowlert-state list-users
```

For a running production container:

```bash
docker compose -f compose.production.yaml exec nowlert \
  python3 tools/manage_users.py create-admin --username administrator
```

Do not put plaintext passwords in command arguments or shell history. Prefer the
interactive prompt or the tool's environment-variable input path for trusted
automation.

## Private state backups

The Backups/Data tools workflow creates a consistent SQLite + owner-scoped
secret snapshot with an integrity manifest below the state mount.

A restore:

1. requires the exact backup identifier;
2. creates a safety snapshot of current state;
3. validates stored hashes and SQLite integrity;
4. stages the replacement;
5. swaps only after validation; and
6. revokes browser sessions after success.

v3.1.1 also allows an administrator to permanently delete one selected private
snapshot. Deletion is audited and does not affect other backups.

These application-managed snapshots are not a substitute for encrypted off-host
disaster recovery. Keep the complete state mount in the host backup policy.

## Upgrade and rollback

Before moving from v3.1.0 to v3.1.1:

1. record the running image/digest;
2. take a matched copy of `config`, `state`, and external `secrets`;
3. deploy the exact promoted v3.1.1 image;
4. verify login, routes, destinations, history, backups, and health; and
5. retain the backup until acceptance passes.

Because the schema remains 9, no migration is expected. Even so, rollback
should use a matched backup when private state has changed after the upgrade.

Older schema transition notes remain in the historical release/acceptance
files; they are not the current v3.1.1 deployment path.

See [platform-api.md](platform-api.md),
[platform-routing.md](platform-routing.md), and
[data-portability.md](data-portability.md).
