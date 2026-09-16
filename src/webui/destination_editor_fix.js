"use strict";

(() => {
  if (typeof document === "undefined") return;

  const LONG_PROVIDER_LAYOUTS = {
    webhook: [
      { title: "Request", keys: ["channel_name", "method"] },
      {
        title: "Payload & security",
        keys: ["timeout_seconds", "headers", "body_template", "sign_hmac", "allow_private_network"],
      },
    ],
    mqtt: [
      { title: "Broker & topic", keys: ["host", "port", "topic"] },
      {
        title: "Delivery options",
        keys: ["channel_name", "qos", "keepalive_seconds", "client_id", "tls", "retain", "allow_private_network"],
      },
    ],
    ntfy: [
      { title: "Server & topic", keys: ["server", "topic", "priority"] },
      {
        title: "Message options",
        keys: ["channel_name", "tags", "title", "timeout_seconds", "include_action", "allow_private_network"],
      },
    ],
  };

  function normalizeDestinationProviderIcons() {
    if (typeof OUTPUT_ICONS !== "object" || !OUTPUT_ICONS) return;
    OUTPUT_ICONS.teams = "/ui/icons/routing-teams.svg";
    OUTPUT_ICONS.slack = "/ui/icons/routing-slack.svg";

    const type = document.getElementById("destination-type")?.value || "discord";
    const icon = document.getElementById("destination-provider-icon");
    if (icon && typeof outputIcon === "function") {
      icon.replaceChildren(outputIcon(type));
    }
  }

  function normalizeDiscordMessageStyle() {
    const settings = document.getElementById("destination-settings");
    if (!settings) return;
    const controls = [...settings.querySelectorAll(".destination-message-style")];
    for (const duplicate of controls.slice(1)) duplicate.remove();
  }

  function normalizeSlackMessageOptions() {
    const settings = document.getElementById("destination-settings");
    const type = document.getElementById("destination-type")?.value || "";
    if (!settings || type !== "slack") return;

    const input = settings.querySelector('[data-field="include_metadata"]');
    const label = input?.closest("label");
    if (!label) return;

    label.classList.add("destination-message-options", "wide");

    if (!label.querySelector(".destination-message-options-title")) {
      const heading = document.createElement("strong");
      heading.className = "destination-message-options-title";
      heading.textContent = "Message options";
      label.prepend(heading);
    }

    if (!label.querySelector(".destination-message-options-help")) {
      const helper = document.createElement("small");
      helper.className = "destination-message-options-help";
      helper.textContent = "Controls Slack message detail; it does not filter events.";
      label.append(helper);
    }
  }

  function normalizeLongDestinationProviderLayout() {
    const settings = document.getElementById("destination-settings");
    const type = document.getElementById("destination-type")?.value || "";
    const layout = LONG_PROVIDER_LAYOUTS[type];
    if (!settings || !layout) return;
    if (settings.querySelector(".destination-provider-settings-group")) return;

    for (const section of layout) {
      const group = document.createElement("fieldset");
      group.className = "destination-credentials-card destination-provider-settings-group wide";

      const heading = document.createElement("div");
      heading.className = "destination-section-heading";
      const copy = document.createElement("div");
      copy.className = "destination-section-copy";
      const title = document.createElement("strong");
      title.textContent = section.title;
      copy.append(title);
      heading.append(copy);

      const groupFields = document.createElement("div");
      groupFields.className = "form-grid";
      for (const key of section.keys) {
        const input = settings.querySelector(`[data-field="${key}"]`);
        const label = input?.closest("label");
        if (label) groupFields.append(label);
      }

      if (!groupFields.children.length) continue;
      group.append(heading, groupFields);
      settings.append(group);
    }
  }

  function normalizeDestinationFooter() {
    const form = document.getElementById("destination-form");
    const main = document.getElementById("destination-editor-main");
    const actions = form?.querySelector(".destination-editor-actions");
    if (!form || !main || !actions) return;

    actions.classList.add("destination-editor-footer-fixed");
    if (actions.parentElement !== form) form.append(actions);
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

  function normalizeRouteDrawer() {
    const manage = document.getElementById("destination-routes-toggle");
    const options = document.getElementById("destination-route-options");

    normalizeRouteOptionRows();

    if (options && options.dataset.destinationPolishBound !== "true") {
      options.dataset.destinationPolishBound = "true";
      new MutationObserver(normalizeRouteOptionRows).observe(options, {
        childList: true,
        subtree: true,
      });
    }

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
    normalizeDestinationProviderIcons();
    normalizeDiscordMessageStyle();
    normalizeSlackMessageOptions();
    normalizeLongDestinationProviderLayout();
    normalizeDestinationTitle();
    normalizeSharedControl();
    normalizeDestinationFooter();
    normalizeRoutingSummary();
    normalizeRouteDrawer();
  }

  const baseOpenDestination = typeof openDestination === "function" ? openDestination : null;
  if (baseOpenDestination) {
    openDestination = function openDestinationWithVisualPolish(id = "") {
      const result = baseOpenDestination(id);
      window.requestAnimationFrame(normalizeDestinationEditor);
      return result;
    };
  }

  document.addEventListener("DOMContentLoaded", () => {
    const settings = document.getElementById("destination-settings");
    const title = document.getElementById("destination-dialog-title");

    if (settings) {
      new MutationObserver(() => {
        normalizeDiscordMessageStyle();
        normalizeLongDestinationProviderLayout();
      }).observe(settings, {
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
