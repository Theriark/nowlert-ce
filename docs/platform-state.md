# Platform state and local accounts

Current Nowlert stores its management-plane state in SQLite plus owner-scoped
private secret files. PostgreSQL, Redis, and separate management services are
not required for a normal single-instance deployment.

The current configuration model is `platform_database_v1`: SQLite is
authoritative for WebUI-managed resources and operational history, while
`config.yaml` is limited to process/bootstrap and listener/security settings.

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
managed secret files are mode `0600`. Secret filenames are generated rather
than based on user input.

Normal metadata operations do not return secret values or secret filesystem
paths.

## Schema 13

Current development uses database schema **13**.

The current schema covers:

- local users and browser sessions;
- hashed Event API token records;
- owner-scoped secret records;
- private/shared destinations;
- reusable routes and destination assignments;
- destination-owned filtering policies;
- regional, integration, backup and housekeeping settings;
- integration categories;
- delivery history;
- audit history;
- backup target/run metadata;
- housekeeping run history; and
- destination-test health state.

A database created by a newer unsupported schema is rejected instead of being
silently downgraded. Recovery restore can stage and migrate an older supported
snapshot to the current schema before it replaces live state.

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

User deletion is not a blind row delete. The API enforces administrative
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
Recommended bootstrap configuration:

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

## Operational history and housekeeping

Delivery History and Audit Log are persisted in SQLite and are therefore
available for administrator inspection until their retention boundary is
reached.

Housekeeping defaults are 90 days for delivery history, 365 days for audit
history and 180 days for completed backup-run records. A value of `0` retains
that category forever. Cleanup runs in bounded batches and records its own
result without storing secret material.

## Trusted recovery CLI

Normal first-run setup and account management use the WebUI/API. A host-trusted
CLI remains available for isolated account recovery:

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

## Complete recovery snapshots

New application-managed snapshots use `nowlert.state-backup.v2` and capture:

- the complete SQLite database, including users, configuration records,
  filtering, retained Delivery History and Audit Log;
- Nowlert-managed owner-scoped secret files;
- mounted bootstrap `config/config.yaml` when available;
- application/database version metadata; and
- a SHA-256 integrity manifest.

Older `nowlert.state-backup.v1` snapshots remain readable.

A restore:

1. requires the exact backup identifier;
2. validates the source snapshot;
3. copies an external Local/NFS/SMB snapshot to private local staging first;
4. creates a safety snapshot of current live state;
5. upgrades an older supported staged database when required;
6. validates stored hashes and SQLite integrity;
7. atomically replaces the database, managed secret store and included
   `config.yaml`;
8. revokes browser sessions; and
9. restarts the live service so restored bootstrap configuration is active.

The application backup does not contain raw application logs, deployment
definitions, container image bytes, or externally managed read-only
`/run/secrets`. Keep those infrastructure-level dependencies under the host
backup policy.

## Upgrade and rollback

Before an upgrade:

1. record the running image/digest;
2. create a verified recovery snapshot and retain its off-host Local/NFS/SMB
   copy;
3. preserve externally managed deployment secrets and the deployment
   definition;
4. deploy the exact promoted image;
5. verify login, routing, filtering, destinations, history, backups and health;
   and
6. retain the recovery copy until acceptance passes.

Older schema/release transition notes remain in historical release and
acceptance files; they are not the current deployment path.

See [platform-api.md](platform-api.md),
[platform-routing.md](platform-routing.md), and
[data-portability.md](data-portability.md).
