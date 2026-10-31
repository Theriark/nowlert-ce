import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

// THE-1654: an admin Destinations list rendered once while state.destinations was
// still empty (direct load of /#destinations before the workspace answered, or a
// failed first /destinations request) kept its "No destinations" placeholder when
// the cards arrived. professional.css then switched the list to display:block and
// every card became a full-width row. renderDestinations must never leave an
// .empty-state child next to destination cards.

const read = name => readFileSync(new URL(`../../src/webui/${name}`, import.meta.url), 'utf8');
const appSource = read('app.js');

function functionSource(name) {
  const start = appSource.indexOf(`\nfunction ${name}(`) + 1;
  assert.notEqual(start, 0, `function ${name} not found`);
  const end = appSource.indexOf('\n}', start);
  return appSource.slice(start, end + 2);
}

// Minimal DOM stand-in: only what renderDestinations and empty() touch.
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

function privateCard(id) {
  const card = element('article', {className: 'resource-card acceptance-private-destination'});
  card.dataset.privateDestinationId = id;
  return card;
}

function harness(destinations) {
  const container = new FakeNode('div');
  const context = {
    JSON, String, Array, Map, WeakMap, Number, Object,
    state: {destinations, routes: [], integrations: [], destinationTestResults: {}, user: {id: 'admin', role: 'admin'}},
    byId: () => container,
    element,
    actionButton: (label, action, id, style = 'secondary') => element('button', {className: `button small ${style}`, text: label, dataset: {action, id}}),
    badge: (label, style = '') => element('span', {className: `badge ${style}`.trim(), text: label}),
    isAdmin: () => true,
    ownResource: () => true,
    destinationRouteSourcesForItem: () => [],
    sourceIcon: () => element('img'),
    routeSourceDescriptor: () => ({integration: ''}),
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

const shape = container => container.children.map(child => (
  child.classList.contains('empty-state') ? 'empty'
    : child.classList.contains('acceptance-private-destination') ? 'private'
      : child.dataset.destinationId ? 'card' : child.tagName
)).join(',');

test('an empty first paint followed by the loaded destinations leaves no empty-state node', () => {
  const {container, context} = harness([]);
  context.renderDestinations();
  assert.equal(shape(container), 'empty');

  context.state.destinations = [destination('a', 'Slack ops'), destination('b', 'Teams noc')];
  context.renderDestinations();
  assert.equal(shape(container), 'card,card');
  assert.equal(container.querySelectorAll(':scope > .empty-state').length, 0);
});

test('admin private view-only cards appended after the placeholder keep their place behind the real cards', () => {
  // The acceptance wrapper appends private metadata cards to the list; on Development
  // the admin saw 5 cards, the stale placeholder at index 5 and 14 private cards.
  const {container, context} = harness([]);
  context.renderDestinations();
  container.append(privateCard('p1'), privateCard('p2'));
  assert.equal(shape(container), 'empty,private,private');

  context.state.destinations = [destination('a', 'Slack ops'), destination('b', 'Teams noc'), destination('c', 'Webhook')];
  context.renderDestinations();
  assert.equal(shape(container), 'card,card,card,private,private');
});

test('a list that becomes empty again shows exactly one placeholder', () => {
  const {container, context} = harness([destination('a', 'Slack ops')]);
  context.renderDestinations();
  assert.equal(shape(container), 'card');
  context.state.destinations = [];
  context.renderDestinations();
  assert.equal(shape(container), 'empty');
  context.renderDestinations();
  assert.equal(shape(container), 'empty');
});

test('the block-layout rule only applies to a list without destination cards', () => {
  const professional = read('professional.css');
  assert.ok(
    professional.includes('#view-destinations #destination-list:has(> .empty-state):not(:has(> .resource-card[data-destination-id])) {\n  display: block;\n}'),
    'professional.css must scope the display:block empty-state rule to lists without destination cards',
  );
  assert.equal(professional.includes('#destination-list:has(> .empty-state) {'), false);
});
