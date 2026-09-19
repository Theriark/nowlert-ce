"use strict";

/* Destination-aware routing canvas. No routing mutation or demo data. */
(() => {
  const NS = "http://www.w3.org/2000/svg";
  const PAGE = "routing-flow";
  const POLL_MS = 5000;
  const OUTPUT_LOGOS = { teams: "/ui/icons/routing-teams.svg", slack: "/ui/icons/routing-slack.svg" };
  const ICONS = {
    flow: "M4 4h5v5H4z M15 15h5v5h-5z M6.5 9v8.5H15 M17.5 15V6.5H9",
    filter: "M3 4h18l-7 8v7l-4 2v-9z",
    pulse: "M2 12h5l3-8 4 16 3-8h5",
    clock: "M12 8v5l3 2 M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0",
    fit: "M8 3H3v5 M16 3h5v5 M21 16v5h-5 M8 21H3v-5 M8 8h8v8H8z",
  };
  let data = null, signature = "", timer = null, controller = null;
  let generation = 0, range = "1d", zoom = 1, busy = false;
  let owner = null, selected = null, seen = new Set(), allHistory = false;
  let pulseFrame = null, pulses = [], edgePaths = new Map(), resizeFrame = null;
  let graphModel = null, pendingRefreshOptions = null;

  function el(tag, cls = "", text = "") {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== "") n.textContent = String(text);
    return n;
  }
  function svg(tag, attrs = {}) {
    const n = document.createElementNS(NS, tag);
    Object.entries(attrs).forEach(([key, value]) => n.setAttribute(key, String(value)));
    return n;
  }
  function icon(name) {
    const n = svg("svg", { viewBox: "0 0 24 24", "aria-hidden": "true", class: "rf-icon" });
    n.append(svg("path", { d: ICONS[name] || ICONS.flow, fill: "none", stroke: "currentColor", "stroke-width": 1.6, "stroke-linecap": "round", "stroke-linejoin": "round" }));
    return n;
  }
  function button(text, action, cls = "rf-control") {
    const n = el("button", cls, text);
    n.type = "button";
    n.addEventListener("click", action);
    return n;
  }
  function dot(kind = "") { return el("span", `rf-dot ${kind}`); }
  function metricText(value) { return value === null || value === undefined ? "—" : Number(value).toLocaleString(); }
  function active() { return Boolean(state.user && state.currentView === PAGE && !document.hidden); }
  function linkKey(route, destination) { return JSON.stringify([route, destination]); }
  function destinationLogo(destination) {
    const path = OUTPUT_LOGOS[destination.output_type];
    if (!path) return outputIcon(destination.output_type);
    const image = el("img", "rf-brand-icon");
    image.src = path;
    image.alt = "";
    return image;
  }

  VIEW_TITLES[PAGE] = "Routing Flow";
  let nav = document.querySelector('#primary-nav [data-view="routing-flow"]');
  if (!nav) {
    nav = button("", () => {}, "nav-item");
    nav.dataset.view = PAGE;
    nav.append(icon("flow"), el("span", "", "Routing Flow"));
    document.querySelector('#primary-nav [data-view="dashboard"]').after(nav);
  }
  const section = el("section", "view rf-page");
  section.id = "view-routing-flow";
  section.dataset.page = PAGE;
  section.hidden = true;
  section.innerHTML = `
    <div class="section-toolbar rf-toolbar">
      <div><h2>Routing Flow</h2><p>Visualize active routes, filters, and destinations.</p></div>
      <label class="rf-range ops-dashboard-range-control"><span class="sr-only">History window</span><select id="rf-range"><option value="10m">Last 10 minutes</option><option value="1h">Last 1 hour</option><option value="1d" selected>Last 24 hours</option><option value="1m">Last 1 month</option><option value="1y">Last 1 year</option></select></label>
    </div>
    <div id="rf-error" class="rf-error" role="alert" hidden></div>
    <div id="rf-metrics" class="rf-metrics"></div>
    <div class="rf-canvas">
      <div id="rf-empty" class="rf-empty" hidden></div>
      <div id="rf-graph" class="rf-graph"><svg id="rf-edges" class="rf-edges" aria-hidden="true"><g id="rf-edge-layer"></g><g id="rf-particle-layer"></g></svg></div>
      <div class="rf-canvas-footer"><div class="rf-controls"><div class="rf-zoom"><button id="rf-minus" type="button" aria-label="Zoom out">−</button><span id="rf-zoom-value">100%</span><button id="rf-plus" type="button" aria-label="Zoom in">+</button></div><button id="rf-fit" class="rf-control" type="button">Fit to view</button></div><svg id="rf-minimap" class="rf-minimap" viewBox="0 0 130 46" role="img" aria-label="Routing overview minimap"></svg></div>
    </div>
    <div class="rf-history"><div class="rf-history-heading"><h3>Recent Deliveries</h3><button id="rf-history-toggle" class="rf-control" type="button">View all</button></div><div class="rf-table-scroll"><table><thead><tr><th>Time</th><th>Integration</th><th>Destination</th><th>Status</th><th>Attempt</th></tr></thead><tbody id="rf-history-body"></tbody></table></div><p id="rf-history-empty" class="rf-empty" hidden>No deliveries recorded in this window.</p></div>
  `;
  byId("view-dashboard").after(section);
  const routingRangeSelect = section.querySelector("#rf-range");
  const $ = id => id === "rf-range" ? routingRangeSelect : section.querySelector(`#${id}`);
  const ROUTING_RANGE_KEYS = new Set(["10m", "1h", "1d", "1m", "1y"]);

  function selectedRoutingRange() {
    const value = String($("rf-range")?.value || range || "1d").trim();
    return ROUTING_RANGE_KEYS.has(value) ? value : "1d";
  }

  $("rf-fit").prepend(icon("fit"));
  const dialog = el("dialog", "rf-dialog");
  dialog.setAttribute("aria-labelledby", "rf-details-title");
  const dialogTop = el("div", "rf-dialog-top"), dialogTitle = el("h2");
  dialogTitle.id = "rf-details-title";
  const dialogBody = el("div", "rf-dialog-body");
  const close = button("×", () => dialog.close());
  close.setAttribute("aria-label", "Close routing details");
  dialogTop.append(dialogTitle, close);
  dialog.append(dialogTop, dialogBody);
  document.body.append(dialog);
  dialog.addEventListener("close", () => { selected = null; drawEdges(); });

  function setDialogTitle(text, visual = null) {
    dialogTitle.replaceChildren();
    if (visual) {
      visual.classList.add("rf-dialog-title-icon");
      dialogTitle.append(visual);
    }
    dialogTitle.append(el("span", "", text));
  }
  function detailRow(label, value) {
    const row = el("div", "rf-detail-row");
    row.append(el("span", "", label), el("strong", "", value));
    return row;
  }
  function detailIdentityRow(label, visual, value) {
    const row = el("div", "rf-detail-row");
    const identity = el("strong", "rf-detail-identity");
    if (visual) {
      visual.classList.add("rf-detail-icon");
      identity.append(visual);
    }
    identity.append(document.createTextNode(value));
    row.append(el("span", "", label), identity);
    return row;
  }
  function appendMetricRows(target, metrics) {
    [["Delivered", "delivered"], ["Retry scheduled", "pending"], ["Failed", "failed"]].forEach(([label, key]) => {
      target.append(detailRow(label, metricText((metrics || {})[key])));
    });
  }
  function policyLines(link) {
    const entries = [];
    for (const p of link.policies) {
      const prefix = link.fallback ? `${p.name}: ` : "";
      if (!p.configured) { if (!link.fallback) entries.push("All notifications"); continue; }
      if (!p.enabled) { entries.push(`${prefix}Filter disabled · all notifications`); continue; }
      const clauses = p.legacy_clauses.length ? p.legacy_clauses : [p.rules];
      const summary = clauses.map(c => Object.entries(c).map(([key, values]) => `${p.labels[key] || key.replaceAll("_", " ")}: ${values.join(", ")}`).join(" AND ")).join(" OR ");
      entries.push(prefix + summary);
    }
    return entries.length ? entries : ["All notifications"];
  }
  function activePolicies(link) {
    return (link.policies || []).filter(p => !p.restricted && p.configured && p.enabled);
  }
  function activePolicyLines(link) {
    const policies = activePolicies(link);
    return policies.length ? policyLines({ ...link, policies }) : [];
  }
  function policyDetailRows(link) {
    const policies = activePolicies(link);
    return policies.map((policy, index) => {
      const line = policyLines({ ...link, policies: [policy] })[0] || "All notifications";
      const prefix = `${policy.name}: `;
      const summary = link.fallback && line.startsWith(prefix) ? line.slice(prefix.length) : line;
      const label = link.fallback ? policy.name : (policies.length > 1 ? `Rule ${index + 1}` : "Rules");
      return detailRow(label, summary);
    });
  }
  function rangeLabel(value = range) {
    return {
      "10m": "Last 10 minutes",
      "15m": "Last 15 minutes",
      "1h": "Last 1 hour",
      "1d": "Last 24 hours",
      "1m": "Last 1 month",
      "1y": "Last 1 year",
    }[value] || value;
  }
  function filterMetricText(value) {
    return Number.isFinite(value) ? String(value) : "—";
  }
  function filterReductionText(metrics = {}) {
    const received = metrics.received;
    const filtered = metrics.filtered;
    if (!Number.isFinite(received) || !Number.isFinite(filtered) || received <= 0) return "—";
    return `${Math.round((filtered / received) * 100)}%`;
  }
  function filterRuleTags(link) {
    const tags = [];
    for (const policy of activePolicies(link)) {
      const clauses = policy.legacy_clauses?.length ? policy.legacy_clauses : [policy.rules || {}];
      for (const clause of clauses) {
        for (const [key, rawValues] of Object.entries(clause || {})) {
          const values = Array.isArray(rawValues) ? rawValues : [rawValues];
          for (const rawValue of values) {
            const text = String(rawValue ?? "").trim();
            if (!text) continue;
            if (key.startsWith("__")) {
              tags.push(text);
              continue;
            }
            const label = policy.labels?.[key] || key.replaceAll("_", " ");
            for (const rawPart of text.split(" AND ")) {
              const part = rawPart.trim();
              if (!part) continue;
              tags.push(part.includes(": ") ? part.replace(": ", " = ") : `${label} = ${part}`);
            }
          }
        }
      }
    }
    return [...new Set(tags)];
  }

  function filterTagTone(value) {
    const normalized = String(value || "").trim().toLowerCase();
    if (normalized.includes("disaster") || normalized.includes("critical") || normalized.includes("emergency")) return "red";
    if (normalized === "high" || normalized.includes("major")) return "high";
    if (normalized.includes("average") || normalized.includes("medium")) return "orange";
    if (normalized.includes("warning") || normalized === "warn") return "yellow";
    if (normalized.includes("not classified") || normalized.includes("unclassified") || normalized === "unknown") return "neutral";
    return "blue";
  }

  function filterCardDescriptor(filter) {
    const policies = Array.isArray(filter?.policies)
      ? filter.policies.filter(policy => {
          const enabled = Object.prototype.hasOwnProperty.call(policy, "filter_enabled")
            ? policy.filter_enabled
            : policy.enabled;
          return !policy.restricted && policy.configured && enabled !== false;
        })
      : [];
    const groups = new Map();

    const addValue = (label, value) => {
      const cleanLabel = String(label || "Filter").trim();
      const cleanValue = String(value || "").trim();
      if (!cleanValue) return;
      const key = cleanLabel.toLowerCase();
      if (!groups.has(key)) groups.set(key, { label: cleanLabel, values: [] });
      const group = groups.get(key);
      if (!group.values.includes(cleanValue)) group.values.push(cleanValue);
    };

    for (const policy of policies) {
      const policyRules = Array.isArray(policy.policy_rules) ? policy.policy_rules : [];
      if (policyRules.length) {
        for (const rule of policyRules) {
          for (const [field, rawValues] of Object.entries(rule.conditions || {})) {
            const label = policy.labels?.[field] || field.replaceAll("_", " ");
            const values = Array.isArray(rawValues) ? rawValues : [rawValues];
            values.forEach(value => addValue(label, value));
          }
        }
        continue;
      }

      const clauses = policy.legacy_clauses?.length ? policy.legacy_clauses : [policy.rules || {}];
      for (const clause of clauses) {
        for (const [key, rawValues] of Object.entries(clause || {})) {
          const values = Array.isArray(rawValues) ? rawValues : [rawValues];
          for (const rawValue of values) {
            for (const rawPart of String(rawValue ?? "").split(" AND ")) {
              const part = rawPart.trim();
              if (!part) continue;
              if (part.includes(": ")) {
                const [rawLabel, ...rest] = part.split(": ");
                addValue(rawLabel, rest.join(": "));
              } else if (!key.startsWith("__")) {
                addValue(policy.labels?.[key] || key.replaceAll("_", " "), part);
              }
            }
          }
        }
      }
    }

    const items = [...groups.values()];
    const title = items.map(group => {
      const label = group.label.replace(/\b\w/g, letter => letter.toUpperCase());
      return `${label} (${group.values.length})`;
    }).join(" · ");
    return {
      title,
      groups: items,
    };
  }

  function filterCardValues(filter) {
    const values = [];
    const seen = new Set();
    for (const group of filterCardDescriptor(filter).groups) {
      for (const rawValue of group.values || []) {
        const value = String(rawValue || "").trim();
        const key = value.toLowerCase();
        if (!value || seen.has(key)) continue;
        seen.add(key);
        values.push(value);
      }
    }
    return values;
  }

  function renderFilterCard(node, filter, routes, destination) {
    node.classList.add("rf-filter-card");
    const descriptor = filterCardDescriptor(filter);

    const header = el("div", "rf-filter-card-header");
    const visual = el("span", "rf-filter-card-icon");
    visual.append(icon("filter"));
    const headingCopy = el("span", "rf-filter-card-heading-copy");
    const configuredName = String(filter?.filter_name || filter?.name || "").trim();
    const title = el("strong", "rf-filter-card-title", configuredName || descriptor.title || "Filter");
    headingCopy.append(title);
    if (configuredName && descriptor.title) {
      headingCopy.append(el("small", "rf-filter-card-summary", descriptor.title));
    }
    header.append(visual, headingCopy);

    const tags = el("div", "rf-filter-card-tags");
    const filterValues = filterCardValues(filter);
    let valueMenuOpen = false;
    let valueFitFrame = null;

    const fitCollapsedFilterValues = () => {
      valueFitFrame = null;
      if (!tags.isConnected) return;
      const width = tags.clientWidth;
      if (!width) return;

      const valueNodes = [...tags.querySelectorAll("[data-filter-value]")];
      const overflowWrap = tags.querySelector(".rf-filter-value-overflow-wrap");
      const toggle = overflowWrap?.querySelector(".rf-filter-value-overflow");
      const popover = overflowWrap?.querySelector(".rf-filter-value-popover");
      if (!overflowWrap || !toggle || !popover) return;

      for (const item of valueNodes) item.hidden = false;
      valueMenuOpen = false;
      overflowWrap.classList.remove("is-open");
      if (typeof popover.hidePopover === "function" && popover.matches(":popover-open")) {
        popover.hidePopover();
      }
      popover.hidden = true;
      toggle.setAttribute("aria-expanded", "false");

      const gap = Number.parseFloat(
        getComputedStyle(tags).columnGap
        || getComputedStyle(tags).gap
        || "0",
      ) || 0;
      const visibleNodes = valueNodes;
      const visibleWidth = visibleNodes.reduce(
        (sum, item, index) => sum + item.getBoundingClientRect().width + (index ? gap : 0),
        0,
      );

      let hiddenValues = valueNodes
        .filter(item => item.hidden)
        .map(item => item.dataset.filterValueText);
      if (!hiddenValues.length && visibleWidth <= width) {
        overflowWrap.hidden = true;
        return;
      }

      overflowWrap.hidden = false;
      toggle.textContent = "+99";
      const overflowWidth = overflowWrap.getBoundingClientRect().width;
      const available = Math.max(0, width - overflowWidth - gap);
      let used = 0;

      for (const item of visibleNodes) {
        const itemWidth = item.getBoundingClientRect().width;
        const next = used + (used ? gap : 0) + itemWidth;
        if (next <= available) {
          item.hidden = false;
          used = next;
        } else {
          item.hidden = true;
        }
      }

      hiddenValues = valueNodes
        .filter(item => item.hidden)
        .map(item => item.dataset.filterValueText)
        .filter(Boolean);

      if (!hiddenValues.length) {
        overflowWrap.hidden = true;
        return;
      }

      toggle.textContent = `+${hiddenValues.length}`;
      toggle.setAttribute("aria-label", `Show ${hiddenValues.length} more filter values`);
      popover.replaceChildren();
      for (const value of hiddenValues) {
        const item = el("span", "rf-filter-value-popover-item");
        const label = el("span", "rf-filter-value-popover-label", friendlyName(value));
        item.setAttribute("role", "menuitem");
        item.append(label);
        popover.append(item);
      }
    };

    const scheduleValueFit = () => {
      if (valueFitFrame !== null) cancelAnimationFrame(valueFitFrame);
      valueFitFrame = requestAnimationFrame(fitCollapsedFilterValues);
    };

    for (const value of filterValues) {
      const chip = el("span", "rf-filter-rule-tag rf-filter-rule-tag-muted", friendlyName(value));
      chip.dataset.filterValue = "1";
      chip.dataset.filterValueText = value;
      chip.title = value;
      tags.append(chip);
    }

    const valueOverflowWrap = el("span", "rf-filter-value-overflow-wrap");
    valueOverflowWrap.hidden = true;
    const valueToggle = el("button", "rf-filter-value-overflow rf-filter-source-overflow", "+0");
    valueToggle.type = "button";
    valueToggle.setAttribute("aria-expanded", "false");
    valueToggle.setAttribute("aria-haspopup", "menu");
    valueToggle.setAttribute("aria-label", "Show more filter values");
    const valuePopover = el("span", "rf-filter-value-popover");
    valuePopover.id = `rf-filter-values-${filter.id}`;
    valuePopover.hidden = true;
    valuePopover.setAttribute("role", "menu");
    valuePopover.setAttribute("popover", "auto");
    valueToggle.setAttribute("aria-controls", valuePopover.id);

    function positionValuePopover() {
      if (valuePopover.hidden) return;
      const toggleRect = valueToggle.getBoundingClientRect();
      const menuRect = valuePopover.getBoundingClientRect();
      const menuWidth = Math.max(150, menuRect.width || 150);
      const menuHeight = Math.max(24, menuRect.height || 24);
      const left = Math.max(
        8,
        Math.min(toggleRect.right - menuWidth, window.innerWidth - menuWidth - 8),
      );
      const above = toggleRect.top - menuHeight - 6;
      const below = Math.min(
        toggleRect.bottom + 6,
        window.innerHeight - menuHeight - 8,
      );
      valuePopover.style.left = `${Math.round(left)}px`;
      valuePopover.style.top = `${Math.round(above >= 8 ? above : Math.max(8, below))}px`;
    }

    function closeValuePopover() {
      if (typeof valuePopover.hidePopover === "function" && valuePopover.matches(":popover-open")) {
        valuePopover.hidePopover();
      }
      valuePopover.hidden = true;
      valueMenuOpen = false;
      valueOverflowWrap.classList.remove("is-open");
      valueToggle.setAttribute("aria-expanded", "false");
    }

    function openValuePopover() {
      valuePopover.hidden = false;
      valuePopover.style.visibility = "hidden";
      if (typeof valuePopover.showPopover === "function") {
        if (!valuePopover.matches(":popover-open")) valuePopover.showPopover();
      }
      positionValuePopover();
      valuePopover.style.visibility = "";
      valueMenuOpen = true;
      valueOverflowWrap.classList.add("is-open");
      valueToggle.setAttribute("aria-expanded", "true");
    }

    valueToggle.addEventListener("click", event => {
      event.stopPropagation();
      if (valueMenuOpen || valuePopover.matches(":popover-open")) closeValuePopover();
      else openValuePopover();
    });
    valuePopover.addEventListener("toggle", event => {
      if (event.newState === "closed") {
        valuePopover.hidden = true;
        valueMenuOpen = false;
        valueOverflowWrap.classList.remove("is-open");
        valueToggle.setAttribute("aria-expanded", "false");
      }
    });
    valuePopover.addEventListener("click", event => event.stopPropagation());
    valueOverflowWrap.append(valueToggle, valuePopover);
    tags.append(valueOverflowWrap);
    scheduleValueFit();

    const stats = el("div", "rf-filter-card-stats");
    stats.setAttribute("aria-label", `Filter metrics for ${rangeLabel()}`);
    [
      ["Events in", filterMetricText(filter.metrics?.received), "yellow"],
      ["Filtered out", filterMetricText(filter.metrics?.filtered), "cyan"],
      ["Reduction", filterReductionText(filter.metrics), "green"],
    ].forEach(([label, value, tone]) => {
      const metric = el("span", `rf-filter-card-stat rf-filter-card-stat-${tone}`);
      metric.append(el("small", "", label), el("strong", "", value));
      stats.append(metric);
    });

    const footer = el("div", "rf-filter-card-footer");
    const sourceGroup = el("span", "rf-filter-card-source-group");
    sourceGroup.append(el("b", "", "Sources"));
    const sourceSummary = el("span", "rf-filter-card-sources");
    const configuredSources = [...new Set((filter.sources || []).filter(Boolean))];
    let sourceMenuOpen = false;
    let sourceFitFrame = null;

    const fitCollapsedSources = () => {
      sourceFitFrame = null;
      if (!sourceSummary.isConnected) return;
      const width = sourceSummary.clientWidth;
      if (!width) return;

      const sourceNodes = [...sourceSummary.querySelectorAll("[data-filter-source]")];
      const overflowWrap = sourceSummary.querySelector(".rf-filter-source-overflow-wrap");
      const toggle = overflowWrap?.querySelector(".rf-filter-source-overflow");
      const popover = overflowWrap?.querySelector(".rf-filter-source-popover");
      if (!overflowWrap || !toggle || !popover) return;

      for (const item of sourceNodes) item.hidden = false;
      sourceMenuOpen = false;
      popover.hidden = true;
      toggle.setAttribute("aria-expanded", "false");
      overflowWrap.hidden = true;

      const gap = Number.parseFloat(
        getComputedStyle(sourceSummary).columnGap
        || getComputedStyle(sourceSummary).gap
        || "0",
      ) || 0;
      const totalWidth = sourceNodes.reduce(
        (sum, item, index) => sum + item.getBoundingClientRect().width + (index ? gap : 0),
        0,
      );
      if (totalWidth <= width) return;

      overflowWrap.hidden = false;
      toggle.textContent = "+99";
      const overflowWidth = overflowWrap.getBoundingClientRect().width;
      const available = Math.max(0, width - overflowWidth - gap);
      let used = 0;
      const hiddenSources = [];

      for (const item of sourceNodes) {
        const itemWidth = item.getBoundingClientRect().width;
        const next = used + (used ? gap : 0) + itemWidth;
        if (next <= available) {
          used = next;
        } else {
          item.hidden = true;
          hiddenSources.push(item.dataset.filterSourceKey);
        }
      }

      if (!hiddenSources.length) {
        overflowWrap.hidden = true;
        return;
      }

      toggle.textContent = `+${hiddenSources.length}`;
      toggle.setAttribute("aria-label", `Show ${hiddenSources.length} more filter sources`);
      popover.replaceChildren();
      for (const source of hiddenSources) {
        const item = el("span", "rf-filter-source-popover-item");
        item.setAttribute("role", "menuitem");
        item.append(sourceIcon(source), el("span", "", friendlyName(source)));
        popover.append(item);
      }
    };

    const scheduleSourceFit = () => {
      if (sourceFitFrame !== null) cancelAnimationFrame(sourceFitFrame);
      sourceFitFrame = requestAnimationFrame(fitCollapsedSources);
    };

    const renderSources = () => {
      sourceSummary.replaceChildren();
      sourceMenuOpen = false;

      for (const source of configuredSources) {
        const sourceNode = sourceIcon(source);
        sourceNode.dataset.filterSource = "1";
        sourceNode.dataset.filterSourceKey = source;
        sourceSummary.append(sourceNode);
      }

      const overflowWrap = el("span", "rf-filter-source-overflow-wrap");
      overflowWrap.hidden = true;
      const toggle = el("button", "rf-filter-source-overflow", "+0");
      toggle.type = "button";
      toggle.setAttribute("aria-expanded", "false");
      toggle.setAttribute("aria-haspopup", "menu");
      toggle.setAttribute("aria-label", "Show more filter sources");

      const popover = el("span", "rf-filter-source-popover");
      popover.hidden = true;
      popover.setAttribute("role", "menu");

      toggle.addEventListener("click", event => {
        event.stopPropagation();
        sourceMenuOpen = !sourceMenuOpen;
        popover.hidden = !sourceMenuOpen;
        toggle.setAttribute("aria-expanded", String(sourceMenuOpen));
      });
      popover.addEventListener("click", event => event.stopPropagation());

      overflowWrap.append(toggle, popover);
      sourceSummary.append(overflowWrap);
      sourceSummary.setAttribute(
        "aria-label",
        `${configuredSources.length} configured filter source${configuredSources.length === 1 ? "" : "s"}`,
      );
      scheduleSourceFit();
    };
    renderSources();
    sourceGroup.append(sourceSummary);

    const destinationGroup = el("span", "rf-filter-card-destination-group");
    destinationGroup.append(el("b", "", "Destination"));
    const destinationSummary = el("span", "rf-filter-card-destination");
    destinationSummary.append(destinationLogo(destination), el("span", "", destination.name));
    destinationGroup.append(destinationSummary);

    footer.append(sourceGroup, destinationGroup);
    node.append(header, tags, stats, footer);
    scheduleValueFit();
    scheduleSourceFit();
  }
  function activeFlowGraph() {
    if (!data) return { routes: [], destinations: [], filters: [], links: [] };
    const enabledRoutes = data.routes.filter(route => route.enabled);
    const enabledDestinations = data.destinations.filter(destination => destination.enabled);
    const routeIds = new Set(enabledRoutes.map(route => route.id));
    const destinationIds = new Set(enabledDestinations.map(destination => destination.id));
    const links = data.links.filter(link => link.enabled && routeIds.has(link.route_id) && destinationIds.has(link.destination_id));
    const connectedRouteIds = new Set(links.map(link => link.route_id));
    const filters = (data.filters || [])
      .filter(filter => destinationIds.has(filter.destination_id))
      .map(filter => ({
        ...filter,
        route_ids: (filter.route_ids || []).filter(routeId => routeIds.has(routeId)),
      }))
      .filter(filter => filter.route_ids.length > 0);
    const filterIds = new Set(filters.map(filter => filter.id));
    return {
      routes: enabledRoutes.filter(route => connectedRouteIds.has(route.id)),
      destinations: enabledDestinations,
      filters,
      links: links.map(link => ({
        ...link,
        filter_ids: (link.filter_ids || []).filter(filterId => filterIds.has(filterId)),
      })),
    };
  }
  function showDetails(kind, identity) {
    const current = graphModel || activeFlowGraph();
    if (!data) return;
    selected = { kind, identity };
    dialogBody.replaceChildren();
    if (kind === "route") {
      const route = current.routes.find(r => r.id === identity);
      if (!route) return;
      const targets = current.links.filter(l => l.route_id === identity);
      const destinationNames = targets.map(link => current.destinations.find(d => d.id === link.destination_id)?.name).filter(Boolean);
      setDialogTitle(route.integration_name, sourceIcon(route.source));
      dialogBody.append(
        detailRow("Route", route.name),
        detailRow("Integration", route.integration_name),
        detailRow("Input / protocol", route.input_type || "Any input"),
        detailRow("Active destinations", destinationNames.join(", ") || "None"),
      );
      appendMetricRows(dialogBody, route.metrics);
    } else if (kind === "destination") {
      const d = current.destinations.find(d => d.id === identity);
      if (!d) return;
      const targets = current.links.filter(l => l.destination_id === identity);
      setDialogTitle(d.name, destinationLogo(d));
      dialogBody.append(
        detailRow("Platform", OUTPUT_NAMES[d.output_type] || d.output_type),
        detailRow("Channel", d.channel || "Not labelled"),
        detailRow("Visibility", d.shared ? "Shared" : "Private"),
        detailRow("Active routes", String(targets.length)),
      );
      appendMetricRows(dialogBody, d.metrics);
    } else {
      const filter = current.filters.find(item => item.id === identity);
      if (!filter) return;
      const d = current.destinations.find(item => item.id === filter.destination_id);
      if (!d) return;
      const sourceNames = (filter.sources || []).map(source => friendlyName(source));
      const descriptor = filterCardDescriptor(filter);
      setDialogTitle(String(filter.filter_name || filter.name || "").trim() || "Active filter", icon("filter"));
      const detailRows = [
        detailRow("Sources", sourceNames.join(", ") || "Managed"),
        detailIdentityRow("Destination", destinationLogo(d), d.name),
      ];
      for (const group of descriptor.groups) {
        detailRows.push(detailRow(group.label, group.values.join(", ")));
      }
      detailRows.push(
        detailRow("Total events", filterMetricText(filter.metrics?.received)),
        detailRow("Filtered out", filterMetricText(filter.metrics?.filtered)),
        detailRow("Reduction", filterReductionText(filter.metrics)),
      );
      dialogBody.append(...detailRows);
      if (!descriptor.groups.length) {
        policyDetailRows({ policies: filter.policies || [], fallback: true }).forEach(row => dialogBody.append(row));
      }
    }
    drawEdges();
    if (!dialog.open) dialog.showModal();
  }
  function createNode(kind, identity, label) {
    const node = el("div", `rf-node rf-${kind}`);
    const openDetails = event => {
      if (event.target instanceof Element && event.target.closest("button, a, input, select, textarea")) return;
      showDetails(kind, identity);
    };
    node.setAttribute("role", "button");
    node.tabIndex = 0;
    node.addEventListener("click", openDetails);
    node.addEventListener("keydown", event => {
      if (event.key === "Enter" || event.key === " ") {
        if (event.target !== node) return;
        event.preventDefault();
        showDetails(kind, identity);
      }
    });
    node.dataset.kind = kind;
    node.dataset.identity = identity;
    node.dataset.focusKey = `${kind}:${identity}`;
    node.setAttribute("aria-label", label);
    node.style.gridColumn = String({ route: 1, filter: 2, destination: 3 }[kind]);
    $("rf-graph").append(node);
    return node;
  }
  function renderMetrics() {
    $("rf-metrics").replaceChildren();
    const spec = [["received", "Received", "Source events", "pulse"], ["delivered", "Delivered", "Destination deliveries", "green"], ["filtered", "Filtered out", "Events not routed", "filter"], ["pending", "Retry scheduled", "Latest recorded status", "amber"], ["failed", "Failed", "Terminal failures", "red"]];
    for (const [key, label, note, symbol] of spec) {
      const box = el("div", "rf-metric"), content = el("div");
      box.append(["pulse", "filter"].includes(symbol) ? icon(symbol) : dot(symbol));
      content.append(el("strong", "", metricText(data.metrics[key])), el("span", "", label), el("small", "", data.metrics[key] === null ? "Not recorded" : note));
      box.append(content);
      $("rf-metrics").append(box);
    }
  }

  function average(values) {
    return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null;
  }
  function barycentricOrder(items, neighbors, neighborRanks) {
    const fallback = new Map(items.map((item, index) => [item.id, index]));
    const score = item => {
      const ranks = neighbors(item).map(id => neighborRanks.get(id)).filter(Number.isFinite);
      return average(ranks);
    };
    return [...items].sort((a, b) => {
      const aScore = score(a), bScore = score(b);
      if (aScore === null && bScore !== null) return 1;
      if (aScore !== null && bScore === null) return -1;
      if (aScore !== null && bScore !== null && aScore !== bScore) return aScore - bScore;
      return fallback.get(a.id) - fallback.get(b.id);
    });
  }
  function orderFlowGraph(current) {
    const linksByRoute = new Map(current.routes.map(route => [route.id, current.links.filter(link => link.route_id === route.id)]));
    const linksByDestination = new Map(current.destinations.map(destination => [destination.id, current.links.filter(link => link.destination_id === destination.id)]));
    let routeOrder = [...current.routes], destinationOrder = [...current.destinations];
    for (let pass = 0; pass < 6; pass++) {
      const destinationRanks = new Map(destinationOrder.map((destination, index) => [destination.id, index]));
      routeOrder = barycentricOrder(routeOrder, route => (linksByRoute.get(route.id) || []).map(link => link.destination_id), destinationRanks);
      const routeRanks = new Map(routeOrder.map((route, index) => [route.id, index]));
      destinationOrder = barycentricOrder(destinationOrder, destination => (linksByDestination.get(destination.id) || []).map(link => link.route_id), routeRanks);
    }
    return { routeOrder, destinationOrder, linksByRoute, linksByDestination };
  }
  function resolveCenters(items, desired, heights, gap, minimumTop) {
    const centers = new Map();
    if (!items.length) return centers;

    // Connection targets influence ordering and position, but no single target
    // may drag every following node hundreds of pixels down the canvas.
    const maxSlack = Math.max(24, Math.min(48, gap * 3));
    let cursor = minimumTop;
    for (const item of items) {
      const height = heights.get(item.id) || 80;
      const baseCenter = cursor + height / 2;
      const target = desired.get(item.id);
      const localShift = Number.isFinite(target)
        ? Math.max(0, Math.min(maxSlack, target - baseCenter))
        : 0;
      const center = baseCenter + localShift;
      centers.set(item.id, center);
      cursor = center + height / 2 + gap;
    }

    const wanted = items.map(item => desired.get(item.id)).filter(Number.isFinite);
    if (wanted.length) {
      const actualMean = average(items.map(item => centers.get(item.id)));
      const wantedMean = average(wanted);
      const requestedShift = wantedMean - actualMean;
      const availableUp = Math.min(...items.map(
        item => centers.get(item.id) - (heights.get(item.id) || 80) / 2 - minimumTop,
      ));
      const layerShift = requestedShift < 0
        ? Math.max(requestedShift, -Math.max(0, availableUp))
        : Math.min(requestedShift, maxSlack);
      if (layerShift) {
        for (const item of items) centers.set(item.id, centers.get(item.id) + layerShift);
      }
    }
    return centers;
  }
  function packCentersFromTop(items, heights, gap, minimumTop) {
    const centers = new Map();
    let cursor = minimumTop;
    for (const item of items) {
      const height = heights.get(item.id) || 80;
      const center = cursor + height / 2;
      centers.set(item.id, center);
      cursor += height + gap;
    }
    return centers;
  }
  function sortLayerByDesired(items, desired) {
    const fallback = new Map(items.map((item, index) => [item.id, index]));
    return [...items].sort((a, b) => {
      const aTarget = desired.get(a.id);
      const bTarget = desired.get(b.id);
      const aFinite = Number.isFinite(aTarget);
      const bFinite = Number.isFinite(bTarget);
      if (aFinite && bFinite && aTarget !== bTarget) return aTarget - bTarget;
      if (aFinite !== bFinite) return aFinite ? -1 : 1;
      return fallback.get(a.id) - fallback.get(b.id);
    });
  }
  function computeFlowLayout(current, ordered, headerBottom) {
    let routeItems = [...ordered.routeOrder];
    let destinationItems = [...ordered.destinationOrder];
    let filterItems = current.filters.map(filter => ({ id: filter.id, filter }));
    const routeHeights = new Map(routeItems.map(route => [route.id, nodeFor("route", route.id)?.offsetHeight || 80]));
    const destinationHeights = new Map(destinationItems.map(destination => [destination.id, nodeFor("destination", destination.id)?.offsetHeight || 150]));
    const filterHeights = new Map(filterItems.map(item => [item.id, nodeFor("filter", item.id)?.offsetHeight || 168]));

    let routeCenters = packCentersFromTop(routeItems, routeHeights, 12, headerBottom);
    let destinationCenters = packCentersFromTop(destinationItems, destinationHeights, 24, headerBottom);
    let filterCenters = packCentersFromTop(filterItems, filterHeights, 12, headerBottom);

    for (let pass = 0; pass < 10; pass++) {
      const filterDesired = new Map(filterItems.map(item => [
        item.id,
        average([
          ...item.filter.route_ids.map(routeId => routeCenters.get(routeId)),
          destinationCenters.get(item.filter.destination_id),
        ].filter(Number.isFinite)),
      ]));
      filterItems = sortLayerByDesired(filterItems, filterDesired);
      filterCenters = resolveCenters(filterItems, filterDesired, filterHeights, 12, headerBottom);

      const routeDesired = new Map(routeItems.map(route => [
        route.id,
        average((ordered.linksByRoute.get(route.id) || []).flatMap(link => {
          const targets = (link.filter_ids || [])
            .map(filterId => filterCenters.get(filterId))
            .filter(Number.isFinite);
          if (link.direct || !targets.length) {
            const destinationCenter = destinationCenters.get(link.destination_id);
            if (Number.isFinite(destinationCenter)) targets.push(destinationCenter);
          }
          return targets;
        }).filter(Number.isFinite)),
      ]));
      routeItems = sortLayerByDesired(routeItems, routeDesired);
      routeCenters = resolveCenters(routeItems, routeDesired, routeHeights, 12, headerBottom);

      const destinationDesired = new Map(destinationItems.map(destination => [
        destination.id,
        average((ordered.linksByDestination.get(destination.id) || []).flatMap(link => {
          const targets = (link.filter_ids || [])
            .map(filterId => filterCenters.get(filterId))
            .filter(Number.isFinite);
          if (link.direct || !targets.length) {
            const routeCenter = routeCenters.get(link.route_id);
            if (Number.isFinite(routeCenter)) targets.push(routeCenter);
          }
          return targets;
        }).filter(Number.isFinite)),
      ]));
      destinationItems = sortLayerByDesired(destinationItems, destinationDesired);
      destinationCenters = resolveCenters(destinationItems, destinationDesired, destinationHeights, 24, headerBottom);
    }

    const finalFilterDesired = new Map(filterItems.map(item => [
      item.id,
      average([
        ...item.filter.route_ids.map(routeId => routeCenters.get(routeId)),
        destinationCenters.get(item.filter.destination_id),
      ].filter(Number.isFinite)),
    ]));
    filterItems = sortLayerByDesired(filterItems, finalFilterDesired);
    filterCenters = resolveCenters(filterItems, finalFilterDesired, filterHeights, 12, headerBottom);

    const finalRouteDesired = new Map(routeItems.map(route => [
      route.id,
      average((ordered.linksByRoute.get(route.id) || []).flatMap(link => {
        const targets = (link.filter_ids || [])
          .map(filterId => filterCenters.get(filterId))
          .filter(Number.isFinite);
        if (link.direct || !targets.length) {
          const destinationCenter = destinationCenters.get(link.destination_id);
          if (Number.isFinite(destinationCenter)) targets.push(destinationCenter);
        }
        return targets;
      }).filter(Number.isFinite)),
    ]));
    routeItems = sortLayerByDesired(routeItems, finalRouteDesired);
    routeCenters = resolveCenters(routeItems, finalRouteDesired, routeHeights, 12, headerBottom);

    const finalDestinationDesired = new Map(destinationItems.map(destination => [
      destination.id,
      average((ordered.linksByDestination.get(destination.id) || []).flatMap(link => {
        const targets = (link.filter_ids || [])
          .map(filterId => filterCenters.get(filterId))
          .filter(Number.isFinite);
        if (link.direct || !targets.length) {
          const routeCenter = routeCenters.get(link.route_id);
          if (Number.isFinite(routeCenter)) targets.push(routeCenter);
        }
        return targets;
      }).filter(Number.isFinite)),
    ]));
    destinationItems = sortLayerByDesired(destinationItems, finalDestinationDesired);
    destinationCenters = resolveCenters(destinationItems, finalDestinationDesired, destinationHeights, 24, headerBottom);

    const bottoms = [headerBottom];
    for (const route of routeItems) bottoms.push(routeCenters.get(route.id) + (routeHeights.get(route.id) || 80) / 2);
    for (const destination of destinationItems) bottoms.push(destinationCenters.get(destination.id) + (destinationHeights.get(destination.id) || 150) / 2);
    for (const item of filterItems) bottoms.push(filterCenters.get(item.id) + (filterHeights.get(item.id) || 168) / 2);
    return {
      ...ordered,
      routeOrder: routeItems,
      destinationOrder: destinationItems,
      routeCenters,
      destinationCenters,
      filterCenters,
      filterItems,
      height: Math.max(...bottoms) + 20,
    };
  }
  function positionNode(node, column, center, headerBottom) {
    if (!node || !column || !Number.isFinite(center)) return;
    node.style.position = "absolute";
    node.style.left = `${column.left}px`;
    node.style.width = `${column.width}px`;
    node.style.top = `${Math.max(headerBottom, center - node.offsetHeight / 2)}px`;
    node.style.gridColumn = "auto";
    node.style.gridRow = "auto";
    node.dataset.layoutY = String(Math.round(center));
  }
  function renderGraph() {
    const graph = $("rf-graph");
    graph.querySelectorAll(":scope > :not(svg)").forEach(n => n.remove());
    graphModel = activeFlowGraph();
    const current = graphModel;
    const ordered = orderFlowGraph(current);
    const headingNodes = new Map();
    [["route", "Integration routes"], ["filter", "Active filters"], ["destination", "Destinations"]].forEach(([kind, label]) => {
      const head = el("div", "rf-column-heading", label); graph.append(head); headingNodes.set(kind, head);
    });

    for (const r of ordered.routeOrder) {
      const node = createNode("route", r.id, `${r.integration_name}: ${r.name}. View details`);
      node.append(sourceIcon(r.source));
      const text = el("div", "rf-node-copy");
      text.append(el("strong", "", r.integration_name), el("small", "", r.name), el("span", "rf-green", `Enabled · ${r.input_type || "Any input"}`));
      node.append(text);
    }

    for (const filter of current.filters) {
      const destination = current.destinations.find(item => item.id === filter.destination_id);
      if (!destination) continue;
      const routes = filter.route_ids.map(routeId => current.routes.find(route => route.id === routeId)).filter(Boolean);
      const node = createNode("filter", filter.id, `Active filter for ${destination.name}`);
      renderFilterCard(node, filter, routes, destination);
    }

    for (const d of ordered.destinationOrder) {
      const node = createNode("destination", d.id, `${d.name}. View destination details`);
      const top = el("div", "rf-destination-top"), copy = el("div", "rf-node-copy");
      copy.append(el("strong", "", d.name), el("small", "", d.channel || OUTPUT_NAMES[d.output_type] || d.output_type));
      top.append(destinationLogo(d), copy);
      const counts = el("div", "rf-destination-metrics");
      [["delivered", "delivered", "green"], ["pending", "retry scheduled", "amber"], ["failed", "failed", "red"]].forEach(([k, label, color]) => {
        const n = el("span", `rf-${color}`); n.append(dot(color), document.createTextNode(`${metricText(d.metrics[k])} ${label}`)); counts.append(n);
      });
      const assigned = current.links.filter(link => link.destination_id === d.id).length;
      node.append(top, counts, el("small", "rf-last", `Enabled · ${assigned} active route${assigned === 1 ? "" : "s"}`));
    }

    const hasGraph = current.routes.length > 0 || current.destinations.length > 0;
    $("rf-empty").hidden = hasGraph;
    $("rf-empty").textContent = "No enabled routes or destinations.";
    graph.hidden = !hasGraph;

    if (hasGraph && window.innerWidth > 640) {
      const columns = new Map([...headingNodes].map(([kind, head]) => [kind, { left: head.offsetLeft, width: head.offsetWidth }]));
      const headerBottom = Math.max(...[...headingNodes.values()].map(head => head.offsetTop + head.offsetHeight)) + 18;
      const layout = computeFlowLayout(current, ordered, headerBottom);
      graph.style.height = `${Math.ceil(layout.height)}px`;
      graph.dataset.layoutMode = "connected-compact-auto";
      for (const route of layout.routeOrder) positionNode(nodeFor("route", route.id), columns.get("route"), layout.routeCenters.get(route.id), headerBottom);
      for (const item of layout.filterItems) positionNode(nodeFor("filter", item.id), columns.get("filter"), layout.filterCenters.get(item.id), headerBottom);
      for (const destination of layout.destinationOrder) positionNode(nodeFor("destination", destination.id), columns.get("destination"), layout.destinationCenters.get(destination.id), headerBottom);
    } else {
      graph.style.height = "";
      graph.dataset.layoutMode = "stacked";
    }
    drawEdges();
  }
  function renderHistory() {
    const body = $("rf-history-body"); body.replaceChildren();
    const items = allHistory ? data.history : data.history.slice(0, 4);
    for (const item of items) {
      const row = el("tr"), time = el("td", "", formatTime(item.completed_at || item.created_at));
      const source = el("td"), sourceWrap = el("span", "rf-history-identity"); sourceWrap.append(sourceIcon(item.source), document.createTextNode(friendlyName(item.source))); source.append(sourceWrap);
      const target = el("td"), dest = data.destinations.find(d => d.id === item.destination_id);
      if (dest) { const wrap = el("span", "rf-history-identity"); wrap.append(destinationLogo(dest), document.createTextNode(dest.name)); target.append(wrap); }
      else target.textContent = "Removed or unavailable";
      const label = { delivered: "Delivered", retry_scheduled: "Retry scheduled", failed: "Failed" }[item.outcome] || item.outcome;
      const status = el("td", {delivered:"rf-green", retry_scheduled:"rf-amber", failed:"rf-red"}[item.outcome] || "", label);
      row.append(time, source, target, status, el("td", "", item.attempt_number)); body.append(row);
    }
    $("rf-history-empty").hidden = Boolean(items.length);
    $("rf-history-toggle").textContent = allHistory ? "Show less" : `View all (${data.history.length})`;
    $("rf-history-toggle").disabled = data.history.length <= 4;
  }
  function render() {
    const focusKey = document.activeElement?.dataset?.focusKey;
    renderMetrics(); renderGraph(); renderHistory();
    if (focusKey) Array.from(section.querySelectorAll("[data-focus-key]")).find(n => n.dataset.focusKey === focusKey)?.focus({ preventScroll: true });
    if (dialog.open && selected) {
      const current = graphModel || activeFlowGraph();
      const found = selected.kind === "route"
        ? current.routes.some(r => r.id === selected.identity)
        : selected.kind === "destination"
          ? current.destinations.some(d => d.id === selected.identity)
          : current.filters.some(filter => filter.id === selected.identity);
      if (found) showDetails(selected.kind, selected.identity); else dialog.close();
    }
  }

  function nodeFor(kind, id) { return Array.from($("rf-graph").querySelectorAll(`.rf-${kind}`)).find(n => n.dataset.identity === id); }
  function relevant(link, filterId = null) {
    return !selected
      || (selected.kind === "route" && selected.identity === link.route_id)
      || (selected.kind === "destination" && selected.identity === link.destination_id)
      || (selected.kind === "filter" && selected.identity === filterId);
  }
  function edgeCurve(a, b) {
    const x = a.offsetLeft + a.offsetWidth, y = a.offsetTop + a.offsetHeight / 2;
    const xx = b.offsetLeft, yy = b.offsetTop + b.offsetHeight / 2, gap = xx - x, bend = Math.max(20, Math.min(gap * .2, 80));
    return `M${x} ${y} C${x+bend} ${y} ${xx-bend} ${yy} ${xx} ${yy}`;
  }
  function drawEdges() {
    if (!data || section.hidden) return;
    const graph = $("rf-graph"), edges = $("rf-edges");
    const edgeLayer = $("rf-edge-layer"); edgeLayer.replaceChildren(); edgePaths = new Map();
    if (graph.hidden || graph.clientWidth === 0 || window.innerWidth <= 640) return;
    edges.setAttribute("viewBox", `0 0 ${graph.clientWidth} ${graph.clientHeight}`);
    const defs = svg("defs"), marker = svg("marker", { id:"rf-arrow", viewBox:"0 0 8 8", refX:7, refY:4, markerWidth:7, markerHeight:7, orient:"auto" });
    marker.append(svg("path", {d:"M0 0 L8 4 L0 8 Z", fill:"currentColor"})); defs.append(marker); edgeLayer.append(defs);
    const current = graphModel || activeFlowGraph();

    for (const link of current.links) {
      const key = linkKey(link.route_id, link.destination_id);
      const route = nodeFor("route", link.route_id);
      const destination = nodeFor("destination", link.destination_id);
      if (!route || !destination) continue;
      const bundle = { direct: [], filters: new Map() };
      const filterRecords = (link.filter_ids || [])
        .map(filterId => current.filters.find(filter => filter.id === filterId))
        .filter(Boolean);

      if (link.direct || !filterRecords.length) {
        const path = svg("path", {
          d: edgeCurve(route, destination),
          class: `rf-edge${relevant(link) ? "" : " rf-dim"}`,
          "marker-end": "url(#rf-arrow)",
        });
        edgeLayer.append(path);
        bundle.direct.push(path);
      }

      for (const filter of filterRecords) {
        const filterNode = nodeFor("filter", filter.id);
        if (!filterNode) continue;
        const paths = [];
        for (const [a, b] of [[route, filterNode], [filterNode, destination]]) {
          const path = svg("path", {
            d: edgeCurve(a, b),
            class: `rf-edge${relevant(link, filter.id) ? "" : " rf-dim"}`,
            "marker-end": "url(#rf-arrow)",
          });
          edgeLayer.append(path);
          paths.push(path);
        }
        for (const source of filter.sources || []) {
          bundle.filters.set(source, paths);
        }
      }
      edgePaths.set(key, bundle);
    }

    const mini = $("rf-minimap"); mini.replaceChildren();
    for (const bundle of edgePaths.values()) {
      const all = [...new Set([...bundle.direct, ...[...bundle.filters.values()].flat()])];
      for (const p of all) {
        const copy = p.cloneNode();
        copy.removeAttribute("marker-end");
        copy.setAttribute("transform", `scale(${130/graph.clientWidth} ${46/graph.clientHeight})`);
        mini.append(copy);
      }
    }
    graph.querySelectorAll(".rf-node").forEach(n=>mini.append(svg("rect", {x:n.offsetLeft/graph.clientWidth*130,y:n.offsetTop/graph.clientHeight*46,width:n.offsetWidth/graph.clientWidth*130,height:Math.max(2,n.offsetHeight/graph.clientHeight*46),rx:1})));
  }
  function stopPulses() {
    if (pulseFrame !== null) cancelAnimationFrame(pulseFrame);
    pulseFrame = null; pulses.forEach(p=>p.dot.remove()); pulses=[];
  }
  function animateAttempts(items) {
    if (!active() || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    for (const item of items.slice(0,12)) {
      const key = linkKey(item.route_id,item.destination_id);
      const bundle = edgePaths.get(key);
      const source = String(item.source || "");
      const filterPaths = bundle?.filters?.get(source);
      const paths = filterPaths?.length ? filterPaths : bundle?.direct;
      if (!paths?.length) continue;
      const filtered = item.outcome === "filtered";
      const circle = svg("circle", {
        r: 3.2,
        class: `rf-particle ${item.outcome === "failed" ? "rf-failed-particle" : filtered ? "rf-filtered-particle" : ""}`,
      });
      $("rf-particle-layer").append(circle);
      pulses.push({dot: circle, key, source, filtered, started: null});
    }
    function frame(now) {
      if (!active()) { stopPulses(); return; }
      pulses = pulses.filter(p => {
        if (p.started === null) p.started = now;
        const elapsed = (now - p.started) / 1600;
        if (elapsed >= 1) { p.dot.remove(); return false; }
        const bundle = edgePaths.get(p.key);
        if (!bundle) { p.dot.remove(); return false; }
        const filterPaths = bundle.filters?.get(p.source);
        const paths = filterPaths?.length ? filterPaths : bundle.direct;
        if (!paths?.length) { p.dot.remove(); return false; }
        const activePaths = p.filtered && filterPaths?.length ? filterPaths.slice(0, 1) : paths;
        const scaled = elapsed * activePaths.length;
        const index = Math.min(activePaths.length - 1, Math.floor(scaled));
        const progress = scaled - index;
        const path = activePaths[index];
        const pt = path.getPointAtLength(path.getTotalLength() * progress);
        p.dot.setAttribute("cx", pt.x);
        p.dot.setAttribute("cy", pt.y);
        return true;
      });
      pulseFrame = pulses.length ? requestAnimationFrame(frame) : null;
    }
    if (pulses.length && pulseFrame===null) pulseFrame=requestAnimationFrame(frame);
  }
  function invalidate() {
    generation++; clearTimeout(timer); timer=null;
    if (controller) controller.abort(); controller=null;
    stopPulses();
  }
  function cachedRoutingFlowSnapshot() {
    range = selectedRoutingRange();
    const snapshots = state.routingFlowSnapshots && typeof state.routingFlowSnapshots === "object"
      ? state.routingFlowSnapshots
      : {};
    const cached = snapshots[range];
    if (
      !cached
      || String(cached.range || "") !== range
      || !Array.isArray(cached.routes)
      || !Array.isArray(cached.destinations)
      || !Array.isArray(cached.filters)
      || !Array.isArray(cached.links)
      || !Array.isArray(cached.history)
      || !cached.metrics
    ) return null;
    return cached;
  }

  function hydrateCachedRoutingFlow() {
    if (data) return false;
    const cached = cachedRoutingFlowSnapshot();
    if (!cached) return false;
    data = cached;
    seen = new Set(cached.history.map(item => item.id));
    signature = JSON.stringify({ ...cached, generated_at: 0, since: 0 });
    render();
    return true;
  }

  function clearPrivateData() {
    stopPulses();
    data=null; signature=""; owner=null; seen=new Set(); graphModel=null;
    $("rf-metrics").replaceChildren(); $("rf-history-body").replaceChildren();
    $("rf-graph").querySelectorAll(":scope > :not(svg)").forEach(n=>n.remove());
    $("rf-edge-layer").replaceChildren(); $("rf-particle-layer").replaceChildren(); edgePaths = new Map(); $("rf-minimap").replaceChildren();
    $("rf-error").hidden=true;
    if(dialog.open) dialog.close();
  }
  async function refresh(options = {}) {
    const allowCache = options.allowCache !== false;
    const forceRender = options.forceRender === true;
    if (!active()) return;
    range = selectedRoutingRange();
    if(owner!==state.user.id){clearPrivateData();owner=state.user.id;}
    if (allowCache) hydrateCachedRoutingFlow();
    if (busy) {
      const previous = pendingRefreshOptions || { allowCache: true, forceRender: false };
      pendingRefreshOptions = {
        allowCache: previous.allowCache && allowCache,
        forceRender: previous.forceRender || forceRender,
      };
      return;
    }
    busy=true;
    const requestRange = selectedRoutingRange();
    range = requestRange;
    const token=generation, userId=state.user.id;
    const abort=new AbortController(); controller=abort;
    const timeout=setTimeout(()=>abort.abort(),20000);
    try {
      const response=await fetch(`${API}/routing-flow/${requestRange}`,{method:"GET",credentials:"same-origin",cache:"no-store",headers:{Accept:"application/json"},signal:abort.signal});
      if(response.status===401){expireSession();return;}
      if(!response.ok) throw new Error(`Overview request failed (${response.status}).`);
      const next=await response.json();
      if(token!==generation || !active() || state.user?.id!==userId || requestRange!==selectedRoutingRange()) return;
      if (String(next.range || "") !== requestRange) throw new Error(`Overview response range mismatch (requested ${requestRange}, received ${next.range || "missing"}).`);
      if(!Array.isArray(next.routes)||!Array.isArray(next.destinations)||!Array.isArray(next.filters)||!Array.isArray(next.links)||!Array.isArray(next.history)||!next.metrics) throw new Error("The overview response is invalid.");
      const fresh=data?next.history.filter(h=>!seen.has(h.id)):[];
      seen=new Set(next.history.map(h=>h.id));
      const nextSignature=JSON.stringify({...next,generated_at:0,since:0});data=next;
      state.routingFlowSnapshots = {
        ...(state.routingFlowSnapshots || {}),
        [requestRange]: next,
      };
      if (typeof qaSaveWorkspaceCache === "function") qaSaveWorkspaceCache();
      if (forceRender || nextSignature !== signature) {
        signature=nextSignature;
        render();
      }
      $("rf-error").hidden=!next.errors?.length;
      $("rf-error").textContent=(next.errors||[]).map(e=>`${e.component}: ${e.message}`).join(" · ");
      animateAttempts(fresh);
    } catch(error) {
      if(token!==generation || !active()) return;
      $("rf-error").hidden=false;
      $("rf-error").textContent=`${error.name==='AbortError'?'Overview request timed out.':error.message} ${data?'Showing the last successful snapshot.':'No overview loaded.'} Retrying automatically.`;
    } finally {
      clearTimeout(timeout);
      if(controller===abort)controller=null;
      busy=false;
      const pending = pendingRefreshOptions;
      pendingRefreshOptions = null;
      if(active()) {
        timer=setTimeout(
          () => pending ? refresh(pending) : refresh(),
          pending || token!==generation ? 0 : POLL_MS,
        );
      }
    }
  }
  function sync() {
    invalidate();
    if(!state.user){clearPrivateData();return;}
    if(!active())return;
    requestAnimationFrame(drawEdges);refresh();
  }
  const previousNavigate=navigate;
  navigate=function routingFlowNavigate(view,historyMode="push") {
    // The regional catalog caches Dashboard on the shared title element. A new
    // view outside that catalog must not inherit its previous translation key.
    if(view===PAGE) delete byId("page-title").dataset.i18nSource;
    const result=previousNavigate(view,historyMode);sync();return result;
  };
  const previousExpire=expireSession;
  expireSession=function routingFlowExpireSession(){
    invalidate();
    clearPrivateData();
    state.routingFlowSnapshots = {};
    return previousExpire();
  };
  document.addEventListener("visibilitychange",sync);
  function changeRoutingRange(nextRange) {
    const requested = String(nextRange || "").trim();
    range = ROUTING_RANGE_KEYS.has(requested) ? requested : selectedRoutingRange();
    signature = "";
    invalidate();
    clearPrivateData();
    refresh({ allowCache: true, forceRender: true });
  }
  $("rf-range").addEventListener("change",()=>changeRoutingRange($("rf-range").value));
  function setZoom(value){zoom=Math.min(1,Math.max(.7,Math.round(value*10)/10));$("rf-graph").style.transform=`scale(${zoom})`;$("rf-zoom-value").textContent=`${Math.round(zoom*100)}%`;$("rf-plus").disabled=zoom===1;$("rf-minus").disabled=zoom===.7;}
  $("rf-minus").addEventListener("click",()=>setZoom(zoom-.1));$("rf-plus").addEventListener("click",()=>setZoom(zoom+.1));$("rf-fit").addEventListener("click",()=>setZoom(1));
  $("rf-history-toggle").addEventListener("click",()=>{allHistory=!allHistory;if(data)renderHistory();});
  new ResizeObserver(()=>{if(resizeFrame!==null)cancelAnimationFrame(resizeFrame);resizeFrame=requestAnimationFrame(()=>{resizeFrame=null;if(data&&active())renderGraph();else drawEdges();});}).observe($("rf-graph"));
  setZoom(1);sync();
})();