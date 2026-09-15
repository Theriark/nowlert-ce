"use strict";

function destinationRouteSummaryLabel(selectedCount, totalCount) {
  const selected = Math.max(0, Number(selectedCount) || 0);
  const total = Math.max(0, Number(totalCount) || 0);
  if (selected === 0) return "No routes assigned";
  if (total > 0 && selected === total) return "All routes assigned";
  return selected === 1 ? "1 route assigned" : `${selected} routes assigned`;
}

function destinationRouteSelectedItems(routes, selectedIds) {
  const selected = selectedIds instanceof Set ? selectedIds : new Set(selectedIds || []);
  return (Array.isArray(routes) ? routes : []).filter((route) => selected.has(route.id));
}

function destinationRouteVisibleItems(selectedRoutes, limit = 3) {
  const items = Array.isArray(selectedRoutes) ? selectedRoutes : [];
  const safeLimit = Math.max(0, Number(limit) || 0);
  return {
    visible: items.slice(0, safeLimit),
    remainder: Math.max(0, items.length - safeLimit),
  };
}

function destinationRouteSelectionForItem(item, routes) {
  const selected = new Set(item && Array.isArray(item.route_ids) ? item.route_ids : []);
  const destinationId = item && item.id ? String(item.id) : "";
  if (destinationId) {
    for (const route of Array.isArray(routes) ? routes : []) {
      if (
        route
        && route.id
        && Array.isArray(route.destination_ids)
        && route.destination_ids.includes(destinationId)
      ) {
        selected.add(route.id);
      }
    }
  }
  return selected;
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    destinationRouteSummaryLabel,
    destinationRouteSelectedItems,
    destinationRouteVisibleItems,
    destinationRouteSelectionForItem,
  };
}

(() => {
  if (typeof document === "undefined") return;

  const ROUTE_SUMMARY_VISIBLE_PILLS = 3;

  function normalizeDiscordMessageStyle() {
    const settings = document.getElementById("destination-settings");
    if (!settings) return;
    const controls = [...settings.querySelectorAll(".destination-message-style")];
    for (const duplicate of controls.slice(1)) duplicate.remove();
  }

  function normalizeDestinationTitle() {
    const title = document.getElementById("destination-dialog-title");
    if (!title) return;
    const editing = Boolean(document.getElementById("destination-id")?.value);
    const name = document.getElementById("destination-name")?.value.trim() || "destination";
    const desired = editing ? `Edit ${name}` : "Add destination";
    if (title.textContent !== desired) title.textContent = desired;
  }

  function refreshSharingStatus() {
    const sharedInput = document.getElementById("destination-shared");
    const sharedField = document.getElementById("destination-shared-field");
    const status = document.getElementById("destination-provider-sharing");
    if (!sharedInput || !status) return;

    status.textContent = sharedInput.checked ? "Shared" : "Private";
    status.classList.toggle("is-private", !sharedInput.checked);
    status.setAttribute("aria-pressed", sharedInput.checked ? "true" : "false");
    status.title = sharedInput.checked
      ? "Make this destination private"
      : "Share this destination with users";
    status.hidden = typeof isAdmin === "function" ? !isAdmin() : Boolean(sharedField?.hidden);
  }

  function normalizeSharedControl() {
    const provider = document.getElementById("destination-provider-card");
    const enabledStatus = document.getElementById("destination-provider-status");
    const sharedField = document.getElementById("destination-shared-field");
    const sharedInput = document.getElementById("destination-shared");
    if (!provider || !enabledStatus || !sharedField || !sharedInput) return;

    sharedField.classList.add("destination-shared-native");

    let actions = document.getElementById("destination-provider-actions");
    if (!actions) {
      actions = document.createElement("div");
      actions.id = "destination-provider-actions";
      actions.className = "destination-provider-actions";
      enabledStatus.before(actions);
      actions.append(enabledStatus);
    }

    let sharing = document.getElementById("destination-provider-sharing");
    if (!sharing) {
      sharing = document.createElement("button");
      sharing.id = "destination-provider-sharing";
      sharing.className = "destination-provider-sharing";
      sharing.type = "button";
      sharing.addEventListener("click", () => {
        sharedInput.checked = !sharedInput.checked;
        sharedInput.dispatchEvent(new Event("change", { bubbles: true }));
        refreshSharingStatus();
      });
      actions.prepend(sharing);
    }

    if (sharedInput.dataset.destinationSharingBound !== "true") {
      sharedInput.dataset.destinationSharingBound = "true";
      sharedInput.addEventListener("change", refreshSharingStatus);
    }

    refreshSharingStatus();
  }

  function normalizeRouteOptionRows() {
    const options = document.getElementById("destination-route-options");
    if (!options) return;
    for (const secondary of options.querySelectorAll(".route-assignment-option-copy small")) {
      secondary.remove();
    }
    for (const status of options.querySelectorAll(".route-assignment-option-state")) {
      status.remove();
    }
  }

  function normalizeRoutingSummary() {
    const routing = document.getElementById("destination-routing-summary");
    if (!routing) return;
    for (const helper of routing.querySelectorAll(".destination-section-copy small")) {
      helper.remove();
    }
  }

  function routeIntegrationName(route) {
    if (typeof routeSourceDescriptor === "function") {
      return routeSourceDescriptor(route.source, route.input_type).integration;
    }
    if (typeof friendlyName === "function") return friendlyName(route.source);
    return String(route.source || "Route");
  }

  function routeSummaryPill(route) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "destination-route-pill";
    button.dataset.routeId = route.id;
    button.title = `Remove ${route.name || routeIntegrationName(route)} from this destination`;
    button.setAttribute("aria-label", button.title);

    const iconWrap = document.createElement("span");
    iconWrap.className = "destination-route-pill-icon";
    if (typeof sourceIcon === "function") iconWrap.append(sourceIcon(route.source));

    const label = document.createElement("span");
    label.className = "destination-route-pill-name";
    label.textContent = routeIntegrationName(route);

    const status = document.createElement("span");
    status.className = `destination-route-pill-status ${route.enabled === false ? "disabled" : "enabled"}`;
    status.textContent = route.enabled === false ? "Disabled" : "Enabled";

    button.append(iconWrap, label, status);
    button.addEventListener("click", () => {
      if (typeof routeAssignmentSelection === "undefined") return;
      routeAssignmentSelection.delete(route.id);
      if (typeof routeAssignmentRenderOptions === "function") {
        routeAssignmentRenderOptions();
      } else {
        refreshRouteAssignmentSummary();
      }
    });
    return button;
  }

  function routeSummaryPillsContainer(summary) {
    let pills = document.getElementById("destination-route-summary-pills");
    if (pills) return pills;
    pills = document.createElement("div");
    pills.id = "destination-route-summary-pills";
    pills.className = "destination-route-summary-pills";
    summary.after(pills);
    return pills;
  }

  function refreshRouteAssignmentSummary() {
    normalizeRoutingSummary();
    const routes = typeof state !== "undefined" && Array.isArray(state.routes)
      ? state.routes
      : [];
    const selectedRoutes = typeof routeAssignmentSelection !== "undefined"
      ? destinationRouteSelectedItems(routes, routeAssignmentSelection)
      : [];
    const selectedCount = selectedRoutes.length;
    const totalCount = routes.length;
    const summary = document.getElementById("destination-route-summary-count");
    const manage = document.getElementById("destination-routes-toggle");

    if (summary) {
      summary.textContent = destinationRouteSummaryLabel(selectedCount, totalCount);
      const pills = routeSummaryPillsContainer(summary);
      pills.replaceChildren();
      const showPills = selectedCount > 0 && selectedCount < totalCount;
      pills.hidden = !showPills;
      if (showPills) {
        const compact = destinationRouteVisibleItems(
          selectedRoutes,
          ROUTE_SUMMARY_VISIBLE_PILLS,
        );
        for (const route of compact.visible) pills.append(routeSummaryPill(route));
        if (compact.remainder > 0) {
          const remainder = document.createElement("span");
          remainder.className = "destination-route-pill-more";
          remainder.textContent = `+${compact.remainder} more`;
          pills.append(remainder);
        }
      }
    }
    if (manage) manage.disabled = totalCount === 0;
  }

  function normalizeRouteDrawer() {
    const manage = document.getElementById("destination-routes-toggle");
    const options = document.getElementById("destination-route-options");

    normalizeRouteOptionRows();

    if (options && options.dataset.destinationSummaryBound !== "true") {
      options.dataset.destinationSummaryBound = "true";
      options.addEventListener("change", () => {
        window.requestAnimationFrame(refreshRouteAssignmentSummary);
      });
    }
    refreshRouteAssignmentSummary();

    if (!manage || manage.dataset.destinationDrawerFixBound === "true") return;

    manage.dataset.destinationDrawerFixBound = "true";
    manage.addEventListener("click", () => {
      const pageX = window.scrollX;
      const pageY = window.scrollY;
      window.requestAnimationFrame(() => {
        const drawer = document.getElementById("destination-routes-fieldset");
        const drawerOptions = document.getElementById("destination-route-options");
        const search = document.getElementById("destination-route-search");
        if (drawer) drawer.scrollTop = 0;
        if (drawerOptions) drawerOptions.scrollTop = 0;
        if (search) search.focus({ preventScroll: true });
        if (window.scrollX !== pageX || window.scrollY !== pageY) {
          window.scrollTo(pageX, pageY);
        }
      });
    });
  }

  function normalizeDestinationEditor() {
    normalizeDiscordMessageStyle();
    normalizeDestinationTitle();
    normalizeSharedControl();
    normalizeRoutingSummary();
    normalizeRouteDrawer();
    refreshRouteAssignmentSummary();
  }

  const baseRouteAssignmentRenderOptions =
    typeof routeAssignmentRenderOptions === "function" ? routeAssignmentRenderOptions : null;
  if (baseRouteAssignmentRenderOptions) {
    routeAssignmentRenderOptions = function routeAssignmentRenderOptionsWithSummary(...args) {
      const result = baseRouteAssignmentRenderOptions(...args);
      normalizeRouteOptionRows();
      refreshRouteAssignmentSummary();
      return result;
    };
  }

  const baseOpenDestination = typeof openDestination === "function" ? openDestination : null;
  if (baseOpenDestination) {
    openDestination = function openDestinationWithFinalEditorPolish(id = "") {
      const item = typeof state !== "undefined" && Array.isArray(state.destinations)
        ? state.destinations.find((candidate) => candidate.id === id) || null
        : null;
      const result = baseOpenDestination(id);
      if (typeof routeAssignmentSelection !== "undefined") {
        routeAssignmentSelection = destinationRouteSelectionForItem(
          item,
          typeof state !== "undefined" ? state.routes : [],
        );
      }
      if (typeof routeAssignmentRenderOptions === "function") routeAssignmentRenderOptions();
      refreshRouteAssignmentSummary();
      window.requestAnimationFrame(normalizeDestinationEditor);
      return result;
    };
  }

  document.addEventListener("DOMContentLoaded", () => {
    const settings = document.getElementById("destination-settings");
    const title = document.getElementById("destination-dialog-title");

    if (settings) {
      new MutationObserver(normalizeDiscordMessageStyle).observe(settings, {
        childList: true,
      });
    }
    if (title) {
      new MutationObserver(normalizeDestinationTitle).observe(title, {
        childList: true,
        characterData: true,
        subtree: true,
      });
    }

    for (const id of [
      "destination-name",
      "destination-type",
      "destination-enabled",
      "destination-shared",
    ]) {
      const control = document.getElementById(id);
      if (!control) continue;
      control.addEventListener(id === "destination-name" ? "input" : "change", () => {
        window.requestAnimationFrame(normalizeDestinationEditor);
      });
    }

    normalizeDestinationEditor();
  });
})();
