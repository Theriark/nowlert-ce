# Backend and event API

Nowlert v1.9.0 introduced the token-authenticated administration and event API
(`/api/...`). It reuses the existing dispatcher, notification model, router,
formatters, and outputs; it is not a second delivery pipeline.

The API is **enabled by default**: when `config.yaml` has no `api.enabled`
setting, Nowlert serves it, and the supplied `config/config.example.yaml` sets
`api.enabled: true`. Set `api.enabled: false` to turn off both this API and the
`/api/v2` platform API (the WebUI then cannot work). `GET /api/health` needs no
token; every other endpoint below needs an Event API token.

The local-session, owned-resource, preview, and user-scoped event contract
used by the WebUI is documented in the
[v2 authenticated platform API guide](platform-api.md).

## Authentication

Tokens are Event API tokens stored as hashes in platform state. Issue, rotate
and revoke them in the WebUI under **Security → Event API tokens** (select your
account name at the bottom of the sidebar, then **Security**) or through
`/api/v2/tokens` ([platform API](platform-api.md)); the value is shown only
once. `config.yaml` can no longer define tokens: under the current
`platform_database_v1` model an `api.tokens` section is refused with
"api.tokens is database-managed; edit applications in the WebUI". An older
installation's YAML tokens are imported once by the one-way migration, under
their YAML names; only a name that the same owner already uses gets "Legacy "
in front ("Legacy NAME", then "Legacy NAME 2"). An enabled token whose
credential cannot be read stops the whole migration. `token_sha256` (64 hexadecimal characters) is used first; otherwise a
`token_env` variable that is set; otherwise `token_file`, which must be a
regular file (not a symbolic link) readable by Nowlert with no group or other
permissions (mode `0600` or `0400`) and holding at most 4096 characters.
A file that breaks any of these rules counts as unreadable. (See
[database-authoritative resources](database-authoritative-resources.md).)
Send a token as `Authorization: Bearer TOKEN` or `X-Nowlert-Token: TOKEN`.

Roles:

- `application`: submit only the integrations allowed for the token;
- `admin`: access backend administration endpoints and any source; only an
  administrator can issue an `admin` token.

Event API tokens are not browser sessions and cannot manage v2 platform
resources. Do not mix them with the `/api/v2` session authentication model.

## Endpoints

| Method | Path | Access | Result |
|---|---|---|---|
| GET | `/api/health` | public when enabled | version and uptime |
| POST | `/api/events` | application/admin | normalized event submission |
| GET | `/api/config` | admin | recursively masked configuration |
| PUT | `/api/config` | admin | validate, back up, atomically replace, reload |
| POST | `/api/config/validate` | admin | schema errors without saving |
| GET | `/api/logs` | admin | last 200 sanitized application-log lines |
| POST | `/api/preview` | admin | real Discord or Teams formatter payload |
| POST | `/api/test-send` | admin | route through configured outputs |

Example generic event:

```bash
curl -sS \
  -H 'Authorization: Bearer TOKEN' \
  -H 'Content-Type: application/json' \
  --data '{
    "schema":"nowlert.event.v1",
    "source":"home_lab",
    "title":"Synthetic warning",
    "message":"A bounded application event.",
    "severity":"warning",
    "status":"active",
    "timestamp":"2026-07-15T21:00:00Z"
  }' \
  http://127.0.0.1:18080/api/events
```

The token must allow `home_lab`, and a route for `home_lab` (or a wildcard
fallback route) must be assigned to at least one enabled destination under
**Destinations → Edit → Manage routes**.

## Configuration safety

`GET /api/config` returns `<configured>` for secret leaves. Sending that masked
document back in `PUT /api/config` preserves the existing secret values. The
service validates before writing, creates mode-`0600` backups, uses an atomic
replace, reloads configuration under a lock, and retains the ten newest
backups. `config.yaml` holds only the bootstrap settings; destinations, routes
and Event API tokens live in platform state and are not changed by
`PUT /api/config`. Listener bind address, port, maximum request size, SMTP
transport, and TLS settings require a controlled container restart. Audit
records omit bodies, credentials, and query strings and are
created mode `0600`.

The API should remain on a trusted network or behind TLS termination in Nginx
Proxy Manager. Do not publish port 8080 directly to the Internet. Apply
firewall restrictions, use long random tokens, mount token files read-only,
and configure conservative per-token rate limits.
