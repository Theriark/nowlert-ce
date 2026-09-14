"use strict";

if (typeof routeAssignmentInstallStyles === "function") {
  routeAssignmentInstallStyles = function routeAssignmentUseExternalStyles() {};
}

(() => {
  if (typeof routeAssignmentRenderOptions !== "function") return;

  const DESTINATION_EDITOR_META = {
    discord: {
      label: "Discord",
      description: "Send alerts to a Discord channel",
      presentation: "Channel",
    },
    teams: {
      label: "Microsoft Teams",
      description: "Send alerts to a Microsoft Teams channel",
      presentation: "Channel / workflow",
    },
    slack: {
      label: "Slack",
      description: "Send alerts to a Slack channel",
      presentation: "Channel",
    },
    webhook: {
      label: "Generic webhook",
      description: "Send structured events to a webhook endpoint",
      presentation: "Destination label",
    },
    mqtt: {
      label: "MQTT",
      description: "Publish alerts to a bounded MQTT topic",
      presentation: "Destination label",
    },
    ntfy: {
      label: "ntfy",
      description: "Publish alerts to an ntfy topic",
      presentation: "Destination label",
    },
  };

  const REQUIRED_CREDENTIAL_TYPES = new Set(["discord", "teams", "slack", "webhook"]);

  function routeAssignmentBindCurrentSubmit(formId, submitHandler) {
    const form = byId(formId);
    if (!form || form.dataset.routeAssignmentSubmitBound === "true") return;

    form.dataset.routeAssignmentSubmitBound = "true";
    form.addEventListener(
      "submit",
      (event) => {
        event.stopImmediatePropagation();
        submitHandler(event);
      },
      true,
    );
  }

  function destinationEditorMeta() {
    const type = byId("destination-type")?.value || "discord";
    return DESTINATION_EDITOR_META[type] || {
      label: friendlyName(type),
      description: "Deliver routed alerts to this destination",
      presentation: "Channel / destination",
    };
  }

  function destinationEditorCurrentItem() {
    const id = byId("destination-id")?.value || "";
    return (state.destinations || []).find((item) => item.id === id) || null;
  }

  function destinationEditorSetTitle() {
    const title = byId("destination-dialog-title");
    if (!title) return;
    const meta = destinationEditorMeta();
    const name = byId("destination-name")?.value.trim() || "destination";
    title.textContent = byId("destination-id")?.value
      ? `Edit ${name} - ${meta.label}`
      : `Add destination - ${meta.label}`;
  }

  function destinationEditorRefreshProvider() {
    const meta = destinationEditorMeta();
    const icon = byId("destination-provider-icon");
    const description = byId("destination-provider-description");
    const typeSelect = byId("destination-type");
    const enabled = byId("destination-enabled");
    const status = byId("destination-provider-status");
    if (icon) {
      icon.replaceChildren(outputIcon(typeSelect?.value || "discord"));
    }
    if (description) description.textContent = meta.description;
    if (status && enabled) {
      status.textContent = enabled.checked ? "Enabled" : "Disabled";
      status.classList.toggle("is-disabled", !enabled.checked);
      status.setAttribute("aria-pressed", enabled.checked ? "true" : "false");
      status.title = enabled.checked ? "Disable this destination" : "Enable this destination";
    }
    destinationEditorSetTitle();
  }

  function destinationEditorRefreshCredentialState() {
    const item = destinationEditorCurrentItem();
    const status = byId("destination-credential-status");
    if (!status) return;
    const type = byId("destination-type")?.value || "discord";
    const originalType = byId("destination-original-type")?.value || "";
    const typeChanged = Boolean(item && originalType && originalType !== type);
    if (item && item.secret_configured && !typeChanged) {
      status.textContent = "Configured";
      status.className = "destination-credential-status configured";
    } else if (REQUIRED_CREDENTIAL_TYPES.has(type)) {
      status.textContent = "Required";
      status.className = "destination-credential-status required";
    } else {
      status.textContent = "Optional";
      status.className = "destination-credential-status optional";
    }
  }

  function destinationEditorInstallDiscordStyleControl() {
    const settings = byId("destination-settings");
    if (!settings || byId("destination-type")?.value !== "discord") return;
    const native = settings.querySelector('[data-field="components_v2"]');
    if (!native) return;
    const nativeLabel = native.closest("label");
    if (nativeLabel) nativeLabel.classList.add("destination-native-control-hidden");

    const wrapper = element("label", { className: "destination-message-style" });
    const caption = element("span", { text: "Message style" });
    const select = element("select", {
      attributes: { id: "destination-discord-style", "aria-label": "Discord message style" },
    });
    select.append(
      element("option", { value: "modern", text: "Modern Card" }),
      element("option", { value: "classic", text: "Classic Embed" }),
    );
    select.value = native.checked ? "modern" : "classic";
    select.addEventListener("change", () => {
      native.checked = select.value === "modern";
      native.dispatchEvent(new Event("change", { bubbles: true }));
    });
    wrapper.append(caption, select);
    settings.append(wrapper);
  }

  function destinationEditorRefreshDynamicFields() {
    const settings = byId("destination-settings");
    if (!settings) return;
    const presentation = settings.querySelector('[data-field="channel_name"]');
    const presentationLabel = presentation?.closest("label")?.querySelector(":scope > span");
    if (presentationLabel) presentationLabel.textContent = destinationEditorMeta().presentation;
    destinationEditorInstallDiscordStyleControl();
    destinationEditorRefreshCredentialState();
    destinationEditorRefreshProvider();
  }

  function destinationEditorEnsureLayout() {
    const dialog = byId("destination-dialog");
    const form = byId("destination-form");
    if (!dialog || !form) return;
    if (byId("destination-editor-main")) return;

    dialog.classList.add("destination-editor-dialog");
    form.classList.add("destination-editor-form");

    const main = element("div", { className: "destination-editor-main" });
    main.id = "destination-editor-main";

    const hiddenIds = new Set(["destination-id", "destination-original-type"]);
    for (const child of [...form.children]) {
      if (hiddenIds.has(child.id)) continue;
      main.append(child);
    }
    form.append(main);

    const heading = main.querySelector(".modal-heading");
    if (heading) heading.classList.add("destination-editor-heading");

    const primaryFields = byId("destination-name")?.closest(".form-grid");
    if (primaryFields) primaryFields.classList.add("destination-primary-fields");

    const typeSelect = byId("destination-type");
    const typeField = typeSelect?.closest("label");
    if (typeField) typeField.classList.add("destination-type-field");

    const enabled = byId("destination-enabled");
    const enabledField = enabled?.closest("label");
    if (enabledField) enabledField.classList.add("destination-enabled-native");

    const provider = element("section", { className: "destination-provider-card" });
    provider.id = "destination-provider-card";
    const providerIcon = element("span", { className: "destination-provider-icon" });
    providerIcon.id = "destination-provider-icon";
    const providerCopy = element("div", { className: "destination-provider-copy" });
    const providerType = element("label", { className: "destination-provider-type" });
    providerType.append(element("span", { className: "sr-only", text: "Destination type" }));
    if (typeSelect) providerType.append(typeSelect);
    const providerDescription = element("small", { text: "" });
    providerDescription.id = "destination-provider-description";
    providerCopy.append(providerType, providerDescription);
    const providerStatus = element("button", {
      className: "destination-provider-status",
      text: "Enabled",
      type: "button",
      attributes: { id: "destination-provider-status", "aria-pressed": "true" },
    });
    providerStatus.addEventListener("click", () => {
      if (!enabled) return;
      enabled.checked = !enabled.checked;
      enabled.dispatchEvent(new Event("change", { bubbles: true }));
      destinationEditorRefreshProvider();
    });
    provider.append(providerIcon, providerCopy, providerStatus);
    if (heading) heading.after(provider);
    else main.prepend(provider);

    if (typeField && !typeField.querySelector("select")) typeField.remove();

    const settings = byId("destination-settings");
    const connection = settings?.closest("fieldset");
    if (connection) connection.classList.add("destination-connection-card");

    const secrets = byId("destination-secrets");
    const credentials = secrets && secrets.closest("fieldset");
    if (credentials) {
      credentials.classList.add("destination-credentials-card");
      const credentialHeading = element("div", { className: "destination-section-heading" });
      credentialHeading.id = "destination-credentials-heading";
      credentialHeading.append(
        element("span", { className: "destination-section-icon", text: "⌕", attributes: { "aria-hidden": "true" } }),
        element("div", { className: "destination-section-copy" }, [
          element("strong", { text: "Credentials" }),
          element("small", { text: "Stored securely and never returned to this browser." }),
        ]),
      );
      const credentialStatus = element("span", { className: "destination-credential-status", text: "Required" });
      credentialStatus.id = "destination-credential-status";
      credentialHeading.append(credentialStatus);
      credentials.querySelector("legend")?.after(credentialHeading);
    }

    const routing = element("section", { className: "destination-routing-summary" });
    routing.id = "destination-routing-summary";
    const routingIcon = element("span", { className: "destination-section-icon", text: "⌘", attributes: { "aria-hidden": "true" } });
    const routingCopy = element("div", { className: "destination-section-copy" }, [
      element("strong", { text: "Routing" }),
      element("span", { id: "destination-route-summary-count", text: "No routes assigned" }),
      element("small", { id: "destination-route-summary-detail", text: "Choose routes that may deliver to this destination." }),
    ]);
    const manage = element("button", {
      className: "button primary destination-manage-routes",
      text: "Manage routes",
      type: "button",
      attributes: { id: "destination-routes-toggle", "aria-expanded": "false" },
    });
    manage.addEventListener("click", routeAssignmentOpenDrawer);
    routing.append(routingIcon, routingCopy, manage);
    if (credentials) credentials.before(routing);
    else main.append(routing);

    const shared = byId("destination-shared-field");
    if (shared) {
      shared.classList.add("destination-share-row");
      const copy = shared.querySelector(":scope > span");
      if (copy) copy.textContent = "Shared with users";
      if (!shared.querySelector("small")) {
        shared.append(element("small", { text: "Make this destination available to other team members." }));
      }
      const error = byId("destination-error");
      if (error) error.before(shared);
      else main.append(shared);
    }

    const actions = main.querySelector(".modal-actions");
    if (actions) actions.classList.add("destination-editor-actions");

    typeSelect?.addEventListener("change", () => {
      window.requestAnimationFrame(destinationEditorRefreshDynamicFields);
    });
    byId("destination-name")?.addEventListener("input", destinationEditorSetTitle);
    enabled?.addEventListener("change", destinationEditorRefreshProvider);

    destinationEditorRefreshDynamicFields();
  }

  function routeAssignmentCloseDrawer() {
    const drawer = byId("destination-routes-fieldset");
    const form = byId("destination-form");
    const toggle = byId("destination-routes-toggle");
    if (drawer) drawer.hidden = true;
    if (form) form.classList.remove("routes-open");
    if (toggle) toggle.setAttribute("aria-expanded", "false");
  }

  function routeAssignmentOpenDrawer() {
    routeAssignmentEnsureDestinationPicker();
    const drawer = byId("destination-routes-fieldset");
    const popover = byId("destination-routes-popover");
    const form = byId("destination-form");
    const toggle = byId("destination-routes-toggle");
    if (!drawer || !form) return;
    drawer.hidden = false;
    if (popover) popover.hidden = false;
    form.classList.add("routes-open");
    if (toggle) toggle.setAttribute("aria-expanded", "true");
    routeAssignmentRenderOptions();
    window.requestAnimationFrame(() => byId("destination-route-search")?.focus());
  }

  function routeAssignmentSummaryDetail() {
    const selected = (state.routes || []).filter((item) => routeAssignmentSelection.has(item.id));
    const labels = [];
    for (const route of selected) {
      const label = routeSourceDescriptor(route.source, route.input_type).integration;
      if (!labels.includes(label)) labels.push(label);
    }
    if (!labels.length) return "Choose routes that may deliver to this destination.";
    const visible = labels.slice(0, 3);
    const remainder = Math.max(0, labels.length - visible.length);
    return `${visible.join(", ")}${remainder ? ` +${remainder}` : ""}`;
  }

  function routeAssignmentRefreshSummary() {
    const allRoutes = state.routes || [];
    const selected = allRoutes.filter((item) => routeAssignmentSelection.has(item.id)).length;
    const count = byId("destination-routes-count");
    const summary = byId("destination-route-summary-count");
    const detail = byId("destination-route-summary-detail");
    const toggle = byId("destination-routes-toggle");
    if (count) count.textContent = `${selected} of ${allRoutes.length} selected`;
    if (summary) summary.textContent = selected === 0
      ? "No routes assigned"
      : selected === 1 ? "1 route assigned" : `${selected} routes assigned`;
    if (detail) detail.textContent = routeAssignmentSummaryDetail();
    if (toggle) toggle.disabled = allRoutes.length === 0;
  }

  routeAssignmentEnsureDestinationPicker = function routeAssignmentEnsureDestinationPickerStable() {
    const form = byId("destination-form");
    if (!form) return;
    destinationEditorEnsureLayout();

    let picker = byId("destination-routes");
    if (!picker) {
      const secrets = byId("destination-secrets");
      const credentials = secrets && secrets.closest("fieldset");
      if (!credentials) return;

      const fieldset = element("fieldset", { className: "route-assignment-drawer", hidden: true });
      fieldset.id = "destination-routes-fieldset";
      const legend = element("legend", { className: "sr-only", text: "Assigned routes" });

      const drawerHeading = element("div", { className: "route-assignment-drawer-heading" });
      const drawerCopy = element("div");
      drawerCopy.append(
        element("strong", { text: "Assigned routes" }),
        element("small", { text: "Select which routes send alerts to this destination." }),
      );
      const close = element("button", {
        className: "icon-button route-assignment-close",
        text: "×",
        type: "button",
        attributes: { id: "destination-routes-close", "aria-label": "Close assigned routes" },
      });
      close.addEventListener("click", routeAssignmentCloseDrawer);
      drawerHeading.append(drawerCopy, close);

      const count = element("strong", { className: "route-assignment-count", text: "0 of 0 selected" });
      count.id = "destination-routes-count";

      picker = element("div", { className: "route-assignment-picker" });
      picker.id = "destination-routes";
      const popover = element("div", {
        className: "route-assignment-popover",
        hidden: false,
        attributes: { id: "destination-routes-popover" },
      });
      const toolbar = element("div", { className: "route-assignment-toolbar" });
      const search = element("input", {
        type: "search",
        attributes: { id: "destination-route-search", placeholder: "Search routes...", "aria-label": "Search routes" },
      });
      const actions = element("div", { className: "route-assignment-actions" });
      const selectAll = element("button", {
        className: "text-button",
        text: "Select all",
        type: "button",
        attributes: { id: "destination-routes-select-all" },
      });
      const clear = element("button", {
        className: "text-button",
        text: "Clear",
        type: "button",
        attributes: { id: "destination-routes-clear" },
      });
      const options = element("div", { className: "route-assignment-options" });
      options.id = "destination-route-options";
      const footer = element("div", { className: "route-assignment-footer" });
      const done = element("button", {
        className: "button primary full",
        text: "Done",
        type: "button",
        attributes: { id: "destination-routes-done" },
      });
      done.addEventListener("click", routeAssignmentCloseDrawer);

      actions.append(selectAll, clear);
      toolbar.append(search);
      popover.append(toolbar, actions, options);
      picker.append(popover);
      footer.append(done);
      fieldset.append(legend, drawerHeading, count, picker, footer);
      form.append(fieldset);
    }

    if (picker.dataset.routeAssignmentBound === "true") return;
    const search = byId("destination-route-search");
    const selectAll = byId("destination-routes-select-all");
    const clear = byId("destination-routes-clear");
    if (!search || !selectAll || !clear) return;

    picker.dataset.routeAssignmentBound = "true";
    search.addEventListener("input", routeAssignmentRenderOptions);
    selectAll.addEventListener("click", () => {
      routeAssignmentSelection = new Set((state.routes || []).map((item) => item.id));
      routeAssignmentRenderOptions();
    });
    clear.addEventListener("click", () => {
      routeAssignmentSelection.clear();
      routeAssignmentRenderOptions();
    });
  };

  routeAssignmentRenderOptions = function routeAssignmentRenderDrawerOptions() {
    routeAssignmentEnsureDestinationPicker();
    const options = byId("destination-route-options");
    if (!options) return;
    const query = String(byId("destination-route-search")?.value || "").trim().toLowerCase();
    const routes = (state.routes || []).filter((item) => {
      if (!query) return true;
      const descriptor = routeSourceDescriptor(item.source, item.input_type);
      return `${item.name} ${descriptor.integration} ${descriptor.input} ${item.priority_name || ""}`.toLowerCase().includes(query);
    });

    options.replaceChildren();
    if (!routes.length) {
      options.append(element("div", {
        className: "route-assignment-empty",
        text: (state.routes || []).length ? "No matching routes." : "No routes are available yet.",
      }));
    }

    for (const route of routes) {
      const descriptor = routeSourceDescriptor(route.source, route.input_type);
      const checkbox = element("input", { type: "checkbox", value: route.id });
      checkbox.checked = routeAssignmentSelection.has(route.id);
      checkbox.setAttribute("aria-label", `Assign ${route.name}`);
      const icon = element("span", { className: "route-assignment-source-icon" }, sourceIcon(route.source));
      const status = element("small", {
        className: `route-assignment-option-state ${route.enabled ? "enabled" : "disabled"}`,
        text: route.enabled ? "Enabled" : "Disabled",
      });
      const leading = element("span", { className: "route-assignment-option-leading" }, [checkbox, icon]);
      const row = element("label", { className: "route-assignment-option" }, [
        leading,
        element("span", { className: "route-assignment-option-copy" }, [
          element("strong", { text: route.name }),
          element("small", { text: `${descriptor.integration} · ${descriptor.input} · ${capitalize(route.priority_name || "normal")}` }),
        ]),
        status,
      ]);
      checkbox.addEventListener("change", () => {
        if (checkbox.checked) routeAssignmentSelection.add(route.id);
        else routeAssignmentSelection.delete(route.id);
        routeAssignmentRefreshSummary();
      });
      options.append(row);
    }
    routeAssignmentRefreshSummary();
  };

  const destinationEditorBaseRenderDestinationFields = renderDestinationFields;
  renderDestinationFields = function renderDestinationFieldsWithEditor(settings = {}) {
    destinationEditorBaseRenderDestinationFields(settings);
    destinationEditorRefreshDynamicFields();
  };

  const destinationEditorBaseOpenDestination = openDestination;
  openDestination = function openDestinationWithEditor(id = "") {
    destinationEditorBaseOpenDestination(id);
    destinationEditorEnsureLayout();
    routeAssignmentEnsureDestinationPicker();
    routeAssignmentCloseDrawer();
    destinationEditorRefreshDynamicFields();
    routeAssignmentRefreshSummary();
  };

  document.addEventListener("DOMContentLoaded", () => {
    destinationEditorEnsureLayout();
    routeAssignmentEnsureDestinationPicker();
    routeAssignmentBindCurrentSubmit(
      "destination-form",
      (event) => saveDestination(event),
    );
    routeAssignmentBindCurrentSubmit(
      "route-form",
      (event) => saveRoute(event),
    );
  });
})();
