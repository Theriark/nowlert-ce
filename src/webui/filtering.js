"use strict";

(() => {
  const filteringState = {
    overview: null,
    destinationView: null,
    integration: null,
    activeTextFields: new Set(),
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
      <div class="section-toolbar">
        <div>
          <h2>Filtering</h2>
          <p>Control which notifications can reach each destination.</p>
        </div>
        <button id="add-filter-button" class="button primary" type="button" data-filter-action="new-filter">New filter</button>
      </div>
      <div class="table-panel">
        <div class="table-scroll">
          <table>
            <thead><tr><th>Destination</th><th>Integrations</th><th>Status</th><th><span class="sr-only">Actions</span></th></tr></thead>
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
      <div class="modal-heading">
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
        <div class="filtering-context">
          <span>Destination</span>
          <strong id="filter-context-destination"></strong>
        </div>
        <p class="field-help">Only integrations currently available on this destination are shown.</p>
        <div id="filter-integration-list" class="filtering-integration-list"></div>
        <div class="modal-actions">
          <button class="button secondary" type="button" data-filter-action="back-destination">Back</button>
          <button class="button primary" type="button" data-filter-action="finish">Done</button>
        </div>
      </section>

      <section id="filter-editor-step" hidden>
        <div class="filtering-editor-heading">
          <div>
            <span class="eyebrow" id="filter-editor-source"></span>
            <h3 id="filter-editor-name"></h3>
          </div>
          <span id="filter-editor-state" class="badge"></span>
        </div>
        <p id="filter-legacy-warning" class="filtering-warning" hidden></p>
        <div id="filter-enum-fields" class="filtering-enum-fields"></div>
        <div id="filter-text-fields" class="filtering-text-fields"></div>
        <div id="filter-add-field-row" class="filtering-add-field-row">
          <select id="filter-add-field-select" aria-label="Additional filter field"></select>
          <button class="button secondary small" type="button" data-filter-action="add-field">Add field</button>
        </div>
        <p class="field-help">Within a field, values are matched as OR. Different configured fields are matched as AND. Text fields accept comma-separated wildcard patterns.</p>
        <div class="modal-actions">
          <button class="button secondary" type="button" data-filter-action="back-integrations">Back</button>
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
    if (description) {
      description.textContent = "Connect integrations and inputs to destinations with routing priorities.";
    }

    const table = byId("route-table") && byId("route-table").closest("table");
    const header = table && table.tHead && table.tHead.rows[0];
    if (header && !header.dataset.filteringDecoupled && header.cells.length >= 8) {
      header.cells[4].remove();
      header.dataset.filteringDecoupled = "true";
    }

    const stripRows = () => {
      const body = byId("route-table");
      if (!body) return;
      for (const row of body.rows) {
        if (row.cells.length >= 8) row.cells[4].remove();
      }
    };
    stripRows();
    const routeBody = byId("route-table");
    if (routeBody) {
      new MutationObserver(stripRows).observe(routeBody, { childList: true });
    }

    const updateFlowCopy = () => {
      const flow = byId("dashboard-flow");
      if (!flow) return;
      for (const detail of flow.querySelectorAll(".flow-route small")) {
        if (detail.textContent !== "Routing only") {
          detail.textContent = "Routing only";
        }
      }
    };
    updateFlowCopy();
    const flow = byId("dashboard-flow");
    if (flow) {
      new MutationObserver(updateFlowCopy).observe(flow, { childList: true, subtree: true });
    }
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

  function renderOverview() {
    const payload = filteringState.overview || { filters: [], destinations: [] };
    const body = byId("filter-table");
    const emptyState = byId("filter-empty");
    if (!body || !emptyState) return;
    body.replaceChildren();

    const policies = Array.isArray(payload.filters) ? payload.filters : [];
    emptyState.hidden = policies.length > 0;
    if (!policies.length) {
      emptyState.replaceChildren(
        element("strong", { text: "No filters configured" }),
        element("span", { text: canEditFilters() ? "Use New filter to configure one destination." : "No destination filters are currently configured." }),
      );
    }

    for (const policy of policies) {
      const active = Array.isArray(policy.sources) ? policy.sources : [];
      const configuredCount = Number(policy.configured_count || 0);
      const activeCount = Number(policy.active_count || 0);
      const integrationText = active.length
        ? active.map((source) => friendlyName(source)).join(", ")
        : configuredCount
          ? "Configured integrations are currently unavailable"
          : "—";
      const status = activeCount > 0 ? "Configured" : "Dormant";
      const actions = element("div", { className: "table-actions" });
      if (canEditFilters()) {
        actions.append(
          actionButtonForFilter("Configure", "manage-destination", policy.destination_id),
          actionButtonForFilter("Delete", "delete-destination-filter", policy.destination_id, "danger"),
        );
      }
      body.append(element("tr", {}, [
        element("td", {}, [
          element("strong", { text: policy.destination_name || "Destination" }),
          element("small", { text: friendlyName(policy.output_type) }),
        ]),
        element("td", { text: integrationText }),
        element("td", {}, [badge(status, activeCount > 0 ? "success" : "warning")]),
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

  function fillDestinationSelect(selectedId = "") {
    const select = byId("filter-destination-select");
    select.replaceChildren();
    const destinations = filteringState.overview && Array.isArray(filteringState.overview.destinations)
      ? filteringState.overview.destinations
      : [];
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
      const option = element("option", {
        value: item.id,
        text: `${item.name} · ${count} integration${count === 1 ? "" : "s"}`,
      });
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
    const selected = filteringState.overview.destinations.find((item) => item.id === destinationId);
    if (!selected) throw new Error("Destination is no longer available.");
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
    byId("filter-context-destination").textContent = view.destination.name;
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
      const status = integration.configured ? "Configured" : "No filter / All notifications";
      list.append(element("article", { className: "filtering-integration-row" }, [
        element("div", { className: "filtering-integration-identity" }, [
          element("span", { className: "filtering-integration-mark", text: String(integration.name || integration.source).slice(0, 1).toUpperCase(), attributes: { "aria-hidden": "true" } }),
          element("div", {}, [
            element("strong", { text: integration.name || friendlyName(integration.source) }),
            element("small", { text: (integration.inputs || []).map((item) => item.name).join(" · ") || "Integration" }),
          ]),
        ]),
        element("div", { className: "filtering-integration-actions" }, [
          badge(status, integration.configured ? "success" : ""),
          canEditFilters()
            ? actionButtonForFilter("Configure", "configure-integration", integration.source)
            : null,
        ]),
      ]));
    }
  }

  function normalizedSet(values) {
    return new Set((values || []).map((value) => String(value).trim().toLowerCase()));
  }

  function openIntegrationEditor(source) {
    const view = filteringState.destinationView;
    if (!view) return;
    const integration = view.integrations.find((item) => item.source === source);
    if (!integration) return;
    filteringState.integration = integration;
    filteringState.activeTextFields = new Set(
      Object.keys(integration.rules || {}).filter((key) => {
        const field = integration.fields.find((item) => item.key === key);
        return field && field.kind === "text";
      }),
    );
    renderEditor();
  }

  function renderEditor() {
    const integration = filteringState.integration;
    if (!integration) return;
    resetDialogSteps();
    byId("filter-editor-step").hidden = false;
    byId("filter-editor-source").textContent = integration.name || friendlyName(integration.source);
    byId("filter-editor-name").textContent = "Filter notifications";
    const status = byId("filter-editor-state");
    status.textContent = integration.configured ? "Configured" : "No filter / All notifications";
    status.className = `badge${integration.configured ? " success" : ""}`;

    const legacy = Array.isArray(integration.legacy_clauses) ? integration.legacy_clauses : [];
    const warning = byId("filter-legacy-warning");
    warning.hidden = legacy.length === 0;
    warning.textContent = legacy.length
      ? "This integration contains migrated route-filter clauses. Saving here replaces those clauses with this destination filter configuration."
      : "";

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
        const label = element("label", { className: "filtering-choice" }, [
          input,
          element("span", { text: value }),
        ]);
        choices.append(label);
      }
      group.append(choices);
      container.append(group);
    }
  }

  function renderTextFields() {
    const integration = filteringState.integration;
    const container = byId("filter-text-fields");
    container.replaceChildren();
    const rules = integration.rules || {};
    for (const field of integration.fields.filter(
      (item) => item.kind === "text" && filteringState.activeTextFields.has(item.key),
    )) {
      const values = Array.isArray(rules[field.key]) ? rules[field.key] : [];
      const input = element("input", {
        value: values.join(", "),
        attributes: {
          "data-filter-text": field.key,
          placeholder: "value, wildcard-*",
          autocomplete: "off",
        },
      });
      container.append(element("label", { className: "filtering-text-field" }, [
        element("span", { text: field.label }),
        element("div", { className: "filtering-text-control" }, [
          input,
          actionButtonForFilter("Remove", "remove-field", field.key),
        ]),
      ]));
    }
  }

  function renderAddFieldChoices() {
    const integration = filteringState.integration;
    const select = byId("filter-add-field-select");
    select.replaceChildren();
    const fields = integration.fields.filter(
      (item) => item.kind === "text" && !filteringState.activeTextFields.has(item.key),
    );
    if (!fields.length) {
      select.append(element("option", { text: "All available fields are shown", value: "" }));
      select.disabled = true;
      byId("filter-add-field-row").querySelector("button").disabled = true;
      return;
    }
    select.disabled = false;
    byId("filter-add-field-row").querySelector("button").disabled = false;
    select.append(element("option", { text: "Add another field…", value: "" }));
    for (const field of fields) {
      select.append(element("option", { text: field.label, value: field.key }));
    }
  }

  function addTextField() {
    const key = byId("filter-add-field-select").value;
    if (!key) return;
    filteringState.activeTextFields.add(key);
    renderTextFields();
    renderAddFieldChoices();
    const input = document.querySelector(`[data-filter-text="${CSS.escape(key)}"]`);
    if (input) input.focus();
  }

  function removeTextField(key) {
    filteringState.activeTextFields.delete(key);
    if (filteringState.integration && filteringState.integration.rules) {
      delete filteringState.integration.rules[key];
    }
    renderTextFields();
    renderAddFieldChoices();
  }

  function editorRules() {
    const integration = filteringState.integration;
    const rules = {};
    for (const field of integration.fields.filter((item) => item.kind === "enum")) {
      const inputs = [...document.querySelectorAll(`[data-filter-enum="${CSS.escape(field.key)}"]`)];
      const selected = inputs.filter((input) => input.checked).map((input) => input.value);
      if (selected.length > 0 && selected.length < inputs.length) {
        rules[field.key] = selected;
      }
    }
    for (const field of integration.fields.filter((item) => item.kind === "text")) {
      const input = document.querySelector(`[data-filter-text="${CSS.escape(field.key)}"]`);
      if (!input) continue;
      const values = String(input.value || "")
        .split(",")
        .map((value) => value.trim())
        .filter(Boolean);
      if (values.length) rules[field.key] = values;
    }
    return rules;
  }

  async function saveIntegration() {
    const integration = filteringState.integration;
    const destination = filteringState.destinationView && filteringState.destinationView.destination;
    if (!integration || !destination) return;
    const response = await request(
      `/filters/destinations/${destination.id}/sources/${encodeURIComponent(integration.source)}`,
      { method: "PUT", body: { rules: editorRules() } },
    );
    const index = filteringState.destinationView.integrations.findIndex(
      (item) => item.source === integration.source,
    );
    if (index >= 0) filteringState.destinationView.integrations[index] = response.integration;
    filteringState.integration = null;
    renderIntegrationStep();
    await loadOverview();
    toast(response.integration.configured ? "Filter saved." : "No filter configured; all notifications are allowed.", "success");
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
    if (action === "back-destination") {
      fillDestinationSelect(filteringState.destinationView && filteringState.destinationView.destination.id);
      resetDialogSteps();
      byId("filter-destination-step").hidden = false;
      return;
    }
    if (action === "manage-destination") return openDestinationFilter(id);
    if (action === "configure-integration") return openIntegrationEditor(id);
    if (action === "back-integrations") return renderIntegrationStep();
    if (action === "add-field") return addTextField();
    if (action === "remove-field") return removeTextField(id);
    if (action === "save-integration") return saveIntegration();
    if (action === "delete-destination-filter") return deleteDestinationFilter(id);
  }

  function bindFilteringEvents() {
    document.addEventListener("click", (event) => {
      const button = event.target.closest("button[data-filter-action]");
      if (!button) return;
      event.preventDefault();
      handleFilterAction(button).catch((error) => {
        toast(error.message || "The filtering action failed.", "error");
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