import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { initializeGuide } from '../../frontend/guide.js';
import { validateValues, MAX_BUDGET_KZT, MAX_DURATION_HOURS } from '../../frontend/validation.js';

globalThis.window = { location: new URL('http://127.0.0.1:8013/ui/') };
const api = await import('../../frontend/api.js');
const { initializeAssistantPreview } = await import('../../frontend/assistant-preview.js');
const { MOCK_REQUESTS, MOCK_RESPONSES, MOCK_FILTERS } = await import('../../frontend/mocks.js');
const configPath = new URL('../../frontend/config.js', import.meta.url);
const values = Object.fromEntries(Object.entries(MOCK_REQUESTS.success).map(([key, value]) => [key, String(value ?? '')]));
const range = MOCK_FILTERS.event_date_range;
const json = (data, status = 200) => new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json' } });

test('handbook opens and closes accessibly without network requests', () => {
  const nodes = Object.fromEntries(['guide-toggle', 'guide-panel', 'guide-title', 'guide-close'].map(id => [id, {
    hidden: true, attributes: {}, events: {}, focused: false,
    setAttribute(name, value) { this.attributes[name] = value; },
    addEventListener(name, handler) { this.events[name] = handler; },
    focus() { this.focused = true; },
  }]));
  const originalDocument = globalThis.document, originalFetch = globalThis.fetch;
  globalThis.document = { querySelector: selector => nodes[selector.slice(1)] };
  globalThis.fetch = () => { assert.fail('Handbook must stay entirely local'); };
  try {
    initializeGuide();
    const toggle = nodes['guide-toggle'], panel = nodes['guide-panel'];
    assert.equal(toggle.hidden, false);
    toggle.events.click();
    assert.equal(panel.hidden, false);
    assert.equal(toggle.attributes['aria-expanded'], 'true');
    assert.equal(nodes['guide-title'].focused, true);
    panel.events.keydown({ key: 'Escape', preventDefault() {} });
    assert.equal(panel.hidden, true);
    assert.equal(toggle.attributes['aria-expanded'], 'false');
    assert.equal(toggle.focused, true);
    toggle.events.click(); nodes['guide-close'].events.click();
    assert.equal(panel.hidden, true);
    toggle.events.click(); toggle.events.click();
    assert.equal(panel.hidden, true);
  } finally { globalThis.document = originalDocument; globalThis.fetch = originalFetch; }
});

test('handbook explains the site and does not contain chat inputs', async () => {
  const html = await readFile(new URL('../../frontend/index.html', import.meta.url), 'utf8');
  const guide = html.slice(html.indexOf('<aside class="site-guide"'));
  assert.doesNotMatch(guide, /<(?:input|textarea|form)\b/);
  assert.equal((guide.match(/<summary>/g) || []).length, 9);
  for (const text of ['Для чего нужен этот сайт?', 'С чего начать подбор?', 'Это не рейтинг качества.', 'бронирование и оплата не подключены.']) assert.ok(guide.includes(text));
});

test('API follows preview or deployed origin; 5173 retains local development API', async () => {
  for (const [origin, expected] of [
    ['http://127.0.0.1:8013/ui/', 'http://127.0.0.1:8013'],
    ['https://example.test/ui/', 'https://example.test'],
    ['http://localhost:5173/', 'http://localhost:8000'],
    ['http://localhost:5173/ui/', 'http://localhost:5173'],
  ]) {
    window.location = new URL(origin);
    const config = await import(`${configPath.href}?test=${encodeURIComponent(origin)}`);
    assert.equal(config.API_URL, `${expected}/recommendations`);
    assert.equal(config.FILTERS_URL, `${expected}/filters`);
    assert.equal(config.MOCK_MODE, false);
  }
});
test('form accepts demo request and backend boundary values', () => {
  for (const extra of [{}, { budget_kzt: String(MAX_BUDGET_KZT), duration_hours: String(MAX_DURATION_HOURS) },
    { event_date: range.min, duration_hours: '0.05' }, { event_date: range.max }]) {
    assert.deepEqual(validateValues({ ...values, ...extra }, range), {});
  }
});
test('form rejects invalid numbers, missing fields and impossible/out-of-range dates', () => {
  const cases = { budget_kzt: ['', '0', '-1', '1.5', '1000000001', 'Infinity'],
    duration_hours: ['0', '-1', '169', 'Infinity', 'abc'],
    event_date: ['', '2026-11-31', '2026-09-22', '2027-01-01'], city: [''] };
  for (const [field, casesForField] of Object.entries(cases)) for (const value of casesForField) {
    assert.ok(validateValues({ ...values, [field]: value }, range)[field], `${field}=${value}`);
  }
});
test('real mode sends exact JSON contract and preserves backend explanations', async () => {
  globalThis.fetch = async (url, options) => {
    assert.equal(url, 'http://127.0.0.1:8013/recommendations');
    assert.equal(options.method, 'POST');
    assert.equal(options.headers['Content-Type'], 'application/json');
    assert.deepEqual(JSON.parse(options.body), MOCK_REQUESTS.success);
    return json(MOCK_RESPONSES.success);
  };
  assert.deepEqual(await api.recommend(MOCK_REQUESTS.success), MOCK_RESPONSES.success);
});
test('filters load from live API and invalid contracts are rejected', async () => {
  globalThis.fetch = async url => { assert.equal(url, 'http://127.0.0.1:8013/filters'); return json(MOCK_FILTERS); };
  assert.deepEqual(await api.getFilters(), MOCK_FILTERS);
  globalThis.fetch = async () => json({});
  await assert.rejects(api.getFilters(), api.ApiError);
  await assert.rejects(api.recommend(MOCK_REQUESTS.success), api.ApiError);
});
test('all three outcomes remain distinct; empty success and missing explanations fail closed', async () => {
  for (const key of ['success', 'rare', 'no_match', 'no_category']) {
    globalThis.fetch = async () => json(MOCK_RESPONSES[key]);
    assert.deepEqual(await api.recommend(MOCK_REQUESTS.success), MOCK_RESPONSES[key]);
  }
  for (const bad of [{ ...MOCK_RESPONSES.success, cards: [] },
    { ...MOCK_RESPONSES.success, cards: [{ ...MOCK_RESPONSES.success.cards[0], explanation: '' }] }]) {
    globalThis.fetch = async () => json(bad);
    await assert.rejects(api.recommend(MOCK_REQUESTS.success), api.ApiError);
  }
});
test('422 errors map to fields without reflecting raw input', async () => {
  globalThis.fetch = async () => json({ detail: [{ loc: ['body', 'budget_kzt'], msg: 'Too large', input: '<script>' }] }, 422);
  await assert.rejects(api.recommend(MOCK_REQUESTS.success), error => {
    assert.deepEqual(error.fieldErrors, { budget_kzt: 'Too large' });
    assert.ok(!error.message.includes('<script>')); return true;
  });
});
test('network, timeout, invalid JSON and HTTP errors never silently return mocks', async () => {
  for (const status of [400, 408, 413, 415, 429, 500, 503]) {
    globalThis.fetch = async () => json({ detail: 'untrusted internals' }, status);
    await assert.rejects(api.recommend(MOCK_REQUESTS.success), error => error instanceof api.ApiError && !error.message.includes('untrusted'));
  }
  for (const error of [new TypeError('Failed to fetch'), new DOMException('aborted', 'AbortError')]) {
    globalThis.fetch = async () => { throw error; };
    await assert.rejects(api.recommend(MOCK_REQUESTS.success), api.ApiError);
  }
  globalThis.fetch = async () => new Response('<html>Proxy error</html>');
  await assert.rejects(api.recommend(MOCK_REQUESTS.success), api.ApiError);
});
test('card renderer uses text nodes and retains explanation and data-quality flags', async () => {
  const source = await readFile(new URL('../../frontend/cards.js', import.meta.url), 'utf8');
  assert.doesNotMatch(source, /\.innerHTML\s*=/);
  for (const name of ['explanation', 'synthetic', 'city_imputed', 'price_imputed']) assert.ok(source.includes(name));
});

test('assistant opens, closes by Escape, confirms parsed criteria and hands off to main form', async () => {
  const nodes = Object.fromEntries(['describe-event', 'event-assistant-panel', 'event-assistant-title',
    'assistant-preview-close', 'assistant-use-form', 'event-description', 'assistant-reply', 'assistant-understood',
    'assistant-apply', 'assistant-fields', 'assistant-reset', 'event-description-form'].map(id => [id, {
      hidden: id === 'event-assistant-panel', disabled: true, attributes: {}, events: {}, focused: false, value: '',
      setAttribute(name, value) { this.attributes[name] = value; },
      addEventListener(name, handler) { this.events[name] = handler; },
      focus() { this.focused = true; },
      querySelectorAll() { return []; }, replaceChildren() {}, append() {},
    }]));
  const originalDocument = globalThis.document;
  const originalFetch = globalThis.fetch;
  let usedForm = 0, networkCalls = 0, applied;
  globalThis.document = { querySelector: selector => nodes[selector.slice(1)], addEventListener() {}, createElement: () => ({ append() {} }) };
  globalThis.fetch = () => { networkCalls++; throw new Error('Preview must not call the bot'); };
  try {
    initializeAssistantPreview(() => usedForm++, context => { applied = context; return true; },
      async () => ({context: MOCK_REQUESTS.success, complete: true, reply: 'Ready'}));
    const trigger = nodes['describe-event'], panel = nodes['event-assistant-panel'];
    assert.equal(trigger.disabled, false);
    trigger.events.click();
    assert.equal(panel.hidden, false);
    assert.equal(trigger.attributes['aria-expanded'], 'true');
    assert.equal(nodes['event-description'].focused, true);
    panel.events.keydown({ key: 'Escape', preventDefault() {} });
    assert.equal(panel.hidden, true);
    assert.equal(trigger.focused, true);
    assert.equal(trigger.attributes['aria-expanded'], 'false');
    trigger.events.click(); trigger.events.click();
    assert.equal(panel.hidden, true);
    trigger.events.click(); nodes['assistant-preview-close'].events.click();
    assert.equal(panel.hidden, true);
    trigger.events.click(); nodes['assistant-use-form'].events.click();
    assert.equal(panel.hidden, true);
    assert.equal(usedForm, 1);
    trigger.events.click();
    nodes['event-description'].value = 'свадьба';
    await nodes['event-description-form'].events.submit({ preventDefault() {} });
    assert.equal(nodes['assistant-apply'].hidden, false);
    await nodes['assistant-apply'].events.click();
    assert.deepEqual(applied, MOCK_REQUESTS.success);
    assert.equal(panel.hidden, true);
    assert.equal(networkCalls, 0);
  } finally { globalThis.document = originalDocument; globalThis.fetch = originalFetch; }
});
