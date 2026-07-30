# WebUI

Nowlert v2.5.2 packages a responsive, dependency-free management interface in
the image. It uses the authenticated `/api/v2` contract over the same origin.

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

On first start, read the short-lived setup token from the container log and
open the WebUI. Choose the first administrator credentials. No default account
exists.

Use direct HTTP only on a trusted private network. A public or untrusted
deployment must terminate TLS at a trusted reverse proxy and enable secure
cookies and HTTPS enforcement.

## Navigation

### Overview

- administrator notices
- routed integrations, destinations, routes, token, request, and success metrics
- complete Integration/Input → Route → Destination flow
- independent working, disabled, and error indicators
- recent deliveries

### Sources

The complete built-in integration catalogue. Integrations are always present
and are not runtime records. Categories are editable at integration level.
Available input badges are only SMTP, HTTP, and Redfish.

### Destinations

Create, edit, preview, test, enable/disable, share/private, and delete
destinations. Credentials are write-only. A positive test result reflects a
real destination test; merely storing a credential is not presented as a
successful validation.

### Routes

Create routes from an integration/input pair to a destination. Routes support
semantic priority and include/exclude filters for hosts, events, severities,
and statuses. Wildcard routes are labelled Fallback and are evaluated only
when no dedicated route matches.

### API access

Event API tokens authorize external applications to submit
`POST /api/v2/events`. They are not required for SMTP, dedicated HTTP webhook
endpoints, Redfish subscriptions, WebUI login, or destination delivery.

Token values are displayed only once. The list shows scopes, rate limit, last
use, and status. Rotate or revoke a token instead of trying to retrieve it.

### Delivery history and Audit log

Delivery history shows normalized event identity, input, attempts, destination,
status, and safe errors. Audit history records protected mutations without
secret values. Users see the resources allowed by the platform ownership model;
administrators can review all activity.

### Users

Administrators can create users, enable/disable accounts, and reset another
user's password. The last enabled administrator is protected.

### Settings

- language, IANA timezone, and 12/24-hour clock
- Xen Orchestra job/run ID visibility
- Zabbix problem ID visibility
- Dell iDRAC trusted management clients
- UniFi Protect device aliases
- Home Assistant endpoint/component aliases
- Redfish deduplication window

Each settings record has an independent error boundary.

### Inputs

SMTP, HTTP, and Redfish are managed independently. Changing their enabled
state requires a Nowlert restart because listener and transport startup are
process-level operations.

### Backups and Data tools

- local snapshots
- named Local/NFS/SMB backup destinations
- daily, weekly, or monthly scheduled backups
- manual scheduled-backup execution
- credential-free export/import
- guarded private-state restore

## Browser security

- HttpOnly, SameSite session cookies
- optional Secure cookie mode
- CSRF protection for unsafe session requests
- restrictive content security policy and frame protection
- no credential, CSRF, token, or API-response storage in localStorage
- write-only destination secrets
- one-time token display

## Migration

On the first v2.5 start, supported v2.4 destinations, routes, API applications,
regional preferences, backup scheduling, integration behavior, aliases, and
deduplication settings are imported into schema 8. The mounted YAML is then
normalized atomically. Later WebUI edits use isolated database resources.
