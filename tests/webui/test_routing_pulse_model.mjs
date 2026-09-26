import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";
import test from "node:test";
import vm from "node:vm";

const modelPath = new URL("../../src/webui/routing_pulse_model.js", import.meta.url);
const context = { window: {} };
if (existsSync(modelPath)) vm.runInNewContext(readFileSync(modelPath, "utf8"), context, { filename: modelPath.pathname });
const model = context.window.NowlertRoutingPulseModel;
const normalize = nodes => JSON.parse(JSON.stringify(nodes));

test("exports the routing pulse model", () => {
  assert.ok(model, "the routing pulse model is available");
});

test("direct links give integrations and destinations the yellow mode", () => {
  assert.ok(model, "the routing pulse model is available");
  assert.deepEqual(normalize(model.resolveNodeModes({
    links: [{ route_id: "direct-route", destination_id: "direct-destination", filter_ids: [] }],
    filters: [],
  })), [
    { kind: "route", id: "direct-route", mode: "single" },
    { kind: "destination", id: "direct-destination", mode: "single" },
  ]);
});

test("filtered links give all connected nodes the grey mode", () => {
  assert.ok(model, "the routing pulse model is available");
  assert.deepEqual(normalize(model.resolveNodeModes({
    links: [{ route_id: "route", destination_id: "destination", filter_ids: ["filter"] }],
    filters: [{ id: "filter" }],
  })), [
    { kind: "route", id: "route", mode: "dual" },
    { kind: "filter", id: "filter", mode: "dual" },
    { kind: "destination", id: "destination", mode: "dual" },
  ]);
});

test("endpoints shared by direct and filtered routes receive mixed mode", () => {
  assert.ok(model, "the routing pulse model is available");
  assert.deepEqual(normalize(model.resolveNodeModes({
    links: [
      { route_id: "route", destination_id: "destination", filter_ids: [] },
      { route_id: "route", destination_id: "destination", filter_ids: ["filter"] },
    ],
    filters: [{ id: "filter" }],
  })), [
    { kind: "route", id: "route", mode: "mixed" },
    { kind: "destination", id: "destination", mode: "mixed" },
    { kind: "filter", id: "filter", mode: "dual" },
  ]);
});
