# Platform routing and delivery

Nowlert v3.1.1 uses database-authoritative Event API tokens, destinations,
routes, delivery history, and audit state. `config.yaml` is not the normal
editing surface for these resources.

## Event API tokens

An Event API token belongs to one local user. Its plaintext value is generated
with cryptographic randomness, returned only at creation or rotation, and stored
only as a digest.

Token metadata includes:

- name;
- role/source scopes;
- rate limit;
- version;
- expiry;
- last-use time; and
- revocation state.

Tokens authorize `POST /api/v2/events`; they are not WebUI management
credentials. Disabled owners, expired/revoked tokens, out-of-scope sources, and
rate-limit violations are rejected.

## Destinations and secrets

A destination has an owner, display name, output type, public settings, enabled
state, sharing state, and optional private secret reference.

Supported platform destination types are:

- Discord;
- Microsoft Teams;
- Slack;
- generic webhook;
- MQTT; and
- ntfy.

Credential-like keys are rejected from public settings. Webhook URLs,
passwords, tokens, and similar values use the owner-scoped secret store. Normal
read APIs report only safe metadata such as `secret_configured`.

Private destinations are visible to their owner and administrators. Only an
administrator can share a destination. A route may reference a shared
destination without revealing or rotating that destination owner's credential.

## Route identity

Routes belong to one user and point to an owned or explicitly shared
destination.

A route persists:

- integration/source key;
- normalized input type;
- destination;
- numeric priority;
- enabled state; and
- bounded filter criteria.

Matching is deterministic: priority first, then normalized route name for stable
tie-breaking.

## Route filters

The v3.1.1 WebUI presents four meaningful filter groups:

- host patterns;
- event patterns;
- included severities; and
- included statuses.

Host and event filters support include/exclude patterns. Values are
case-insensitive and may use shell-style wildcard patterns such as `backup*` or
`test-*`.

A representative route filter document is:

```json
{
  "hosts": ["pve-*"],
  "events": ["backup*"],
  "severities": ["warning", "critical"],
  "statuses": ["active"],
  "exclude_hosts": ["test-*"],
  "exclude_events": ["heartbeat*"]
}
```

Interpretation:

- host/event include values are ORed within their category;
- separate categories are ANDed;
- explicit host/event exclusions win after include matching;
- only selected severity/status values are included; and
- an unselected severity/status is implicitly excluded in the current route
  editor.

The current UI intentionally does not expose redundant **Excluded Severities**
or **Excluded Statuses** lists.

Included Severity/Status controls support normal single-click additive and
subtractive selection while retaining native range/drag behavior. The available
choices are scoped to the selected integration/input contract.

## Full-list criteria

Selecting the full list is still meaningful configuration. v3.1.1 preserves and
displays full-list severity/status criteria on the Routes page even when the
other criterion is a partial selection. This prevents a saved route from
appearing less constrained or differently configured than it really is.

## Dedicated routes and fallback

Wildcard source routes are **fallback-only**.

Evaluation order:

1. identify the normalized integration and input;
2. evaluate enabled dedicated integration routes;
3. apply route filters;
4. deliver dedicated matches;
5. if no dedicated route matched, evaluate enabled fallback routes; and
6. suppress duplicate delivery to the same destination.

This means a dedicated Dell iDRAC, Zabbix, or other integration route does not
also fan out through a generic fallback unless no dedicated route matched.

## Delivery orchestration

For each selected route, the platform delivery service:

1. rechecks route and destination state;
2. rechecks visibility/ownership;
3. resolves destination secrets internally as the true owner;
4. invokes only the adapter registered for the destination output type;
5. retries only explicitly retryable outcomes, with a bounded attempt count;
   and
6. records a safe history row for each attempt.

Adapter exceptions become bounded safe error codes. Response bodies, secret
values, token values, and raw exception text are not stored in delivery history.

## Delivery History

Delivery History records information needed for operational diagnosis without
turning the history table into a credential or payload archive.

Typical fields include:

- source/integration;
- title and severity;
- route and destination identifiers;
- attempt number;
- outcome/status;
- retryability;
- safe error code/text; and
- timestamp.

v3.1.1 removes redundant visual status badges and standardizes paginated
navigation with the Audit Log. The underlying delivery semantics are unchanged.

## Audit events

Protected token, destination, route, user, backup, settings, and operational
mutations can write audit events. Sensitive keys and credential-like text are
redacted/sanitized before persistence.

v3.1.1 adds audited administrator workflows for user deletion and individual
private-state backup deletion.

## Ownership model

Regular users see only resources allowed by ownership/sharing policy.
Administrators can inspect platform-wide state and perform protected management
operations.

An administrator may create a resource for another owner where the API contract
explicitly permits `owner_user_id`. Regular users cannot select arbitrary
owners or create administrator-only wildcard authority.

## Database authority

Current installations use `platform_database_v1`:

- SQLite is authoritative for destinations, routes, Event API tokens,
  preferences, backup schedules, integration behavior, aliases, users, notices,
  history, and audit state;
- destination credential values remain in private owner-scoped files; and
- `config.yaml` remains the process/bootstrap document.

Legacy migration/compatibility code exists so older installations can be
upgraded safely. It is not a reason to reintroduce removed WebUI-managed YAML
sections into a healthy v3.1.1 deployment.

See [current-configuration-model.md](current-configuration-model.md),
[platform-api.md](platform-api.md), and [platform-state.md](platform-state.md).
