"use strict";

const QA_PAGE_SIZE = 25;
let qaRoutePage = 1;
let qaDeliveryPage = 1;
let qaAuditPage = 1;
const QA_AUDIT_PAGE_SIZE_KEY = "nowlert.audit.pageSize";
const QA_AUDIT_PAGE_SIZES = [25, 50, 100, 150, 250, 500];

function qaReadAuditPageSize() {
  let stored = 25;
  try {
    stored = Number(window.localStorage.getItem(QA_AUDIT_PAGE_SIZE_KEY));
  } catch (error) {
    stored = 25;
  }
  return QA_AUDIT_PAGE_SIZES.includes(stored) ? stored : 25;
}

function qaWriteAuditPageSize(value) {
  try {
    window.localStorage.setItem(QA_AUDIT_PAGE_SIZE_KEY, String(value));
  } catch (error) {
    /* storage unavailable; selection stays in-session only */
  }
}

let qaAuditPageSize = qaReadAuditPageSize();
let qaDeliveryPagination = { page: 1, page_size: QA_PAGE_SIZE, total: 0, total_pages: 1 };
let qaAuditPagination = { page: 1, page_size: QA_PAGE_SIZE, total: 0, total_pages: 1 };

function qaPager(containerId, pagination, onPage) {
  let container = byId(containerId);
  if (!container) {
    container = element("div", {
      className: "qa-pagination",
      attributes: { id: containerId, "aria-label": "Pagination" },
    });
    return container;
  }

  container.replaceChildren();

  const page = Number(pagination.page || 1);
  const totalPages = Math.max(1, Number(pagination.total_pages || 1));
  const total = Number(pagination.total || 0);
  const directNavigation =
    containerId === "delivery-pagination" ||
    containerId === "audit-pagination";

  const previous = element("button", {
    className: "button secondary small",
    text: "Previous",
    type: "button",
    disabled: page <= 1,
  });
  const next = element("button", {
    className: "button secondary small",
    text: "Next",
    type: "button",
    disabled: page >= totalPages,
  });
  const status = element("span", {
    text: `Page ${page} of ${totalPages} - ${total} item${total === 1 ? "" : "s"}`,
  });

  previous.addEventListener("click", () => onPage(page - 1));
  next.addEventListener("click", () => onPage(page + 1));

  // Routes keep the existing compact Previous / Next pager.
  if (!directNavigation) {
    container.append(previous, status, next);
    return container;
  }

  const first = element("button", {
    className: "button secondary small",
    text: "First",
    type: "button",
    disabled: page <= 1,
    attributes: { "aria-label": "First page" },
  });
  const last = element("button", {
    className: "button secondary small",
    text: "Last",
    type: "button",
    disabled: page >= totalPages,
    attributes: { "aria-label": "Last page" },
  });
  const pageInput = element("input", {
    className: "qa-page-number",
    type: "number",
    value: page,
    attributes: {
      min: "1",
      max: String(totalPages),
      step: "1",
      inputmode: "numeric",
      "aria-label": `Page number, 1 to ${totalPages}`,
    },
  });
  const go = element("button", {
    className: "button secondary small",
    text: "Go",
    type: "button",
    attributes: { "aria-label": "Go to page" },
  });

  const requestedPage = () => {
    const value = Number(pageInput.value);
    if (!Number.isInteger(value) || value < 1 || value > totalPages) {
      return null;
    }
    return value;
  };

  const updateJumpState = () => {
    const requested = requestedPage();
    const valid = requested !== null;
    pageInput.setAttribute("aria-invalid", valid ? "false" : "true");
    go.disabled = !valid || requested === page;
  };

  const jumpToRequestedPage = () => {
    const requested = requestedPage();

    if (requested === null) {
      pageInput.value = String(page);
      updateJumpState();
      return;
    }

    if (requested !== page) onPage(requested);
  };

  first.addEventListener("click", () => onPage(1));
  last.addEventListener("click", () => onPage(totalPages));
  pageInput.addEventListener("input", updateJumpState);
  pageInput.addEventListener("change", jumpToRequestedPage);
  pageInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      jumpToRequestedPage();
    }
  });
  go.addEventListener("click", jumpToRequestedPage);

  updateJumpState();

  container.append(
    first,
    previous,
    status,
    pageInput,
    go,
    next,
    last,
  );
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
    qaMountPager("view-deliveries", "delivery-pagination", qaDeliveryPagination, qaLoadDeliveryPage);
  } catch (error) {
    toast(error.message || "Delivery history page could not be loaded.", "error");
  }
}

async function qaLoadAuditPage(page) {
  try {
    const response = await request(
      `/audit-events/page/${Math.max(1, Number(page || 1))}/size/${qaAuditPageSize}`,
    );
    state.audit = response.audit_events || [];
    if (typeof state.auditPageSize === "number") state.auditPageSize = qaAuditPageSize;
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

function qaBindAuditPageSize() {
  const select = byId("audit-page-size");
  if (!select || select.dataset.qaPageSize === "1") return;
  select.dataset.qaPageSize = "1";
  qaAuditPageSize = qaReadAuditPageSize();
  select.value = String(qaAuditPageSize);
  if (typeof state.auditPageSize === "number") state.auditPageSize = qaAuditPageSize;
  select.addEventListener("change", () => {
    const chosen = Number(select.value);
    qaAuditPageSize = QA_AUDIT_PAGE_SIZES.includes(chosen) ? chosen : 25;
    qaWriteAuditPageSize(qaAuditPageSize);
    if (typeof state.auditPageSize === "number") state.auditPageSize = qaAuditPageSize;
    qaAuditPage = 1;
    qaLoadAuditPage(1);
  });
}

document.addEventListener("DOMContentLoaded", qaBindAuditPageSize);

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

document.addEventListener("DOMContentLoaded", () => {
  qaAddCounter("preview-event-title", 256);
  qaAddCounter("preview-message", 4000);
  qaAddCounter("user-name", 64);
  for (const id of ["route-severities", "route-statuses", "route-exclude_severities", "route-exclude_statuses"]) qaAddSelectActions(id);
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
