import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

// The language list shows English and Português once. en-US and pt-BR stay
// available only while they are the saved value.
const source = readFileSync(new URL('../../src/webui/i18n.js', import.meta.url), 'utf8');
function block(start, end) {
  const from = source.indexOf(start);
  const to = source.indexOf(end, from);
  assert.ok(from >= 0 && to > from, `${start} exists in i18n.js`);
  return source.slice(from, to);
}

function fakeSelect(values) {
  const select = {
    children: [],
    get options() { return this.children; },
    get value() { return (this.children.find(option => option.selected) || this.children[0] || {}).value || ''; },
    set value(next) { for (const option of this.children) option.selected = option.value === next; },
    querySelector(selector) {
      const value = selector.match(/value="([^"]+)"/)[1];
      return this.children.find(option => option.value === value) || null;
    },
    insertBefore(option, before) {
      const index = before ? this.children.indexOf(before) : -1;
      option.parent = this;
      if (index < 0) this.children.push(option); else this.children.splice(index, 0, option);
    },
  };
  for (const value of values) {
    select.insertBefore({
      value, textContent: value, hidden: false, selected: false, dataset: {},
      get nextSibling() { const list = this.parent.children; return list[list.indexOf(this) + 1] || null; },
      remove() { const list = this.parent.children; list.splice(list.indexOf(this), 1); },
    }, null);
  }
  return select;
}

function languageContext(saved) {
  const select = fakeSelect(['en-GB', 'en-US', 'pt-PT', 'pt-BR', 'es-ES']);
  const context = {
    byId: id => (id === 'preference-language' ? select : null),
    state: {preferences: {language: saved}},
    renderPreferences() { select.value = context.state.preferences.language; },
  };
  const code = [
    block('  const regionalDetachedLanguageAliases', '  applyLanguage = function'),
    block('  const regionalOriginalRenderPreferences', '  if (document.readyState'),
  ].join('\n');
  vm.runInNewContext(code, context);
  return {context, select};
}

const visible = select => select.options.filter(option => !option.hidden).map(option => option.textContent);
const listed = select => select.options.map(option => option.value);

test('the language list names English and Português once', () => {
  const {context, select} = languageContext('pt-PT');
  context.renderPreferences();
  assert.deepEqual(listed(select), ['en-GB', 'pt-PT', 'es-ES']);
  assert.deepEqual(visible(select), ['English', 'Português', 'es-ES']);
  assert.equal(select.value, 'pt-PT');
});

test('a saved en-US value still shows and the list returns to one English later', () => {
  const {context, select} = languageContext('en-US');
  context.renderPreferences();
  assert.equal(select.value, 'en-US');
  assert.deepEqual(listed(select), ['en-GB', 'en-US', 'pt-PT', 'es-ES']);

  context.state.preferences.language = 'en-GB';
  context.renderPreferences();
  assert.deepEqual(listed(select), ['en-GB', 'pt-PT', 'es-ES']);

  context.state.preferences.language = 'pt-BR';
  context.renderPreferences();
  assert.equal(select.value, 'pt-BR');
  assert.deepEqual(listed(select), ['en-GB', 'pt-PT', 'pt-BR', 'es-ES']);
});
