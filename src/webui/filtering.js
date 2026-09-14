"use strict";

(() => {
  const filteringState = {
    overview: null,
    destinationView: null,
    integration: null,
    activeTextFields: new Set(),
    operators: new Map(),
  };

  const LEGACY_FILTER_LABELS = {
    hosts: "Host / device",
    events: "Event",
    severities: "Severity",
    statuses: "Status",
    exclude_hosts: "Exclude host / device",
    exclude_events: "Exclude event",
    exclude_severities: "Exclude severity",
    exclude_statuses: "Exclude status",
  };

  function canEditFilters() {
    return Boolean(state.user && state.user.role === "admin");
  }

  function installNavigation() {
    VIEW_TITLES.filtering = "Filtering";
    const routesNav = document.querySelector('#primary-nav [data-view="routes"]');
    if (!routesNav || document.querySelector('#primary-nav [data-view="filtering"]')) return;
    const button = element("button", {
      className: "nav-item",
      type: "button",
      dataset: { view: "filtering" },
    }, [
      element("span", { className: "nav-icon", text: "⊙", attributes: { "aria-hidden": "true" } }),
      element("span", { text: "Filtering" }),
    ]);
    routesNav.after(button);
  }

  function installView() {
    if (byId("view-filtering")) return;
    const routesView = byId("view-routes");
    if (!routesView) return;
    const section = element("section", {
      className: "view",
      hidden: true,
      attributes: { id: "view-filtering", "data-page": "filtering" },
    });
    section.innerHTML = `
      <div class="section-toolbar filtering-toolbar">
        <div>
          <h2>Filtering</h2>
          <p>Control which notifications can reach each destination.</p>
        </div>
        <button id="add-filter-button" class="button primary" type="button" data-filter-action="new-filter">＋ New filter</button>
      </div>
      <div class="table-panel filtering-table-panel">
        <div class="table-scroll">
          <table class="filtering-table">
            <thead><tr><th>Destination</th><th>Filters</th><th>Status</th><th>Actions</th></tr></thead>
            <tbody id="filter-table"></tbody>
          </table>
        </div>
        <div id="filter-empty" class="empty-state" hidden></div>
      </div>
    `;
    routesView.after(section);
  }

  function installDialog() {
    if (byId("filtering-dialog")) return;
    const dialog = element("dialog", {
      className: "modal filtering-modal",
      attributes: { id: "filtering-dialog" },
    });
    dialog.innerHTML = `
      <div class="modal-heading filtering-modal-heading">
        <div><p class="eyebrow">Destination filtering</p><h2 id="filtering-dialog-title">New filter</h2></div>
        <button class="icon-button" type="button" data-filter-action="close" aria-label="Close">×</button>
      </div>

      <section id="filter-destination-step">
        <p class="field-help">Choose the destination to filter. Nowlert will detect the integrations currently enabled for it.</p>
        <label class="filtering-destination-field">
          <span>Destination</span>
          <select id="filter-destination-select"></select>
        </label>
        <p id="filter-destination-help" class="field-help"></p>
        <div class="modal-actions">
          <button class="button secondary" type="button" data-filter-action="close">Cancel</button>
          <button id="filter-destination-continue" class="button primary" type="button" data-filter-action="continue-destination">Continue</button>
        </div>
      </section>

      <section id="filter-integration-step" hidden>
        <div id="filtering-context" class="filtering-context"></div>
        <p class="filtering-available-note">Only integrations currently enabled for this destination are shown.</p>
        <div id="filter-integration-list" class="filtering-integration-list"></div>
        <div class="modal-actions">
          <button class="button secondary" type="button" data-filter-action="close">Cancel</button>
          <button class="button primary" type="button" data-filter-action="finish">Close</button>
        </div>
      </section>

      <section id="filter-editor-step" hidden>
        <div id="filter-editor-identity" class="filtering-editor-identity"></div>
        <p id="filter-legacy-warning" class="filtering-warning" hidden></p>
        <div id="filter-enum-fields" class="filtering-enum-fields"></div>
        <div id="filter-text-fields" class="filtering-text-fields"></div>
        <div id="filter-add-field-row" class="filtering-add-field-row" hidden>
          <select id="filter-add-field-select" aria-label="Additional filter field"></select>
          <button class="button secondary small" type="button" data-filter-action="add-field">Add field</button>
        </div>
        <div class="modal-actions filtering-editor-actions">
          <button id="filter-remove-button" class="button danger" type="button" data-filter-action="remove-integration-filter">Remove filter</button>
          <span class="filtering-action-spacer"></span>
          <button class="button secondary" type="button" data-filter-action="back-integrations">Cancel</button>
          <button class="button primary" type="button" data-filter-action="save-integration">Save filter</button>
        </div>
      </section>
    `;
    document.body.append(dialog);
  }

  function decoupleRouteUI() {
    const routeField = byId("route-severities");
    const fieldset = routeField && routeField.closest("fieldset");
    if (fieldset) fieldset.hidden = true;
    const routesView = byId("view-routes");
    const description = routesView && routesView.querySelector(".section-toolbar p");
    if (description) description.textContent = "Connect integrations and inputs to destinations with routing priorities.";
    const table = byId("route-table") && byId("route-table").closest("table");
    const header = table && table.tHead && table.tHead.rows[0];
    if (header && !header.dataset.filteringDecoupled && header.cells.length >= 8) {
      header.cells[4].remove();
      header.dataset.filteringDecoupled = "true";
    }
    const stripRows = () => {
      const body = byId("route-table");
      if (!body) return;
      for (const row of body.rows) if (row.cells.length >= 8) row.cells[4].remove();
    };
    stripRows();
    const routeBody = byId("route-table");
    if (routeBody) new MutationObserver(stripRows).observe(routeBody, { childList: true });
    const updateFlowCopy = () => {
      const flow = byId("dashboard-flow");
      if (!flow) return;
      for (const detail of flow.querySelectorAll(".flow-route small")) {
        if (detail.textContent !== "Routing only") detail.textContent = "Routing only";
      }
    };
    updateFlowCopy();
    const flow = byId("dashboard-flow");
    if (flow) new MutationObserver(updateFlowCopy).observe(flow, { childList: true, subtree: true });
  }

  function resetDialogSteps() {
    byId("filter-destination-step").hidden = true;
    byId("filter-integration-step").hidden = true;
    byId("filter-editor-step").hidden = true;
  }

  async function loadOverview() {
    filteringState.overview = await request("/filters");
    renderOverview();
    return filteringState.overview;
  }

  function filterFieldDescriptor(integration, key) {
    const nativeKey = key.startsWith("exclude_") ? key.slice("exclude_".length) : key;
    const aliases = { severities: "severity", statuses: "status" };
    const lookup = aliases[nativeKey] || nativeKey;
    return (integration.fields || []).find((field) => field.key === lookup) || null;
  }

  function filterFieldLabel(integration, key) {
    if (LEGACY_FILTER_LABELS[key]) return LEGACY_FILTER_LABELS[key];
    const descriptor = filterFieldDescriptor(integration, key);
    return descriptor ? descriptor.label : friendlyName(key);
  }

  function filterSummaryClauses(integration) {
    const rules = integration.rules && typeof integration.rules === "object" ? integration.rules : {};
    if (Object.keys(rules).length) return [rules];
    return Array.isArray(integration.legacy_clauses) ? integration.legacy_clauses : [];
  }

  function compactRuleChips(integration) {
    const chips = element("div", { className: "filtering-overview-chips" });
    const seenValues = new Set();
    for (const clause of filterSummaryClauses(integration)) {
      for (const [key, values] of Object.entries(clause || {})) {
        if (!Array.isArray(values) || !values.length) continue;
        for (const value of values) {
          const text = String(value).trim();
          if (!text) continue;
          const token = text.toLowerCase();
          if (seenValues.has(token)) continue;
          seenValues.add(token);
          chips.append(element("span", {
            className: "filtering-overview-chip filtering-overview-rule-value",
            text: friendlyName(text),
            title: values.join(", "),
            attributes: { "aria-label": `${filterFieldLabel(integration, key)} ${friendlyName(text)}` },
          }));
        }
      }
    }
    return chips;
  }

  function filterOverviewIntegration(integration) {
    const icon = sourceIcon(integration.source);
    icon.classList.add("filtering-source-icon");
    return element("article", { className: "filtering-overview-integration" }, [
      icon,
      element("div", { className: "filtering-overview-copy" }, [
        element("strong", { text: integration.name || friendlyName(integration.source) }),
        compactRuleChips(integration),
      ]),
      element("span", { className: "filtering-card-check", text: "✓", attributes: { "aria-label": "Filter enabled" } }),
    ]);
  }

  function policyFilterSummary(policy) {
    const integrations = Array.isArray(policy.integrations) ? policy.integrations : [];
    const active = integrations.length;
    const container = element("details", { className: "filtering-overview-list filtering-overview-details" });
    container.open = true;
    container.append(element("summary", { className: "filtering-overview-header" }, [
      element("span", { className: "filtering-overview-header-check", text: "✓" }),
      element("strong", { text: `${active} active filter${active === 1 ? "" : "s"}` }),
    ]));
    const grid = element("div", { className: "filtering-overview-grid" });
    integrations.forEach((integration) => grid.append(filterOverviewIntegration(integration)));
    container.append(grid);
    return container;
  }

  function destinationSummary(policy) {
    const icon = outputIcon(policy.output_type);
    icon.classList.add("filtering-destination-icon");
    return element("div", { className: "filtering-destination-summary" }, [
      icon,
      element("div", {}, [
        element("strong", { text: policy.destination_name || "Destination" }),
        element("small", { text: friendlyName(policy.output_type) }),
      ]),
    ]);
  }

  function policyStatusBadge() {
    return badge("Active", "success");
  }

  function renderOverview() {
    const payload = filteringState.overview || { filters: [], destinations: [] };
    const body = byId("filter-table");
    const emptyState = byId("filter-empty");
    if (!body || !emptyState) return;
    body.replaceChildren();
    const policies = (Array.isArray(payload.filters) ? payload.filters : [])
      .filter((policy) => Array.isArray(policy.integrations) && policy.integrations.length > 0);
    emptyState.hidden = policies.length > 0;
    if (!policies.length) {
      emptyState.replaceChildren(
        element("strong", { text: "No active filters" }),
        element("span", { text: canEditFilters() ? "Use New filter to configure one destination." : "No destination filters are currently enabled." }),
      );
    }
    for (const policy of policies) {
      const actions = element("div", { className: "table-actions filtering-table-actions" });
      if (canEditFilters()) {
        actions.append(
          actionButtonForFilter("✎ Configure", "manage-destination", policy.destination_id, "primary"),
          actionButtonForFilter("Delete", "delete-destination-filter", policy.destination_id, "danger"),
        );
      }
      body.append(element("tr", {}, [
        element("td", {}, [destinationSummary(policy)]),
        element("td", {}, [policyFilterSummary(policy)]),
        element("td", {}, [policyStatusBadge(policy)]),
        element("td", {}, [actions]),
      ]));
    }
    const addButton = byId("add-filter-button");
    if (addButton) addButton.hidden = !canEditFilters();
  }

  function actionButtonForFilter(label, action, id = "", style = "secondary") {
    return element("button", {
      className: `button small ${style}`,
      text: label,
      type: "button",
      dataset: { filterAction: action, filterId: id },
    });
  }

  function makeSwitch(checked, source, disabled = false, context = "list") {
    const input = document.createElement("input");
    input.type = "checkbox";
    input.checked = Boolean(checked);
    input.disabled = Boolean(disabled);
    input.dataset.filterToggle = source;
    input.dataset.filterToggleContext = context;
    input.setAttribute("aria-label", `Enable filtering for ${source}`);
    return element("label", { className: "filtering-switch" }, [input, element("span", { className: "filtering-switch-track" })]);
  }

  function fillDestinationSelect(selectedId = "") {
    const select = byId("filter-destination-select");
    select.replaceChildren();
    const destinations = filteringState.overview && Array.isArray(filteringState.overview.destinations)
      ? filteringState.overview.destinations : [];
    const available = destinations.filter((item) => Number(item.available_integration_count || 0) > 0);
    if (!available.length) {
      select.append(element("option", { text: "No destination has an enabled integration", value: "" }));
      select.disabled = true;
      byId("filter-destination-continue").disabled = true;
      byId("filter-destination-help").textContent = "Enable at least one route to a destination before creating a filter.";
      return;
    }
    select.disabled = false;
    byId("filter-destination-continue").disabled = false;
    for (const item of available) {
      const count = Number(item.available_integration_count || 0);
      const option = element("option", { value: item.id, text: `${item.name} · ${count} integration${count === 1 ? "" : "s"}` });
      if (item.id === selectedId) option.selected = true;
      select.append(option);
    }
    byId("filter-destination-help").textContent = "Only destinations with at least one enabled integration are listed.";
  }

  async function openNewFilter() {
    if (!canEditFilters()) return;
    if (!filteringState.overview) await loadOverview();
    filteringState.destinationView = null;
    filteringState.integration = null;
    byId("filtering-dialog-title").textContent = "New filter";
    fillDestinationSelect();
    resetDialogSteps();
    byId("filter-destination-step").hidden = false;
    byId("filtering-dialog").showModal();
  }

  async function openDestinationFilter(destinationId) {
    if (!filteringState.overview) await loadOverview();
    filteringState.destinationView = await request(`/filters/destinations/${destinationId}`);
    filteringState.integration = null;
    byId("filtering-dialog-title").textContent = "Configure filter";
    renderIntegrationStep();
    if (!byId("filtering-dialog").open) byId("filtering-dialog").showModal();
  }

  async function continueDestination() {
    const destinationId = byId("filter-destination-select").value;
    if (!destinationId) return;
    filteringState.destinationView = await request(`/filters/destinations/${destinationId}`);
    renderIntegrationStep();
  }

  function renderIntegrationStep() {
    const view = filteringState.destinationView;
    if (!view) return;
    resetDialogSteps();
    byId("filter-integration-step").hidden = false;
    byId("filtering-dialog-title").textContent = "Configure filter";
    const context = byId("filtering-context");
    context.replaceChildren();
    const destinationIcon = outputIcon(view.destination.output_type);
    destinationIcon.classList.add("filtering-context-icon");
    context.append(
      element("span", { className: "filtering-context-label", text: "Destination" }),
      destinationIcon,
      element("strong", { text: view.destination.name }),
    );
    const list = byId("filter-integration-list");
    list.replaceChildren();
    const integrations = Array.isArray(view.integrations) ? view.integrations : [];
    if (!integrations.length) {
      list.append(element("div", { className: "empty-state" }, [
        element("strong", { text: "No enabled integrations" }),
        element("span", { text: "This destination currently has no enabled route/integration relationship." }),
      ]));
      return;
    }
    for (const integration of integrations) {
      const enabled = Boolean(integration.filter_enabled);
      const configured = Boolean(integration.configured);
      const status = enabled ? "Configured" : configured ? "Filter off" : "No filter / All notifications";
      const icon = sourceIcon(integration.source);
      icon.classList.add("filtering-source-icon");
      list.append(element("article", { className: "filtering-integration-row" }, [
        makeSwitch(enabled, integration.source, !canEditFilters(), "list"),
        element("div", { className: "filtering-integration-identity" }, [
          icon,
          element("div", {}, [
            element("strong", { text: integration.name || friendlyName(integration.source) }),
            element("small", { text: (integration.inputs || []).map((item) => item.name).join(" · ") || "Integration" }),
          ]),
        ]),
        element("div", { className: "filtering-integration-actions" }, [
          badge(status, enabled ? "success" : configured ? "warning" : ""),
          canEditFilters() ? actionButtonForFilter("Configure", "configure-integration", integration.source) : null,
        ]),
      ]));
    }
  }

  function normalizedSet(values) {
    return new Set((values || []).map((value) => String(value).trim().toLowerCase()));
  }

  function inferOperator(values) {
    const list = (values || []).map(String);
    if (list.length && list.every((value) => value.length >= 2 && value.startsWith("*") && value.endsWith("*") && !/[?\[]/.test(value.slice(1, -1)))) return "contains";
    if (list.some((value) => /[*?\[]/.test(value))) return "wildcard";
    return "equals";
  }

  function displayTextValues(values, operator) {
    if (operator !== "contains") return (values || []).join(", ");
    return (values || []).map((value) => {
      const text = String(value);
      return text.startsWith("*") && text.endsWith("*") ? text.slice(1, -1) : text;
    }).join(", ");
  }

  function openIntegrationEditor(source) {
    const view = filteringState.destinationView;
    if (!view) return;
    const integration = view.integrations.find((item) => item.source === source);
    if (!integration) return;
    filteringState.integration = integration;
    filteringState.activeTextFields = new Set(
      (integration.fields || []).filter((item) => item.kind === "text").map((item) => item.key),
    );
    filteringState.operators = new Map();
    for (const field of (integration.fields || []).filter((item) => item.kind === "text")) {
      filteringState.operators.set(field.key, inferOperator((integration.rules || {})[field.key] || []));
    }
    renderEditor();
  }

  function renderEditor() {
    const integration = filteringState.integration;
    if (!integration) return;
    resetDialogSteps();
    byId("filter-editor-step").hidden = false;
    byId("filtering-dialog-title").textContent = `Configure filter — ${integration.name || friendlyName(integration.source)}`;
    const identity = byId("filter-editor-identity");
    identity.replaceChildren();
    const icon = sourceIcon(integration.source);
    icon.classList.add("filtering-source-icon");
    const enabled = integration.configured ? Boolean(integration.filter_enabled) : true;
    identity.append(
      element("div", { className: "filtering-editor-source" }, [
        element("span", { className: "filtering-editor-source-label", text: "Integration" }),
        icon,
        element("div", {}, [
          element("strong", { text: integration.name || friendlyName(integration.source) }),
          element("small", { text: (integration.inputs || []).map((item) => item.name).join(" · ") || "Integration" }),
        ]),
      ]),
      element("div", { className: "filtering-editor-toggle" }, [
        element("span", { text: "Enable filtering" }),
        makeSwitch(enabled, integration.source, !canEditFilters(), "editor"),
      ]),
    );
    const legacy = Array.isArray(integration.legacy_clauses) ? integration.legacy_clauses : [];
    const warning = byId("filter-legacy-warning");
    warning.hidden = legacy.length === 0;
    warning.textContent = legacy.length
      ? "This integration contains migrated route-filter clauses. Saving here replaces those clauses with this destination filter configuration."
      : "";
    byId("filter-remove-button").hidden = !integration.configured;
    renderEnumFields();
    renderTextFields();
    renderAddFieldChoices();
  }

  function renderEnumFields() {
    const integration = filteringState.integration;
    const container = byId("filter-enum-fields");
    container.replaceChildren();
    const rules = integration.rules || {};
    for (const field of integration.fields.filter((item) => item.kind === "enum")) {
      const current = normalizedSet(rules[field.key]);
      const restricted = current.size > 0;
      const group = element("fieldset", { className: "filtering-enum-group" });
      group.append(element("legend", { text: field.label }));
      const choices = element("div", { className: "filtering-choice-grid" });
      for (const value of field.values || []) {
        const input = element("input", { type: "checkbox", value });
        input.dataset.filterEnum = field.key;
        input.checked = restricted ? current.has(String(value).toLowerCase()) : true;
        choices.append(element("label", { className: "filtering-choice" }, [input, element("span", { text: value })]));
      }
      group.append(choices);
      container.append(group);
    }
  }

  function operatorSelect(field) {
    const select = element("select", { className: "filtering-operator", dataset: { filterOperator: field.key } });
    const options = [
      ["equals", "equals"],
      ["wildcard", "matches wildcard"],
      ["contains", "contains"],
    ];
    const current = filteringState.operators.get(field.key) || "equals";
    for (const [value, label] of options) {
      const option = element("option", { value, text: label });
      if (value === current) option.selected = true;
      select.append(option);
    }
    return select;
  }

  function renderTextFields() {
    const integration = filteringState.integration;
    const container = byId("filter-text-fields");
    container.replaceChildren();
    const rules = integration.rules || {};
    for (const field of integration.fields.filter((item) => item.kind === "text" && filteringState.activeTextFields.has(item.key))) {
      const values = Array.isArray(rules[field.key]) ? rules[field.key] : [];
      const operator = filteringState.operators.get(field.key) || inferOperator(values);
      const input = element("input", {
        value: displayTextValues(values, operator),
        attributes: { "data-filter-text": field.key, placeholder: field.placeholder || `e.g. ${field.key}`, autocomplete: "off" },
      });
      const clear = actionButtonForFilter("×", "remove-field", field.key, "secondary");
      clear.classList.add("filtering-field-remove");
      container.append(element("div", { className: "filtering-text-field" }, [
        element("strong", { text: field.label }),
        operatorSelect(field),
        input,
        clear,
      ]));
    }
  }

  function renderAddFieldChoices() {
    const integration = filteringState.integration;
    const select = byId("filter-add-field-select");
    const row = byId("filter-add-field-row");
    select.replaceChildren();
    const fields = integration.fields.filter((item) => item.kind === "text" && !filteringState.activeTextFields.has(item.key));
    row.hidden = fields.length === 0;
    if (!fields.length) return;
    select.append(element("option", { text: "Add another field…", value: "" }));
    fields.forEach((field) => select.append(element("option", { text: field.label, value: field.key })));
  }

  function addTextField() {
    const key = byId("filter-add-field-select").value;
    if (!key) return;
    filteringState.activeTextFields.add(key);
    filteringState.operators.set(key, "equals");
    renderTextFields();
    renderAddFieldChoices();
  }

  function removeTextField(key) {
    filteringState.activeTextFields.delete(key);
    if (filteringState.integration && filteringState.integration.rules) delete filteringState.integration.rules[key];
    renderTextFields();
    renderAddFieldChoices();
  }

  function editorRules() {
    const integration = filteringState.integration;
    const rules = {};
    for (const field of integration.fields.filter((item) => item.kind === "enum")) {
      const inputs = [...document.querySelectorAll(`[data-filter-enum="${CSS.escape(field.key)}"]`)];
      const selected = inputs.filter((input) => input.checked).map((input) => input.value);
      if (selected.length > 0 && selected.length < inputs.length) rules[field.key] = selected;
    }
    for (const field of integration.fields.filter((item) => item.kind === "text")) {
      const input = document.querySelector(`[data-filter-text="${CSS.escape(field.key)}"]`);
      if (!input) continue;
      const operatorNode = document.querySelector(`[data-filter-operator="${CSS.escape(field.key)}"]`);
      const operator = operatorNode ? operatorNode.value : "equals";
      let values = String(input.value || "").split(",").map((value) => value.trim()).filter(Boolean);
      if (operator === "contains") values = values.map((value) => `*${value.replace(/^\*|\*$/g, "")}*`);
      if (values.length) rules[field.key] = values;
    }
    return rules;
  }

  async function saveIntegration() {
    const integration = filteringState.integration;
    const destination = filteringState.destinationView && filteringState.destinationView.destination;
    if (!integration || !destination) return;
    const rules = editorRules();
    const toggle = document.querySelector('[data-filter-toggle-context="editor"]');
    const enabled = Boolean(toggle && toggle.checked && Object.keys(rules).length);
    const response = await request(
      `/filters/destinations/${destination.id}/sources/${encodeURIComponent(integration.source)}`,
      { method: "PUT", body: { rules, enabled } },
    );
    const index = filteringState.destinationView.integrations.findIndex((item) => item.source === integration.source);
    if (index >= 0) filteringState.destinationView.integrations[index] = response.integration;
    filteringState.integration = null;
    renderIntegrationStep();
    await loadOverview();
    toast(response.integration.filter_enabled ? "Filter saved and enabled." : response.integration.configured ? "Filter saved but disabled." : "No filter configured; all notifications are allowed.", "success");
  }

  async function toggleIntegration(source, enabled) {
    const view = filteringState.destinationView;
    if (!view) return;
    const integration = view.integrations.find((item) => item.source === source);
    if (!integration) return;
    if (!integration.configured && enabled) {
      openIntegrationEditor(source);
      return;
    }
    const response = await request(
      `/filters/destinations/${view.destination.id}/sources/${encodeURIComponent(source)}`,
      { method: "PUT", body: { enabled } },
    );
    const index = view.integrations.findIndex((item) => item.source === source);
    if (index >= 0) view.integrations[index] = response.integration;
    renderIntegrationStep();
    await loadOverview();
    toast(enabled ? "Filter enabled." : "Filter disabled; saved rules were kept.", "success");
  }

  async function removeIntegrationFilter() {
    const integration = filteringState.integration;
    const view = filteringState.destinationView;
    if (!integration || !view) return;
    const accepted = await confirmAction(
      "Remove integration filter?",
      `The saved ${integration.name || friendlyName(integration.source)} filter rules will be deleted.`,
      "Remove filter",
    );
    if (!accepted) return;
    await request(`/filters/destinations/${view.destination.id}/sources/${encodeURIComponent(integration.source)}`, { method: "DELETE" });
    filteringState.destinationView = await request(`/filters/destinations/${view.destination.id}`);
    filteringState.integration = null;
    renderIntegrationStep();
    await loadOverview();
    toast("Integration filter removed.");
  }

  async function deleteDestinationFilter(destinationId) {
    const accepted = await confirmAction(
      "Delete destination filter?",
      "Every saved integration filter for this destination will be cleared. Routing is not changed.",
      "Delete filter",
    );
    if (!accepted) return;
    await request(`/filters/destinations/${destinationId}`, { method: "DELETE" });
    await loadOverview();
    toast("Destination filter deleted.");
  }

  function closeDialog() {
    const dialog = byId("filtering-dialog");
    if (dialog && dialog.open) dialog.close();
    filteringState.destinationView = null;
    filteringState.integration = null;
  }

  async function handleFilterAction(button) {
    const action = button.dataset.filterAction;
    const id = button.dataset.filterId || "";
    if (action === "new-filter") return openNewFilter();
    if (action === "close" || action === "finish") {
      closeDialog();
      await loadOverview();
      return;
    }
    if (action === "continue-destination") return continueDestination();
    if (action === "manage-destination") return openDestinationFilter(id);
    if (action === "configure-integration") return openIntegrationEditor(id);
    if (action === "back-integrations") return renderIntegrationStep();
    if (action === "add-field") return addTextField();
    if (action === "remove-field") return removeTextField(id);
    if (action === "save-integration") return saveIntegration();
    if (action === "remove-integration-filter") return removeIntegrationFilter();
    if (action === "delete-destination-filter") return deleteDestinationFilter(id);
  }

  function bindFilteringEvents() {
    document.addEventListener("click", (event) => {
      const button = event.target.closest("button[data-filter-action]");
      if (!button) return;
      event.preventDefault();
      handleFilterAction(button).catch((error) => toast(error.message || "The filtering action failed.", "error"));
    });
    document.addEventListener("change", (event) => {
      const operator = event.target.closest("select[data-filter-operator]");
      if (operator) filteringState.operators.set(operator.dataset.filterOperator, operator.value);
      const toggle = event.target.closest("input[data-filter-toggle]");
      if (!toggle || toggle.dataset.filterToggleContext === "editor") return;
      toggleIntegration(toggle.dataset.filterToggle, toggle.checked).catch((error) => {
        toggle.checked = !toggle.checked;
        toast(error.message || "The filter state could not be changed.", "error");
      });
    });
    const dialog = byId("filtering-dialog");
    dialog.addEventListener("cancel", (event) => {
      event.preventDefault();
      closeDialog();
    });
  }

  function wrapNavigation() {
    const previousNavigate = navigate;
    navigate = function filteringNavigate(view, historyMode = "push") {
      const result = previousNavigate(view, historyMode);
      if (state.currentView === "filtering") {
        const pageTitle = byId("page-title");
        if (pageTitle) byId("page-title").textContent = VIEW_TITLES.filtering;
        loadOverview().catch((error) => toast(error.message || "Filtering could not be loaded.", "error"));
      }
      return result;
    };
  }

  installNavigation();
  installView();
  installDialog();
  decoupleRouteUI();
  bindFilteringEvents();
  wrapNavigation();
})();
