"use strict";

/* Ownership-aware Filtering controls layered after the accepted CE WebUI extensions. */
(() => {
  const FILTER_VIEW = "filtering";
  let latest = null;
  let timer = 0;
  let activeDestinationId = "";
  let readOnlyDestinationId = "";
  let decorating = false;
  let authenticatedUsername = "";
  let profileIdentityObserver = null;
  let dialogPatchQueued = false;

  const previousRequest = request;
  request = async function filteringOwnershipRequest(path, options = {}) {
    const response = await previousRequest(path, options);
    if (path === "/filters") latest = response;
    return response;
  };

  function node(tag, className = "", text = "") {
    const item = document.createElement(tag);
    if (className) item.className = className;
    if (text !== "") item.textContent = String(text);
    return item;
  }

  function icon(kind) {
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("width", "16");
    svg.setAttribute("height", "16");
    svg.setAttribute("fill", "none");
    svg.setAttribute("stroke", "currentColor");
    svg.setAttribute("stroke-width", "2");
    svg.setAttribute("stroke-linecap", "round");
    svg.setAttribute("stroke-linejoin", "round");
    svg.setAttribute("aria-hidden", "true");
    svg.classList.add("filtering-control-icon");

    const paths = {
      eye: '<path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12z"></path><circle cx="12" cy="12" r="2.5"></circle>',
      share: '<circle cx="18" cy="5" r="2"></circle><circle cx="6" cy="12" r="2"></circle><circle cx="18" cy="19" r="2"></circle><path d="m8 11 8-5M8 13l8 5"></path>',
      configure: '<path d="M12 20h9"></path><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L8 18l-4 1 1-4Z"></path>',
      delete: '<path d="M3 6h18"></path><path d="M8 6V4h8v2"></path><path d="m19 6-1 14H6L5 6"></path><path d="M10 11v5M14 11v5"></path>',
    };
    svg.innerHTML = paths[kind] || "";
    return svg;
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

  function syncProfileIdentity() {
    if (!authenticatedUsername && state.user?.username) {
      authenticatedUsername = String(state.user.username);
    }
    const username = authenticatedUsername || String(state.user?.username || "");
    if (!username) return;
    const profileName = document.getElementById("profile-name");
    const accountName = document.getElementById("account-name");
    if (profileName && profileName.textContent !== username) profileName.textContent = username;
    if (accountName && accountName.textContent !== username) accountName.textContent = username;
  }

  function observeProfileIdentity() {
    const profileName = document.getElementById("profile-name");
    if (!profileName || profileIdentityObserver) return;
    profileIdentityObserver = new MutationObserver(() => syncProfileIdentity());
    profileIdentityObserver.observe(profileName, {
      childList: true,
      characterData: true,
      subtree: true,
    });
  }

  function statusControl(label, kind, action, policy) {
    const interactive = Boolean(action);
    const item = node(
      interactive ? "button" : "span",
      `badge filtering-status-control filtering-${kind}-control ${kind === "filtering" ? (policy.filtering_enabled ? "success" : "warning") : ""}`.trim(),
    );
    if (interactive) item.type = "button";

    if (kind === "filtering") {
      const dot = node("span", "filtering-status-dot");
      Object.assign(dot.style, {
        width: "0.65rem",
        height: "0.65rem",
        borderRadius: "999px",
        background: policy.filtering_enabled ? "#35d66f" : "#f0b93c",
        boxShadow: policy.filtering_enabled ? "0 0 8px rgba(53,214,111,.45)" : "none",
        flex: "0 0 auto",
      });
      item.append(dot, node("span", "", label));
    } else {
      item.append(icon("share"), node("span", "", label));
      Object.assign(item.style, policy.shared ? {
        color: "#a8c7ff",
        borderColor: "#4c7fe7",
        background: "rgba(45, 104, 220, 0.10)",
      } : {
        color: "#f1c45f",
        borderColor: "rgba(241,196,95,.42)",
        background: "rgba(241,196,95,.08)",
      });
    }

    Object.assign(item.style, {
      display: "inline-flex",
      alignItems: "center",
      gap: "0.5rem",
      minHeight: "2rem",
      paddingInline: "0.75rem",
      whiteSpace: "nowrap",
    });

    if (!interactive) return item;
    item.dataset.filterSyncAction = action;
    item.dataset.filterSyncId = policy.destination_id;
    item.dataset.filterSyncValue = action === "filtering"
      ? String(Boolean(policy.filtering_enabled))
      : String(Boolean(policy.shared));
    item.setAttribute("aria-label", action === "filtering"
      ? `${label}. Change destination filtering state`
      : `${label}. Change destination sharing`);
    return item;
  }

  function rowAction(label, iconName, style, policy, action, sync = false) {
    const button = node("button", `button small ${style} filtering-row-action filtering-row-action-${iconName}`.trim());
    button.type = "button";
    button.append(icon(iconName), node("span", "", label));
    Object.assign(button.style, {
      display: "inline-flex",
      alignItems: "center",
      justifyContent: "center",
      gap: "0.45rem",
      whiteSpace: "nowrap",
    });
    if (sync) {
      button.dataset.filterSyncAction = action;
      button.dataset.filterSyncId = policy.destination_id;
    } else {
      button.dataset.filterAction = action;
      button.dataset.filterId = policy.destination_id;
    }
    return button;
  }

  function ensureSharingColumn() {
    const headerRow = document.querySelector(".filtering-table thead tr");
    if (!headerRow) return;
    const nameHeading = headerRow.children[1];
    if (nameHeading && nameHeading.textContent !== "Name") nameHeading.textContent = "Name";
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
    const detailRow = row.nextElementSibling?.matches(".filtering-expanded-row")
      && row.nextElementSibling.dataset.filterDetailId === String(policy.destination_id)
      ? row.nextElementSibling
      : null;
    const cards = [...(detailRow || row).querySelectorAll(".filtering-overview-integration")];
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

  function renderActions(row, policy) {
    const cell = row.lastElementChild;
    if (!cell) return;
    const actions = node("div", "table-actions filtering-table-actions");
    Object.assign(actions.style, {
      display: "flex",
      alignItems: "center",
      justifyContent: "flex-end",
      flexWrap: "nowrap",
      gap: "0.75rem",
      whiteSpace: "nowrap",
    });

    if (policy.can_manage_filters) {
      actions.append(
        rowAction("View", "eye", "secondary", policy, "view-filter", true),
        rowAction("Configure", "configure", "primary", policy, "manage-destination"),
        rowAction("Delete", "delete", "danger", policy, "delete-destination-filter"),
      );
    } else if (policy.managed_by_admin) {
      actions.append(rowAction("View", "eye", "secondary", policy, "view-filter", true));
    }
    cell.replaceChildren(actions);
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
    renderActions(row, policy);
    removeLegacyVisibility(row);

    const statusCell = row.querySelector(".filtering-status-cell") || row.children[3];
    if (!statusCell || !sharingCell) return;
    statusCell.replaceChildren(
      statusControl(
        policy.filtering_enabled ? "Active" : "Disabled",
        "filtering",
        policy.can_manage_filters ? "filtering" : "",
        policy,
      ),
    );
    sharingCell.replaceChildren(
      statusControl(
        policy.shared ? "Shared" : "Private",
        "sharing",
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
      syncProfileIdentity();
      ensureSharingColumn();
      document.querySelectorAll("#filter-table > .acceptance-private-filter").forEach(item => item.remove());
      const rows = [...document.querySelectorAll("#filter-table > tr.filtering-policy-row")];
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

  function scheduleDialogPatch() {
    if (dialogPatchQueued) return;
    dialogPatchQueued = true;
    queueMicrotask(() => {
      dialogPatchQueued = false;
      patchDialog();
    });
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

  function triggerCoreFilterAction(action, destinationId, readOnly = false) {
    const trigger = node("button");
    trigger.type = "button";
    trigger.hidden = true;
    trigger.dataset.filterAction = action;
    trigger.dataset.filterId = destinationId;
    if (readOnly) trigger.dataset.filterViewReadonly = "true";
    document.body.append(trigger);
    trigger.click();
    trigger.remove();
  }

  function openCoreDestination(destinationId) {
    activeDestinationId = destinationId;
    readOnlyDestinationId = "";
    triggerCoreFilterAction("manage-destination", destinationId);
  }

  function openReadOnlyView(destinationId) {
    const policy = policyFor(destinationId);
    if (!policy) return;
    activeDestinationId = destinationId;
    readOnlyDestinationId = destinationId;
    triggerCoreFilterAction(
      policy.can_manage_filters ? "manage-destination" : "view-destination-filter",
      destinationId,
      true,
    );
    scheduleDialogPatch();
  }

  function patchDialog() {
    if (!activeDestinationId) return;
    const policy = policyFor(activeDestinationId);
    const choice = choiceFor(activeDestinationId);
    if (!policy && !choice) return;
    const dialog = document.getElementById("filtering-dialog");
    if (!dialog?.open) return;

    const readOnly = readOnlyDestinationId === activeDestinationId;
    const canManage = Boolean(policy?.can_manage_filters || choice?.can_manage_filters);
    dialog.classList.toggle("filtering-readonly-view", readOnly);

    const title = document.getElementById("filtering-dialog-title");
    const note = document.querySelector(".filtering-available-note");
    const integrationStep = document.getElementById("filter-integration-step");
    const footer = integrationStep?.querySelector(".modal-actions");
    const cancel = footer?.querySelector('[data-filter-action="close"]');
    const finish = footer?.querySelector('[data-filter-action="finish"]');

    if (readOnly) {
      if (title && integrationStep && !integrationStep.hidden) title.textContent = "View filter";
      if (note && integrationStep && !integrationStep.hidden) {
        note.textContent = "Read-only view. Filter rules remain private to the destination owner.";
      }
      if (cancel) cancel.hidden = true;
      if (finish) {
        finish.hidden = false;
        finish.textContent = "Close";
      }
      dialog.querySelectorAll('input[data-filter-toggle]').forEach(input => {
        input.disabled = true;
      });
      dialog.querySelectorAll('[data-filter-action="configure-integration"]').forEach(button => button.remove());
    } else {
      if (cancel) cancel.hidden = false;
      if (canManage) {
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
      }
    }

    let masterNotice = dialog.querySelector(".filtering-master-disabled-note");
    if (!readOnly && policy && !policy.filtering_enabled) {
      if (!masterNotice) {
        masterNotice = node(
          "p",
          "filtering-warning filtering-master-disabled-note",
          "Destination filtering is disabled. Saved integration filter states are preserved and will resume when filtering is enabled.",
        );
        const visibleSection = [...dialog.querySelectorAll(":scope > section")].find(section => !section.hidden);
        visibleSection?.prepend(masterNotice);
      }
    } else {
      masterNotice?.remove();
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
      if (coreAction.dataset.filterViewReadonly !== "true") readOnlyDestinationId = "";
      scheduleDialogPatch();
    }
    if (coreAction?.dataset.filterAction === "view-destination-filter") {
      activeDestinationId = coreAction.dataset.filterId || "";
      if (coreAction.dataset.filterViewReadonly === "true") {
        readOnlyDestinationId = activeDestinationId;
      }
      scheduleDialogPatch();
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
    if (action === "view-filter") {
      event.preventDefault();
      event.stopImmediatePropagation();
      openReadOnlyView(sync.dataset.filterSyncId || "");
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

  const previousShowApp = showApp;
  showApp = function filteringOwnershipShowApp(session) {
    authenticatedUsername = String(session?.user?.username || "");
    const result = previousShowApp(session);
    syncProfileIdentity();
    observeProfileIdentity();
    return result;
  };

  const previousNavigate = navigate;
  navigate = function filteringOwnershipNavigate(view, historyMode = "push") {
    const result = previousNavigate(view, historyMode);
    syncProfileIdentity();
    if (state.currentView === FILTER_VIEW) schedule();
    if (state.currentView === "destinations") {
      refreshDestinationsState().catch(() => {
        // Keep the last successful Destination view if a refresh fails.
      });
    }
    return result;
  };

  document.addEventListener("nowlert:filtering-rendered", event => {
    decorate(event.detail);
  });

  document.addEventListener("DOMContentLoaded", () => {
    if (state.user?.username) authenticatedUsername = String(state.user.username);
    syncProfileIdentity();
    observeProfileIdentity();
    normalizeRoutingHeadings();
    ensureSharingColumn();
    const graph = document.getElementById("rf-graph");
    if (graph) {
      new MutationObserver(normalizeRoutingHeadings).observe(graph, { childList: true });
    }
    const table = document.getElementById("filter-table");
    if (table) {
      new MutationObserver(() => {
        if (decorating || state.currentView !== FILTER_VIEW) return;
        if (latest) decorate(latest);
      }).observe(table, { childList: true, subtree: false });
    }
    const dialog = document.getElementById("filtering-dialog");
    if (dialog) {
      const dialogPatchObserver = new MutationObserver(scheduleDialogPatch);
      dialogPatchObserver.observe(dialog, {
        attributes: true,
        attributeFilter: ["open"],
      });
      for (const step of dialog.querySelectorAll(":scope > section")) {
        dialogPatchObserver.observe(step, {
          attributes: true,
          attributeFilter: ["hidden"],
        });
      }
      dialog.addEventListener("close", () => {
        activeDestinationId = "";
        readOnlyDestinationId = "";
        dialog.classList.remove("filtering-readonly-view");
        const cancel = document.querySelector('#filter-integration-step .modal-actions [data-filter-action="close"]');
        if (cancel) cancel.hidden = false;
      });
    }
    if (state.currentView === FILTER_VIEW) schedule(0);
  });
})();