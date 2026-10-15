# WebUI

Current Nowlert packages a responsive, dependency-free management interface in
the application image. The browser uses the authenticated same-origin
`/api/v2` contract and never needs direct access to SQLite or secret files.

Historical v3.1.0 screenshots in this guide illustrate older layouts. Current
development has newer management workflows; follow the written steps below.

## Activation

```yaml
http:
  enabled: true
  host: 0.0.0.0
  port: 8080

api:
  enabled: true

platform:
  enabled: true
  state_dir: /nowlert/state
  configuration_model: platform_database_v1
  secure_cookies: false

webui:
  enabled: true
  public_url: ""
  enforce_https: false
```

On an empty platform database, container output includes a short-lived,
single-use setup token. Open the WebUI and use it to choose the first
administrator username and password. No default account exists.

Use direct HTTP only on a trusted private network. Public or otherwise
untrusted deployments should terminate TLS at a trusted reverse proxy and set:

```yaml
platform:
  secure_cookies: true

webui:
  public_url: "https://nowlert.example.com"
  enforce_https: true
```

## Navigation

### Dashboard / Overview

The Dashboard combines the operational state that is most useful during normal
administration:

- administrator notices;
- event/delivery metrics over selectable time ranges;
- recent activity;
- top sources and destinations;
- health state;
- complete Integration/Input → Route → Destination flow; and
- independent working, disabled, warning, and error states.

The delivery chart plots cumulative delivery outcomes with a thin pulsing yellow
line and animated pulses at recorded events. The animation restarts when the
Dashboard is entered or refreshed; reduced-motion preferences disable it. The
chart shares its selected time range with the Dashboard controls and has no
manual replay button.

![Historical v3.1.0 Dashboard](images/v3.1.0-dashboard.png)

### Destinations

Destination owners can create, edit, preview, test, enable/disable,
share/private, and delete their own destinations. Sharing preserves the
creator's owner identity. Administrators can inspect, preview, and test another
user's destination, while its configuration remains view-only.

Credentials are write-only. The WebUI can indicate that a credential exists,
but normal read APIs do not return the stored webhook URL, password, token, or
secret-file path. A positive test state means a real destination test passed;
saving a credential alone is not presented as validation.

### Route assignments

In **Destinations**, create or edit a destination and select **Manage routes**.
Choose the built-in integration/input routes, select **Done**, then save the
destination. Done updates the form; **Save changes** (or **Add destination**)
persists the assignments. There is no separate Sources or Routes page.

Built-in integrations are packaged application capabilities. The normalized
input badges are **SMTP**, **HTTP**, and **Redfish**. Dedicated matching routes
are evaluated before wildcard **Fallback** routes.

### Filtering

Open **Filtering** to configure destination-specific integration filters for
severity, status and supported application fields. Keep source notifications
broad, then suppress unwanted events centrally. Administrative deterministic
processing settings appear under **Integration behavior** on this page as well:
Xen Orchestra job/run ID visibility, Zabbix problem ID visibility, Dell iDRAC
trusted management clients, UniFi Protect device aliases, Home Assistant
endpoint/component aliases, and Redfish deduplication.

### Routing Flow

Routing Flow shows the active integration, filter, and destination topology. Its
card highlight follows route type: direct paths pulse yellow, filtered paths
pulse grey, and endpoints shared by both use a split yellow/grey pulse. Filter
criteria and routing behavior are unchanged.
### Event API tokens

Open **Profile menu → Security → API tokens** to issue, rotate or revoke an Event API token.

Event API tokens authorize external applications to submit
`POST /api/v2/events`. They are not required for SMTP, dedicated vendor webhook
endpoints, Redfish subscriptions, WebUI login, or destination delivery.

Token values are displayed only at creation or successful rotation. The list
shows safe metadata such as source scopes, rate limit, last use, and state.
Rotate or revoke a token instead of trying to retrieve its previous value.

### Delivery History

Delivery History shows normalized event identity, source/input, destination,
attempt, outcome, safe error state, and time without exposing response bodies or
credentials.

The v3.1.2 UI keeps the corrected Delivery History presentation without
redundant/empty status decoration.

Pagination behavior is shared with Audit Log:

- **First / Previous / Next / Last** remain available;
- the editable page number is embedded in `Page [n] of N - X items`;
- pressing Enter in that field performs direct navigation;
- **Top** sits on the left side of the bottom control row;
- **Entries** sits on the right side of the same row;
- page size persists; and
- the header **Bottom** shortcut and page-change scroll behavior remain.

![Historical v3.1.0 Delivery History](images/v3.1.0-delivery-history.png)

### Audit Log

Audit Log records protected mutations using bounded, secret-free detail. Users
see activity allowed by the ownership model; administrators can inspect all
retained audit events.

It uses the same v3.1.2 pagination contract as Delivery History.

### Users

Administrators can:

- create regular or administrator accounts;
- enable/disable accounts;
- reset another user's password; and
- permanently delete an eligible user after explicit confirmation.

Deletion is protected by server-side account/ownership safety checks and is
audited. The last enabled administrator cannot be removed through a path that
would leave the platform without administrative access.

The sidebar profile chip uses the same authoritative account role as access
control, so administrator accounts display **Admin** and regular accounts
display **User**.

### Settings

Settings includes:

- language, IANA timezone, and 12/24-hour clock;
- scheduled-only housekeeping with Enabled/Disabled state and recommended retention choices for Delivery History, Audit Log, and backup-run records; and
- administrative update checks.

Integration behavior controls live under **Filtering**.

Each settings record has an independent error boundary. One invalid record does
not make unrelated settings or pages unavailable.

### Backups and Data tools

The Backups administration dashboard provides summary health, configured destinations, scheduled backup settings, portable Data Tools, local Recovery snapshots, and Stored copies discovered on Local/NFS/SMB targets.

The administration UI provides:

- complete recovery snapshots containing SQLite state/history, managed secrets,
  and mounted bootstrap configuration when available;
- individual local snapshot deletion after confirmation;
- Local/NFS/SMB backup destinations and discovery of snapshots stored there;
- scheduled daily, weekly, or monthly backup execution;
- manual backup runs;
- restore from either local or Local/NFS/SMB storage using local staging,
  integrity verification, a pre-restore safety snapshot and an automatic
  service restart; and
- credential-free Data Tools export/import for user-created configuration only.

Data Tools deliberately excludes users, credentials, token material, Delivery
History and Audit Log. Housekeeping controls local history retention separately.

## Browser security

The WebUI relies on server-enforced security boundaries:

- HttpOnly, SameSite session cookies;
- optional Secure cookie mode;
- CSRF protection for unsafe session requests;
- restrictive content-security and frame policies;
- no credential, CSRF, token, or API-response persistence in localStorage;
- active-user keepalive for the 2-hour idle timeout without background-tab
  polling keeping an unattended session alive;
- a five-minute session-expiry warning and in-place re-authentication that keeps
  the current page and form state available while credentials are revalidated;
- timeout re-authentication preserves user-scoped sessionStorage display
  snapshots for warm first paint, while explicit Sign out purges those caches;
- write-only destination secrets; and
- one-time Event API token display.

## Persistent configuration model

SMTP, HTTP and Redfish listeners are configured through bootstrap settings.
Binding, TLS, authentication and process-level enablement changes require a
Nowlert restart. There is no separate Inputs navigation page.

WebUI-managed resources are database-authoritative under `/nowlert/state`.
`config.yaml` is limited to process/bootstrap concerns such as listeners,
transport security, state location, and WebUI publication. See
[current-configuration-model.md](current-configuration-model.md).

## Current persistent schema

Current development uses database schema **17** and
`platform_database_v1`. Take a verified recovery snapshot before an upgrade
and keep an off-host copy until acceptance passes.
