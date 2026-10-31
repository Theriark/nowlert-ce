import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

// THE-1676: the assigned-integration icon row of a destination card is built from
// state.routes, but the card reconciliation signature only covered the destination
// item, its test result and the viewer's permissions. A card first painted while
// /api/v2/routes had not answered (or had failed, as in the admin-only 500 burst
// right after the first sign-in) kept its empty icon row through every later
// render, even after the routes arrived. The signature must change when the
// assigned sources change so the row is repainted.

const read = name => readFileSync(new URL(`../../src/webui/${name}`, import.meta.url), 'utf8');
const appSource = read('app.js');

function functionSource(name) {
  const start = appSource.indexOf(`\nfunction ${name}(`) + 1;
  assert.notEqual(start, 0, `function ${name} not found`);
  const end = appSource.indexOf('\n}', start);
  return appSource.slice(start, end + 2);
}

class FakeNode {
  constructor(tag) {
    this.tagName = tag.toUpperCase();
    this.children = [];
    this.parentNode = null;
    this.dataset = {};
    this.attributes = {};
    this.textContent = '';
    this._className = '';
  }
  get className() { return this._className; }
  set className(value) { this._className = String(value); }
  get classList() {
    const node = this;
    return {
      contains(name) { return node._className.split(/\s+/).includes(name); },
      add(...names) {
        const current = new Set(node._className.split(/\s+/).filter(Boolean));
        names.forEach(name => current.add(name));
        node._className = [...current].join(' ');
      },
    };
  }
  get childNodes() { return [...this.children]; }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  append(...nodes) { nodes.forEach(node => this.insertBefore(node, null)); }
  remove() {
    if (!this.parentNode) return;
    const siblings = this.parentNode.children;
    siblings.splice(siblings.indexOf(this), 1);
    this.parentNode = null;
  }
  replaceChildren(...nodes) {
    [...this.children].forEach(child => child.remove());
    this.append(...nodes);
  }
  insertBefore(node, reference) {
    if (node.parentNode) node.remove();
    node.parentNode = this;
    const index = reference ? this.children.indexOf(reference) : -1;
    if (index < 0) this.children.push(node);
    else this.children.splice(index, 0, node);
    return node;
  }
  matches(selector) {
    return selector.split(/(?=[.[])/).filter(Boolean).every(part => {
      if (part.startsWith('.')) return this.classList.contains(part.slice(1));
      const attribute = part.slice(1, -1);
      if (!attribute.startsWith('data-')) return false;
      const key = attribute.slice(5).replace(/-([a-z])/g, (_, letter) => letter.toUpperCase());
      return this.dataset[key] !== undefined;
    });
  }
  querySelectorAll(selector) {
    assert.ok(selector.startsWith(':scope > '), `unsupported selector ${selector}`);
    return this.children.filter(child => child.matches(selector.slice(':scope > '.length)));
  }
  descendants() {
    return this.children.flatMap(child => [child, ...child.descendants()]);
  }
}

function element(tag, options = {}, children = []) {
  const item = new FakeNode(tag);
  if (options.className) item.className = options.className;
  if (options.text !== undefined) item.textContent = String(options.text);
  if (options.title) item.title = options.title;
  if (options.type) item.type = options.type;
  if (options.disabled) item.disabled = true;
  for (const [name, value] of Object.entries(options.attributes || {})) item.setAttribute(name, value);
  for (const [name, value] of Object.entries(options.dataset || {})) item.dataset[name] = String(value);
  const values = Array.isArray(children) ? children : [children];
  for (const child of values) {
    if (child === null || child === undefined) continue;
    item.append(child instanceof FakeNode ? child : Object.assign(new FakeNode('#text'), {textContent: String(child)}));
  }
  return item;
}

function destination(id, name) {
  return {id, name, output_type: 'slack', enabled: true, shared: true, owned: true, secret_configured: true, settings: {channel_name: '#ops'}};
}

function route(id, source, destinationIds) {
  return {id, source, destination_ids: destinationIds, enabled: true};
}

// The real helper from destination_routes.js: a route counts for a card when its
// destination_ids contain the destination (or the destination lists the route).
const destinationRoutesSource = read('destination_routes.js');
const helperStart = destinationRoutesSource.indexOf('function destinationRouteSourcesForItem(');
const helperEnd = destinationRoutesSource.indexOf('\n}', helperStart);
const destinationRouteSourcesForItem = vm.runInNewContext(
  `(${destinationRoutesSource.slice(helperStart, helperEnd + 2)})`,
  {Array, String, Map, Set},
);

function harness(destinations, routes) {
  const container = new FakeNode('div');
  const context = {
    JSON, String, Array, Map, WeakMap, Number, Object,
    state: {destinations, routes, integrations: [], destinationTestResults: {}, user: {id: 'admin', role: 'admin'}},
    byId: () => container,
    element,
    actionButton: (label, action, id, style = 'secondary') => element('button', {className: `button small ${style}`, text: label, dataset: {action, id}}),
    badge: (label, style = '') => element('span', {className: `badge ${style}`.trim(), text: label}),
    isAdmin: () => true,
    ownResource: () => true,
    destinationRouteSourcesForItem,
    integrationBySource: () => null,
    sourceIcon: source => element('img', {className: 'source-product-icon', dataset: {sourceKey: source}}),
    routeSourceDescriptor: source => ({integration: String(source)}),
    outputIcon: () => element('span'),
    friendlyName: value => String(value),
    destinationTestResult: () => null,
    destinationTestDetail: () => '',
    OUTPUT_NAMES: {slack: 'Slack'},
  };
  vm.runInNewContext(
    `const destinationCardSignatures = new WeakMap();\n${functionSource('empty')}\n${functionSource('renderDestinations')}`,
    context,
  );
  return {container, context};
}

function iconKeys(container) {
  return container.children.map(card => {
    const row = card.descendants().find(node => node.classList.contains('destination-assigned-route-icons'));
    assert.ok(row, 'every destination card carries an icon row');
    return row.children.map(icon => icon.dataset.sourceKey).join('+');
  });
}

test('a card painted before the routes answered gets its icon row once the routes arrive', () => {
  const {container, context} = harness([destination('a', 'Slack ops'), destination('b', 'Teams noc')], []);
  context.renderDestinations();
  assert.deepEqual(iconKeys(container), ['', '']);

  context.state.routes = [route('r1', 'proxmox', ['a']), route('r2', 'unifi_network', ['a']), route('r3', 'synology', ['b'])];
  context.renderDestinations();
  assert.deepEqual(iconKeys(container), ['proxmox+unifi_network', 'synology']);
});

test('a route moved away from a destination clears its icon on the next render', () => {
  const {container, context} = harness([destination('a', 'Slack ops')], [route('r1', 'proxmox', ['a'])]);
  context.renderDestinations();
  assert.deepEqual(iconKeys(container), ['proxmox']);

  context.state.routes = [route('r1', 'proxmox', [])];
  context.renderDestinations();
  assert.deepEqual(iconKeys(container), ['']);
});

test('an unchanged card is not repainted when the routes are unchanged', () => {
  const {container, context} = harness([destination('a', 'Slack ops')], [route('r1', 'proxmox', ['a'])]);
  context.renderDestinations();
  const [card] = container.children;
  const [heading] = card.children;
  context.renderDestinations();
  assert.equal(container.children[0], card);
  assert.equal(card.children[0], heading, 'same routes and item must keep the rendered children');
});
