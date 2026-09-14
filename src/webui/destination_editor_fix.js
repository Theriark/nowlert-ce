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

  function normalizeRouteDrawer() {
    const manage = document.getElementById("destination-routes-toggle");
    if (!manage || manage.dataset.destinationDrawerFixBound === "true") return;

    manage.dataset.destinationDrawerFixBound = "true";
    manage.addEventListener("click", () => {
      const pageX = window.scrollX;
      const pageY = window.scrollY;
      window.requestAnimationFrame(() => {
        const drawer = document.getElementById("destination-routes-fieldset");
        const options = document.getElementById("destination-route-options");
        const search = document.getElementById("destination-route-search");
        if (drawer) drawer.scrollTop = 0;
        if (options) options.scrollTop = 0;
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
    normalizeRouteDrawer();
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
