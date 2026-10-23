import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const source = readFileSync(new URL('../../src/webui/reference_acceptance.js', import.meta.url), 'utf8');

function extract(name) {
  const match = source.match(new RegExp(`^  (async )?function ${name}\\(`, 'm'));
  assert.ok(match, `${name} exists`);
  const start = match.index;
  const end = source.indexOf('\n  }\n', start);
  return source.slice(start, end + 5);
}

// Catalog as the Preview dialog sees it: Xen Orchestra declares no severities.
const catalog = {
  xo: [],
  zabbix: ['not classified', 'information', 'warning', 'average', 'high', 'disaster'],
  grafana: ['information', 'warning', 'error', 'critical'],
};

function build(routes) {
  const context = {
    state: {routes},
    previewRouteSelection: new Set(routes.map((route) => route.id)),
    routeFilterValuesForSource: (name) => (catalog[name] || []).slice(),
  };
  const functions = [
    'selectedPreviewRoutes',
    'previewDeclaredSeverities',
    'previewAvailableSeverities',
    'previewRouteSupportsSeverity',
  ].map(extract).join('\n');
  return vm.runInNewContext(
    `const PREVIEW_DEFAULT_SEVERITIES = ["critical", "warning", "info"];\n` +
      `${functions}\n({previewAvailableSeverities, previewRouteSupportsSeverity, selectedPreviewRoutes});`,
    context,
  );
}

const xo = {id: 'r-xo', source: 'xo'};
const zabbix = {id: 'r-zbx', source: 'zabbix'};
const grafana = {id: 'r-grf', source: 'grafana'};

test('an XO-only destination offers the default severities and previews the XO route', () => {
  const api = build([xo]);
  assert.deepEqual([...api.previewAvailableSeverities()], ['critical', 'warning', 'info']);
  for (const severity of api.previewAvailableSeverities()) {
    assert.equal(api.previewRouteSupportsSeverity(xo, severity), true);
  }
});

test('XO stays in the preview whatever severity other routes put first (THE-903)', () => {
  const api = build([zabbix, grafana, xo]);
  const severities = [...api.previewAvailableSeverities()];
  // Only declared severities are offered; the XO defaults do not add "info".
  assert.deepEqual(severities, ['not classified', 'information', 'warning', 'average', 'high', 'disaster', 'error', 'critical']);
  for (const severity of severities) {
    assert.equal(api.previewRouteSupportsSeverity(xo, severity), true, `XO supports ${severity}`);
  }
});

test('routes that declare severities still only preview the severities they declare', () => {
  const api = build([zabbix, grafana, xo]);
  assert.equal(api.previewRouteSupportsSeverity(zabbix, 'average'), true);
  assert.equal(api.previewRouteSupportsSeverity(zabbix, 'critical'), false);
  assert.equal(api.previewRouteSupportsSeverity(grafana, 'average'), false);
  assert.equal(api.previewRouteSupportsSeverity(grafana, 'Critical'), true);
  assert.equal(api.previewRouteSupportsSeverity(grafana, ''), false);
});

test('no selected route means no severities', () => {
  const api = build([]);
  assert.deepEqual([...api.previewAvailableSeverities()], []);
});

test('preview requests run in order with a bounded number in flight', async () => {
  const run = vm.runInNewContext(`${extract('previewRunLimited')}\npreviewRunLimited;`);
  let inFlight = 0;
  let peak = 0;
  const items = Array.from({length: 20}, (_, index) => index);
  const results = await run(items, 4, async (item) => {
    inFlight += 1;
    peak = Math.max(peak, inFlight);
    await new Promise((resolve) => setTimeout(resolve, item % 3));
    inFlight -= 1;
    return item * 2;
  });
  assert.equal(peak, 4);
  assert.deepEqual([...results], items.map((item) => item * 2));
  assert.deepEqual([...(await run([], 4, async () => 1))], []);
});

test('a server failure reports its status and support reference, client errors keep their message', () => {
  class APIError extends Error {
    constructor(status, publicMessage, reference = '') {
      super(publicMessage);
      this.status = status;
      this.publicMessage = publicMessage;
      this.reference = reference;
    }
  }
  const message = vm.runInNewContext(
    `${extract('previewRequestFailure')}\npreviewRequestFailure;`,
    {
      APIError,
      uiErrorMessage: (error, fallback) => (error instanceof APIError && error.publicMessage ? error.publicMessage : fallback),
    },
  );
  assert.equal(message(new APIError(500, '', 'abc123def456')), 'Preview request failed (HTTP 500, reference abc123def456).');
  assert.equal(message(new APIError(500, '', 'bad ref!')), 'Preview request failed (HTTP 500).');
  assert.equal(message(new APIError(400, 'destination cannot preview this notification')), 'destination cannot preview this notification');
  assert.equal(message(new Error('boom')), 'Preview request failed.');
});
