"use strict";

if (typeof routeAssignmentInstallStyles === "function") {
  routeAssignmentInstallStyles = function routeAssignmentUseExternalStyles() {};
}

(() => {
  if (typeof routeAssignmentRenderOptions !== "function") return;

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

  routeAssignmentEnsureDestinationPicker = function routeAssignmentEnsureDestinationPickerStable() {
    const form = byId("destination-form");
    if (!form) return;

    let picker = byId("destination-routes");
    if (!picker) {
      const secrets = byId("destination-secrets");
      const credentials = secrets && secrets.closest("fieldset");
      if (!credentials) return;

      const fieldset = element("fieldset", { className: "route-assignment-fieldset" });
      fieldset.id = "destination-routes-fieldset";
      const legend = element("legend", { text: "Routes" });
      const help = element("p", {
        className: "field-help",
        text: "Select which reusable routes may deliver notifications to this destination.",
      });
      picker = element("div", { className: "route-assignment-picker" });
      picker.id = "destination-routes";
      const toggle = element("button", {
        className: "button secondary route-assignment-toggle",
        text: "No routes selected",
        type: "button",
        attributes: { id: "destination-routes-toggle", "aria-expanded": "false" },
      });
      const popover = element("div", {
        className: "route-assignment-popover",
        hidden: true,
        attributes: { id: "destination-routes-popover" },
      });
      const toolbar = element("div", { className: "route-assignment-toolbar" });
      const search = element("input", {
        type: "search",
        attributes: { id: "destination-route-search", placeholder: "Search routes", "aria-label": "Search routes" },
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

      actions.append(selectAll, clear);
      toolbar.append(search, actions);
      popover.append(toolbar, options);
      picker.append(toggle, popover);
      fieldset.append(legend, help, picker);
      credentials.before(fieldset);
    }

    if (picker.dataset.routeAssignmentBound === "true") return;
    const toggle = byId("destination-routes-toggle");
    const popover = byId("destination-routes-popover");
    const search = byId("destination-route-search");
    const selectAll = byId("destination-routes-select-all");
    const clear = byId("destination-routes-clear");
    if (!toggle || !popover || !search || !selectAll || !clear) return;

    picker.dataset.routeAssignmentBound = "true";
    toggle.addEventListener("click", () => {
      popover.hidden = !popover.hidden;
      toggle.setAttribute("aria-expanded", popover.hidden ? "false" : "true");
      if (!popover.hidden) search.focus();
    });
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

  document.addEventListener("DOMContentLoaded", () => {
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
