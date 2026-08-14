# Authenticated platform API

Nowlert v3.1.1 exposes the management plane and Event API through `/api/v2` on
the same HTTP service as the WebUI.

The normal v3.1.1 authority model is:

- `config.yaml` for process/bootstrap, listeners, transport security, state
  location, and WebUI publication;
- SQLite under `/nowlert/state` for WebUI-managed platform resources; and
- owner-scoped private secret files for credential values.

The browser and normal read API never receive stored destination credentials,
password hashes, session tokens, API-token hashes, or secret-file paths.

## Activation

```yaml
http:
  enabled: true
  host: "0.0.0.0"
  port: 8080

api:
  enabled: true

platform:
  enabled: true
  state_dir: "/nowlert/state"
  configuration_model: "platform_database_v1"
  secure_cookies: false
```

Do not expose port 8080 directly to an untrusted network. Use a trusted reverse
proxy with TLS, preserve the original client address, and do not cache `/api/v2`
responses.

## First-run bootstrap

On an empty database, `GET /api/v2/bootstrap` reports that setup is required.
The application creates a random short-lived setup token, stores only its
SHA-256 digest, and prints the plaintext value once to container output.

`POST /api/v2/bootstrap` consumes the token while creating the first
administrator and browser session. No default username/password exists.

## Browser authentication

Browser and management operations use a local session:

- `POST /api/v2/session` accepts username/password;
- the server returns an HttpOnly, SameSite=Strict session cookie;
- secure deployments use `__Host-` cookie names and the Secure attribute;
- login/bootstrap responses include the CSRF value; and
- session-authenticated `POST`, `PUT`, `PATCH`, and `DELETE` requests must send
  `X-CSRF-Token`.

Sessions have idle and absolute expiry. Logout, password reset, account disable,
and private-state restore revoke affected sessions.

## Event API tokens

Event API tokens are accepted by `POST /api/v2/events`. They do not grant
management access.

Tokens are:

- owned by a local account;
- explicitly source-scoped;
- rate-limited per token/client;
- returned only at creation or rotation; and
- stored only as digests.

## Core endpoints

### Session and users

| Method | Path | Access | Purpose |
|---|---|---|---|
| GET | `/api/v2/bootstrap` | public | report first-run setup state |
| POST | `/api/v2/bootstrap` | setup token | create first administrator/session |
| POST | `/api/v2/session` | public | authenticate local account |
| GET | `/api/v2/session` | session | return current account/session metadata |
| DELETE | `/api/v2/session` | session + CSRF | revoke current session |
| GET | `/api/v2/users` | administrator | list accounts |
| POST | `/api/v2/users` | administrator + CSRF | create account |
| GET | `/api/v2/users/{id}` | administrator | return account |
| PATCH | `/api/v2/users/{id}` | administrator + CSRF | enable/disable account |
| DELETE | `/api/v2/users/{id}` | administrator + CSRF | permanently delete eligible account |
| PUT | `/api/v2/users/{id}/password` | administrator + CSRF | reset password/sessions |
| GET | `/api/v2/users/{id}/tokens` | administrator | list owner token metadata |
| GET | `/api/v2/users/{id}/routes` | administrator | list owner routes |
| PUT | `/api/v2/account/password` | session + CSRF | change current password |
| PUT/DELETE | `/api/v2/account/avatar` | session + CSRF | set/remove current avatar |

v3.1.1 user deletion is server-side protected. An administrator cannot delete
its own currently authenticated account, and storage ownership/integrity rules
must permit the deletion. Successful deletion writes a `user.delete` audit
event.

### Integrations, preferences, and operations

| Method | Path | Access | Purpose |
|---|---|---|---|
| GET | `/api/v2/integrations` | session | built-in integration catalogue |
| GET | `/api/v2/integration-settings` | session | integration behavior + isolated errors |
| GET/PUT | `/api/v2/integration-settings/{source}` | session / administrator + CSRF | inspect/update one integration record |
| GET/PUT | `/api/v2/source-categories` | session / administrator + CSRF | list/update categories |
| DELETE | `/api/v2/source-categories/{source}` | administrator + CSRF | reset category override |
| GET | `/api/v2/preferences` | session | regional preferences |
| PUT | `/api/v2/preferences` | administrator + CSRF | update regional preferences |
| GET | `/api/v2/version` | session | running/advertised version |
| GET/POST | `/api/v2/notices` | session / administrator + CSRF | list/publish notices |
| POST | `/api/v2/notices/{id}/dismiss` | session + CSRF | dismiss ordinary notice |
| PATCH/DELETE | `/api/v2/notices/{id}` | administrator + CSRF | edit/resolve notice |
| GET | `/api/v2/metrics/{range}` | session | Overview metrics |
| GET | `/api/v2/health-checks` | session | safe operational checks |
| POST | `/api/v2/reboot` | administrator + CSRF | audited restart request |

### Event API tokens

| Method | Path | Access | Purpose |
|---|---|---|---|
| GET | `/api/v2/tokens` | session | list current-user token metadata |
| POST | `/api/v2/tokens` | session + CSRF | create token and return value once |
| POST | `/api/v2/tokens/{id}/rotate` | owner/admin + CSRF | rotate and return value once |
| POST | `/api/v2/tokens/{id}/revoke` | owner/admin + CSRF | permanently revoke token |
| PATCH/DELETE | `/api/v2/tokens/{id}` | owner/admin + CSRF | change state/delete token metadata |

### Destinations and routes

| Method | Path | Access | Purpose |
|---|---|---|---|
| GET | `/api/v2/destinations` | session | list visible destinations + row errors |
| POST | `/api/v2/destinations` | administrator + CSRF | create destination/write-only secret |
| GET | `/api/v2/destinations/{id}` | visible session | read secret-free metadata |
| PATCH | `/api/v2/destinations/{id}` | administrator + CSRF | update metadata/type/secret |
| DELETE | `/api/v2/destinations/{id}` | administrator + CSRF | delete unused destination |
| POST | `/api/v2/destinations/{id}/preview` | visible session + CSRF | preview payload |
| POST | `/api/v2/destinations/{id}/test` | administrator + CSRF | perform destination test |
| GET | `/api/v2/routes` | session | list visible routes + row errors |
| POST | `/api/v2/routes` | administrator + CSRF | create route |
| GET | `/api/v2/routes/{id}` | owner/admin | return route |
| PATCH | `/api/v2/routes/{id}` | owner/admin + CSRF | update route atomically |
| DELETE | `/api/v2/routes/{id}` | owner/admin + CSRF | delete route |
| POST | `/api/v2/events` | scoped token or session + CSRF | route normalized application event |

Route filters are bounded and normalized server-side. See
[platform-routing.md](platform-routing.md) for dedicated/fallback behavior.

### Delivery and audit history

| Method | Path | Access | Purpose |
|---|---|---|---|
| GET | `/api/v2/deliveries` | session | compatible delivery list |
| GET | `/api/v2/deliveries/page/{page}` | session | paginated delivery history |
| GET | `/api/v2/deliveries/page/{page}/size/{size}` | session | paginated history with explicit size |
| GET | `/api/v2/audit-events` | session | compatible audit list |
| GET | `/api/v2/audit-events/page/{page}` | session | paginated audit history |
| GET | `/api/v2/audit-events/page/{page}/size/{size}` | session | paginated audit history with size |

History is owner-filtered. Administrators may inspect all retained rows. Safe
history does not persist destination credentials, token values, response bodies,
or raw adapter exception text.

### Backup targets and private state backups

| Method | Path | Access | Purpose |
|---|---|---|---|
| GET/PUT | `/api/v2/backup-settings` | administrator + CSRF for PUT | schedule/selected target |
| GET/POST | `/api/v2/backup-targets` | administrator + CSRF for POST | list/create Local/NFS/SMB target |
| GET/PATCH/DELETE | `/api/v2/backup-targets/{id}` | administrator + CSRF for mutation | inspect/update/delete target |
| POST | `/api/v2/backup-targets/{id}/test` | administrator + CSRF | test target connectivity/write |
| POST | `/api/v2/backups/run` | administrator + CSRF | run scheduled-style external backup |
| GET | `/api/v2/backups` | administrator | list verified private snapshots |
| POST | `/api/v2/backups` | administrator + CSRF | create private state snapshot |
| DELETE | `/api/v2/backups/{id}` | administrator + CSRF | permanently delete one private snapshot |
| POST | `/api/v2/backups/{id}/restore` | administrator + CSRF | restore exact snapshot after confirmation |

v3.1.1 exposes private snapshot deletion separately from restore. Deletion is
audited and affects only the selected backup directory.

### Portability and legacy migration

| Method | Path | Access | Purpose |
|---|---|---|---|
| GET | `/api/v2/portability/export` | administrator | credential-free platform JSON |
| POST | `/api/v2/portability/preview` | administrator + CSRF | validate/fingerprint import |
| POST | `/api/v2/portability/import` | administrator + CSRF | apply unchanged confirmed import |
| POST | `/api/v2/migrations/v1/preview` | administrator + CSRF | preview legacy YAML import |
| POST | `/api/v2/migrations/v1/import` | administrator + CSRF | apply confirmed legacy import |
| GET | `/api/v2/configuration/inventory` | administrator | secret-free mounted-config inventory |

Compatibility/recovery endpoints for older configuration-authority transitions
may remain present, but a normal v3.1.1 installation uses
`platform_database_v1`. Do not switch a healthy current deployment back to
legacy YAML resource authority.

## Session example

Login and store cookies:

```bash
curl --fail-with-body \
  --cookie-jar /tmp/nowlert.cookies \
  --header 'Content-Type: application/json' \
  --data '{"username":"administrator","password":"REPLACE_ME"}' \
  https://nowlert.example.com/api/v2/session
```

The response includes `csrf_token`. Send that value on state-changing browser
session requests:

```bash
curl --fail-with-body \
  --cookie /tmp/nowlert.cookies \
  --header 'Content-Type: application/json' \
  --header 'X-CSRF-Token: RETURNED_LOGIN_VALUE' \
  --data '{"name":"Home lab application","source_scopes":["home_assistant"],"rate_limit_per_minute":60}' \
  https://nowlert.example.com/api/v2/tokens
```

## Event submission example

```bash
curl --fail-with-body \
  --header 'Authorization: Bearer PLATFORM_TOKEN' \
  --header 'Content-Type: application/json' \
  --data '{
    "schema":"nowlert.event.v1",
    "source":"home_assistant",
    "title":"Synthetic warning",
    "message":"A bounded application event.",
    "severity":"warning",
    "status":"active"
  }' \
  https://nowlert.example.com/api/v2/events
```

The token must include the submitted source scope. Routing resolves destination
credentials internally and never returns them to the submitting application.

## Safe response contract

Management responses use no-store/browser hardening headers. Errors are bounded
and sanitized. Preview/test responses expose safe transport outcomes rather
than response bodies or secrets.

For state ownership, backup, and migration details see
[platform-state.md](platform-state.md) and
[data-portability.md](data-portability.md).
