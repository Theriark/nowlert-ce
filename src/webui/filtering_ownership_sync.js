"use strict";

/* Ownership-aware Filtering controls layered after the accepted CE WebUI extensions. */
(() => {
  const FILTER_VIEW = "filtering";
  let latest = null;
  let timer = 0;
  let activeDestinationId = "";
  let decorating = false;

  function node(tag, className = "", text = "") {
    const item = document.createElement(tag);
    if (className) item.className = className;
    if (text !== "") item.textContent = String(text);
    return item;
  }

  function policyRows(payload) {
    return (Array.isArray(payload?.filters) ? payload.filters : [])
      .filter(policy => Array.isArray(policy.integrations) && policy.integrations.length > 0);
  }

  function ownedChoices(payload) {
    return (Array.isArray(payload?.destinations) ? payload.destinations : [])
      .filter(item => (
        item.owned
        && item.can_manage_filters
        && Number(item.available_integration_count || 0) > 0
      ));
  }

  function policyFor(destinationId) {
    return policyRows(latest).find(item => item.destination_id === destinationId) || null;
  }

  function choiceFor(destinationId) {
    return ownedChoices(latest).find(item => item.id === destinationId) || null;
  }

  function statusBadge(label, style = "") {
    return node("span", `badge ${style}`.trim(), label);
  }

  function statusControl(label, style, action, policy) {
    if (!action) return statusBadge(label, style);
    const button = node("button", `badge filtering-status-control ${style}`.trim(), label);
    button.type = "button";
    button.dataset.filterSyncAction = action;
    button.dataset.filterSyncId = policy.destination_id;
    button.dataset.filterSyncValue = action === "filtering"
      ? String(Boolean(policy.filtering_enabled))
      : String(Boolean(policy.shared));
    button.setAttribute("aria-label", action === "filtering"
      ? `${label}. Change destination filtering state`
      : `${label}. Change destination sharing`);
    return button;
  }

  function ensureSharingColumn() {
    const headerRow = document.querySelector(".filtering-table thead tr");
    if (!headerRow) return;
    let heading = headerRow.querySelector('[data-filter-sync-column="sharing"]');
    if (!heading) {
      heading = node("th", "", "Sharing");
      heading.dataset.filterSyncColumn = "sharing";
      headerRow.insertBefore(heading, headerRow.lastElementChild);
    }
    if (heading.textContent !== "Sharing") heading.textContent = "Sharing";
  }

  function sharingCellFor(row) {
    let cell = row.querySelector('td[data-filter-sync-column="sharing"]');
    if (cell) return cell;
    cell = node("td", "filtering-sharing-cell");
    cell.dataset.filterSyncColumn = "sharing";
    row.insertBefore(cell, row.lastElementChild);
    return cell;
  }

  function removeLegacyVisibility(row) {
    row.querySelectorAll(".acceptance-visibility-badge, .filtering-access-badge")
      .forEach(item => item.remove());
  }

  function decorateManagedIntegrations(row, policy) {
    const cards = [...row.querySelectorAll(".filtering-overview-integration")];
    cards.forEach((card, index) => {
      const integration = policy.integrations[index];
      if (!integration) return;
      const marker = card.querySelector(".filtering-card-check");
      if (marker) {
        marker.textContent = integration.filter_enabled ? "✓" : "○";
        marker.setAttribute(
          "aria-label",
          integration.filter_enabled ? "Filter enabled" : "Filter disabled",
        );
        card.classList.toggle("acceptance-filter-disabled", !integration.filter_enabled);
      }
      const copy = card.querySelector(".filtering-overview-copy");
      let note = copy?.querySelector(".filtering-managed-note");
      if (integration.restricted) {
        if (!note && copy) {
          note = node("small", "filtering-managed-note", "Managed by administrator");
          copy.append(note);
        }
        card.classList.add("filtering-managed-integration");
      } else {
        note?.remove();
        card.classList.remove("filtering-managed-integration");
      }
    });
  }

  function ensureOwnerActions(row, policy) {
    const actions = row.lastElementChild;
    if (!actions || !policy.can_manage_filters) return;
    let container = actions.querySelector(".filtering-table-actions");
    if (!container) {
      container = node("div", "table-actions filtering-table-actions");
      actions.replaceChildren(container);
    }
    if (!container.querySelector('[data-filter-action="manage-destination"]')) {
      const configure = node("button", "button small primary", "✎ Configure");
      configure.type = "button";
      configure.dataset.filterAction = "manage-destination";
      configure.dataset.filterId = policy.destination_id;
      container.append(configure);
    }
    if (!container.querySelector('[data-filter-action="delete-destination-filter"]')) {
      const remove = node("button", "button small danger", "Delete");
      remove.type = "button";
      remove.dataset.filterAction = "delete-destination-filter";
      remove.dataset.filterId = policy.destination_id;
      container.append(remove);
    }
  }

  function decorateRow(row, policy) {
    const sharingCell = sharingCellFor(row);
    const summary = row.querySelector(".filtering-overview-header strong");
    if (summary) {
      const configured = Number(policy.configured_count || policy.integrations.length || 0);
      const active = Number(policy.active_count || 0);
      summary.textContent = policy.filtering_enabled
        ? `${configured} configured · ${active} active`
        : `${configured} configured · disabled`;
    }
    decorateManagedIntegrations(row, policy);
    ensureOwnerActions(row, policy);
    removeLegacyVisibility(row);

    const statusCell = row.children[2];
    if (!statusCell || !sharingCell) return;
    statusCell.replaceChildren(
      statusControl(
        policy.filtering_enabled ? "Active" : "Disabled",
        policy.filtering_enabled ? "success" : "warning",
        policy.can_manage_filters ? "filtering" : "",
        policy,
      ),
    );
    sharingCell.replaceChildren(
      statusControl(
        policy.shared ? "Shared" : "Private",
        policy.shared ? "success" : "warning",
        policy.can_change_sharing ? "sharing" : "",
        policy,
      ),
    );
  }

  function configureAddButton(payload) {
    const add = document.getElementById("add-filter-button");
    if (!add) return;
    const choices = ownedChoices(payload);
    if (state.user?.role === "admin") {
      add.hidden = choices.length === 0;
      add.dataset.filterAction = "new-filter";
      delete add.dataset.filterSyncAction;
      return;
    }
    add.hidden = choices.length === 0;
    add.dataset.filterAction = "owner-new-filter";
    add.dataset.filterSyncAction = "owner-new-filter";
  }

  function decorate(payload) {
    if (!payload || state.currentView !== FILTER_VIEW) return;
    decorating = true;
    try {
      latest = payload;
      ensureSharingColumn();
      document.querySelectorAll("#filter-table > .acceptance-private-filter").forEach(item => item.remove());
      const rows = [...document.querySelectorAll("#filter-table > tr:not(.acceptance-private-filter)")];
      const policies = policyRows(payload);
      policies.forEach((policy, index) => {
        if (rows[index]) decorateRow(rows[index], policy);
      });
      configureAddButton(payload);
      patchDialog();
    } finally {
      decorating = false;
    }
  }

  async function refresh() {
    if (!state.user || state.currentView !== FILTER_VIEW) return;
    try {
      const payload = await request("/filters");
      decorate(payload);
    } catch (_error) {
      // Core Filtering remains usable if this presentation/access sync fails.
    }
  }

  async function refreshDestinationsState() {
    if (!state.user) return;
    const payload = await request("/destinations");
    state.destinations = payload.destinations || [];
    state.destinationErrors = payload.errors || [];
    renderDestinations();
  }

  function schedule(delay = 220) {
    window.clearTimeout(timer);
    timer = window.setTimeout(refresh, delay);
  }

  function picker() {
    let dialog = document.getElementById("filter-owner-picker");
    if (dialog) return dialog;
    dialog = node("dialog", "modal filtering-owner-picker");
    dialog.id = "filter-owner-picker";
    dialog.innerHTML = `
      <div class="modal-heading filtering-modal-heading">
        <div><p class="eyebrow">Destination filtering</p><h2>New filter</h2></div>
        <button class="icon-button" type="button" data-filter-owner-close aria-label="Close">×</button>
      </div>
      <p class="field-help">Choose one of your destinations to configure private filtering.</p>
      <label class="filtering-destination-field"><span>Destination</span><select id="filter-owner-destination"></select></label>
      <div class="modal-actions">
        <button class="button secondary" type="button" data-filter-owner-close>Cancel</button>
        <button class="button primary" type="button" data-filter-owner-continue>Continue</button>
      </div>`;
    document.body.append(dialog);
    dialog.addEventListener("click", event => {
      if (event.target.closest("[data-filter-owner-close]")) dialog.close();
      if (event.target.closest("[data-filter-owner-continue]")) {
        const id = dialog.querySelector("#filter-owner-destination")?.value || "";
        if (!id) return;
        dialog.close();
        openCoreDestination(id);
      }
    });
    return dialog;
  }

  function openOwnerPicker() {
    const choices = ownedChoices(latest);
    if (!choices.length) return;
    if (choices.length === 1) {
      openCoreDestination(choices[0].id);
      return;
    }
    const dialog = picker();
    const select = dialog.querySelector("#filter-owner-destination");
    select.replaceChildren();
    choices.forEach(item => {
      const option = node("option", "", item.name);
      option.value = item.id;
      select.append(option);
    });
    dialog.showModal();
  }

  function openCoreDestination(destinationId) {
    activeDestinationId = destinationId;
    const trigger = node("button");
    trigger.type = "button";
    trigger.hidden = true;
    trigger.dataset.filterAction = "manage-destination";
    trigger.dataset.filterId = destinationId;
    document.body.append(trigger);
    trigger.click();
    trigger.remove();
  }

  function patchDialog() {
    if (!activeDestinationId || !choiceFor(activeDestinationId)) return;
    const dialog = document.getElementById("filtering-dialog");
    if (!dialog?.open) return;
    dialog.querySelectorAll('input[data-filter-toggle]').forEach(input => {
      input.disabled = false;
    });
    const list = document.getElementById("filter-integration-list");
    if (list) {
      for (const row of list.querySelectorAll(":scope > .filtering-integration-row")) {
        const source = row.querySelector('input[data-filter-toggle]')?.dataset.filterToggle;
        const actions = row.querySelector(".filtering-integration-actions");
        if (!source || !actions || actions.querySelector('[data-filter-action="configure-integration"]')) continue;
        const configure = node("button", "button small secondary", "Configure");
        configure.type = "button";
        configure.dataset.filterAction = "configure-integration";
        configure.dataset.filterId = source;
        actions.append(configure);
      }
    }
    const policy = policyFor(activeDestinationId);
    let notice = dialog.querySelector(".filtering-master-disabled-note");
    if (policy && !policy.filtering_enabled) {
      if (!notice) {
        notice = node(
          "p",
          "filtering-warning filtering-master-disabled-note",
          "Destination filtering is disabled. Saved integration filter states are preserved and will resume when filtering is enabled.",
        );
        const visibleSection = [...dialog.querySelectorAll(":scope > section")].find(section => !section.hidden);
        visibleSection?.prepend(notice);
      }
    } else {
      notice?.remove();
    }
  }

  async function toggleFiltering(button) {
    const destinationId = button.dataset.filterSyncId;
    const current = button.dataset.filterSyncValue === "true";
    await request(`/filters/destinations/${destinationId}/enabled`, {
      method: "PUT",
      body: { enabled: !current },
    });
    await refresh();
    toast(!current ? "Destination filtering enabled." : "Destination filtering disabled; saved rules were kept.", "success");
  }

  async function toggleSharing(button) {
    const destinationId = button.dataset.filterSyncId;
    const current = button.dataset.filterSyncValue === "true";
    const response = await request(`/destinations/${destinationId}`, {
      method: "PATCH",
      body: { shared: !current },
    });
    if (response?.destination && Array.isArray(state.destinations)) {
      const index = state.destinations.findIndex(item => item.id === destinationId);
      if (index >= 0) state.destinations[index] = { ...state.destinations[index], ...response.destination };
    }
    await Promise.all([refresh(), refreshDestinationsState()]);
    toast(!current ? "Destination is now shared." : "Destination is now private.", "success");
  }

  function normalizeRoutingHeadings() {
    const headings = [...document.querySelectorAll("#rf-graph > .rf-column-heading")];
    const labels = ["Integrations", "Filters", "Destinations"];
    headings.slice(0, 3).forEach((heading, index) => {
      if (heading.textContent !== labels[index]) heading.textContent = labels[index];
      heading.dataset.routingColumn = ["integration", "filter", "destination"][index];
    });
  }

  document.addEventListener("click", event => {
    const coreAction = event.target.closest("[data-filter-action]");
    if (coreAction?.dataset.filterAction === "manage-destination") {
      activeDestinationId = coreAction.dataset.filterId || "";
      window.setTimeout(patchDialog, 0);
    }
    const sync = event.target.closest("[data-filter-sync-action]");
    if (!sync) return;
    const action = sync.dataset.filterSyncAction;
    if (action === "owner-new-filter") {
      event.preventDefault();
      event.stopImmediatePropagation();
      openOwnerPicker();
      return;
    }
    if (action === "filtering") {
      event.preventDefault();
      toggleFiltering(sync).catch(error => toast(error.message || "Filtering state could not be changed.", "error"));
      return;
    }
    if (action === "sharing") {
      event.preventDefault();
      toggleSharing(sync).catch(error => toast(error.message || "Destination visibility could not be changed.", "error"));
    }
  }, true);

  const previousNavigate = navigate;
  navigate = function filteringOwnershipNavigate(view, historyMode = "push") {
    const result = previousNavigate(view, historyMode);
    if (state.currentView === FILTER_VIEW) schedule();
    if (state.currentView === "destinations") {
      refreshDestinationsState().catch(() => {
        // Keep the last successful Destination view if a refresh fails.
      });
    }
    return result;
  };

  document.addEventListener("DOMContentLoaded", () => {
    normalizeRoutingHeadings();
    ensureSharingColumn();
    const graph = document.getElementById("rf-graph");
    if (graph) {
      new MutationObserver(normalizeRoutingHeadings).observe(graph, { childList: true });
    }
    const table = document.getElementById("filter-table");
    if (table) {
      new MutationObserver(() => {
        if (!decorating && state.currentView === FILTER_VIEW) schedule();
      }).observe(table, { childList: true, subtree: false });
    }
    const dialog = document.getElementById("filtering-dialog");
    if (dialog) {
      new MutationObserver(() => window.setTimeout(patchDialog, 0)).observe(dialog, {
        childList: true,
        subtree: true,
        attributes: true,
        attributeFilter: ["hidden", "open"],
      });
    }
    if (state.currentView === FILTER_VIEW) schedule(0);
  });
})();
