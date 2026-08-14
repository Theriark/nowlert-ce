# Database-authoritative resources

Nowlert v3.1.1 uses `platform_database_v1` to separate process bootstrap from
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
- notices;
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

## Backups and rollback

A production recovery set keeps `config`, `state`, and external `secrets`
together with the exact deployment image/reference.

Private state snapshots preserve database resources and owner-scoped secrets.
Portable exports intentionally omit passwords, Event API token values, and
destination credentials.

v3.1.1 keeps schema 9, so no database migration is required from v3.1.0.
Historical rollback notes for older schema transitions remain in their original
release/acceptance files.

See [current-configuration-model.md](current-configuration-model.md),
[platform-state.md](platform-state.md), and
[data-portability.md](data-portability.md).
