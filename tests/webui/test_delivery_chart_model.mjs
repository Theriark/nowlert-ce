import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";
import test from "node:test";
import vm from "node:vm";

const modelPath = new URL("../../src/webui/delivery_chart_model.js", import.meta.url);
const context = { window: {} };
if (existsSync(modelPath)) vm.runInNewContext(readFileSync(modelPath, "utf8"), context, { filename: modelPath.pathname });
const chart = context.window.NowlertDeliveryChart;
const plain = (value) => JSON.parse(JSON.stringify(value));

test("exports the delivery chart model", () => {
  assert.ok(chart, "the dashboard delivery chart model is available");
});

test("columns count each slot on its own instead of a running total", () => {
  assert.deepEqual(plain(chart.buildColumns([])), { columns: [], peak: 0 });
  const result = chart.buildColumns([
    { start: 100, delivered: 3, failed: 1, retry: 0 },
    { start: 110, delivered: 0, failed: 0, retry: 0 },
    { start: 120, delivered: 1, failed: 0, retry: 2 },
  ]);
  assert.deepEqual(plain(result.columns.map((column) => column.total)), [4, 0, 3]);
  assert.equal(result.peak, 4);
  assert.deepEqual(plain(result.columns[2]), { start: 120, delivered: 1, failed: 0, retry: 2, total: 3 });
});

test("axis uses round steps with headroom above the busiest slot", () => {
  assert.deepEqual(plain(chart.niceAxis(0)), { tickStep: 1, maximum: 1, intervals: 1 });
  assert.deepEqual(plain(chart.niceAxis(4)), { tickStep: 1, maximum: 5, intervals: 5 });
  assert.deepEqual(plain(chart.niceAxis(37)), { tickStep: 10, maximum: 40, intervals: 4 });
  assert.deepEqual(plain(chart.niceAxis(160)), { tickStep: 50, maximum: 200, intervals: 4 });
});

test("slot labels read naturally for each range", () => {
  assert.equal(chart.slotLabel(60), "minute");
  assert.equal(chart.slotLabel(300), "5 minutes");
  assert.equal(chart.slotLabel(3_600), "hour");
  assert.equal(chart.slotLabel(86_400), "day");
  assert.equal(chart.slotLabel(366 * 86_400 / 12), "month");
});

test("animation restarts on changed data or explicit dashboard entry only", () => {
  assert.equal(chart.shouldAnimateRender("same", "same", false), false);
  assert.equal(chart.shouldAnimateRender("same", "same", true), true);
  assert.equal(chart.shouldAnimateRender("old", "new", false), true);
});

const dashboardSource = readFileSync(new URL("../../src/webui/operations_dashboard.js", import.meta.url), "utf8");
const dashboardCss = readFileSync(new URL("../../src/webui/operations_dashboard.css", import.meta.url), "utf8");
const acceptanceCss = readFileSync(new URL("../../src/webui/operations_acceptance.css", import.meta.url), "utf8");

test("dashboard draws per-slot stacked columns at the card's real width", () => {
  assert.match(dashboardSource, /chartModel\.buildColumns\(buckets\)/);
  assert.match(dashboardSource, /Deliveries per \$\{unit\}/);
  assert.match(dashboardSource, /ops-chart-col-\$\{kind\}/);
  assert.doesNotMatch(dashboardSource, /buildCumulativeSeries|Cumulative outcome/);
  // A fixed viewBox stretched with preserveAspectRatio="none" distorted the axis text.
  assert.doesNotMatch(dashboardSource, /preserveAspectRatio/);
  assert.match(dashboardSource, /new ResizeObserver/);
  assert.match(dashboardSource, /No deliveries in this period/);
  assert.match(dashboardCss, /\.ops-chart-col\s*\{\s*animation:\s*ops-chart-col-pulse/);
  assert.match(dashboardCss, /\.ops-chart-col-delivered\s*\{/);
  assert.match(dashboardCss, /\.ops-chart-col-failed\s*\{/);
});

test("dashboard keeps its range and aligns Workspace Summary content", () => {
  assert.match(dashboardSource, /id="ops-dashboard-range"/);
  assert.doesNotMatch(dashboardSource, /id="history-range"/);
  assert.match(acceptanceCss, /\.ops-workspace-summary-copy\s*\{[^}]*align-self:\s*center;/s);
});
