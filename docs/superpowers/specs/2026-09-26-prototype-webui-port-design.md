# Prototype WebUI port to Nowlert CE design

## Goal

Move the UI the user approved in the Nowlert CE visual prototype into the real
Nowlert CE `development` application so it can be evaluated there. Preserve the
existing application behavior and layouts except for the explicitly approved
Dashboard graph and visual treatments. Remove legacy blue/cyan card surfaces
that conflict with the approved charcoal and gold appearance so they cannot
show through the new surfaces.

## Approved experience

### Shared WebUI surfaces

- Use the prototype's charcoal card/background palette and yellow corner
  accents across the menus and nested card surfaces shown there.
- Keep `Critical` and `Shared` controls in their established semantic colors;
  preserve other status colors and readable contrast.
- Remove superseded blue/cyan background fills from affected styles instead
  of relying on a later overlay to hide them. Load shared surface rules after
  the page styles and audit each menu for uncovered nested surfaces or color
  bleed.
- Retain the prototype's clean title treatment and divider placement.

### Dashboard

- Match the prototype's card backgrounds, pulsing yellow header accent, and
  spacing/alignment, including Workspace Summary.
- Keep the approved cumulative yellow neon step graph with a thin line,
  delivery pulses, and continuous line glow. Do not add replay controls or
  point dots; the graph animation runs when the dashboard is entered, after
  login, and after refresh. Keep its labels and summary values consistent with
  the plotted delivery data and respect reduced-motion preferences.

### Routing Flow

- Match the prototype's card surfaces and the Dashboard header treatment on
  Recent Deliveries.
- Preserve the routing graph and data semantics. Apply the approved node
  pulse classification: direct links highlight integration and destination in
  yellow; filtered links use the approved grey/yellow treatment, combining
  colors when a node participates in both kinds of route.
- Preserve filter-card geometry, chips, and metrics, and do not alter filter
  criteria or routing behavior. Keep the filter's approved visual treatment.
- Keep the five Routing Flow summary metrics free of the yellow corner stripes.

## Implementation shape

Use a selective port into the existing `src/webui` application, not the static
prototype bundle. The known prototype deltas are the Dashboard renderer and
styles, Routing Flow renderer and styles, `operations_acceptance.css`, and the
prototype-only shared surface stylesheet and two small chart/routing model
scripts. Register new assets in `WebUIService`'s allowlist and inject CSS and
scripts in dependency order. Update the WebUI cache build identifier.

During the port, consolidate or remove affected legacy background declarations
where practical, while retaining the global theme layer for cross-menu custom
surfaces. Do not change API contracts, stored data, authentication, routing
rules, filter criteria, or unrelated behavior.

## Validation

- Add focused tests for cumulative chart paths/timing, route-to-node pulse
  classification, runtime asset allowlisting/load order, and the approved
  filter/semantic-color invariants.
- Run the relevant WebUI tests, full `python -m pytest -q`, and current-doc
  validation. Build and run the development WebUI locally.
- Visually compare Dashboard and Routing Flow to the prototype, inspect all
  menus for legacy blue/cyan bleed and nested surfaces, and correct mismatches
  before pushing the verified change to `development`.
- No production release or promotion is part of this change.

## Design trade-off

The recommended selective port preserves CE runtime wiring and API behavior
while bringing over the prototype's approved UI. Replacing the prototype bundle
wholesale would risk losing application-specific wiring and is out of scope.
