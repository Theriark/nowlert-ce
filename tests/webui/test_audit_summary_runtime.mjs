import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import vm from "node:vm";

const source = readFileSync(new URL("../../src/webui/audit_log_refinement.js", import.meta.url), "utf8");
const fetcher = source.slice(source.indexOf("  async function fetchAuditAnalytics("), source.indexOf("  function healthStorageKey("));
const summary = { total: 735339, current: { success: 1200, warning: 20, failed: 3, other: 4 }, previous: { success: 900, warning: 5, failed: 1, other: 2 } };

function harness(reply = async () => ({ summary })) {
  const paths = [];
  const saved = [];
  const totalNode = { textContent: "735339" };
  const context = vm.createContext({
    Date, Number, Promise, Error,
    qaAuditPagination: { total: summary.total },
    request: async path => { paths.push(path); return reply(path); },
    persistAuditAnalytics: value => saved.push(value),
    applyAuditAnalytics() {},
    countEvents: () => ({ success: 0, warning: 0, failed: 0, other: 0 }),
    document: { getElementById: () => totalNode },
  });
  vm.runInContext(`let auditAnalytics = null; let analyticsPromise = null; const ANALYTICS_TTL_MS = 60000; ${fetcher}`, context);
  return { context, paths, saved, totalNode };
}

test("audit analytics requests one bounded aggregate and reuses its TTL cache", async () => {
  const h = harness();
  const result = await h.context.fetchAuditAnalytics();
  assert.deepEqual(h.paths, ["/audit-events/summary"]);
  assert.equal(result.total, summary.total);
  assert.equal(result.current.success, 1200);
  await h.context.fetchAuditAnalytics();
  assert.equal(h.paths.length, 1);
  await h.context.fetchAuditAnalytics(true);
  assert.equal(h.paths.length, 2);
  assert.equal(h.saved.length, 2);
});

test("summary transport failure preserves cached counts and does not refresh their age", async () => {
  const h = harness(async () => { throw new Error("upstream unavailable"); });
  const cached = { ...summary, loadedAt: Date.now() - 120000 };
  vm.runInContext(`auditAnalytics = ${JSON.stringify(cached)};`, h.context);
  assert.equal(await h.context.fetchAuditAnalytics(), null);
  assert.equal(vm.runInContext("auditAnalytics.loadedAt", h.context), cached.loadedAt);
  assert.equal(vm.runInContext("auditAnalytics.current.success", h.context), 1200);
  assert.equal(h.saved.length, 0);
});

test("malformed aggregate cannot become fabricated zero metrics", async () => {
  const h = harness(async () => ({ summary: { total: "bad", current: {}, previous: {} } }));
  assert.equal(await h.context.fetchAuditAnalytics(), null);
  assert.equal(vm.runInContext("auditAnalytics", h.context), null);
  assert.equal(h.saved.length, 0);
});
