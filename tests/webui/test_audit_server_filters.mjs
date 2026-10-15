import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const read = name => readFileSync(new URL(`../../src/webui/${name}`, import.meta.url), 'utf8');

function auditFetchContext(request, query) {
  const context = {
    state: {user: {id: 'admin'}, sessionGeneration: 1, audit: [], auditPageSize: 50},
    window: {nowlertAuditQuery: () => query},
    request,
    URLSearchParams,
  };
  const source = read('qa_patch.js');
  const start = source.indexOf('function qaApplyAuditPage(');
  const end = source.indexOf('window.nowlertInitialDeliveryRequest');
  vm.runInNewContext(
    'let qaAuditRequestId = 0; let qaAuditPagination = {page: 1}; let qaAuditPage = 1; const qaAuditPageSize = 50;\n'
      + source.slice(start, end),
    context,
  );
  return context;
}

test('audit page requests carry the active server-side filters and keep filter options', async () => {
  const requests = [];
  const context = auditFetchContext(async path => {
    requests.push(path);
    return {
      audit_events: [{id: 7}],
      pagination: {page: 3, page_size: 50, total: 120, total_pages: 3},
      filter_options: {actions: ['backup.run'], outcomes: ['failed']},
    };
  }, {action: 'backup.run', outcome: '', range: '7d', sort: 'oldest', search: 'needle detail'});
  await context.qaFetchAuditPage(3);
  assert.equal(
    requests[0],
    '/audit-events/page/3/size/50?action=backup.run&outcome=&range=7d&sort=oldest&search=needle+detail',
  );
  assert.deepEqual(context.state.audit, [{id: 7}]);
  assert.deepEqual(context.state.auditFilterOptions, {actions: ['backup.run'], outcomes: ['failed']});
});

test('a slower earlier audit response cannot overwrite a newer filter result', async () => {
  const resolvers = [];
  const context = auditFetchContext(
    () => new Promise(resolve => resolvers.push(resolve)),
    {action: '', outcome: '', range: '7d', sort: 'newest', search: ''},
  );
  const first = context.qaFetchAuditPage(1);
  const second = context.qaFetchAuditPage(1);
  const page = rows => ({audit_events: rows, pagination: {page: 1, page_size: 50, total: rows.length, total_pages: 1}});
  resolvers[1](page([{id: 2}]));
  assert.ok(await second);
  resolvers[0](page([{id: 1}]));
  assert.equal(await first, null);
  assert.deepEqual(context.state.audit, [{id: 2}]);
});

test('audit workbench refetches from the server instead of filtering the loaded page', () => {
  const source = read('page_headers.js');
  const start = source.indexOf('/* Selected Audit Log workbench acceptance. */');
  const audit = source.slice(start);
  assert.match(audit, /window\.nowlertAuditQuery = \(\) => \(\{/);
  assert.match(audit, /function filteredAuditItems\(\) \{\s*return state\.audit \|\| \[\];/);
  assert.doesNotMatch(audit, /rangeMs/);
  assert.ok((audit.match(/refreshAuditPage\(\)/g) || []).length >= 4);
});
