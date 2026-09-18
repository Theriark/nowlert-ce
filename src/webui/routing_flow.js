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
  let graphModel = null;

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
  const $ = id => section.querySelector(`#${id}`);

  function syncRangeOptionsFromDashboard() {
    const dashboardRange = document.getElementById("history-range");
    const routingRange = $("rf-range");
    if (!dashboardRange || !routingRange) return;

    const selected = routingRange.value || range;
    const fragment = document.createDocumentFragment();
    for (const option of dashboardRange.options) {
      const next = document.createElement("option");
      next.value = option.value;
      const prefix = option.textContent.trim().startsWith("Last ") ? "" : "Last ";
      next.textContent = `${prefix}${option.textContent.trim()}`;
      fragment.append(next);
    }
    routingRange.replaceChildren(fragment);

    const hasSelected = [...routingRange.options].some(
      (option) => option.value === selected,
    );
    routingRange.value = hasSelected ? selected : (dashboardRange.value || "1d");
    range = routingRange.value;
  }

  syncRangeOptionsFromDashboard();
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
  function renderFilterCard(node, filter, routes, destination) {
    node.classList.add("rf-filter-card");
    const descriptor = filterCardDescriptor(filter);

    const header = el("div", "rf-filter-card-header");
    const visual = el("span", "rf-filter-card-icon");
    visual.append(icon("filter"));
    const headingCopy = el("span", "rf-filter-card-heading-copy");
    const title = el("strong", "rf-filter-card-title");
    title.append(
      document.createTextNode("Filter: "),
      el("span", "rf-filter-card-title-accent", descriptor.title),
    );
    headingCopy.append(title);
    header.append(visual, headingCopy);

    const tags = el("div", "rf-filter-card-tags");

    function renderFilterRuleRow(group, groupIndex) {
      const row = el("div", "rf-filter-rule-row");
      let expanded = false;
      let fitFrame = null;

      const fitCollapsedRow = () => {
        fitFrame = null;
        if (expanded || !row.isConnected) return;
        const width = row.clientWidth;
        if (!width) return;

        const label = row.querySelector("[data-filter-label]");
        const values = [...row.querySelectorAll("[data-filter-value]")];
        const toggle = row.querySelector(".rf-filter-overflow-button");
        if (!label || !toggle) return;

        label.hidden = false;
        for (const value of values) value.hidden = false;
        toggle.hidden = true;

        const computed = getComputedStyle(row);
        const gap = Number.parseFloat(computed.columnGap || computed.gap || "0") || 0;
        const labelWidth = label.getBoundingClientRect().width;
        const valuesWidth = values.reduce(
          (sum, value, index) => sum + value.getBoundingClientRect().width + (index ? gap : 0),
          0,
        );
        if (labelWidth + (values.length ? gap : 0) + valuesWidth <= width) return;

        toggle.hidden = false;
        toggle.textContent = "+99";
        const toggleWidth = toggle.getBoundingClientRect().width;
        const available = Math.max(
          0,
          width - labelWidth - gap - toggleWidth - gap,
        );
        let used = 0;
        for (const value of values) {
          const valueWidth = value.getBoundingClientRect().width;
          const next = used + (used ? gap : 0) + valueWidth;
          if (next <= available) {
            used = next;
          } else {
            value.hidden = true;
          }
        }

        const hidden = values.filter(value => value.hidden).length;
        if (!hidden) {
          toggle.hidden = true;
          return;
        }
        toggle.textContent = `+${hidden}`;
        toggle.setAttribute("aria-label", `Show ${hidden} more ${group.label} values`);
      };

      const scheduleFit = () => {
        if (fitFrame !== null) cancelAnimationFrame(fitFrame);
        fitFrame = requestAnimationFrame(fitCollapsedRow);
      };

      const renderRow = () => {
        row.replaceChildren();
        row.classList.toggle("is-expanded", expanded);

        const label = el("span", "rf-filter-rule-label", `${group.label}:`);
        label.dataset.filterLabel = "1";
        label.dataset.filterGroup = String(groupIndex);
        row.append(label);

        for (const value of group.values) {
          const item = el(
            "span",
            `rf-filter-rule-tag rf-filter-rule-tag-${filterTagTone(value)}`,
            value,
          );
          item.dataset.filterValue = "1";
          item.dataset.filterGroup = String(groupIndex);
          row.append(item);
        }

        const toggle = el(
          "button",
          "rf-filter-rule-tag rf-filter-rule-tag-muted rf-filter-overflow-button",
          expanded ? "−" : "+0",
        );
        toggle.type = "button";
        toggle.hidden = !expanded;
        toggle.setAttribute("aria-expanded", String(expanded));
        toggle.setAttribute(
          "aria-label",
          expanded ? `Collapse ${group.label} values` : `Show more ${group.label} values`,
        );
        toggle.addEventListener("click", event => {
          event.stopPropagation();
          expanded = !expanded;
          renderRow();
        });
        row.append(toggle);

        if (!expanded) scheduleFit();
      };

      renderRow();
      return row;
    }

    for (const [groupIndex, group] of descriptor.groups.entries()) {
      tags.append(renderFilterRuleRow(group, groupIndex));
    }

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
    let sourcesExpanded = false;
    let sourceFitFrame = null;

    const fitCollapsedSources = () => {
      sourceFitFrame = null;
      if (sourcesExpanded || !sourceSummary.isConnected) return;
      const width = sourceSummary.clientWidth;
      if (!width) return;

      const sourceNodes = [...sourceSummary.querySelectorAll("[data-filter-source]")];
      const toggle = sourceSummary.querySelector(".rf-filter-source-overflow");
      if (!toggle) return;

      for (const item of sourceNodes) item.hidden = false;
      toggle.hidden = true;

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

      toggle.hidden = false;
      toggle.textContent = "+99";
      const toggleWidth = toggle.getBoundingClientRect().width + gap;
      const available = Math.max(0, width - toggleWidth);
      let used = 0;

      for (const item of sourceNodes) {
        const itemWidth = item.getBoundingClientRect().width;
        const next = used + (used ? gap : 0) + itemWidth;
        if (next <= available) {
          used = next;
        } else {
          item.hidden = true;
        }
      }

      const hidden = sourceNodes.filter(item => item.hidden).length;
      if (!hidden) {
        toggle.hidden = true;
        return;
      }
      toggle.textContent = `+${hidden}`;
      toggle.setAttribute("aria-label", `Show ${hidden} more filter sources`);
    };

    const scheduleSourceFit = () => {
      if (sourceFitFrame !== null) cancelAnimationFrame(sourceFitFrame);
      sourceFitFrame = requestAnimationFrame(fitCollapsedSources);
    };

    const renderSources = () => {
      sourceSummary.replaceChildren();
      sourceSummary.classList.toggle("is-expanded", sourcesExpanded);

      for (const source of configuredSources) {
        const sourceNode = sourceIcon(source);
        sourceNode.dataset.filterSource = "1";
        sourceSummary.append(sourceNode);
      }

      const toggle = el(
        "button",
        "rf-filter-source-overflow",
        sourcesExpanded ? "−" : "+0",
      );
      toggle.type = "button";
      toggle.hidden = !sourcesExpanded;
      toggle.setAttribute("aria-expanded", String(sourcesExpanded));
      toggle.setAttribute(
        "aria-label",
        sourcesExpanded ? "Collapse filter sources" : "Show more filter sources",
      );
      toggle.addEventListener("click", event => {
        event.stopPropagation();
        sourcesExpanded = !sourcesExpanded;
        renderSources();
      });
      sourceSummary.append(toggle);

      sourceSummary.setAttribute(
        "aria-label",
        `${configuredSources.length} configured filter source${configuredSources.length === 1 ? "" : "s"}`,
      );

      if (!sourcesExpanded) scheduleSourceFit();
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
      setDialogTitle("Active filter", icon("filter"));
      dialogBody.append(
        detailRow("Sources", sourceNames.join(", ") || "Managed"),
        detailIdentityRow("Destination", destinationLogo(d), d.name),
        detailRow("Status", "Active"),
      );
      policyDetailRows({ policies: filter.policies || [], fallback: true }).forEach(row => dialogBody.append(row));
    }
    drawEdges();
    if (!dialog.open) dialog.showModal();
  }
  function createNode(kind, identity, label) {
    const node = button("", () => showDetails(kind, identity), `rf-node rf-${kind}`);
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
    let cursor = minimumTop;
    for (const item of items) {
      const height = heights.get(item.id) || 80;
      const target = desired.get(item.id);
      const center = Math.max(Number.isFinite(target) ? target : cursor + height / 2, cursor + height / 2);
      centers.set(item.id, center);
      cursor = center + height / 2 + gap;
    }
    const wanted = items.map(item => desired.get(item.id)).filter(Number.isFinite);
    if (wanted.length && items.length) {
      const actualMean = average(items.map(item => centers.get(item.id)));
      const wantedMean = average(wanted);
      const availableUp = Math.min(...items.map(item => centers.get(item.id) - (heights.get(item.id) || 80) / 2 - minimumTop));
      const shift = Math.min(Math.max(0, actualMean - wantedMean), Math.max(0, availableUp));
      if (shift > 0) for (const item of items) centers.set(item.id, centers.get(item.id) - shift);
    }
    return centers;
  }
  function computeFlowLayout(current, ordered, headerBottom) {
    const routeHeights = new Map(ordered.routeOrder.map(route => [route.id, nodeFor("route", route.id)?.offsetHeight || 80]));
    const destinationHeights = new Map(ordered.destinationOrder.map(destination => [destination.id, nodeFor("destination", destination.id)?.offsetHeight || 150]));
    let filterItems = current.filters.map(filter => ({ id: filter.id, filter }));
    const filterHeights = new Map(filterItems.map(item => [item.id, nodeFor("filter", item.id)?.offsetHeight || 168]));

    const destinationSeed = new Map();
    let seedCursor = headerBottom;
    for (const destination of ordered.destinationOrder) {
      const incoming = ordered.linksByDestination.get(destination.id) || [];
      const averageRouteHeight = average(incoming.map(link => routeHeights.get(link.route_id)).filter(Number.isFinite)) || 80;
      const bandHeight = Math.max(destinationHeights.get(destination.id) || 150, incoming.length * (averageRouteHeight + 12));
      destinationSeed.set(destination.id, seedCursor + bandHeight / 2);
      seedCursor += bandHeight + 24;
    }

    const routeDesired = new Map(ordered.routeOrder.map(route => [route.id, average((ordered.linksByRoute.get(route.id) || []).map(link => destinationSeed.get(link.destination_id)).filter(Number.isFinite))]));
    let routeCenters = resolveCenters(ordered.routeOrder, routeDesired, routeHeights, 12, headerBottom);
    const destinationDesired = new Map(ordered.destinationOrder.map(destination => [destination.id, average((ordered.linksByDestination.get(destination.id) || []).map(link => routeCenters.get(link.route_id)).filter(Number.isFinite))]));
    let destinationCenters = resolveCenters(ordered.destinationOrder, destinationDesired, destinationHeights, 24, headerBottom);
    let filterCenters = new Map();

    for (let pass = 0; pass < 5; pass++) {
      const filterDesired = new Map(filterItems.map(item => [
        item.id,
        average([
          ...item.filter.route_ids.map(routeId => routeCenters.get(routeId)),
          destinationCenters.get(item.filter.destination_id),
        ].filter(Number.isFinite)),
      ]));
      filterItems = [...filterItems].sort((a, b) => (filterDesired.get(a.id) ?? 0) - (filterDesired.get(b.id) ?? 0) || a.id.localeCompare(b.id));
      filterCenters = resolveCenters(filterItems, filterDesired, filterHeights, 12, headerBottom);

      const nextRouteDesired = new Map(ordered.routeOrder.map(route => [route.id, average((ordered.linksByRoute.get(route.id) || []).flatMap(link => {
        const targets = (link.filter_ids || []).map(filterId => filterCenters.get(filterId)).filter(Number.isFinite);
        if (link.direct || !targets.length) targets.push(destinationCenters.get(link.destination_id));
        return targets;
      }).filter(Number.isFinite))]));
      routeCenters = resolveCenters(ordered.routeOrder, nextRouteDesired, routeHeights, 12, headerBottom);

      const nextDestinationDesired = new Map(ordered.destinationOrder.map(destination => [destination.id, average((ordered.linksByDestination.get(destination.id) || []).flatMap(link => {
        const targets = (link.filter_ids || []).map(filterId => filterCenters.get(filterId)).filter(Number.isFinite);
        if (link.direct || !targets.length) targets.push(routeCenters.get(link.route_id));
        return targets;
      }).filter(Number.isFinite))]));
      destinationCenters = resolveCenters(ordered.destinationOrder, nextDestinationDesired, destinationHeights, 24, headerBottom);
    }

    const finalFilterDesired = new Map(filterItems.map(item => [
      item.id,
      average([
        ...item.filter.route_ids.map(routeId => routeCenters.get(routeId)),
        destinationCenters.get(item.filter.destination_id),
      ].filter(Number.isFinite)),
    ]));
    filterItems = [...filterItems].sort((a, b) => (finalFilterDesired.get(a.id) ?? 0) - (finalFilterDesired.get(b.id) ?? 0) || a.id.localeCompare(b.id));
    filterCenters = resolveCenters(filterItems, finalFilterDesired, filterHeights, 12, headerBottom);

    const topEdges = [
      ...ordered.routeOrder.map(route => routeCenters.get(route.id) - (routeHeights.get(route.id) || 80) / 2),
      ...ordered.destinationOrder.map(destination => destinationCenters.get(destination.id) - (destinationHeights.get(destination.id) || 150) / 2),
      ...filterItems.map(item => filterCenters.get(item.id) - (filterHeights.get(item.id) || 168) / 2),
    ].filter(Number.isFinite);
    const topShift = topEdges.length ? Math.max(0, Math.min(...topEdges) - headerBottom) : 0;
    if (topShift > 0) {
      for (const centers of [routeCenters, destinationCenters, filterCenters]) {
        for (const [id, center] of centers) centers.set(id, center - topShift);
      }
    }

    const bottoms = [headerBottom];
    for (const route of ordered.routeOrder) bottoms.push(routeCenters.get(route.id) + (routeHeights.get(route.id) || 80) / 2);
    for (const destination of ordered.destinationOrder) bottoms.push(destinationCenters.get(destination.id) + (destinationHeights.get(destination.id) || 150) / 2);
    for (const item of filterItems) bottoms.push(filterCenters.get(item.id) + (filterHeights.get(item.id) || 168) / 2);
    return { ...ordered, routeCenters, destinationCenters, filterCenters, filterItems, height: Math.max(...bottoms) + 20 };
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
      graph.dataset.layoutMode = "connected-pixel-auto";
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
    const xx = b.offsetLeft, yy = b.offsetTop + b.offsetHeight / 2, gap = xx - x, bend = gap * .52;
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
    const snapshots = state.routingFlowSnapshots && typeof state.routingFlowSnapshots === "object"
      ? state.routingFlowSnapshots
      : {};
    const cached = snapshots[range];
    if (
      !cached
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
  async function refresh() {
    if (!active() || busy) return;
    if(owner!==state.user.id){clearPrivateData();owner=state.user.id;}
    hydrateCachedRoutingFlow();
    busy=true;
    const token=generation, userId=state.user.id, requestRange=range;
    const abort=new AbortController(); controller=abort;
    const timeout=setTimeout(()=>abort.abort(),20000);
    try {
      const response=await fetch(`${API}/routing-flow/${range}`,{method:"GET",credentials:"same-origin",cache:"no-store",headers:{Accept:"application/json"},signal:abort.signal});
      if(response.status===401){expireSession();return;}
      if(!response.ok) throw new Error(`Overview request failed (${response.status}).`);
      const next=await response.json();
      if(token!==generation || !active() || state.user?.id!==userId || requestRange!==range) return;
      if(!Array.isArray(next.routes)||!Array.isArray(next.destinations)||!Array.isArray(next.filters)||!Array.isArray(next.links)||!Array.isArray(next.history)||!next.metrics) throw new Error("The overview response is invalid.");
      const fresh=data?next.history.filter(h=>!seen.has(h.id)):[];
      seen=new Set(next.history.map(h=>h.id));
      const nextSignature=JSON.stringify({...next,generated_at:0,since:0});data=next;
      state.routingFlowSnapshots = {
        ...(state.routingFlowSnapshots || {}),
        [range]: next,
      };
      if (typeof qaSaveWorkspaceCache === "function") qaSaveWorkspaceCache();
      if(nextSignature!==signature){signature=nextSignature;render();}
      $("rf-error").hidden=!next.errors?.length;
      $("rf-error").textContent=(next.errors||[]).map(e=>`${e.component}: ${e.message}`).join(" · ");
      animateAttempts(fresh);
    } catch(error) {
      if(token!==generation || !active()) return;
      $("rf-error").hidden=false;
      $("rf-error").textContent=`${error.name==='AbortError'?'Overview request timed out.':error.message} ${data?'Showing the last successful snapshot.':'No overview loaded.'} Retrying automatically.`;
    } finally {
      clearTimeout(timeout);if(controller===abort)controller=null;busy=false;
      if(active()) timer=setTimeout(refresh,token===generation?POLL_MS:0);
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
  $("rf-range").addEventListener("change",()=>{range=$("rf-range").value;signature="";invalidate();clearPrivateData();refresh();});
  function setZoom(value){zoom=Math.min(1,Math.max(.7,Math.round(value*10)/10));$("rf-graph").style.transform=`scale(${zoom})`;$("rf-zoom-value").textContent=`${Math.round(zoom*100)}%`;$("rf-plus").disabled=zoom===1;$("rf-minus").disabled=zoom===.7;}
  $("rf-minus").addEventListener("click",()=>setZoom(zoom-.1));$("rf-plus").addEventListener("click",()=>setZoom(zoom+.1));$("rf-fit").addEventListener("click",()=>setZoom(1));
  $("rf-history-toggle").addEventListener("click",()=>{allHistory=!allHistory;if(data)renderHistory();});
  new ResizeObserver(()=>{if(resizeFrame!==null)cancelAnimationFrame(resizeFrame);resizeFrame=requestAnimationFrame(()=>{resizeFrame=null;if(data&&active())renderGraph();else drawEdges();});}).observe($("rf-graph"));
  setZoom(1);sync();
})();