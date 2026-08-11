"use strict";

const QA_PAGE_SIZE = 25;
const QA_ALL_SEVERITIES = ["debug", "information", "warning", "error", "critical", "failure"];
const QA_ALL_STATUSES = ["active", "resolved", "firing", "recovered", "success", "skipped", "failure"];
let qaRoutePage = 1;
let qaDeliveryPage = 1;
let qaAuditPage = 1;
let qaDeliveryPagination = { page: 1, page_size: QA_PAGE_SIZE, total: 0, total_pages: 1 };
let qaAuditPagination = { page: 1, page_size: QA_PAGE_SIZE, total: 0, total_pages: 1 };

const qaOriginalRequest = request;

function qaSanitizeApiError(error) {
  if (!(error instanceof APIError)) return;
  const details = [];
  if (error.status) details.push(`HTTP ${error.status}`);
  if (error.path) details.push(`${API}${error.path}`);
  if (error.reference) details.push(`reference ${error.reference}`);
  const suffix = details.length ? ` (${details.join(" · ")})` : "";
  if (suffix && error.message.endsWith(suffix)) {
    error.message = error.message.slice(0, -suffix.length) || "Request failed";
  }
}

request = async function requestWithSafeUserErrors(path, options = {}) {
  try {
    return await qaOriginalRequest(path, options);
  } catch (error) {
    if (error instanceof APIError) {
      console.error("Nowlert API request failed", {
        status: error.status,
        path: error.path,
        code: error.code,
        reference: error.reference,
      });
      qaSanitizeApiError(error);
    }
    throw error;
  }
};

const qaOriginalDestinationTestToast = destinationTestToast;
destinationTestToast = function destinationTestToastWithSafeErrors(delivery, outputType) {
  if (delivery && !delivery.success) {
    console.error("Destination test failed", {
      response_status: delivery.response_status,
      error_code: delivery.error_code,
      safe_error: delivery.safe_error,
    });
    return {
      message: "Test delivery failed. Check the destination configuration and logs.",
      style: "error",
    };
  }
  return qaOriginalDestinationTestToast(delivery, outputType);
};

function qaSelectionCoversAll(values, expected) {
  const selected = new Set(
    (Array.isArray(values) ? values : []).map((value) => String(value).toLowerCase()),
  );
  return selected.size === expected.length && expected.every((value) => selected.has(value));
}

const qaOriginalFilterSummary = filterSummary;
filterSummary = function filterSummaryWithAllEvents(filters = {}) {
  const normalized = { ...filters };
  if (qaSelectionCoversAll(normalized.severities, QA_ALL_SEVERITIES)) normalized.severities = [];
  if (qaSelectionCoversAll(normalized.statuses, QA_ALL_STATUSES)) normalized.statuses = [];
  const summary = qaOriginalFilterSummary(normalized);
  return summary === "All events" ? "All Events" : summary;
};

function qaNormalizeDeliveryBadges() {
  for (const meta of document.querySelectorAll("#delivery-list .resource-meta")) {
    const seen = new Set();
    for (const item of [...meta.querySelectorAll(".badge")]) {
      const text = item.textContent.trim();
      const key = text.toLowerCase();
      if (!text || text === "—" || seen.has(key)) {
        item.remove();
        continue;
      }
      seen.add(key);
    }
  }
}

function qaPager(containerId, pagination, onPage) {
  let container = byId(containerId);
  if (!container) {
    container = element("div", { className: "qa-pagination", attributes: { id: containerId, "aria-label": "Pagination" } });
    return container;
  }
  container.replaceChildren();
  const page = Number(pagination.page || 1);
  const totalPages = Math.max(1, Number(pagination.total_pages || 1));
  const total = Number(pagination.total || 0);
  const previous = element("button", { className: "button secondary small", text: "Previous", type: "button", disabled: page <= 1 });
  const next = element("button", { className: "button secondary small", text: "Next", type: "button", disabled: page >= totalPages });
  previous.addEventListener("click", () => onPage(page - 1));
  next.addEventListener("click", () => onPage(page + 1));
  container.append(previous, element("span", { text: `Page ${page} of ${totalPages} - ${total} item${total === 1 ? "" : "s"}` }), next);
  return container;
}

function qaMountPager(viewId, containerId, pagination, onPage) {
  const view = byId(viewId);
  if (!view) return;
  let pager = byId(containerId);
  if (!pager) {
    pager = element("div", { className: "qa-pagination", attributes: { id: containerId, "aria-label": "Pagination" } });
    view.append(pager);
  }
  qaPager(containerId, pagination, onPage);
}

const qaOriginalRenderRoutes = renderRoutes;
renderRoutes = function renderRoutesWithPagination() {
  qaOriginalRenderRoutes();
  const rows = [...byId("route-table").children];
  const total = rows.length;
  const totalPages = Math.max(1, Math.ceil(total / QA_PAGE_SIZE));
  qaRoutePage = Math.min(Math.max(1, qaRoutePage), totalPages);
  const start = (qaRoutePage - 1) * QA_PAGE_SIZE;
  rows.forEach((row, index) => { row.hidden = index < start || index >= start + QA_PAGE_SIZE; });
  qaMountPager("view-routes", "route-pagination", {
    page: qaRoutePage,
    page_size: QA_PAGE_SIZE,
    total,
    total_pages: totalPages,
  }, (page) => {
    qaRoutePage = page;
    renderRoutes();
  });
};

const qaOriginalRenderDestinationFields = renderDestinationFields;
renderDestinationFields = function renderDestinationFieldsWithCredentialState(settings = {}) {
  qaOriginalRenderDestinationFields(settings);
  const id = byId("destination-id").value;
  const destination = state.destinations.find((item) => item.id === id);
  if (!destination || !destination.secret_configured) return;
  const urlInput = byId("destination-secrets").querySelector('[data-field="url"]');
  if (!urlInput) return;
  urlInput.placeholder = "Configured (hidden) - enter a new URL to replace it";
  urlInput.setAttribute("aria-label", "Configured URL is hidden; enter a new URL to replace it");
  const help = element("small", { className: "qa-credential-state", text: "A URL is already configured. It is hidden for security; leave this field empty to keep it, or enter a new URL to replace it." });
  urlInput.parentElement.append(help);
};

async function qaLoadDeliveryPage(page) {
  try {
    const response = await request(`/deliveries/page/${Math.max(1, Number(page || 1))}`);
    state.deliveries = response.deliveries || [];
    qaDeliveryPagination = response.pagination || qaDeliveryPagination;
    qaDeliveryPage = qaDeliveryPagination.page || 1;
    qaOriginalRenderDeliveries();
    qaNormalizeDeliveryBadges();
    qaMountPager("view-deliveries", "delivery-pagination", qaDeliveryPagination, qaLoadDeliveryPage);
  } catch (error) {
    toast(error.message || "Delivery history page could not be loaded.", "error");
  }
}

async function qaLoadAuditPage(page) {
  try {
    const response = await request(`/audit-events/page/${Math.max(1, Number(page || 1))}`);
    state.audit = response.audit_events || [];
    qaAuditPagination = response.pagination || qaAuditPagination;
    qaAuditPage = qaAuditPagination.page || 1;
    qaOriginalRenderAudit();
    qaMountPager("view-audit", "audit-pagination", qaAuditPagination, qaLoadAuditPage);
  } catch (error) {
    toast(error.message || "Audit page could not be loaded.", "error");
  }
}

const qaOriginalRenderDeliveries = renderDeliveries;
renderDeliveries = function renderDeliveriesWithPagination() {
  qaOriginalRenderDeliveries();
  qaNormalizeDeliveryBadges();
  qaMountPager("view-deliveries", "delivery-pagination", qaDeliveryPagination, qaLoadDeliveryPage);
};

const qaOriginalRenderAudit = renderAudit;
renderAudit = function renderAuditWithPagination() {
  qaOriginalRenderAudit();
  qaMountPager("view-audit", "audit-pagination", qaAuditPagination, qaLoadAuditPage);
};

const qaOriginalLoadWorkspace = loadWorkspace;
loadWorkspace = async function loadWorkspaceWithPagination() {
  await qaOriginalLoadWorkspace();
  await Promise.all([qaLoadDeliveryPage(qaDeliveryPage), qaLoadAuditPage(qaAuditPage)]);
};

function qaAddSelectActions(selectId) {
  const select = byId(selectId);
  if (!select || select.dataset.qaActions === "1") return;
  select.dataset.qaActions = "1";
  const actions = element("div", { className: "qa-select-actions" });
  const all = element("button", { className: "text-button", text: "Select all", type: "button" });
  const clear = element("button", { className: "text-button", text: "Clear", type: "button" });
  all.addEventListener("click", () => { for (const option of select.options) option.selected = true; select.dispatchEvent(new Event("change", { bubbles: true })); });
  clear.addEventListener("click", () => { for (const option of select.options) option.selected = false; select.dispatchEvent(new Event("change", { bubbles: true })); });
  actions.append(all, clear);
  select.parentElement.append(actions);
}

function qaAddCounter(inputId, maximum) {
  const input = byId(inputId);
  if (!input || input.dataset.qaCounter === "1") return;
  input.dataset.qaCounter = "1";
  input.maxLength = maximum;
  const counter = element("small", { className: "qa-char-count" });
  const update = () => {
    const length = input.value.length;
    counter.textContent = `${length}/${maximum}`;
    input.setCustomValidity(length > maximum ? `Maximum ${maximum} characters.` : "");
  };
  input.addEventListener("input", update);
  input.parentElement.append(counter);
  update();
}

function qaUpdateAvatarSave() {
  const save = byId("avatar-save");
  const file = byId("avatar-file");
  if (!save || !file) return;
  const selected = Boolean(file.files && file.files.length);
  save.hidden = !selected;
  save.disabled = !selected;
}

function qaEnhanceRegionalSettings() {
  const language = byId("preference-language");
  if (language) {
    const labels = {
      "en-US": "English (United States)",
      "pt-BR": "Portuguese (Brazil)",
    };
    for (const [value, label] of Object.entries(labels)) {
      if (![...language.options].some((option) => option.value === value)) {
        language.append(element("option", { value, text: label }));
      }
    }
  }
  const zones = byId("timezone-suggestions");
  if (zones) {
    for (const value of [
      "Europe/Berlin", "Europe/Amsterdam", "Europe/Rome", "Europe/Zurich", "Europe/Stockholm",
      "America/Chicago", "America/Denver", "America/Toronto", "America/Sao_Paulo", "America/Mexico_City",
      "Asia/Dubai", "Asia/Kolkata", "Asia/Singapore", "Asia/Tokyo", "Asia/Seoul",
      "Australia/Sydney", "Pacific/Auckland", "Africa/Johannesburg",
    ]) {
      if (![...zones.options].some((option) => option.value === value)) zones.append(element("option", { value }));
    }
  }
}

document.addEventListener("DOMContentLoaded", () => {
  qaAddCounter("preview-event-title", 256);
  qaAddCounter("preview-message", 4000);
  qaAddCounter("user-name", 64);
  for (const id of ["route-severities", "route-statuses", "route-exclude_severities", "route-exclude_statuses"]) qaAddSelectActions(id);
  qaEnhanceRegionalSettings();
  qaUpdateAvatarSave();
  byId("avatar-file")?.addEventListener("change", qaUpdateAvatarSave);
  byId("avatar-form")?.addEventListener("submit", () => window.setTimeout(qaUpdateAvatarSave, 0));
  document.addEventListener("click", (event) => {
    if (event.target.closest('[data-action="remove-avatar"]')) window.setTimeout(qaUpdateAvatarSave, 0);
  });
});

/* Nowlert 3.1.0 empty-state icon restoration */
(() => {
  const ICON_PATH = "/ui/brand/nowlert-owl-v3.1.0.png";

  function restoreEmptyStateIcons(root = document) {
    const candidates = root.querySelectorAll('.empty-state, .empty-panel, .fallback-product-mark');
    candidates.forEach((node) => {
      if (node.querySelector('.empty-state-icon')) return;
      const icon = document.createElement('div');
      icon.className = 'empty-state-icon';
      const img = document.createElement('img');
      img.src = ICON_PATH;
      img.alt = 'Nowlert';
      icon.appendChild(img);
      node.insertBefore(icon, node.firstChild);
    });
  }

  function run() {
    restoreEmptyStateIcons(document);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', run, { once: true });
  } else {
    run();
  }

  let pending = false;
  const observer = new MutationObserver(() => {
    if (pending) return;
    pending = true;
    requestAnimationFrame(() => {
      pending = false;
      run();
    });
  });
  observer.observe(document.documentElement, { childList: true, subtree: true });
})();
