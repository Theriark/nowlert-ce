import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const read = name => readFileSync(new URL(`../../src/webui/${name}`, import.meta.url), 'utf8');
class Node {
  constructor(tag, options = {}, children = []) {
    this.tag = tag;
    Object.assign(this, options);
    this.attributes = {...options.attributes};
    this.children = children;
    this.dataset = {};
    this.events = {};
  }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  addEventListener(name, handler) { this.events[name] = handler; }
  setAttribute(name, value) { this.attributes[name] = value; }
  removeAttribute(name) { delete this.attributes[name]; }
}
const descendants = node => [node, ...(node.children || []).flatMap(child => typeof child === 'object' ? descendants(child) : [])];

for (const id of ['delivery-pagination', 'audit-pagination']) {
  test(`${id} retains the editable current-page status and Enter navigation`, async () => {
    const pager = new Node('div');
    const visited = [];
    let scrolled = 0;
    const context = {
      byId: () => pager,
      element: (tag, options, children) => new Node(tag, options, children),
      span: (className, text) => new Node('span', {className, text}),
      document: {createElement: tag => new Node(tag)},
      REFERENCE_PAGERS: new Set(['delivery-pagination', 'audit-pagination']),
      qaScrollPageBottom: () => { scrolled++; },
    };
    const source = read('qa_patch.js');
    vm.runInNewContext(source.slice(source.indexOf('function qaPager('), source.indexOf('\nfunction qaMountPager(')), context);
    const management = read('management_consistency.js');
    const override = management.indexOf('  function pagerButton(');
    if (override >= 0) {
      vm.runInNewContext(management.slice(override, management.indexOf('  function syncDeliveryHistory(', override)) + '\ninstallReferencePagination();', context);
    }
    context.qaPager(id, {page: 2, page_size: 25, total: 90, total_pages: 4}, page => visited.push(page));
    const status = descendants(pager).find(node => node.className === 'qa-page-status');
    assert.ok(status, 'current page must be embedded in Page [n] of N - X items');
    const input = status.children.find(node => node.tag === 'input');
    assert.equal(input.value, 2);
    assert.equal(status.children.at(-1), ' of 4 - 90 items');
    input.value = '3';
    input.events.keydown({key: 'Enter', preventDefault() {}});
    await Promise.resolve();
    assert.deepEqual(visited, [3]);
    assert.equal(scrolled, 1);
    input.value = '999';
    input.events.keydown({key: 'Enter', preventDefault() {}});
    assert.equal(input.value, '2');
    assert.deepEqual(visited, [3]);
    assert.equal(descendants(pager).filter(node => node.tag === 'button' && node.text === 'Go').length, 0);
  });
}

for (const view of ['deliveries', 'audit']) {
  test(`${view} exposes its Bottom shortcut in the visible page header`, () => {
    const bottom = {};
    // The shortcut may already have moved out of its original view section.
    const section = {querySelector: () => null};
    const source = read('page_headers.js');
    const start = source.indexOf('  function normalActionNodes(');
    const end = source.indexOf('\n  function syncPageHeader(', start);
    const pagerId = view === 'deliveries' ? 'delivery-pagination' : 'audit-pagination';
    const context = {document: {
      getElementById: () => null,
      querySelector: selector => selector === `[data-qa-bottom="${pagerId}"]` ? bottom : null,
    }};
    vm.runInNewContext(source.slice(start, end), context);
    assert.ok(context.normalActionNodes(view, section).includes(bottom));
  });
}
