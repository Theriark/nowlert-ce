# Authenticated platform API

Current Nowlert exposes the management plane and Event API through `/api/v2` on
the same HTTP service as the WebUI.

The normal authority model is:

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

Browser sessions have a 2-hour idle expiry and a 24-hour absolute expiry.
Authenticated unsafe writes and explicit `GET /api/v2/session` keepalives refresh
the idle deadline without extending the 24-hour maximum. Session responses expose
both `idle_expires_at` and `expires_at` so clients can warn before timeout.
Logout, password reset, account disable, and private-state restore revoke
affected sessions.

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
| POST | `/api/v2/account/mfa/setup` | session + CSRF | start authenticator enrolment (secret and QR code) |
| PUT | `/api/v2/account/mfa` | session + CSRF | confirm enrolment with an authenticator `code`; returns recovery codes once |
| DELETE | `/api/v2/account/mfa` | session + CSRF | turn multi-factor authentication off (`password` and `code`) |
| POST | `/api/v2/account/mfa/recovery-codes` | session + CSRF | replace recovery codes (`password` and `code`) |
| GET/PUT | `/api/v2/users/{id}/destination-permissions` | administrator (+ CSRF for PUT) | list/set a user's edit and filter permissions on shared destinations |

A wrong current password on `PUT /api/v2/account/password` returns 403 with
`"code": "password_invalid"` and the message "The current password is not
correct." The multi-factor endpoints return 403 with `password_invalid` for a
wrong password and `mfa_invalid` for a wrong authenticator code.

The current user-deletion path is server-side protected. An administrator cannot
delete its own currently authenticated account, and storage ownership/integrity
rules must permit the deletion. Successful deletion writes a `user.delete`
audit event.

### Integrations, preferences, and operations

| Method | Path | Access | Purpose |
|---|---|---|---|
| GET | `/api/v2/integrations` | session | built-in integration catalogue |
| GET | `/api/v2/integration-settings` | session | integration behavior + isolated errors |
| GET/PUT | `/api/v2/integration-settings/{source}` | session / administrator + CSRF | inspect/update one integration record (`xo` and `zabbix` accept only `"show_ids": false`: those IDs are always hidden) |
| GET/PUT | `/api/v2/source-categories` | session / administrator + CSRF | list/update categories |
| DELETE | `/api/v2/source-categories/{source}` | administrator + CSRF | reset category override |
| GET | `/api/v2/preferences` | session | regional preferences |
| PUT | `/api/v2/preferences` | administrator + CSRF | update regional preferences |
| GET | `/api/v2/version` | session | running/advertised version |
| GET | `/api/v2/metrics/{range}` | session | Overview metrics |
| GET | `/api/v2/health-checks` | session | safe operational checks |
| POST | `/api/v2/reboot` | administrator + CSRF | audited restart request |
| GET/PUT | `/api/v2/housekeeping` | administrator + CSRF for PUT | inspect/update history retention |
| PATCH | `/api/v2/configuration/inputs/{smtp,http,redfish}` | administrator + CSRF | enable/disable an input (applies after restart) |

Notices (`/api/v2/notices`) were removed; those paths answer 404.

`GET /api/v2/health-checks` returns the database, configuration, destination
credential, route assignment, backup target, recent delivery and mailbox
synchronization checks, each with `status` `healthy`, `warning` or `error`.

Housekeeping execution is scheduler-only. The persisted daily run key makes the
once-per-day boundary survive container restarts and image updates.

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
| POST | `/api/v2/destinations` | session + CSRF | create an own destination with a write-only secret (an administrator may set `owner_user_id`) |
| GET | `/api/v2/destinations/{id}` | visible session | read secret-free metadata |
| PATCH | `/api/v2/destinations/{id}` | owner + CSRF | update metadata/type/secret |
| DELETE | `/api/v2/destinations/{id}` | owner + CSRF | delete destination |
| POST | `/api/v2/destinations/{id}/preview` | visible session + CSRF | preview payload |
| POST | `/api/v2/destinations/{id}/test` | owner/admin + CSRF | perform destination test |
| GET | `/api/v2/routes` | session | list visible routes + row errors |
| POST | `/api/v2/routes` | session + CSRF | create route |
| GET | `/api/v2/routes/{id}` | owner/admin | return route |
| PATCH | `/api/v2/routes/{id}` | owner/admin + CSRF | update route atomically |
| DELETE | `/api/v2/routes/{id}` | owner/admin + CSRF | delete route |
| POST | `/api/v2/events` | scoped token or session + CSRF | route normalized application event |

Route filters are bounded and normalized server-side. See
[platform-routing.md](platform-routing.md) for dedicated/fallback behavior.

Validation rules worth knowing:

- The URL of a Discord, Microsoft Teams, Slack or Generic webhook destination
  must be a complete, credential-free `https://` address; anything else is
  refused with 400 before the destination is saved, for example "Discord
  webhook URL must be a complete https:// address without a user name or
  password, …".
- Route names are unique across all accounts, ignoring case. A new or renamed
  route that reuses a name answers 409 "A route named … already exists. Choose
  another name." Every writer follows the same rule: the built-in routes seeded
  for each account, configuration import and portability import. A built-in
  route seeded for a later account gets a numbered name such as
  "Checkmk HTTP (2)", which its owner can rename or edit. When Nowlert starts,
  older duplicate names left by earlier versions are renamed the same way; the
  oldest route keeps its name and ownership, assignments and history do not
  change.
- Sharing a destination lets other users select and preview it; only its owner
  or an administrator can send a test delivery (403 otherwise).

### Nowlert Mobile connections

| Method | Path | Access | Purpose |
|---|---|---|---|
| POST | `/api/v2/mobile-connections` | session + CSRF | start pairing a Nowlert Mobile topic (`name`) |
| POST | `/api/v2/mobile-connections/{id}` | session + CSRF | poll the pairing status |

A finished pairing is saved by sending `mobile_connection_id` with a
`nowlert_mobile` destination create (`POST /api/v2/destinations`) or with the
owner's update (`PATCH /api/v2/destinations/{id}`). The topic publish key stays
server-side.

### Routing Flow and Filtering

| Method | Path | Access | Purpose |
|---|---|---|---|
| GET | `/api/v2/routing-flow/{range}` | session | Routing Flow snapshot; range `10m`, `15m`, `1h`, `3h`, `6h`, `1d`, `1m` or `1y` |
| GET | `/api/v2/filters` | session | filtering overview of visible destinations |
| GET/PUT/DELETE | `/api/v2/filters/destinations/{id}` | destination owner (+ CSRF for writes) | read/replace/clear a destination's filters |
| GET/PUT | `/api/v2/filters/destinations/{id}/enabled` | destination owner (+ CSRF for PUT) | turn filtering for a destination on or off |
| GET/PUT/DELETE | `/api/v2/filters/destinations/{id}/sources/{source}` | destination owner (+ CSRF for writes) | one integration's filter on that destination |

### Email Alerts

Email Alerts endpoints are owner-scoped: each account sees and changes its own
mailboxes, groups and rules, plus mailboxes shared with it; an administrator may
create resources for another account with `owner_user_id`.

| Method | Path | Access | Purpose |
|---|---|---|---|
| GET | `/api/v2/email-overview` | session | mailbox, group, rule and recent message summary |
| GET | `/api/v2/email-activity` | session | recent messages with their processing result |
| GET | `/api/v2/email-mailbox-providers` | session | which providers (Gmail, Microsoft 365, IMAP) are configured |
| GET/POST | `/api/v2/email-mailboxes` | session (+ CSRF for POST) | list/add mailboxes |
| GET/PATCH/DELETE | `/api/v2/email-mailboxes/{id}` | owner (+ CSRF for writes) | read/update/remove a mailbox |
| POST | `/api/v2/email-mailboxes/{id}/oauth-start` | owner + CSRF | start the Google or Microsoft sign-in |
| POST | `/api/v2/email-mailboxes/{id}/oauth-complete` | owner + CSRF | finish the sign-in for that mailbox |
| POST | `/api/v2/email-mailboxes/oauth-complete` | session + CSRF | finish a sign-in from its OAuth `state` and `code` |
| POST | `/api/v2/email-mailboxes/oauth-failed` | session + CSRF | record a provider sign-in error from its `state` |
| POST | `/api/v2/email-mailboxes/{id}/sync` | owner + CSRF | synchronize the mailbox now |
| GET/POST | `/api/v2/email-mailboxes/{id}/folders` | owner (+ CSRF for POST) | list folders/labels or choose the watched ones |
| GET/POST | `/api/v2/email-groups` | session (+ CSRF for POST) | list/create rule groups |
| GET/PATCH/DELETE | `/api/v2/email-groups/{id}` | owner (+ CSRF for writes) | read/update/delete a group |
| GET/POST | `/api/v2/email-rules` | session (+ CSRF for POST) | list/create rules |
| GET/PATCH/DELETE | `/api/v2/email-rules/{id}` | owner (+ CSRF for writes) | read/update/delete a rule |
| POST | `/api/v2/email-rules/evaluate` | session + CSRF | test the rules against a stored message (`message_id`) |
| GET | `/api/v2/email-messages/{id}/preview` | owner | sandboxed, body-only message preview |
| POST | `/api/v2/email-messages/{id}/{action}` | owner + CSRF | `reprocess`, `mute-similar`, `ignore-sender` or `change-severity` |

Repeated mailbox synchronization failures appear in the `mailbox_sync` health
check; see [Integrations and inputs](integrations-and-inputs.md) for Email Alerts
setup.

### Delivery and audit history

| Method | Path | Access | Purpose |
|---|---|---|---|
| GET | `/api/v2/deliveries` | session | compatible delivery list |
| GET | `/api/v2/deliveries/page/{page}` | session | paginated delivery history |
| GET | `/api/v2/deliveries/page/{page}/size/{size}` | session | paginated history with explicit size |
| GET | `/api/v2/audit-events` | session | compatible audit list |
| GET | `/api/v2/audit-events/summary` | session | visible audit totals: `total` plus `current` and `previous` seven-day counts of `success`, `warning`, `failed` and `other` (the Audit log trend cards) |
| GET | `/api/v2/audit-events/page/{page}` | session | paginated audit history |
| GET | `/api/v2/audit-events/page/{page}/size/{size}` | session | paginated audit history with size |

Delivery history follows the destination: every account, administrators
included, sees the attempts to destinations it owns and every attempt to a
shared destination, whoever owns the route that matched; attempts to another
account's private destination are not returned. The audit endpoints answer
200 to every signed-in account, but only administrators receive events: for a
regular user the list is empty and the summary counts are zero. Administrators
see every audit event except those about other users' private destinations
and their filters. Safe
history does not persist destination credentials, token values, response bodies,
or raw adapter exception text.

### Backup targets and recovery snapshots

| Method | Path | Access | Purpose |
|---|---|---|---|
| GET/PUT | `/api/v2/backup-settings` | administrator + CSRF for PUT | schedule/selected target |
| GET/POST | `/api/v2/backup-targets` | administrator + CSRF for POST | list/create Local/NFS/SMB target |
| GET/PATCH/DELETE | `/api/v2/backup-targets/{id}` | administrator + CSRF for mutation | inspect/update/delete target |
| POST | `/api/v2/backup-targets/{id}/test` | administrator + CSRF | test target connectivity/write |
| GET | `/api/v2/backup-targets/{id}/backups` | administrator | list verified snapshots stored on target |
| POST | `/api/v2/backup-targets/{id}/backups/{backup}/restore` | administrator + CSRF | stage/verify/restore external snapshot and restart |
| POST | `/api/v2/backups/run` | administrator + CSRF | run scheduled-style target backup |
| GET | `/api/v2/backups` | administrator | list verified local recovery snapshots |
| POST | `/api/v2/backups` | administrator + CSRF | create complete local recovery snapshot |
| DELETE | `/api/v2/backups/{id}` | administrator + CSRF | permanently delete one local snapshot |
| POST | `/api/v2/backups/{id}/restore` | administrator + CSRF | restore exact snapshot and restart |

Recovery snapshot deletion remains separate from restore. New snapshots contain the
complete SQLite state, Nowlert-managed secret files and mounted `config.yaml` when
available. External restores are copied to local staging and fully validated before
live state is replaced.

### Portability and legacy migration

| Method | Path | Access | Purpose |
|---|---|---|---|
| GET | `/api/v2/portability/export` | administrator | credential-free platform JSON |
| POST | `/api/v2/portability/preview` | administrator + CSRF | validate/fingerprint import |
| POST | `/api/v2/portability/import` | administrator + CSRF | apply unchanged confirmed import |
| POST | `/api/v2/migrations/v1/preview` | administrator + CSRF | preview legacy YAML import |
| POST | `/api/v2/migrations/v1/import` | administrator + CSRF | apply confirmed legacy import |
| GET | `/api/v2/configuration/inventory` | administrator | secret-free mounted-config inventory |
| POST | `/api/v2/configuration/migration/preview` | administrator + CSRF | retired on a normal installation: answers 400 "routing-authority migration is retired by database-authoritative resources" |
| POST | `/api/v2/configuration/migration/apply` | administrator + CSRF | retired on a normal installation: answers 400 with the same message |
| PUT | `/api/v2/configuration/routing-authority` | administrator + CSRF | retired on a normal installation: answers 400 "routing authority is fixed to database-authoritative resources" |

The three configuration-authority endpoints belonged to the transition from
YAML to database resources. They still exist so an older client gets a clear
answer, but every current installation uses `platform_database_v1` and they
refuse to run. Do not switch a healthy current deployment back to legacy YAML
resource authority.

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
