import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";
import test from "node:test";
import vm from "node:vm";

const modelPath = new URL("../../src/webui/delivery_chart_model.js", import.meta.url);
const context = { window: {} };
if (existsSync(modelPath)) vm.runInNewContext(readFileSync(modelPath, "utf8"), context, { filename: modelPath.pathname });
const chart = context.window.NowlertDeliveryChart;

test("exports the delivery chart model", () => {
  assert.ok(chart, "the dashboard delivery chart model is available");
});

test("empty and sparse ranges preserve cumulative totals", () => {
  assert.ok(chart, "the dashboard delivery chart model is available");
  assert.deepEqual(JSON.parse(JSON.stringify(chart.buildCumulativeSeries([], 10))), { points: [], total: 0 });
  const result = chart.buildCumulativeSeries([
    { start: 100, delivered: 0, failed: 0, retry: 0 },
    { start: 110, delivered: 2, failed: 1, retry: 0 },
    { start: 120, delivered: 0, failed: 0, retry: 0 },
  ], 10);
  assert.equal(result.total, 3);
  assert.deepEqual(JSON.parse(JSON.stringify(result.points)), [{ index: 1, time: 115, value: 3, delta: 3 }]);
});

test("step paths and delivery pulse delays share the event timeline", () => {
  assert.ok(chart, "the dashboard delivery chart model is available");
  const series = chart.buildCumulativeSeries([
    { start: 100, delivered: 1 }, { start: 110, delivered: 1 },
  ], 10);
  assert.equal(
    chart.buildStepPath(series.points, time => time, value => 100 - value, 100, 130),
    "M 100 100 H 105 V 99 H 115 V 98 H 130",
  );
  assert.deepEqual(JSON.parse(JSON.stringify(series.points.map(point => chart.pulseDelay(point.time, 100, 20, 1000)))), [250, 750]);
});

test("animation restarts on changed data or explicit dashboard entry only", () => {
  assert.ok(chart, "the dashboard delivery chart model is available");
  assert.equal(chart.shouldAnimateRender("same", "same", false), false);
  assert.equal(chart.shouldAnimateRender("same", "same", true), true);
  assert.equal(chart.shouldAnimateRender("old", "new", false), true);
});

const dashboardSource = readFileSync(new URL("../../src/webui/operations_dashboard.js", import.meta.url), "utf8");
const dashboardCss = readFileSync(new URL("../../src/webui/operations_dashboard.css", import.meta.url), "utf8");
const acceptanceCss = readFileSync(new URL("../../src/webui/operations_acceptance.css", import.meta.url), "utf8");

test("dashboard renders the pulsing cumulative line without replay or static dots", () => {
  assert.match(dashboardSource, /chartModel\.buildCumulativeSeries\(buckets, bucketSeconds\)/);
  assert.match(dashboardSource, /chartModel\.buildStepPath\(points/);
  assert.match(dashboardSource, /ops-chart-delivery-pulse/);
  assert.doesNotMatch(dashboardSource, /ops-chart-replay|ops-chart-outcome-point|ops-chart-bar/);
  assert.match(dashboardCss, /\.ops-chart-outcome-line\s*\{[^}]*stroke-width:\s*2;/s);
  assert.match(dashboardCss, /ops-chart-line-core 2s ease-in-out infinite/);
  assert.match(dashboardCss, /prefers-reduced-motion:\s*reduce/);
});

test("dashboard keeps its range and aligns Workspace Summary content", () => {
  assert.match(dashboardSource, /id="ops-dashboard-range"/);
  assert.doesNotMatch(dashboardSource, /id="history-range"/);
  assert.match(acceptanceCss, /\.ops-workspace-summary-copy\s*\{[^}]*align-self:\s*center;/s);
});
