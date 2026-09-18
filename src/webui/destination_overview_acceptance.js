"use strict";

(() => {
  const privateDestinations = new Map();
  let refreshTimer = 0;

  function privateItem(id) {
    const key = String(id || "");
    const cached = privateDestinations.get(key);
    if (cached) return cached;
    return (state.privateDestinations || []).find(
      (item) => String(item?.id || "") === key,
    ) || null;
  }

  function syncPrivateDestinationCards(resources) {
    const list = document.getElementById("destination-list");
    if (!list) return;
    const items = Array.isArray(resources) ? resources : [];
    privateDestinations.clear();
    items.forEach((item) => privateDestinations.set(String(item.id), item));
    const cards = [...list.querySelectorAll(".acceptance-private-destination")];
    cards.forEach((card, index) => decoratePrivateCard(card, items[index]));
  }

  function schedulePrivateDestinationRefresh() {
    window.clearTimeout(refreshTimer);
    syncPrivateDestinationCards(state.privateDestinations);
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
      state.privateDestinations = resources;
      syncPrivateDestinationCards(resources);
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

/* Selected Delivery History workbench acceptance. */
(() => {
  let selectedDeliveryId = "";
  let filtersBound = false;
  const filters = {
    source: "",
    severity: "",
    outcome: "",
    range: "7d",
    sort: "newest",
  };

  const originalRenderDeliveries = renderDeliveries;
  const originalLoadDeliveryPage =
    typeof qaLoadDeliveryPage === "function" ? qaLoadDeliveryPage : null;

  function deliveryId(item) {
    return String(item?.id || item?.delivery_id || "");
  }

  function deliveryTimestamp(item) {
    const value = item?.completed_at || item?.created_at || 0;
    const number = Number(value);
    if (!Number.isFinite(number) || number <= 0) return 0;
    return number < 10_000_000_000 ? number * 1000 : number;
  }

  function deliveryTitle(item) {
    const event = item?.event_name || item?.title || "Untitled event";
    if (item?.device_name) return `${item.device_name} | ${event}`;
    return event;
  }

  function deliveryDescription(item) {
    return String(
      item?.event_description
      || item?.safe_error
      || item?.error_code
      || item?.title
      || "No message was recorded for this delivery attempt.",
    );
  }

  function deliveryTone(value) {
    const normalized = String(value || "").toLowerCase();
    if (["failure", "failed", "error", "critical", "severe", "high"].includes(normalized)) {
      return "danger";
    }
    if (["warning", "warn", "pending", "retrying"].includes(normalized)) {
      return "warning";
    }
    if (["success", "delivered", "ok", "healthy"].includes(normalized)) {
      return "success";
    }
    return "information";
  }

  function selectControl(id, label, options) {
    const wrapper = element("label", { className: "delivery-history-select" });
    wrapper.append(element("span", { className: "sr-only", text: label }));
    const select = element("select", { attributes: { id, "aria-label": label } });
    for (const [value, text] of options) {
      select.append(element("option", { value, text }));
    }
    wrapper.append(select);
    return wrapper;
  }

  function setSelectOptions(select, values, emptyLabel) {
    if (!select) return;
    const current = select.value;
    const normalized = [...new Set(values.filter(Boolean).map((value) => String(value)))];
    normalized.sort((left, right) => left.localeCompare(right));
    if (current && !normalized.includes(current)) normalized.unshift(current);
    select.replaceChildren(element("option", { value: "", text: emptyLabel }));
    for (const value of normalized) {
      select.append(element("option", { value, text: friendlyName(value) }));
    }
    select.value = current;
  }

  function ensureLayout() {
    const view = byId("view-deliveries");
    if (!view || byId("delivery-history-workbench")) return;

    const search = byId("delivery-search");
    const searchField = search?.closest(".search-field") || null;
    const legacyPanel = view.querySelector(":scope > .professional-timeline-panel");
    const list = byId("delivery-list");
    if (!search || !searchField || !legacyPanel || !list) return;

    view.classList.add("delivery-history-revamp");
    search.placeholder = "Search source, title, message...";

    const controls = element("div", {
      className: "delivery-history-filters",
      attributes: { id: "delivery-history-filters", "aria-label": "Delivery history filters" },
    });
    controls.append(searchField);
    controls.append(
      selectControl("delivery-history-source-filter", "Filter by source", [["", "All sources"]]),
      selectControl("delivery-history-severity-filter", "Filter by severity", [["", "All severities"]]),
      selectControl("delivery-history-outcome-filter", "Filter by outcome", [["", "All outcomes"]]),
      selectControl("delivery-history-range-filter", "Filter by date range", [
        ["all", "All dates"],
        ["1d", "Last 24 hours"],
        ["7d", "Last 7 days"],
        ["30d", "Last 30 days"],
      ]),
    );

    const clear = element("button", {
      className: "button secondary delivery-history-clear",
      text: "Clear filters",
      type: "button",
      attributes: { id: "delivery-history-clear-filters" },
    });
    controls.append(clear);

    const workbench = element("div", {
      className: "delivery-history-workbench",
      attributes: { id: "delivery-history-workbench" },
    });

    const listPanel = element("section", {
      className: "delivery-history-list-panel",
      attributes: { "aria-label": "Delivery events" },
    });
    const listHeader = element("div", { className: "delivery-history-list-heading" });
    const listTitle = element("div", {}, [
      element("strong", { text: "Delivery events" }),
      element("span", { attributes: { id: "delivery-history-total" }, text: "0 events" }),
    ]);
    const sort = selectControl("delivery-history-sort", "Sort deliveries", [
      ["newest", "Newest first"],
      ["oldest", "Oldest first"],
    ]);
    listHeader.append(listTitle, sort);

    const columns = element("div", { className: "delivery-history-columns", attributes: { "aria-hidden": "true" } }, [
      element("span", { text: "Source" }),
      element("span", { text: "Title" }),
      element("span", { text: "Severity" }),
      element("span", { text: "Outcome" }),
      element("span", { text: "Time" }),
      element("span", { text: "" }),
    ]);
    const listScroll = element("div", { className: "delivery-history-list-scroll" });
    list.className = "delivery-history-list";
    listScroll.append(list);
    const listFooter = element("div", {
      className: "delivery-history-list-footer",
      attributes: { id: "delivery-history-list-footer" },
    });
    listPanel.append(listHeader, columns, listScroll, listFooter);

    const detail = element("aside", {
      className: "delivery-history-detail",
      attributes: { id: "delivery-history-detail", "aria-label": "Selected delivery details" },
    });
    workbench.append(listPanel, detail);

    legacyPanel.remove();
    view.append(controls, workbench);

    byId("delivery-history-range-filter").value = filters.range;
    byId("delivery-history-sort").value = filters.sort;
    bindControls();
    syncPagination();
  }

  function bindControls() {
    if (filtersBound) return;
    filtersBound = true;

    const search = byId("delivery-search");
    if (search) search.addEventListener("input", renderWorkbench);

    for (const [id, key] of [
      ["delivery-history-source-filter", "source"],
      ["delivery-history-severity-filter", "severity"],
      ["delivery-history-outcome-filter", "outcome"],
      ["delivery-history-range-filter", "range"],
      ["delivery-history-sort", "sort"],
    ]) {
      byId(id)?.addEventListener("change", (event) => {
        filters[key] = event.target.value;
        selectedDeliveryId = "";
        renderWorkbench();
      });
    }

    byId("delivery-history-clear-filters")?.addEventListener("click", () => {
      filters.source = "";
      filters.severity = "";
      filters.outcome = "";
      filters.range = "7d";
      filters.sort = "newest";
      if (search) search.value = "";
      byId("delivery-history-source-filter").value = "";
      byId("delivery-history-severity-filter").value = "";
      byId("delivery-history-outcome-filter").value = "";
      byId("delivery-history-range-filter").value = "7d";
      byId("delivery-history-sort").value = "newest";
      selectedDeliveryId = "";
      renderWorkbench();
    });

  }

  function filteredDeliveries() {
    const query = String(byId("delivery-search")?.value || "").trim().toLowerCase();
    const now = Date.now();
    const rangeMs = {
      "1d": 24 * 60 * 60 * 1000,
      "7d": 7 * 24 * 60 * 60 * 1000,
      "30d": 30 * 24 * 60 * 60 * 1000,
    }[filters.range] || 0;

    const items = (state.deliveries || []).filter((item) => {
      if (filters.source && String(item.source || "") !== filters.source) return false;
      if (filters.severity && String(item.severity || "") !== filters.severity) return false;
      if (filters.outcome && String(item.outcome || "") !== filters.outcome) return false;
      if (rangeMs) {
        const timestamp = deliveryTimestamp(item);
        if (timestamp && timestamp < now - rangeMs) return false;
      }
      if (!query) return true;
      return JSON.stringify([
        item.source,
        item.device_name,
        item.event_name,
        item.title,
        item.event_description,
        item.severity,
        item.event_status,
        item.outcome,
        item.safe_error,
        item.error_code,
      ]).toLowerCase().includes(query);
    });

    items.sort((left, right) => {
      const delta = deliveryTimestamp(right) - deliveryTimestamp(left);
      return filters.sort === "oldest" ? -delta : delta;
    });
    return items;
  }

  function refreshFilterOptions() {
    const items = state.deliveries || [];
    setSelectOptions(
      byId("delivery-history-source-filter"),
      items.map((item) => item.source),
      "All sources",
    );
    setSelectOptions(
      byId("delivery-history-severity-filter"),
      items.map((item) => item.severity),
      "All severities",
    );
    setSelectOptions(
      byId("delivery-history-outcome-filter"),
      items.map((item) => item.outcome),
      "All outcomes",
    );
  }

  function sourceCell(item) {
    const wrapper = element("span", { className: "delivery-history-source" });
    wrapper.append(sourceIcon(item.source));
    wrapper.append(element("strong", { text: friendlyName(item.source) }));
    return wrapper;
  }

  function renderRows(items) {
    const list = byId("delivery-list");
    if (!list) return;
    list.replaceChildren();

    if (!items.length) {
      list.append(element("div", { className: "delivery-history-empty" }, [
        element("strong", { text: "No matching delivery events" }),
        element("span", { text: "Change the search or filters to show delivery attempts." }),
      ]));
      return;
    }

    for (const item of items) {
      const id = deliveryId(item);
      const row = element("button", {
        className: `delivery-history-row${id === selectedDeliveryId ? " selected" : ""}`,
        type: "button",
        attributes: { "data-delivery-history-id": id, "aria-pressed": id === selectedDeliveryId ? "true" : "false" },
      });
      row.append(
        sourceCell(item),
        element("span", { className: "delivery-history-title-cell" }, [
          element("strong", { text: deliveryTitle(item) }),
          element("small", { text: deliveryDescription(item) }),
        ]),
        badge(capitalize(item.severity || "unknown"), deliveryTone(item.severity)),
        badge(capitalize(item.outcome || "unknown"), deliveryTone(item.outcome)),
        element("span", { className: "delivery-history-time", text: formatTime(item.completed_at || item.created_at) }),
        element("span", { className: "delivery-history-chevron", text: "›", attributes: { "aria-hidden": "true" } }),
      );
      row.addEventListener("click", () => {
        selectedDeliveryId = id;
        renderWorkbench();
      });
      list.append(row);
    }
  }

  function detailItem(label, value) {
    return element("div", { className: "delivery-history-detail-item" }, [
      element("span", { text: label }),
      element("strong", { text: value || "—" }),
    ]);
  }

  function shortId(value) {
    const text = String(value || "");
    return text ? text.slice(0, 12) : "—";
  }

  async function copyMessage(text) {
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(text);
      } else {
        const helper = document.createElement("textarea");
        helper.value = text;
        helper.style.position = "fixed";
        helper.style.opacity = "0";
        document.body.append(helper);
        helper.select();
        document.execCommand("copy");
        helper.remove();
      }
      toast("Delivery message copied.", "success");
    } catch (_error) {
      toast("Delivery message could not be copied.", "error");
    }
  }

  function deliveryTagIcon(kind) {
    const wrapper = element("span", {
      className: `delivery-history-tag-icon is-${kind}`,
      attributes: { "aria-hidden": "true" },
    });
    const icons = {
      tag: '<svg viewBox="0 0 24 24"><path d="M3.5 5.5v7.2L11.8 21l8.2-8.2-8.3-8.3H5.5a2 2 0 0 0-2 2Z"></path><circle cx="8" cy="9" r="1.4"></circle></svg>',
      source: '<svg viewBox="0 0 24 24"><ellipse cx="12" cy="5" rx="7" ry="3"></ellipse><path d="M5 5v6c0 1.7 3.1 3 7 3s7-1.3 7-3V5M5 11v6c0 1.7 3.1 3 7 3s7-1.3 7-3v-6"></path></svg>',
      severity: '<svg viewBox="0 0 24 24"><path d="M12 3 21 20H3L12 3Z"></path><path d="M12 9v5M12 17h.01"></path></svg>',
      status: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="8"></circle><path d="M12 7v5l3 2"></path></svg>',
      input: '<svg viewBox="0 0 24 24"><circle cx="6" cy="5" r="2"></circle><circle cx="18" cy="12" r="2"></circle><circle cx="6" cy="19" r="2"></circle><path d="m8 6 7.8 5M8 18l7.8-5"></path></svg>',
      response: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="8"></circle><path d="m8.5 12 2.2 2.2 4.8-5"></path></svg>',
      route: '<svg viewBox="0 0 24 24"><circle cx="7" cy="5" r="2"></circle><circle cx="17" cy="7" r="2"></circle><circle cx="17" cy="18" r="2"></circle><path d="M7 7v7a4 4 0 0 0 4 4h4M9 6h4a4 4 0 0 1 4 4v6"></path></svg>',
    };
    wrapper.innerHTML = icons[kind] || icons.tag;
    return wrapper;
  }

  function deliveryTag(label, value, kind, tone = "") {
    const tag = element("span", {
      className: `delivery-history-tag-pill${tone ? ` is-${tone}` : ""}`,
    });
    const copy = element("span", { className: "delivery-history-tag-copy" }, [
      element("span", { text: `${label}:` }),
      element("strong", { text: String(value || "—") }),
    ]);
    tag.append(deliveryTagIcon(kind), copy);
    return tag;
  }

  function renderDetail(item) {
    const panel = byId("delivery-history-detail");
    if (!panel) return;
    panel.replaceChildren();

    if (!item) {
      panel.append(element("div", { className: "delivery-history-detail-empty" }, [
        element("strong", { text: "Select a delivery event" }),
        element("span", { text: "Choose an event on the left to inspect its message and transport outcome." }),
      ]));
      return;
    }

    const destination = (state.destinations || []).find((candidate) => candidate.id === item.destination_id);
    const message = deliveryDescription(item);
    const heading = element("div", { className: "delivery-history-detail-heading" });
    const identity = element("div", { className: "delivery-history-detail-identity" });
    identity.append(sourceIcon(item.source));
    identity.append(element("div", {}, [
      element("strong", { text: deliveryTitle(item) }),
      element("small", { text: `${friendlyName(item.source)} • ${capitalize(item.outcome || "unknown")} • ${formatTime(item.completed_at || item.created_at)}` }),
    ]));
    const close = element("button", {
      className: "icon-button delivery-history-detail-close",
      text: "×",
      type: "button",
      attributes: { "aria-label": "Clear selected delivery" },
    });
    close.addEventListener("click", () => {
      selectedDeliveryId = "";
      renderWorkbench();
    });
    heading.append(identity, badge(capitalize(item.severity || "unknown"), deliveryTone(item.severity)), close);

    const messageCard = element("section", { className: "delivery-history-detail-card" });
    const messageHeader = element("div", { className: "delivery-history-card-heading" }, [
      element("strong", { text: "Message" }),
    ]);
    const copy = element("button", {
      className: "button secondary small",
      text: "Copy",
      type: "button",
      attributes: { id: "delivery-history-copy" },
    });
    copy.addEventListener("click", () => copyMessage(message));
    messageHeader.append(copy);
    messageCard.append(messageHeader, element("pre", { className: "delivery-history-message", text: message }));

    const statusCard = element("section", { className: "delivery-history-detail-card" }, [
      element("strong", { text: "Status & outcome" }),
      element("div", { className: "delivery-history-status-row" }, [
        badge(capitalize(item.outcome || "unknown"), deliveryTone(item.outcome)),
        badge(capitalize(item.event_status || item.severity || "unknown"), deliveryTone(item.event_status || item.severity)),
        badge(`Attempt ${item.attempt_number || 1}`),
        item.retryable ? badge("Retryable", "warning") : null,
      ]),
    ]);

    const transport = element("section", { className: "delivery-history-detail-card delivery-history-transport" }, [
      element("strong", { text: "Transport information" }),
      detailItem("Input", String(item.input_type || sourceInputType(item.source) || "—").toUpperCase()),
      detailItem("Destination", destination?.name || shortId(item.destination_id)),
      detailItem("Destination type", destination ? friendlyName(destination.output_type) : "Configured destination"),
      detailItem("Response", item.response_status ? `HTTP ${item.response_status}` : "—"),
      detailItem("Error", item.safe_error || item.error_code || "None"),
    ]);

    const timeline = element("section", { className: "delivery-history-detail-card delivery-history-detail-timeline" }, [
      element("strong", { text: "Timeline" }),
      element("div", { className: "delivery-history-timeline-step success" }, [
        element("span", { className: "delivery-history-timeline-dot" }),
        element("div", {}, [element("strong", { text: "Delivery attempt created" }), element("small", { text: formatTime(item.created_at) })]),
      ]),
      element("div", { className: `delivery-history-timeline-step ${deliveryTone(item.outcome)}` }, [
        element("span", { className: "delivery-history-timeline-dot" }),
        element("div", {}, [element("strong", { text: capitalize(item.outcome || "Completed") }), element("small", { text: formatTime(item.completed_at || item.created_at) })]),
      ]),
    ]);

    const lower = element("div", { className: "delivery-history-detail-grid" }, [transport, timeline]);

    const inputType = item.input_type || sourceInputType(item.source) || "";
    const responseStatus = Number(item.response_status || 0);
    const responseTone = responseStatus >= 200 && responseStatus < 300
      ? "success"
      : responseStatus >= 400
        ? "danger"
        : "";
    const tagBadges = [
      deliveryTag("Source", friendlyName(item.source || "unknown"), "source"),
      item.severity
        ? deliveryTag("Severity", friendlyName(item.severity), "severity", deliveryTone(item.severity))
        : null,
      item.event_status
        ? deliveryTag("Status", friendlyName(item.event_status), "status", deliveryTone(item.event_status))
        : null,
      inputType ? deliveryTag("Input", inputLabel(inputType), "input") : null,
      item.response_status
        ? deliveryTag("HTTP", item.response_status, "response", responseTone)
        : null,
      item.route_id ? deliveryTag("Route", shortId(item.route_id), "route") : null,
    ].filter(Boolean);
    const tagCard = element("section", {
      className: "delivery-history-detail-card delivery-history-tags-card",
    }, [
      element("div", { className: "delivery-history-tags-heading" }, [
        deliveryTagIcon("tag"),
        element("strong", { text: "Tags" }),
      ]),
      element("div", { className: "delivery-history-tags" }, tagBadges),
    ]);

    panel.append(heading, messageCard, statusCard, lower, tagCard);
  }

  function syncPagination() {
    const view = byId("view-deliveries");
    const target = byId("delivery-history-list-footer");
    if (!view || !target) return;
    const row = view.querySelector('.qa-pagination-row[data-qa-pager="delivery-pagination"]');
    if (row && row.parentElement !== target) target.append(row);
  }

  function renderWorkbench() {
    ensureLayout();
    if (!byId("delivery-history-workbench")) return;

    refreshFilterOptions();
    filters.source = byId("delivery-history-source-filter")?.value || filters.source;
    filters.severity = byId("delivery-history-severity-filter")?.value || filters.severity;
    filters.outcome = byId("delivery-history-outcome-filter")?.value || filters.outcome;
    filters.range = byId("delivery-history-range-filter")?.value || filters.range;
    filters.sort = byId("delivery-history-sort")?.value || filters.sort;

    const items = filteredDeliveries();
    if (!items.some((item) => deliveryId(item) === selectedDeliveryId)) {
      selectedDeliveryId = items.length ? deliveryId(items[0]) : "";
    }

    const total = typeof qaDeliveryPagination !== "undefined"
      ? Number(qaDeliveryPagination.total || state.deliveries.length)
      : state.deliveries.length;
    const totalLabel = byId("delivery-history-total");
    if (totalLabel) totalLabel.textContent = `${total} event${total === 1 ? "" : "s"}`;

    renderRows(items);
    renderDetail(items.find((item) => deliveryId(item) === selectedDeliveryId));
    syncPagination();
  }

  renderDeliveries = function renderDeliveriesWithDeliveryHistoryWorkbench() {
    originalRenderDeliveries();
    renderWorkbench();
  };

  if (originalLoadDeliveryPage) {
    qaLoadDeliveryPage = async function qaLoadDeliveryPageWithDeliveryHistoryWorkbench(page) {
      const result = await originalLoadDeliveryPage(page);
      renderWorkbench();
      return result;
    };
  }

  document.addEventListener("DOMContentLoaded", () => {
    ensureLayout();
    renderWorkbench();
  });
})();
