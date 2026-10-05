import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import vm from "node:vm";

const source = readFileSync(new URL("../../src/webui/app.js", import.meta.url), "utf8");
const start = source.indexOf("function prepareMobileDestinationPayload(");
const end = source.indexOf("function renderDestinationFields(", start);
function run(payload, { connection = null, destinations = [], id = "" } = {}) {
  const context = { payload, id, mobileConnection: connection, state: { destinations } };
  vm.runInNewContext(source.slice(start, end) + "prepareMobileDestinationPayload(payload, id);", context);
  return payload;
}
test("approved connection preserves normal name and route selection", () => {
  const payload = { name: "My phone", output_type: "nowlert_mobile", settings: {}, route_ids: ["route-a", "route-b"] };
  run(payload, { connection: { id: "connection-a", approved: true } });
  assert.deepEqual(payload.route_ids, ["route-a", "route-b"]);
  assert.equal(payload.name, "My phone");
  assert.equal(payload.mobile_connection_id, "connection-a");
  assert.equal("settings" in payload, false);
});
test("pending and unconnected destinations cannot save", () => {
  assert.throws(() => run({ output_type: "nowlert_mobile" }), /Connect Nowlert Mobile/);
  assert.throws(() => run({ output_type: "nowlert_mobile" }, { connection: { id: "a", approved: false } }), /Approve/);
});
test("existing connected destination retains hidden settings and credentials", () => {
  const payload = { name: "Renamed phone", output_type: "nowlert_mobile", settings: {}, route_ids: ["a"] };
  run(payload, { id: "phone", destinations: [{ id: "phone", output_type: "nowlert_mobile", secret_configured: true }] });
  assert.equal("settings" in payload, false);
  assert.equal("secret" in payload, false);
  assert.equal("mobile_connection_id" in payload, false);
});
test("other provider saves remain unchanged", () => {
  const payload = { output_type: "discord", settings: { components_v2: true } };
  run(payload);
  assert.equal(payload.settings.components_v2, true);
});

test("closing the editor cancels polling and invalidates an in-flight response", () => {
  const resetStart = source.indexOf("function resetMobileConnection(");
  const resetEnd = source.indexOf("function renderMobileConnection(", resetStart);
  const cancelledTimers = [];
  const context = {
    mobileConnection: { id: "pending-connection", approved: false },
    mobileConnectionTimer: 123,
    mobileConnectionGeneration: 4,
    clearTimeout: (timer) => cancelledTimers.push(timer),
  };
  vm.runInNewContext(source.slice(resetStart, resetEnd) + "resetMobileConnection();", context);
  assert.deepEqual(cancelledTimers, [123]);
  assert.equal(context.mobileConnection, null);
  assert.equal(context.mobileConnectionGeneration, 5);
});
