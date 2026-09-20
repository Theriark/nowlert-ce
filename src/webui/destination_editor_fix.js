"use strict";

(() => {
  if (typeof document === "undefined") return;

  const REMOVED_DESTINATION_TYPES = new Set(["mqtt", "ntfy"]);
  const WEBHOOK_ADVANCED_FIELDS = new Set([
    "method",
    "timeout_seconds",
    "headers",
    "body_template",
    "sign_hmac",
    "allow_private_network",
  ]);
  const WEBHOOK_ADVANCED_SECRETS = new Set(["hmac_secret", "headers"]);

  function normalizeSupportedDestinationTypes() {
    const typeSelect = document.getElementById("destination-type");
    if (typeSelect) {
      for (const option of [...typeSelect.options]) {
        if (REMOVED_DESTINATION_TYPES.has(option.value)) option.remove();
      }
    }

    if (typeof OUTPUT_NAMES === "object" && OUTPUT_NAMES) {
      for (const type of REMOVED_DESTINATION_TYPES) delete OUTPUT_NAMES[type];
    }
    if (typeof OUTPUT_ICONS === "object" && OUTPUT_ICONS) {
      for (const type of REMOVED_DESTINATION_TYPES) delete OUTPUT_ICONS[type];
    }

    const copy = document.querySelector("#view-destinations .section-toolbar p");
    if (copy) {
      copy.textContent = "Configure delivery targets for Discord, Microsoft Teams, Slack, and generic webhooks.";
    }
  }

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

  function webhookStoredStyle() {
    const id = document.getElementById("destination-id")?.value || "";
    if (!id || typeof state !== "object" || !Array.isArray(state.destinations)) {
      return "modern";
    }
    const destination = state.destinations.find((item) => item.id === id);
    return destination?.settings?.message_style === "classic" ? "classic" : "modern";
  }

  function normalizeWebhookSettings() {
    const settings = document.getElementById("destination-settings");
    const type = document.getElementById("destination-type")?.value || "";
    if (!settings || type !== "webhook") return;

    const existingStyle = settings.querySelector('[data-field="message_style"]')?.value;
    const channelInput = settings.querySelector('[data-field="channel_name"]');
    const channel = channelInput?.closest("label");
    const existingStyleField = settings.querySelector(".destination-message-style");
    if (!channel) return;

    const alreadySimplified = (
      settings.dataset.destinationWebhookSimplified === "true"
      && settings.children.length === 2
      && channel.parentElement === settings
      && existingStyleField?.parentElement === settings
      && ![...settings.querySelectorAll("[data-field]")].some(
        (input) => WEBHOOK_ADVANCED_FIELDS.has(input.dataset.field),
      )
    );
    if (alreadySimplified) return;

    for (const input of [...settings.querySelectorAll("[data-field]")]) {
      if (WEBHOOK_ADVANCED_FIELDS.has(input.dataset.field)) input.closest("label")?.remove();
    }
    for (const group of [...settings.querySelectorAll(".destination-provider-settings-group")]) {
      for (const label of [...group.querySelectorAll("label")]) settings.append(label);
      group.remove();
    }

    const channelTitle = channel.querySelector("span");
    if (channelTitle) channelTitle.textContent = "Destination label";
    channel.className = "";

    let styleField = settings.querySelector(".destination-message-style");
    if (!styleField) {
      styleField = document.createElement("label");
      styleField.className = "destination-message-style";
      const title = document.createElement("span");
      title.textContent = "Message style";
      const select = document.createElement("select");
      select.dataset.field = "message_style";
      const modern = document.createElement("option");
      modern.value = "modern";
      modern.textContent = "Modern Card";
      const classic = document.createElement("option");
      classic.value = "classic";
      classic.textContent = "Classic Card";
      select.append(modern, classic);
      styleField.append(title, select);
    }

    const styleSelect = styleField.querySelector('[data-field="message_style"]');
    if (styleSelect) {
      styleSelect.value = existingStyle === "classic" ? "classic" : webhookStoredStyle();
    }

    settings.replaceChildren(channel, styleField);
    settings.dataset.destinationWebhookSimplified = "true";

    const help = document.getElementById("destination-help");
    if (help) {
      help.textContent = "Choose how Nowlert prepares the notification payload for this webhook.";
    }
  }

  function normalizeWebhookCredentials() {
    const type = document.getElementById("destination-type")?.value || "";
    if (type !== "webhook") return;
    const secrets = document.getElementById("destination-secrets");
    const credentials = secrets?.closest("fieldset");
    const routing = document.getElementById("destination-routing-summary");
    if (!secrets || !credentials || !routing) return;

    const urlInput = secrets.querySelector('[data-field="url"]');
    const urlField = urlInput?.closest("label");
    if (!urlField) return;

    for (const input of [...secrets.querySelectorAll("[data-field]")]) {
      if (WEBHOOK_ADVANCED_SECRETS.has(input.dataset.field)) input.closest("label")?.remove();
    }
    secrets.replaceChildren(urlField);
    const urlTitle = urlField.querySelector("span");
    if (urlTitle) urlTitle.textContent = "Webhook URL";

    const heading = document.getElementById("destination-credentials-heading");
    const title = heading?.querySelector(".destination-section-copy strong");
    if (title) title.textContent = "Credentials";
    if (credentials.previousElementSibling !== routing) routing.after(credentials);
  }

  function normalizeWebhookEditor() {
    normalizeWebhookSettings();
    normalizeWebhookCredentials();
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
    status.hidden = Boolean(sharedField?.hidden);
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
    normalizeSupportedDestinationTypes();
    normalizeDestinationProviderIcons();
    normalizeDiscordMessageStyle();
    normalizeSlackMessageOptions();
    normalizeWebhookEditor();
    normalizeDestinationTitle();
    normalizeSharedControl();
    normalizeDestinationFooter();
    normalizeRoutingSummary();
    normalizeRouteDrawer();
  }

  const baseRenderDestinationFields = typeof renderDestinationFields === "function"
    ? renderDestinationFields
    : null;
  if (baseRenderDestinationFields) {
    renderDestinationFields = function renderDestinationFieldsWithWebhookTemplate(settings = {}) {
      const result = baseRenderDestinationFields(settings);
      normalizeSlackMessageOptions();
      normalizeWebhookEditor();
      return result;
    };
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

    normalizeSupportedDestinationTypes();

    if (settings) {
      new MutationObserver(() => {
        window.requestAnimationFrame(() => {
          normalizeDiscordMessageStyle();
          normalizeSlackMessageOptions();
          normalizeWebhookEditor();
        });
      }).observe(settings, { childList: true });
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
