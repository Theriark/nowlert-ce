"use strict";

const DESTINATION_ROUTE_SUMMARY_PILL_LIMIT = 3;

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

function destinationRouteVisibleItems(selectedRoutes, limit = DESTINATION_ROUTE_SUMMARY_PILL_LIMIT) {
  const items = Array.isArray(selectedRoutes) ? selectedRoutes : [];
  const safeLimit = Math.max(0, Number(limit) || 0);
  return {
    visible: items.slice(0, safeLimit),
    overflow: items.slice(safeLimit),
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

function destinationRouteSummaryModel(routes, selectedIds, limit = DESTINATION_ROUTE_SUMMARY_PILL_LIMIT) {
  const allRoutes = Array.isArray(routes) ? routes : [];
  const selectedRoutes = destinationRouteSelectedItems(allRoutes, selectedIds);
  const compact = destinationRouteVisibleItems(selectedRoutes, limit);
  return {
    label: destinationRouteSummaryLabel(selectedRoutes.length, allRoutes.length),
    selectedRoutes,
    visible: compact.visible,
    overflow: compact.overflow,
    remainder: compact.remainder,
    showPills: selectedRoutes.length > 0 && selectedRoutes.length < allRoutes.length,
  };
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    destinationRouteSummaryLabel,
    destinationRouteSelectedItems,
    destinationRouteVisibleItems,
    destinationRouteSelectionForItem,
    destinationRouteSummaryModel,
  };
}

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
  let routeAssignmentMoreMenuOpen = false;
  let routeAssignmentMoreMenuDismissalBound = false;

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
      element("span", { text: "No routes assigned", attributes: { id: "destination-route-summary-count" } }),
      element("small", { text: "Choose routes that may deliver to this destination.", attributes: { id: "destination-route-summary-detail" } }),
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

  function routeAssignmentIntegrationName(route) {
    return routeSourceDescriptor(route.source, route.input_type).integration;
  }

  function routeAssignmentInstallMoreMenuStyles() {
    if (byId("destination-route-more-menu-style")) return;
    const style = document.createElement("style");
    style.id = "destination-route-more-menu-style";
    style.textContent = `
      .destination-route-more-wrap {
        display: inline-flex;
        position: relative;
      }

      button.destination-route-pill-more {
        cursor: pointer;
        font: inherit;
      }

      button.destination-route-pill-more:hover,
      button.destination-route-pill-more:focus-visible {
        border-color: rgba(244, 197, 66, 0.58);
        box-shadow: 0 0 0 2px rgba(244, 197, 66, 0.08);
        color: var(--text, #f2ebdd);
        outline: 0;
      }

      .destination-route-more-menu {
        background: var(--destination-surface-raised, #151d25);
        border: 1px solid var(--destination-border);
        border-radius: 9px;
        box-shadow: 0 14px 32px rgba(0, 0, 0, 0.38);
        display: grid;
        gap: 4px;
        max-height: min(280px, 45vh);
        min-width: 250px;
        overflow-y: auto;
        padding: 6px;
        position: absolute;
        right: 0;
        top: calc(100% + 7px);
        z-index: 30;
      }

      .destination-route-more-menu[hidden] {
        display: none !important;
      }

      .destination-route-more-menu .destination-route-pill {
        justify-content: flex-start;
        max-width: none;
        width: 100%;
      }

      .destination-route-more-menu .destination-route-pill-name {
        flex: 1 1 auto;
        text-align: left;
      }
    `;
    document.head.append(style);
  }

  function routeAssignmentCloseMoreMenu(restoreFocus = false) {
    routeAssignmentMoreMenuOpen = false;
    const menu = byId("destination-route-more-menu");
    const toggle = byId("destination-route-more-toggle");
    if (menu) menu.hidden = true;
    if (toggle) {
      toggle.setAttribute("aria-expanded", "false");
      if (restoreFocus) toggle.focus();
    }
  }

  function routeAssignmentBindMoreMenuDismissal() {
    if (routeAssignmentMoreMenuDismissalBound) return;
    routeAssignmentMoreMenuDismissalBound = true;
    document.addEventListener("click", (event) => {
      if (!routeAssignmentMoreMenuOpen) return;
      const wrapper = byId("destination-route-more-menu")?.closest(".destination-route-more-wrap");
      if (wrapper && !wrapper.contains(event.target)) routeAssignmentCloseMoreMenu();
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && routeAssignmentMoreMenuOpen) {
        routeAssignmentCloseMoreMenu(true);
      }
    });
  }

  function routeAssignmentSummaryPillsContainer(summary) {
    let pills = byId("destination-route-summary-pills");
    if (pills) return pills;
    pills = element("div", { className: "destination-route-summary-pills" });
    pills.id = "destination-route-summary-pills";
    summary.after(pills);
    return pills;
  }

  function routeAssignmentSummaryPill(route, extraClass = "") {
    const label = routeAssignmentIntegrationName(route);
    const button = element("button", {
      className: `destination-route-pill${extraClass ? ` ${extraClass}` : ""}`,
      type: "button",
      attributes: {
        "aria-label": `Remove ${route.name || label} from this destination`,
        title: `Remove ${route.name || label} from this destination`,
      },
      dataset: { routeId: route.id },
    });
    const icon = element("span", { className: "destination-route-pill-icon" }, sourceIcon(route.source));
    const name = element("span", { className: "destination-route-pill-name", text: label });
    const status = element("span", {
      className: `destination-route-pill-status ${route.enabled === false ? "disabled" : "enabled"}`,
      text: route.enabled === false ? "Disabled" : "Enabled",
    });
    button.append(icon, name, status);
    button.addEventListener("click", () => {
      routeAssignmentSelection.delete(route.id);
      routeAssignmentRenderOptions();
    });
    return button;
  }

  function routeAssignmentSummaryMoreMenu(model) {
    routeAssignmentInstallMoreMenuStyles();
    routeAssignmentBindMoreMenuDismissal();

    const wrapper = element("span", { className: "destination-route-more-wrap" });
    const trigger = element("button", {
      className: "destination-route-pill-more",
      text: `+${model.remainder} more`,
      type: "button",
      attributes: {
        id: "destination-route-more-toggle",
        "aria-controls": "destination-route-more-menu",
        "aria-expanded": routeAssignmentMoreMenuOpen ? "true" : "false",
        "aria-haspopup": "menu",
      },
    });
    const menu = element("div", {
      className: "destination-route-more-menu",
      hidden: !routeAssignmentMoreMenuOpen,
      attributes: { id: "destination-route-more-menu", role: "menu" },
    });

    for (const route of model.overflow) {
      const item = routeAssignmentSummaryPill(route, "destination-route-more-item");
      item.setAttribute("role", "menuitem");
      menu.append(item);
    }

    trigger.addEventListener("click", (event) => {
      event.stopPropagation();
      routeAssignmentMoreMenuOpen = !routeAssignmentMoreMenuOpen;
      menu.hidden = !routeAssignmentMoreMenuOpen;
      trigger.setAttribute("aria-expanded", routeAssignmentMoreMenuOpen ? "true" : "false");
    });

    wrapper.append(trigger, menu);
    return wrapper;
  }

  function routeAssignmentRefreshSummary() {
    const allRoutes = state.routes || [];
    const model = destinationRouteSummaryModel(
      allRoutes,
      routeAssignmentSelection,
      DESTINATION_ROUTE_SUMMARY_PILL_LIMIT,
    );
    const count = byId("destination-routes-count");
    const summary = byId("destination-route-summary-count");
    const detail = byId("destination-route-summary-detail");
    const toggle = byId("destination-routes-toggle");

    if (!model.showPills || model.remainder === 0) routeAssignmentMoreMenuOpen = false;
    if (count) count.textContent = `${model.selectedRoutes.length} of ${allRoutes.length} selected`;
    if (summary) {
      summary.textContent = model.label;
      const pills = routeAssignmentSummaryPillsContainer(summary);
      pills.replaceChildren();
      pills.hidden = !model.showPills;
      if (model.showPills) {
        for (const route of model.visible) pills.append(routeAssignmentSummaryPill(route));
        if (model.remainder > 0) pills.append(routeAssignmentSummaryMoreMenu(model));
      }
    }
    if (detail) detail.textContent = "";
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
    const item = (state.destinations || []).find((candidate) => candidate.id === id) || null;
    destinationEditorBaseOpenDestination(id);
    destinationEditorEnsureLayout();
    routeAssignmentEnsureDestinationPicker();
    routeAssignmentSelection = destinationRouteSelectionForItem(item, state.routes || []);
    routeAssignmentMoreMenuOpen = false;
    routeAssignmentRenderOptions();
    routeAssignmentCloseDrawer();
    destinationEditorRefreshDynamicFields();
    routeAssignmentRefreshSummary();
  };

  document.addEventListener("DOMContentLoaded", () => {
    destinationEditorEnsureLayout();
    routeAssignmentEnsureDestinationPicker();
    routeAssignmentBindMoreMenuDismissal();
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
