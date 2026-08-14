# Nowlert CE documentation

This directory contains current operator/developer guidance plus historical
release records.

## Current documentation

Use these guides for the current v3.1.1 release line:

| Guide | Purpose |
|---|---|
| [Current configuration model](current-configuration-model.md) | What belongs in `config.yaml` versus database-authoritative platform state |
| [Deployment](deployment.md) | Docker/Compose operation, immutable promotion flow, upgrade and rollback |
| [WebUI](webui.md) | Current pages, permissions, route editing, history, users and backups |
| [Integrations and inputs](integrations-and-inputs.md) | Built-in integration catalogue and SMTP/HTTP/Redfish input model |
| [Platform routing](platform-routing.md) | Tokens, destinations, routes, fallback behavior, delivery and audit rules |
| [Platform outputs](platform-outputs.md) | Destination adapters and safe output contracts |
| [Platform API](platform-api.md) | `/api/v2` authentication, endpoints, CSRF and event ingestion |
| [Platform state](platform-state.md) | SQLite schema, local accounts, secrets, backup layout and recovery |
| [Data portability](data-portability.md) | Credential-free export/import, private backups, restore and deletion |
| [SMTP security](smtp-security.md) | STARTTLS, SMTP AUTH and trusted-network boundaries |
| [Presentation contract](presentation-contract.md) | Normalized notification presentation rules |
| [Roadmap](roadmap.md) | Shipped milestones and current maintenance priorities |

## Integration guides

Integration-specific setup lives under [`integrations/`](integrations/):

- Dell iDRAC
- Grafana
- Home Assistant
- HPE iLO
- Portainer
- Proxmox
- QNAP
- Redfish
- Supermicro
- Synology
- TrueNAS
- UniFi Network / Protect / Drive

The built-in catalogue is authoritative for which normalized inputs are
available to each integration. A guide may contain product-specific endpoint or
payload examples, but routing always uses the shared integration + input model.

## Release documentation

Current release material:

- [v3.1.1 release notes](releases/v3.1.1.md)
- [v3.1.1 QA checklist](v3.1.1-qa-checklist.md)

Historical notes under `releases/` and historical acceptance/QA checklists are
version snapshots. They are intentionally preserved even when a newer release
changes current behavior.

## Screenshots

Current public screenshots live under `images/` and must be captured from the
release candidate that is actually promoted. Do not publish screenshots that
show passwords, destination URLs, API tokens, setup tokens, private hostnames,
email addresses, or other secret/personal material.

For v3.1.1, the documentation uses:

- `v3.1.1-dashboard.png`
- `v3.1.1-routes.png`
- `v3.1.1-route-editor.png`
- `v3.1.1-users.png`
- `v3.1.1-backups.png`
- `v3.1.1-delivery-history.png`
- `v3.1.1-audit-log.png`

## Documentation validation

Run:

```bash
python tools/validate_current_documentation.py
python -m pytest -q tests/test_comprehensive_readme.py \
  tests/test_v252_documentation_refresh.py \
  tests/test_v310_release_docs.py \
  tests/test_v311_release_docs.py
```

Documentation, release metadata, runtime version, Compose defaults, and current
screenshots should describe the same release before a tag is created.
