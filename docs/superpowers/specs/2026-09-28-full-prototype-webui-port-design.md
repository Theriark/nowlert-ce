# Full prototype WebUI parity port

## Goal and user constraints

Bring the Nowlert CE WebUI on `development` into visual and interaction parity
with the finished visual prototype, using the last CE commit as the comparison
baseline. Preserve the real application's functionality and data behavior.
The Activity title band and its pulsing yellow accent, plus other title/accent
details explicitly approved in the prototype, must remain as shown there.

## Scope

Port the user-visible differences across all changed prototype sections:

- Shared page headers, navigation, surfaces, accents, and typography.
- Dashboard cards, summary layout, and animated delivery chart.
- Routing Flow cards, graph treatment, filter surfaces, and status pulses.
- Destinations and Filtering cards, tables, status/sharing controls, and actions.
- Email Alerts Rules, Groups, Mailboxes, and Activity layouts and interactions.
- Delivery history, Audit Log, Backups, Settings, Account, and Users surfaces.

The prototype's sample groups, mailboxes, rules, and activity records are layout
fixtures. They must not become production seed data. The static Sites preview,
its demo API, generated archives, cache-busting query strings, and screenshots
are not part of the CE application.

## Behavior and compatibility

- Keep CE authentication, authorization, API routes and payloads, persistence,
  provider connections, routing criteria, and message processing unchanged.
- Reuse existing CE endpoints and actions. Add frontend behavior only where the
  prototype requires it and the application does not already provide it.
- Preserve the Email Alerts subsection in the URL across reloads, including
  Rules, Groups, Mailboxes, and Activity.
- Refresh Activity data automatically while Activity is visible; retain the
  prototype's severity filters, local search, timeline, and per-message action
  menu without removing existing actions or original-message links.
- Maintain responsive layouts, keyboard access, semantic status colors, and
  reduced-motion handling.

## Implementation approach

Make a selective port into the current `src/webui` modules, preserving CE's
runtime wiring and helpers. Compare every changed prototype asset against the
current `development` tree, then translate only the final, user-visible changes
into the corresponding CE sources. Update the WebUI asset allowlist and load
order only for genuinely new assets. Do not replace the CE bundle wholesale or
change backend contracts to fit the mock preview.

## Validation

- Add focused regressions for each affected page and for asset allowlisting and
  load order.
- Verify Email Alerts subsection refresh persistence, polling, filters, search,
  every existing message action, mailbox/group/rule CRUD, and OAuth entry points
  against the live CE API behavior.
- Run relevant UI/backend tests, the full `python -m pytest -q` suite, and
  current-documentation validation.
- Build and run the CE WebUI locally, then visually compare every changed page
  with the prototype at desktop and narrow widths. Confirm title bands, accents,
  status semantics, and real dynamic data remain correct.
- Deliver as a reviewed change to `development`; do not publish a production
  release or promote a deployment as part of this work.

## Main risk and mitigation

The prototype uses broad shared CSS overrides, while CE has live interactions
and stricter runtime asset serving. Port changes page by page, scope styles to
the intended views, keep the existing event/API handlers, and verify both visual
parity and working real-data flows before considering the port complete.
