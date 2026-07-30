# Current configuration model

Nowlert v2.5.2 separates process bootstrap from WebUI-managed resources.

## Bootstrap file

`config/config.yaml` is intentionally small. It controls only:

- SMTP binding, STARTTLS, and SMTP AUTH bootstrap
- HTTP binding and request-size limits
- API and platform activation
- persistent state location and backup retention
- secure-cookie mode
- WebUI activation, canonical URL, and HTTPS enforcement

Listener, certificate, binding, and cookie-mode changes require a container
restart.

## Platform state

The persistent `/nowlert/state` mount contains the SQLite database and
private state required by the WebUI. SQLite is authoritative for:

- destinations and credential references
- routes, input types, priorities, and include/exclude filters
- Event API token hashes, scopes, rate limits, and usage
- regional preferences and backup schedules
- integration categories, behavior, aliases, and Redfish deduplication
- users, sessions, notices, audit events, and delivery history

Destination secrets remain in private owner-only files and are never returned
through the normal read API.

## Removed legacy YAML sections

Fresh v2.5 configurations must not recreate these formerly WebUI-managed
sections:

- `outputs`
- `routing`
- `notifications`
- `presentation`
- `home_assistant`
- `redfish`
- `api.tokens`
- `platform.backups`
- `webui.language`

The first successful v2.5 migration imports supported v2.4 resources and then
atomically writes the normalized `platform_database_v1` document.

## Persistent paths

The supplied production Compose definition mounts:

```text
./config          -> /nowlert/config
./state           -> /nowlert/state
./logs            -> /nowlert/logs
./secrets         -> /run/secrets (read-only)
./external-backups -> /nowlert/external-backups
```

The public example configuration uses `/nowlert/state`, matching the
production Compose file. A legacy `/nowlert/config/platform-state` directory
may still exist on installations created before the explicit state mount; do
not move or delete it without confirming the active `platform.state_dir`.

## Backup boundary

A complete recovery backup keeps these together:

1. mounted `config`
2. mounted `state`
3. mounted external `secrets`, when used
4. the exact image tag and deployment definition

Portable JSON export is useful for migration but is not a replacement for a
matched private-state backup because it deliberately omits credentials,
passwords, sessions, and token values.
