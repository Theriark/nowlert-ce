# Database-authoritative resources

Nowlert uses `platform_database_v1` to separate process bootstrap from
WebUI-managed resources.

## Bootstrap configuration

`config/config.yaml` contains process-level configuration such as:

- listener binding;
- SMTP/HTTP transport security;
- API/platform activation;
- state-directory location;
- secure-cookie mode; and
- WebUI publication/HTTPS settings.

It is not the normal destination, route, user, token, preference, or backup
editing surface.

## Platform state

SQLite stores authoritative management state for:

- users and sessions;
- Event API token hashes/metadata;
- destinations and safe secret references;
- routes and integration/input criteria;
- regional preferences;
- backup scheduling/targets;
- integration behavior/categories/aliases;
- audit events; and
- delivery history.

Destination credential values remain in private owner-scoped secret files.

Each resource uses scoped validation/transaction boundaries so a damaged row can
be reported without making unrelated valid resources or pages unavailable.

## Legacy migration boundary

Supported older installations can import their legacy YAML-managed resources
into the database model. After successful migration, current platform resources
are managed through SQLite/WebUI/API and removed from the normal bootstrap YAML.

Do not recreate legacy `outputs`, `routing`, `api.tokens`, or other
WebUI-managed YAML sections in a healthy current installation.

Legacy `api.tokens` entries are imported as Event API tokens under their YAML
names; a name that the same owner already uses gets "Legacy " in front ("Legacy
NAME", then "Legacy NAME 2"). The migration needs the credential of every
enabled token. The credential is read the same way as for authentication:
`token_sha256` is used when it holds 64 hexadecimal characters; otherwise, when
`token_env` names a variable, only that variable is used (an unset or empty
variable means no credential, and `token_file` is then not read); otherwise
`token_file` is read. The file must be a regular file, not a symbolic link,
with no permission bits for the group or for others (for example mode `0600`,
`0400` or `0700`), and hold at most 4096 characters; a file that breaks any of
these rules gives no credential. If an enabled token has no credential, the
whole migration stops with "resource migration failed: api token NAME cannot be
imported because its credential is unavailable", `config.yaml` keeps its legacy
sections and Nowlert reports the error until the next synchronization succeeds.
A disabled entry (`enabled: false`) is imported without a usable credential.
The current Compose file and `.env.example` no longer pass any token variable,
so when upgrading an installation whose tokens use `token_env`, add those
variables to the container environment for that first start (or disable or
remove the entries), confirm the imported tokens under **Security → Event API
tokens**, then remove the variables again.


## Backups and rollback

A production recovery set keeps `config`, `state`, and external `secrets`
together with the exact deployment image/reference.

Private state snapshots preserve database resources and owner-scoped secrets.
Portable exports intentionally omit passwords, Event API token values, and
destination credentials.

Current development uses database schema **18**. Supported older databases are
migrated transactionally; take a verified snapshot before upgrading.
Historical rollback notes for older schema transitions remain in their original
release/acceptance files.

See [current-configuration-model.md](current-configuration-model.md),
[platform-state.md](platform-state.md), and
[data-portability.md](data-portability.md).
