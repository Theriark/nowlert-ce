"use strict";

(() => {
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

  function routeAssignmentCountFromDrawer() {
    const count = document.getElementById("destination-routes-count");
    const match = String(count?.textContent || "").match(/^(\d+)\s+of\s+\d+\s+selected$/i);
    if (match) return Number(match[1]);
    const checkboxes = [
      ...document.querySelectorAll('#destination-route-options input[type="checkbox"]'),
    ];
    if (checkboxes.length) {
      return checkboxes.filter((checkbox) => checkbox.checked).length;
    }
    if (
      typeof routeAssignmentSelection !== "undefined"
      && routeAssignmentSelection instanceof Set
    ) {
      return routeAssignmentSelection.size;
    }
    return 0;
  }

  function refreshRouteAssignmentSummary() {
    const routes = typeof state !== "undefined" && Array.isArray(state.routes)
      ? state.routes
      : [];
    const selected = routeAssignmentCountFromDrawer();
    const summary = document.getElementById("destination-route-summary-count");
    const manage = document.getElementById("destination-routes-toggle");

    if (summary) {
      summary.textContent = selected === 0
        ? "No routes assigned"
        : selected === 1
          ? "1 route assigned"
          : `${selected} routes assigned`;
    }
    if (manage) manage.disabled = routes.length === 0;
  }

  function bindRouteCountSummary() {
    const count = document.getElementById("destination-routes-count");
    if (!count || count.dataset.destinationSummaryObserved === "true") return;
    count.dataset.destinationSummaryObserved = "true";
    new MutationObserver(refreshRouteAssignmentSummary).observe(count, {
      childList: true,
      characterData: true,
      subtree: true,
    });
  }

  function normalizeRouteDrawer() {
    const manage = document.getElementById("destination-routes-toggle");
    const options = document.getElementById("destination-route-options");

    normalizeRouteOptionRows();
    bindRouteCountSummary();

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
    document.getElementById("destination-route-summary-detail")?.remove();
    normalizeRouteDrawer();
    refreshRouteAssignmentSummary();
  }

  const baseRouteAssignmentRenderOptions =
    typeof routeAssignmentRenderOptions === "function" ? routeAssignmentRenderOptions : null;
  if (baseRouteAssignmentRenderOptions) {
    routeAssignmentRenderOptions = function routeAssignmentRenderOptionsWithSummary(...args) {
      const result = baseRouteAssignmentRenderOptions(...args);
      normalizeRouteOptionRows();
      bindRouteCountSummary();
      refreshRouteAssignmentSummary();
      return result;
    };
  }

  const baseOpenDestination = typeof openDestination === "function" ? openDestination : null;
  if (baseOpenDestination) {
    openDestination = function openDestinationWithFinalEditorPolish(id = "") {
      const result = baseOpenDestination(id);
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
