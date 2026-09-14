"use strict";

/* Nowlert 3.1.0 dashboard analytics, built from existing platform data. */
(() => {
  const SVG_NS = "http://www.w3.org/2000/svg";
  const WINDOWS = {
    "10m": { seconds: 600, buckets: 10, label: "10 minutes" },
    "1h": { seconds: 3600, buckets: 12, label: "1 hour" },
    "1d": { seconds: 86400, buckets: 12, label: "1 day" },
    "1m": { seconds: 31 * 86400, buckets: 15, label: "1 month" },
    "1y": { seconds: 366 * 86400, buckets: 12, label: "1 year" },
  };

  function node(tag, className = "", text = "") {
    const item = document.createElement(tag);
    if (className) item.className = className;
    if (text !== "") item.textContent = String(text);
    return item;
  }

  function svgNode(tag, attributes = {}) {
    const item = document.createElementNS(SVG_NS, tag);
    for (const [name, value] of Object.entries(attributes)) {
      item.setAttribute(name, String(value));
    }
    return item;
  }

  function attemptTime(item) {
    const value = Number(item.completed_at || item.created_at || 0);
    return value < 10_000_000_000 ? value : Math.floor(value / 1000);
  }

  function latestAttempts() {
    const latest = new Map();
    for (const item of state.deliveries || []) {
      const key = item.delivery_id || item.id;
      const current = latest.get(key);
      if (!current || Number(item.attempt_number || 0) >= Number(current.attempt_number || 0)) {
        latest.set(key, item);
      }
    }
    return [...latest.values()];
  }

  function attemptsForRange() {
    const spec = WINDOWS[state.historyRange] || WINDOWS["1h"];
    const since = Math.floor(Date.now() / 1000) - spec.seconds;
    return latestAttempts().filter((item) => attemptTime(item) >= since);
  }

  function bucketLabel(timestamp, range) {
    const date = new Date(timestamp * 1000);
    const options = range === "1y"
      ? { month: "short" }
      : range === "1m"
        ? { day: "2-digit", month: "short" }
        : range === "1d"
          ? { hour: "2-digit", minute: "2-digit" }
          : { hour: "2-digit", minute: "2-digit" };
    return new Intl.DateTimeFormat(state.preferences.language || "en-GB", {
      ...options,
      hour12: state.preferences.time_format === "12",
      timeZone: state.preferences.timezone || "Europe/Lisbon",
    }).format(date);
  }

  function renderChart() {
    const container = byId("dashboard-delivery-chart");
    const summary = byId("dashboard-chart-summary");
    if (!container || !summary) return;
    container.replaceChildren();
    summary.replaceChildren();

    const spec = WINDOWS[state.historyRange] || WINDOWS["1h"];
    const now = Math.floor(Date.now() / 1000);
    const bucketSeconds = Math.max(1, Math.ceil(spec.seconds / spec.buckets));
    const start = now - spec.seconds;
    const buckets = Array.from({ length: spec.buckets }, (_, index) => ({
      start: start + index * bucketSeconds,
      delivered: 0,
      failed: 0,
    }));
    const attempts = attemptsForRange();
    for (const item of attempts) {
      const index = Math.min(
        buckets.length - 1,
        Math.max(0, Math.floor((attemptTime(item) - start) / bucketSeconds)),
      );
      if (["delivered", "success"].includes(item.outcome)) buckets[index].delivered += 1;
      else buckets[index].failed += 1;
    }

    const width = 760;
    const height = 270;
    const padding = { top: 18, right: 18, bottom: 42, left: 44 };
    const plotWidth = width - padding.left - padding.right;
    const plotHeight = height - padding.top - padding.bottom;
    const maximum = Math.max(1, ...buckets.map((item) => item.delivered + item.failed));
    const svg = svgNode("svg", {
      viewBox: `0 0 ${width} ${height}`,
      role: "img",
      "aria-label": `Delivery history for ${spec.label}`,
      preserveAspectRatio: "none",
    });
    const defs = svgNode("defs");
    const gradient = svgNode("linearGradient", {
      id: "dashboard-amber-gradient",
      x1: "0%",
      y1: "0%",
      x2: "0%",
      y2: "100%",
    });
    gradient.append(
      svgNode("stop", { offset: "0%", "stop-color": "#ffcf4c" }),
      svgNode("stop", { offset: "100%", "stop-color": "#d9a629" }),
    );
    defs.append(gradient);
    svg.append(defs);

    for (let line = 0; line <= 4; line += 1) {
      const y = padding.top + (plotHeight * line) / 4;
      svg.append(svgNode("line", {
        class: "chart-grid-line",
        x1: padding.left,
        y1: y,
        x2: width - padding.right,
        y2: y,
      }));
      const value = Math.round(maximum * (1 - line / 4));
      const label = svgNode("text", {
        class: "chart-axis-label",
        x: padding.left - 10,
        y: y + 4,
        "text-anchor": "end",
      });
      label.textContent = String(value);
      svg.append(label);
    }

    const slot = plotWidth / buckets.length;
    const barWidth = Math.max(8, Math.min(34, slot * 0.56));
    buckets.forEach((bucket, index) => {
      const x = padding.left + index * slot + (slot - barWidth) / 2;
      const deliveredHeight = (bucket.delivered / maximum) * plotHeight;
      const failedHeight = (bucket.failed / maximum) * plotHeight;
      const baseline = padding.top + plotHeight;
      if (bucket.delivered + bucket.failed === 0) {
        svg.append(svgNode("rect", {
          class: "chart-zero-bar",
          x,
          y: baseline - 3,
          width: barWidth,
          height: 3,
          rx: 2,
        }));
      } else {
        if (bucket.delivered > 0) {
          svg.append(svgNode("rect", {
            class: "chart-bar-delivered",
            x,
            y: baseline - deliveredHeight,
            width: barWidth,
            height: Math.max(2, deliveredHeight),
            rx: 4,
          }));
        }
        if (bucket.failed > 0) {
          svg.append(svgNode("rect", {
            class: "chart-bar-failed",
            x,
            y: baseline - deliveredHeight - failedHeight,
            width: barWidth,
            height: Math.max(2, failedHeight),
            rx: 4,
          }));
        }
      }
      if (index % Math.max(1, Math.ceil(buckets.length / 6)) === 0 || index === buckets.length - 1) {
        const label = svgNode("text", {
          class: "chart-bucket-label",
          x: x + barWidth / 2,
          y: height - 14,
          "text-anchor": "middle",
        });
        label.textContent = bucketLabel(bucket.start, state.historyRange);
        svg.append(label);
      }
    });
    container.append(svg);

    const delivered = attempts.filter((item) => ["delivered", "success"].includes(item.outcome)).length;
    const failed = Math.max(0, attempts.length - delivered);
    const keyDelivered = node("span", "dashboard-chart-key delivered", `${delivered} delivered`);
    const keyFailed = node("span", "dashboard-chart-key failed", `${failed} failed`);
    const note = node(
      "span",
      "",
      attempts.length
        ? `${attempts.length} final delivery outcome${attempts.length === 1 ? "" : "s"} available in recent history.`
        : `No delivery outcomes are available for ${spec.label}.`,
    );
    summary.append(keyDelivered, keyFailed, note);
  }

  function renderRanking(containerId, entries, emptyTitle, emptyCopy) {
    const container = byId(containerId);
    if (!container) return;
    container.replaceChildren();
    if (!entries.length) {
      const emptyState = node("div", "dashboard-ranking-empty");
      const icon = node("img");
      icon.src = "/ui/brand/nowlert-owl-v3.1.0.png";
      icon.alt = "";
      icon.setAttribute("aria-hidden", "true");
      emptyState.append(
        icon,
        node("strong", "", emptyTitle),
        node("span", "", emptyCopy),
      );
      container.append(emptyState);
      return;
    }
    const maximum = Math.max(...entries.map((item) => item.count), 1);
    for (const entry of entries.slice(0, 4)) {
      const row = node("div", "dashboard-ranking-row");
      const heading = node("div", "dashboard-ranking-heading");
      const name = node("strong", "", entry.name);
      name.title = entry.name;
      heading.append(name, node("span", "", entry.count));
      const track = node("div", "dashboard-ranking-track");
      const percentage = Math.max(5, Math.round((entry.count / maximum) * 100));
      const bucket = Math.max(5, Math.min(100, Math.round(percentage / 5) * 5));
      const fill = node("span", `dashboard-ranking-fill width-${bucket}`);
      track.append(fill);
      row.append(heading, track);
      container.append(row);
    }
  }

  function renderRankings() {
    const attempts = attemptsForRange();
    const sources = new Map();
    const destinations = new Map();
    const destinationNames = new Map(
      (state.destinations || []).map((item) => [item.id, item.name || friendlyName(item.output_type)]),
    );
    for (const item of attempts) {
      const source = friendlyName(item.source);
      sources.set(source, (sources.get(source) || 0) + 1);
      const destination = destinationNames.get(item.destination_id) || "Unresolved destination";
      destinations.set(destination, (destinations.get(destination) || 0) + 1);
    }
    const sorted = (map) => [...map.entries()]
      .map(([name, count]) => ({ name, count }))
      .sort((left, right) => right.count - left.count || left.name.localeCompare(right.name));
    renderRanking(
      "dashboard-top-sources",
      sorted(sources),
      "No top sources",
      "Source activity will appear after events are delivered.",
    );
    renderRanking(
      "dashboard-top-destinations",
      sorted(destinations),
      "No top destinations",
      "Destination activity will appear after events are delivered.",
    );
  }

  function renderHealth() {
    const container = byId("dashboard-system-health");
    if (!container) return;
    container.replaceChildren();
    const checks = state.healthChecks || [];
    const errors = checks.filter((item) => item.status === "error");
    const warnings = checks.filter((item) => item.status === "warning");
    const status = errors.length ? "error" : warnings.length ? "warning" : checks.length ? "healthy" : "warning";
    const title = errors.length
      ? "Attention required"
      : warnings.length
        ? "Review recommended"
        : checks.length
          ? "All systems operational"
          : "Health status unavailable";
    const detail = errors.length
      ? `${errors.length} health check${errors.length === 1 ? "" : "s"} failed.`
      : warnings.length
        ? `${warnings.length} health warning${warnings.length === 1 ? "" : "s"} detected.`
        : checks.length
          ? `${checks.length} operational checks are healthy.`
          : "Run the health checks from the Audit Log.";
    const summary = node("div", "dashboard-health-summary");
    const icon = node("span", `dashboard-health-icon ${status === "healthy" ? "" : status}`.trim(), status === "healthy" ? "✓" : status === "warning" ? "!" : "×");
    const copy = node("div");
    copy.append(node("strong", "", title), node("small", "", detail));
    summary.append(icon, copy);
    container.append(summary);

    const list = node("div", "dashboard-health-checks");
    for (const check of checks.slice(0, 5)) {
      const row = node("div", "dashboard-health-check");
      const name = node("span", "", check.name || friendlyName(check.key));
      name.title = check.detail || "";
      row.append(name, node("span", `dashboard-health-status ${check.status}`, check.status));
      list.append(row);
    }
    container.append(list);
  }

  function renderProfessionalDashboard() {
    renderChart();
    renderRankings();
    renderHealth();
  }

  const baseRenderDashboard = renderDashboard;
  renderDashboard = function renderDashboardWithAnalytics() {
    baseRenderDashboard();
    renderProfessionalDashboard();
  };
})();

/* Independent Routes + Destination-owned assignment UI. */
let routeAssignmentSelection = new Set();

function routeAssignmentSummary(count) {
  if (!count) return "No routes selected";
  return count === 1 ? "1 route selected" : `${count} routes selected`;
}

function routeAssignmentInstallStyles() {
  if (byId("route-assignment-style")) return;
  const style = document.createElement("style");
  style.id = "route-assignment-style";
  style.textContent = `
    .route-assignment-picker { position: relative; }
    .route-assignment-toggle { width: 100%; justify-content: space-between; min-height: 44px; }
    .route-assignment-popover { margin-top: .55rem; padding: .7rem; border: 1px solid var(--border, #3d3b30); border-radius: 10px; background: var(--surface-2, #161b20); }
    .route-assignment-popover[hidden] { display: none !important; }
    .route-assignment-toolbar { display: flex; gap: .55rem; align-items: center; margin-bottom: .6rem; }
    .route-assignment-toolbar input { flex: 1; }
    .route-assignment-actions { display: flex; gap: .45rem; }
    .route-assignment-options { display: grid; gap: .35rem; max-height: 19rem; overflow: auto; padding-right: .2rem; }
    .route-assignment-option { display: grid; grid-template-columns: auto 1fr auto; gap: .6rem; align-items: center; padding: .55rem .65rem; border: 1px solid var(--border, #3d3b30); border-radius: 8px; background: rgba(255,255,255,.018); cursor: pointer; }
    .route-assignment-option:hover { border-color: rgba(244,183,39,.55); }
    .route-assignment-option input { margin: 0; }
    .route-assignment-option-copy { display: flex; flex-direction: column; gap: .12rem; min-width: 0; }
    .route-assignment-option-copy strong, .route-assignment-option-copy small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .route-assignment-empty { padding: .7rem; color: var(--muted, #aaa); }
    .route-assignment-fieldset { margin-top: .15rem; }
  `;
  document.head.append(style);
}

function routeAssignmentEnsureDestinationPicker() {
  if (byId("destination-routes")) return;
  const form = byId("destination-form");
  if (!form) return;
  const fieldsets = form.querySelectorAll("fieldset");
  const credentials = [...fieldsets].find((item) => item.querySelector("legend")?.textContent.trim() === "Write-only credentials");
  if (!credentials) return;

  const fieldset = element("fieldset", { className: "route-assignment-fieldset" });
  fieldset.id = "destination-routes-fieldset";
  const legend = element("legend", { text: "Routes" });
  const help = element("p", {
    className: "field-help",
    text: "Select which reusable routes may deliver notifications to this destination.",
  });
  const picker = element("div", { className: "route-assignment-picker" });
  picker.id = "destination-routes";
  const toggle = element("button", {
    className: "button secondary route-assignment-toggle",
    text: "No routes selected",
    type: "button",
    attributes: { id: "destination-routes-toggle", "aria-expanded": "false" },
  });
  const popover = element("div", {
    className: "route-assignment-popover",
    hidden: true,
    attributes: { id: "destination-routes-popover" },
  });
  const toolbar = element("div", { className: "route-assignment-toolbar" });
  const search = element("input", {
    type: "search",
    attributes: { id: "destination-route-search", placeholder: "Search routes", "aria-label": "Search routes" },
  });
  const actions = element("div", { className: "route-assignment-actions" });
  const selectAll = element("button", {
    className: "text-button",
    text: "Select all",
    type: "button",
    dataset: { action: "destination-routes-select-all" },
  });
  const clear = element("button", {
    className: "text-button",
    text: "Clear",
    type: "button",
    dataset: { action: "destination-routes-clear" },
  });
  const options = element("div", { className: "route-assignment-options" });
  options.id = "destination-route-options";

  toggle.addEventListener("click", () => {
    popover.hidden = !popover.hidden;
    toggle.setAttribute("aria-expanded", popover.hidden ? "false" : "true");
    if (!popover.hidden) search.focus();
  });
  search.addEventListener("input", routeAssignmentRenderOptions);
  selectAll.addEventListener("click", () => {
    routeAssignmentSelection = new Set((state.routes || []).map((item) => item.id));
    routeAssignmentRenderOptions();
  });
  clear.addEventListener("click", () => {
    routeAssignmentSelection.clear();
    routeAssignmentRenderOptions();
  });

  actions.append(selectAll, clear);
  toolbar.append(search, actions);
  popover.append(toolbar, options);
  picker.append(toggle, popover);
  fieldset.append(legend, help, picker);
  credentials.before(fieldset);
}

function routeAssignmentRenderOptions() {
  routeAssignmentEnsureDestinationPicker();
  const options = byId("destination-route-options");
  const toggle = byId("destination-routes-toggle");
  if (!options || !toggle) return;
  const query = String(byId("destination-route-search")?.value || "").trim().toLowerCase();
  const routes = (state.routes || []).filter((item) => {
    if (!query) return true;
    const descriptor = routeSourceDescriptor(item.source, item.input_type);
    return `${item.name} ${descriptor.integration} ${descriptor.input} ${item.priority_name || ""}`.toLowerCase().includes(query);
  });
  options.replaceChildren();
  if (!routes.length) {
    options.append(element("div", { className: "route-assignment-empty", text: state.routes.length ? "No matching routes." : "No routes are available yet." }));
  }
  for (const route of routes) {
    const descriptor = routeSourceDescriptor(route.source, route.input_type);
    const checkbox = element("input", { type: "checkbox", value: route.id });
    checkbox.checked = routeAssignmentSelection.has(route.id);
    const status = badge(route.enabled ? "Enabled" : "Disabled", route.enabled ? "success" : "warning");
    const row = element("label", { className: "route-assignment-option" }, [
      checkbox,
      element("span", { className: "route-assignment-option-copy" }, [
        element("strong", { text: route.name }),
        element("small", { text: `${descriptor.integration} · ${descriptor.input} · ${capitalize(route.priority_name || "normal")}` }),
      ]),
      status,
    ]);
    checkbox.addEventListener("change", () => {
      if (checkbox.checked) routeAssignmentSelection.add(route.id);
      else routeAssignmentSelection.delete(route.id);
      toggle.textContent = routeAssignmentSummary(routeAssignmentSelection.size);
    });
    options.append(row);
  }
  toggle.textContent = routeAssignmentSummary(routeAssignmentSelection.size);
}

function routeAssignmentPrepareDestination(item) {
  routeAssignmentEnsureDestinationPicker();
  routeAssignmentSelection = new Set(item && Array.isArray(item.route_ids) ? item.route_ids : []);
  const search = byId("destination-route-search");
  if (search) search.value = "";
  const popover = byId("destination-routes-popover");
  if (popover) popover.hidden = true;
  const toggle = byId("destination-routes-toggle");
  if (toggle) toggle.setAttribute("aria-expanded", "false");
  routeAssignmentRenderOptions();
}

const routeAssignmentOriginalOpenDestination = openDestination;
openDestination = function openDestinationWithRoutes(id = "") {
  const item = state.destinations.find((candidate) => candidate.id === id);
  routeAssignmentOriginalOpenDestination(id);
  routeAssignmentPrepareDestination(item || null);
};

saveDestination = async function saveDestinationWithRoutes(event) {
  event.preventDefault();
  if (event.submitter && event.submitter.value === "cancel") {
    byId("destination-dialog").close();
    return;
  }
  clearError("destination-error");
  const id = byId("destination-id").value;
  const submit = byId("destination-submit");
  const name = byId("destination-name").value.trim();
  const duplicate = state.destinations.find((item) => item.id !== id && item.name.trim().toLowerCase() === name.toLowerCase());
  if (duplicate) {
    showError("destination-error", new APIError(409, `A destination named "${name}" already exists. Choose another name.`, id ? `/destinations/${id}` : "/destinations", "resource_conflict"));
    return;
  }
  submit.disabled = true;
  try {
    const settings = collectFields(byId("destination-settings"));
    const secret = collectFields(byId("destination-secrets"));
    const payload = {
      name,
      output_type: byId("destination-type").value,
      settings,
      enabled: byId("destination-enabled").checked,
      route_ids: [...routeAssignmentSelection],
    };
    if (isAdmin()) payload.shared = byId("destination-shared").checked;
    if (Object.keys(secret).length) payload.secret = secret;
    await request(id ? `/destinations/${id}` : "/destinations", {
      method: id ? "PATCH" : "POST",
      body: payload,
    });
    byId("destination-dialog").close();
    await loadWorkspace();
    toast(id ? "Destination updated." : "Destination added.");
  } catch (error) {
    showError("destination-error", error);
  } finally {
    submit.disabled = false;
  }
};

function routeAssignmentInstallRouteDefinitionUi() {
  const destinationSelect = byId("route-destination");
  if (destinationSelect) {
    destinationSelect.required = false;
    destinationSelect.disabled = true;
    const label = destinationSelect.closest("label");
    if (label) label.hidden = true;
  }
  const routeForm = byId("route-form");
  if (routeForm) {
    for (const fieldset of routeForm.querySelectorAll("fieldset")) {
      if (fieldset.querySelector("legend")?.textContent.trim() === "Optional route filters") {
        fieldset.hidden = true;
        for (const input of fieldset.querySelectorAll("input, select, textarea")) input.disabled = true;
      }
    }
  }
  const copy = byId("view-routes")?.querySelector(".section-toolbar p");
  if (copy) copy.textContent = "Define which integration and input traffic qualifies for delivery.";
  const heading = byId("view-routes")?.querySelector("thead tr");
  if (heading) {
    heading.replaceChildren(
      element("th", { text: "Name" }),
      element("th", { text: "Integration" }),
      element("th", { text: "Input" }),
      element("th", { text: "Used by" }),
      element("th", { text: "Priority" }),
      element("th", { text: "Status" }),
      element("th", {}, element("span", { className: "sr-only", text: "Delete" })),
    );
  }
}

renderRoutes = function renderIndependentRoutes() {
  routeAssignmentInstallRouteDefinitionUi();
  const body = byId("route-table");
  body.replaceChildren();
  byId("route-empty").hidden = state.routes.length > 0;
  if (!state.routes.length) {
    byId("route-empty").replaceChildren(
      element("strong", { text: "No routes" }),
      element("span", { text: "Create a reusable route to define which integration traffic qualifies for delivery." }),
    );
  } else {
    for (const item of state.routes) {
      const descriptor = routeSourceDescriptor(item.source, item.input_type);
      const name = isAdmin()
        ? element("button", { className: "route-name-button", text: item.name, type: "button", dataset: { action: "edit-route", id: item.id } })
        : element("strong", { text: item.name });
      const status = element("button", {
        className: `badge status-button ${item.enabled ? "success" : "warning"}`,
        text: item.enabled ? "Enabled" : "Disabled",
        type: "button",
        disabled: !isAdmin(),
        dataset: { action: "toggle-route", id: item.id },
      });
      const count = Number(item.destination_count || 0);
      const usedBy = count === 0 ? "Unassigned" : count === 1 ? "1 destination" : `${count} destinations`;
      body.append(element("tr", {}, [
        element("td", {}, name),
        element("td", { text: descriptor.integration }),
        element("td", { text: descriptor.input }),
        element("td", { text: usedBy }),
        element("td", { text: capitalize(item.priority_name || "normal") }),
        element("td", {}, status),
        element("td", {}, isAdmin() ? actionButton("Delete", "delete-route", item.id, "danger") : null),
      ]));
    }
  }

  if (typeof qaMountPager === "function" && typeof QA_PAGE_SIZE !== "undefined") {
    const rows = [...body.children];
    const total = rows.length;
    const totalPages = Math.max(1, Math.ceil(total / QA_PAGE_SIZE));
    qaRoutePage = Math.min(Math.max(1, qaRoutePage), totalPages);
    const start = (qaRoutePage - 1) * QA_PAGE_SIZE;
    rows.forEach((row, index) => { row.hidden = index < start || index >= start + QA_PAGE_SIZE; });
    qaMountPager("view-routes", "route-pagination", {
      page: qaRoutePage,
      page_size: QA_PAGE_SIZE,
      total,
      total_pages: totalPages,
    }, (page) => {
      qaRoutePage = page;
      renderRoutes();
    });
  }
};

openRoute = function openIndependentRoute(id = "") {
  const item = state.routes.find((candidate) => candidate.id === id);
  byId("route-form").reset();
  clearError("route-error");
  byId("route-id").value = item ? item.id : "";
  byId("route-name").value = item ? item.name : "";
  setRouteSourceOptions(item ? item.source : "zabbix", item ? item.input_type : "smtp");
  byId("route-priority").value = item ? (item.priority_name || "normal") : "normal";
  byId("route-enabled").checked = item ? item.enabled : true;
  routeAssignmentInstallRouteDefinitionUi();
  byId("route-dialog-title").textContent = item ? `Edit ${item.name}` : "Add route";
  byId("route-dialog").showModal();
};

saveRoute = async function saveIndependentRoute(event) {
  event.preventDefault();
  if (event.submitter && event.submitter.value === "cancel") {
    byId("route-dialog").close();
    return;
  }
  clearError("route-error");
  const id = byId("route-id").value;
  const [source, inputType] = byId("route-source").value.split("::", 2);
  try {
    await request(id ? `/routes/${id}` : "/routes", {
      method: id ? "PATCH" : "POST",
      body: {
        name: byId("route-name").value.trim(),
        source,
        input_type: inputType,
        priority: byId("route-priority").value,
        enabled: byId("route-enabled").checked,
      },
    });
    byId("route-dialog").close();
    await loadWorkspace();
    toast(id ? "Route updated." : "Route added.");
  } catch (error) {
    showError("route-error", error);
  }
};

renderFlow = function renderAssignmentFlow() {
  const container = byId("dashboard-flow");
  container.replaceChildren();
  for (const route of state.routes) {
    for (const destinationId of (route.destination_ids || [])) {
      const destination = state.destinations.find((item) => item.id === destinationId);
      const inputStatus = inputFlowState(route.input_type || "http");
      const routeStatus = routeFlowState(route);
      const destinationStatus = destinationFlowState(destination);
      const destinationLabels = destinationFlowLabels(destination);
      const firstStatus = combinedFlowState(inputStatus, routeStatus);
      const descriptor = routeSourceDescriptor(route.source, route.input_type);
      const integration = integrationBySource(route.source);
      const iconKey = route.source === "*" ? "generic" : integration ? integration.icon_key : route.source;
      const category = route.source === "*" ? SOURCE_CATEGORIES.generic : sourceCategory(route.source);
      container.append(element("div", { className: `flow-row source-${inputStatus.state}` }, [
        element("div", {
          className: `flow-node source-node category-${category.key} state-${inputStatus.state}`,
          title: inputStatus.detail,
        }, [sourceIcon(iconKey), element("div", {}, [element("strong", { text: descriptor.integration }), element("small", { text: descriptor.input })])]),
        element("div", {
          className: `flow-route state-${routeStatus.state}`,
          title: routeStatus.detail,
        }, [
          flowSignal(firstStatus, `${inputStatus.detail}; ${routeStatus.detail}`),
          element("div", {}, [element("strong", { text: route.name }), element("small", { text: `${route.destination_count || 0} destination${Number(route.destination_count || 0) === 1 ? "" : "s"}` })]),
          flowSignal(destinationStatus.state, destinationStatus.detail, true),
        ]),
        element("div", {
          className: `flow-node destination-node state-${destinationStatus.state}`,
          title: destinationStatus.detail,
        }, [outputIcon(destination && destination.output_type), element("div", {}, [element("strong", { text: destinationLabels.name }), element("small", { text: destinationLabels.detail })])]),
      ]));
    }
  }
  if (!container.children.length) empty(container, "No routing flow", "Assign one or more routes to a destination to display the delivery flow here.");
};

openPreview = function openAssignmentAwarePreview(id) {
  const item = state.destinations.find((candidate) => candidate.id === id);
  if (!item) return;
  byId("preview-form").reset();
  byId("preview-destination-id").value = id;
  byId("preview-title").textContent = `Preview ${item.name}`;
  const route = state.routes.find((candidate) => (candidate.destination_ids || []).includes(id) && candidate.source !== "*");
  byId("preview-source").value = route ? route.source : "home_assistant";
  byId("preview-result").hidden = true;
  byId("test-button").hidden = !isAdmin();
  clearError("preview-error");
  byId("preview-dialog").showModal();
};

cardSampleEvent = function assignmentAwareCardSampleEvent(destination) {
  const route = state.routes.find((candidate) => (candidate.destination_ids || []).includes(destination.id) && candidate.source && candidate.source !== "*");
  const source = route ? route.source : "nowlert";
  return {
    schema: "nowlert.event.v1",
    source,
    title: `${destination.name} test delivery`,
    message: `This is a safe Nowlert test for the ${OUTPUT_NAMES[destination.output_type] || friendlyName(destination.output_type)} destination "${destination.name}".`,
    severity: "information",
    status: "active",
    provider: friendlyName(source),
    metadata: { host: destination.name, component: "Destination test" },
  };
};

document.addEventListener("DOMContentLoaded", () => {
  routeAssignmentInstallStyles();
  routeAssignmentEnsureDestinationPicker();
  routeAssignmentInstallRouteDefinitionUi();
});
