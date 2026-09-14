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

  function normalizeSharedControl() {
    const shared = document.getElementById("destination-shared-field");
    const secrets = document.getElementById("destination-secrets");
    const credentials = secrets?.closest("fieldset");
    if (!shared || !credentials || shared.parentElement === credentials) return;
    credentials.append(shared);
  }

  function normalizeDestinationEditor() {
    normalizeDiscordMessageStyle();
    normalizeDestinationTitle();
    normalizeSharedControl();
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

    for (const id of ["destination-name", "destination-type", "destination-enabled"]) {
      const control = document.getElementById(id);
      if (!control) continue;
      control.addEventListener(id === "destination-name" ? "input" : "change", () => {
        window.requestAnimationFrame(normalizeDestinationEditor);
      });
    }

    normalizeDestinationEditor();
  });
})();
