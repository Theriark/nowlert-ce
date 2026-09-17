"use strict";

(() => {
  const privateDestinations = new Map();
  let refreshTimer = 0;

  function privateItem(id) {
    return privateDestinations.get(String(id || "")) || null;
  }

  function schedulePrivateDestinationRefresh() {
    window.clearTimeout(refreshTimer);
    refreshTimer = window.setTimeout(refreshPrivateDestinationCards, 80);
  }

  function decoratePrivateCard(card, item) {
    if (!card || !item) return;
    card.dataset.privateDestinationId = item.id;
    card.dataset.privateDestinationOutputType = item.output_type || "";

    card.querySelector(".field-help")?.remove();

    let actions = card.querySelector(".acceptance-private-actions");
    if (!actions) {
      actions = element("div", {
        className: "resource-actions acceptance-private-actions",
      }, [
        actionButton("Preview", "preview-private-destination", item.id),
        actionButton("Send test", "test-private-destination-card", item.id, "primary"),
      ]);
      card.append(actions);
    }
  }

  async function refreshPrivateDestinationCards() {
    const list = document.getElementById("destination-list");
    if (!list || state.currentView !== "destinations" || !isAdmin()) return;

    try {
      const payload = await request("/destinations");
      const resources = Array.isArray(payload.private_resources)
        ? payload.private_resources
        : [];
      privateDestinations.clear();
      resources.forEach((item) => privateDestinations.set(String(item.id), item));

      const cards = [...list.querySelectorAll(".acceptance-private-destination")];
      cards.forEach((card, index) => decoratePrivateCard(card, resources[index]));
    } catch (_error) {
      // Keep the ordinary Destinations view usable if metadata refresh fails.
    }
  }

  function openPrivatePreview(item) {
    if (!item) return;
    byId("preview-form").reset();
    byId("preview-destination-id").value = item.id;
    byId("preview-title").textContent = `Preview ${item.name || "Private destination"}`;
    byId("preview-source").value = "home_assistant";
    byId("preview-result").hidden = true;
    byId("test-button").hidden = false;
    clearError("preview-error");
    byId("preview-dialog").showModal();
  }

  async function testPrivateDestination(item, button) {
    if (!item) return;
    if (button) button.disabled = true;
    try {
      const response = await request(`/destinations/${item.id}/test`, {
        method: "POST",
        body: { event: cardSampleEvent(item) },
      });
      const delivery = response.result || {};
      if (delivery.success) {
        toast("Destination test delivered successfully.", "success");
      } else {
        toast(
          delivery.safe_error || delivery.error_code || "Destination test failed.",
          "error",
        );
      }
    } catch (error) {
      toast(error.message || "Destination test failed.", "error");
    } finally {
      if (button) button.disabled = false;
    }
  }

  async function runPrivatePreview(event) {
    const id = byId("preview-destination-id")?.value || "";
    const item = privateItem(id);
    if (!item) return;

    event.preventDefault();
    event.stopImmediatePropagation();

    const action = event.submitter && event.submitter.value;
    if (action === "cancel") {
      byId("preview-dialog").close();
      return;
    }
    if (!action) return;

    clearError("preview-error");
    try {
      const response = await request(`/destinations/${id}/${action}`, {
        method: "POST",
        body: { event: sampleEvent() },
      });
      const result = byId("preview-result");
      const outputType = response.preview
        ? response.preview.output_type
        : item.output_type;
      result.textContent = `${OUTPUT_NAMES[outputType] || friendlyName(outputType)} preview\n\n${JSON.stringify(response, null, 2)}`;
      result.hidden = false;

      if (action === "test") {
        const delivery = response.result || {};
        if (delivery.success) {
          toast("Destination test delivered successfully.", "success");
        } else {
          toast(
            delivery.safe_error || delivery.error_code || "Destination test failed.",
            "error",
          );
        }
      }
    } catch (error) {
      showError("preview-error", error);
    }
  }

  document.addEventListener("click", (event) => {
    const target = event.target.closest("[data-action]");
    if (!target) return;
    const action = target.dataset.action;
    const item = privateItem(target.dataset.id);
    if (!item) return;

    if (action === "preview-private-destination") {
      event.preventDefault();
      openPrivatePreview(item);
    } else if (action === "test-private-destination-card") {
      event.preventDefault();
      testPrivateDestination(item, target);
    }
  }, true);

  document.addEventListener("DOMContentLoaded", () => {
    const form = byId("preview-form");
    if (form) form.addEventListener("submit", runPrivatePreview, true);

    const list = document.getElementById("destination-list");
    if (list) {
      new MutationObserver((mutations) => {
        const privateCardChanged = mutations.some((mutation) => (
          [...mutation.addedNodes, ...mutation.removedNodes].some((node) => (
            node.nodeType === Node.ELEMENT_NODE
            && (
              node.matches?.(".acceptance-private-destination")
              || node.querySelector?.(".acceptance-private-destination")
            )
          ))
        ));
        if (privateCardChanged) schedulePrivateDestinationRefresh();
      }).observe(list, { childList: true, subtree: false });
    }

    schedulePrivateDestinationRefresh();
  });
})();
