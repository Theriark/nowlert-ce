# Prototype WebUI Port Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task by task. Do not delegate; this session is configured for native implementation.

**Goal:** Port the approved Nowlert CE prototype UI into the real `development` WebUI, preserve application behavior and layouts, remove legacy blue/cyan background bleed, verify the rendered result against the prototype, and push the verified implementation to `development`.

**Architecture:** Selectively port the prototype's dashboard and routing-flow rendering/styles plus its chart and routing-pulse models. Add the approved shared visual treatment as a final, audited stylesheet. Register every new asset in `WebUIService`'s allowlist and in dependency order. Keep app APIs, stored data, authentication, routing/filter behavior, and filter card geometry unchanged.

**Tech Stack:** Python 3.13, pytest, browser-side JavaScript/CSS, Node.js 24, existing CE WebUI runtime.

**Approved design:** `docs/superpowers/specs/2026-09-26-prototype-webui-port-design.md`

## Global Constraints

- Work on the already checked out `development` branch and preserve its existing application wiring.
- Do not port the prototype as a static bundle or overwrite unrelated CE functionality.
- Do not change Routing Flow filter criteria, filter data, layout geometry, graph layout, or operational semantics.
- Keep semantic status colors (including Critical and Shared) intact.
- Remove obsolete affected blue/cyan surface fills at their source where practical; do not hide them under another background layer.
- Dashboard graph stays a thin cumulative yellow step line with delivery pulses and persistent glow, with no dots and no replay control. Keep the plotted series and labels consistent, animate on dashboard entry/login/refresh, and respect reduced motion.
- Verify the running UI visually before claiming success or pushing. Push only the completed, verified change to `origin/development`; do not release to production.

## Review Focus

- Empty and sparse delivery ranges: the graph should remain valid, and totals/labels must match the available events. Pin this in Task 1 model tests and Task 2 renderer tests.
- Dashboard re-entry, login, refresh, and live refresh: intentional entry/refresh animations should restart without needless replay on unchanged updates. Pin this in Task 1 model tests and Task 2 renderer tests.
- Direct, filtered, and overlapping routes: integrations/destinations must receive the right yellow/grey/mixed modes. Pin each topology in Task 1 model tests and Task 3 presentation tests.
- Routing Flow filter cards: approved geometry, chips, metrics, and criteria must survive pulse decoration. Pin geometry/content and style invariants in Task 3 and Task 4 tests.
- Legacy background bleed versus semantic blue/cyan: every menu/nested surface should use the approved charcoal while Information/provider/link meanings retain their colors. Pin representative menu surfaces and semantic exceptions in Task 4 theme tests.

---

### Task 1: Add deterministic chart and pulse model tests

**Files:**
- Create `tests/webui/test_delivery_chart_model.mjs`
- Create `tests/webui/test_routing_pulse_model.mjs`
- Modify `.github/workflows/ci.yml`

- [ ] Write Node tests for empty/sparse and populated bucket totals, step-path coordinates, delivery pulse timing, and animation restart decisions. Include checks that the graph contract has no dots or replay control.
- [ ] Write Node tests for direct, filtered, and mixed route topologies; cover filter content and geometry separately with DOM/CSS presentation regressions in Task 3.
- [ ] Run both tests before implementations and confirm they fail because the models/tests are not yet integrated.
- [ ] Add Node 24 test execution to CI after Node setup, keeping the existing syntax checks.
- [ ] Run `node --test tests/webui/test_delivery_chart_model.mjs tests/webui/test_routing_pulse_model.mjs` and confirm expected initial failures.
- [ ] Commit the failing contract tests and CI runner with `test: define prototype chart and routing pulse contracts`.

### Task 2: Implement the Dashboard chart model and renderer

**Files:**
- Create `src/webui/delivery_chart_model.js`
- Modify `src/webui/operations_dashboard.js`
- Modify `src/webui/operations_dashboard.css`
- Modify `src/webui/operations_acceptance.css`
- Modify `tests/test_operations_dashboard_revamp.py`
- Modify `docs/webui.md`

- [ ] Implement the tested `window.NowlertDeliveryChart` functions: `buildCumulativeSeries`, `buildStepPath`, `pulseDelay`, and `shouldAnimateRender`.
- [ ] Port the prototype's cumulative step graph and delivery pulses while retaining existing dashboard history controls, refresh, first-paint snapshot behavior, live feed, labels, and event totals.
- [ ] Remove replay UI and point markers; use the approved thin yellow line, continuous soft glow, and accessible reduced-motion behavior. Restart its entrance animation on dashboard entry, login, and refresh.
- [ ] Port approved dashboard card accents, header spacing/alignment, Workspace Summary alignment, and the same detail pulse behavior for System Health and Workspace Summary that the dashboard uses for Recent Activity.
- [ ] Update the old graph expectations in `tests/test_operations_dashboard_revamp.py` to the approved graph and assert existing range/feed contracts remain intact.
- [ ] Update current WebUI docs to describe the delivered graph and behavior.
- [ ] Add renderer assertions in `tests/test_operations_dashboard_revamp.py` for consistent plotted totals/labels, replay/dot absence, entry/login/refresh animation, unchanged-data refresh behavior, and reduced motion. Run `node --test tests/webui/test_delivery_chart_model.mjs`, `python -m pytest -q tests/test_operations_dashboard_revamp.py tests/test_dashboard_acceptance_followup.py tests/test_dashboard_acceptance_polish.py`, and `node --check src/webui/operations_dashboard.js`.
- [ ] Commit the passing chart model and Dashboard integration with `feat: port approved dashboard delivery graph`.

### Task 3: Implement Routing Flow pulse model and rendering

**Files:**
- Create `src/webui/routing_pulse_model.js`
- Modify `src/webui/routing_flow.js`
- Modify `src/webui/routing_flow.css`
- Modify `tests/test_routing_flow_presentation.py`
- Modify `tests/test_routing_flow_layout.py`
- Modify `docs/webui.md`

- [ ] Implement tested `window.NowlertRoutingPulseModel.resolveNodeModes(graph)` to classify direct-only nodes as yellow, filter-only nodes as grey, and shared endpoints as mixed when both route types exist.
- [ ] Port the prototype's approved soft pulse rendering and line/glow dimensions without multiplying decorative lines or changing graph links, positions, filter card geometry/chips/metrics, or filter behavior.
- [ ] Remove yellow corner stripes from the five Routing Flow metric cards; retain the approved accents on routing cards and Recent Deliveries header.
- [ ] Preserve the prototype-approved filter visual treatment and all current filter presentation behavior.
- [ ] Add presentation regressions for direct/filtered/mixed pulse classes, metric-card accent exclusion, and unchanged filter geometry/content contracts.
- [ ] Run `node --test tests/webui/test_routing_pulse_model.mjs` and `python -m pytest -q tests/test_routing_flow_presentation.py tests/test_routing_flow_layout.py tests/test_routing_flow_runtime_telemetry.py tests/test_filtering_routing_acceptance_regressions.py`; the tests must cover direct-only, filtered-only, overlapping mixed endpoints, plus filter geometry/content unchanged.
- [ ] Commit the passing pulse model and Routing Flow integration with `feat: port approved routing flow pulses`.

### Task 4: Port and audit shared surface styling

**Files:**
- Create `src/webui/visual_refinement.css`
- Modify affected legacy surface rules in `src/webui/styles.css`, `src/webui/operations_dashboard.css`, `src/webui/routing_flow.css`, `src/webui/audit_log_refinement.css`, `src/webui/email_alerts.css`, `src/webui/enhancements.css`, `src/webui/management_consistency.css`, `src/webui/professional.css`, and any additional loaded stylesheet found by the surface audit
- Create `tests/test_webui_prototype_theme.py`

- [ ] First add `tests/test_webui_prototype_theme.py` with failing assertions for representative menu/nested surfaces, approved accent placement, semantic-color retention, and the Routing Flow filter/metric exceptions.
- [ ] Run `python -m pytest -q tests/test_webui_prototype_theme.py` and confirm it fails against current styles.
- [ ] Search every loaded WebUI stylesheet for legacy blue/cyan surface fills and identify visible affected menu/panel selectors.
- [ ] Port approved charcoal backgrounds, yellow upper-left accents, title/divider treatment, and page-specific exceptions; remove or replace superseded fills at their source while preserving semantic blue/cyan meanings such as Information, links, and provider identity.
- [ ] Keep Routing Flow filter and metric-card exceptions explicit, then rerun the theme test and confirm it passes.
- [ ] Run relevant existing contracts: `python -m pytest -q tests/test_unified_page_headers.py tests/test_audit_log_refinement.py tests/test_email_alert_rules_ux.py tests/test_webui_backups_layout_round13.py tests/test_webui_backups_housekeeping_round14.py tests/test_webui_backups_compact_round19.py tests/test_management_consistency_ui.py`.
- [ ] Commit the shared surface styling and regression coverage with `feat: unify approved WebUI surfaces`.
### Task 5: Register assets, load order, and cache version

**Files:**
- Modify `src/webui/service.py`
- Modify `tests/test_webui.py`
- Modify `.github/workflows/ci.yml`

- [ ] Add both model scripts and the shared stylesheet to the strict WebUI asset allowlist.
- [ ] Inject chart model before Dashboard code, pulse model before Routing Flow code, and shared visual CSS after affected page styles.
- [ ] Bump `UI_BUILD` once to a fresh cache version and assert injection order/cache query behavior in tests.
- [ ] Add/adjust service contract checks for the new assets and ensure unknown assets remain rejected.
- [ ] Run `python -m pytest -q tests/test_webui.py tests/test_webui_refresh_cache.py tests/test_webui_first_paint_round11.py` plus `node --check` on every changed JavaScript asset.
- [ ] Commit the asset wiring and cache version with `feat: register prototype WebUI assets`.

### Task 6: Full application and visual verification

**Files:**
- Any implementation files requiring corrections from verification
- `docs/webui.md` if verification reveals a documentation mismatch

- [ ] Run full `python -m pytest -q`, Python compile checks, Node syntax checks, and both new Node test files.
- [ ] Start the development WebUI locally and compare Dashboard and Routing Flow with the approved prototype at the same viewport and interaction state.
- [ ] Visit every menu and representative nested card; inspect for old blue/cyan fills showing through, missing approved background/accents, clipping, spacing drift, or semantic color regressions.
- [ ] Check dashboard animation after login/refresh/navigation, verify graph pulse and no replay/dots, and test reduced-motion behavior.
- [ ] Check direct, filtered, and mixed Routing Flow routes and verify filters remain unchanged.
- [ ] Correct any observed mismatch, rerun the relevant tests, and repeat the visual check until the approved result is met.
- [ ] Review the final diff, ensure no unrelated changes, then create a final verification commit if Task 6 required corrections and push the verified branch to `origin/development`.

## Final acceptance checklist

- [ ] All previously approved Dashboard and Routing Flow behavior matches the prototype.
- [ ] All affected menus and nested panels use the approved surface color, with no old blue/cyan background bleed.
- [ ] No routing, filtering, API, authentication, or stored-data behavior changed.
- [ ] Full tests, syntax checks, and visual checks pass.
- [ ] The implementation is pushed to `development`; no production deployment was triggered.





