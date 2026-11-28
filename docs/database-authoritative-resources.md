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

A legacy `api.tokens` entry that names an environment variable
(`token_env`) is imported only if that variable is set when the migration
runs. The current Compose file and `.env.example` no longer pass any token
variable, so when upgrading such an installation, add the variable to the
container environment for that first start, confirm the imported "Legacy …"
token under **Security → Event API tokens**, then remove it again.

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
