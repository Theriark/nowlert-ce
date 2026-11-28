# Nowlert roadmap

The roadmap records shipped milestones separately from future candidates. A
candidate is not a promise or assigned release date until it is accepted into a
tracked release scope.

## Shipped

### v2.4.0 — Integrations and inputs

- built-in integration catalogue;
- normalized SMTP, HTTP, and Redfish input model (the fourth input, Email
  Alerts from connected mailboxes, was added after v3.1.6 on the v27.0.0
  release-candidate line; see
  [Development after v3.1.6](releases/post-v3.1.6-development.md));
- input-aware routes; and
- integration category state.

### v2.5.0–v2.5.5 — Database authority and delivery hardening

- database-authoritative destinations, routes, Event API tokens, and settings;
- bootstrap-only `config.yaml`;
- fallback-only wildcard routing and duplicate-delivery suppression;
- include/exclude route filters;
- packaged source artwork;
- destination-test state and delivery history; and
- Discord/Microsoft Teams transport/presentation corrections.

### v3.0.0 — Nowlert identity

- final Nowlert product/runtime identity;
- `Theriark/nowlert-ce` repository and container coordinates;
- `NOWLERT_*` environment variables and `/nowlert` paths;
- schema-9 compatibility; and
- guarded release publication.

### v3.1.0 — Amber WebUI and operational quality

- professional Dashboard analytics and routing flow;
- approved owl branding and Amber Accent UI;
- browser Back/Forward section navigation;
- management-page layout and pagination polish;
- safer Integration Settings editing; and
- version-aware deployment health gates.

### v3.1.1 — QA and immutable promotion hardening

- administrator user deletion with safety/audit controls;
- individual private state backup deletion;
- authoritative Admin/User profile chip;
- Delivery History presentation correction;
- unified Delivery History/Audit Log pagination footer;
- simplified Included Severity/Status route editing;
- mouse-only additive route selection with native range behavior retained;
- integration-scoped route criteria and correct full-list display;
- `development` / `stage` / `main` environment branch alignment;
- build-once immutable Development → Stage → Production Reference promotion;
- release tag bound to current `main`; and
- stable GHCR/Docker Hub aliases copied from the approved digest without rebuild.

### v3.1.2 — Maintenance and release-safety hardening

- clearer first-screen Community Edition positioning and Quick Start path;
- production dependency refreshes;
- fast-forward-only Stage source advancement with ref-propagation polling;
- release tag/version equality enforced before publication;
- v3.1.2 release notes and QA acceptance contract; and
- stable v3.1.2 image/tag references synchronized across deployment surfaces.

### v3.1.3 — Operator guides

- end-to-end use-case guides (Xen Orchestra to Discord and Microsoft Teams,
  direct homelab SMTP, Dell iDRAC Redfish routing, Zabbix Event API to
  Discord); and
- a stable `docs/integrations/` index.

### v3.1.4–v3.1.5 — Stage-final release chain

- Stage as the final runtime acceptance gate before release; and
- release automation cleanup around the same immutable Development digest.

### v3.1.6 — Three-workflow release model

- Continuous Integration builds, verifies and deploys Development;
- Promote CE to Stage and Finalize CE Release promote the same digest without
  rebuild; see [v3.1.6 release notes](releases/v3.1.6.md).

## Next release: v27.0.0

The `development` branch is the v27.0.0 release-candidate line (`v27.0.0-rc.N`
pre-release tags). It adds Email Alerts, the Email and Nowlert Mobile
destinations, seven new integrations, multi-factor authentication, filtering
that is separate from routes and the current WebUI; see
[Development after v3.1.6](releases/post-v3.1.6-development.md) for the full
list. v3.1.6 stays the current stable release until v27.0.0 is released.

## Current maintenance priorities

1. Keep runtime version, README, Docker Hub text, configuration examples,
   screenshots, release notes, and stable images synchronized.
2. Preserve the build-once promotion invariant and desired-state ledger evidence.
3. Expand real-system validation for integrations that currently rely heavily on
   fixtures.
4. Preserve upgrade/rollback coverage for supported older schema/state paths.
5. Keep the production image non-root, read-only, capability-minimal, and
   reproducible.
6. Add integrations/outputs only behind explicit contracts, tests, and
   ownership/security boundaries.

## Candidate work after v27.0.0

Candidates, not commitments:

- broader Proxmox VE real-system compatibility validation;
- broader Synology DSM compatibility validation;
- Redfish vendor/firmware matrix expansion;
- additional destination adapters such as Telegram;
- persistent background retry/queue orchestration;
- optional operational metrics export;
- automatic documentation/screenshot drift detection;
- automated Docker Hub documentation publication;
- additional WebUI localization; and
- stronger automated environment/runtime drift reporting.

## Issue and release policy

Create one issue per independently testable outcome. A useful issue defines:

- problem/goal;
- security and compatibility boundary;
- acceptance criteria;
- real-system versus fixture validation level; and
- target release only after scope is approved.

Release candidates must be cumulative on `development`. After a successful Stage
promotion, `stage` is fast-forwarded to the promoted candidate commit. Right
before a release, `stage` is merged into `main` (a merge commit with Stage's
files), so `main` always holds what was last released. `main` is never merged
into `development`; see [Deployment](deployment.md) for the release flow.

Completed historical issues remain closed; new compatibility findings should be
tracked as new issues referencing the original work rather than reopening old
release records.
