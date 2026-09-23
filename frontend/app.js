import { MOCK_MODE } from './config.js';
import { getFilters, recommend } from './api.js';
import { renderRecommendations, renderSkeletons } from './cards.js';
import { MOCK_REQUESTS } from './mocks.js';
import { createFormState } from './form-state.js';

const form = document.querySelector('#order-form');
const result = document.querySelector('#result');
const fields = document.querySelector('#fields');
const scenario = document.querySelector('#scenario');
const filterStatus = document.querySelector('#filters-status');
const status = document.querySelector('#request-status');
const summary = document.querySelector('#request-summary');
const stale = document.querySelector('#stale-notice');
const names = ['event_format', 'category', 'city', 'event_date', 'budget_kzt', 'duration_hours', 'language'];
const formState = createFormState(form, names, MOCK_MODE, scenario);
let pending = false;
let filters;
let hasResult = false;
let lastSubmittedKey = null;
const formKey = () => JSON.stringify(names.map(name => form.elements[name].value).concat(scenario.value));
const modeLink = document.querySelector('#mode-link');
modeLink.textContent = MOCK_MODE ? 'Перейти к сервису' : 'Открыть демо';
modeLink.href = MOCK_MODE ? '?demo=0' : '?demo=1';
document.querySelector('#demo').hidden = !MOCK_MODE;

function today() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}
function displayDate(value) { return value.split('-').reverse().join('.'); }
function setError(name, message) {
  if (!names.includes(name)) return;
  document.getElementById(`${name}-error`).textContent = message;
  form.elements[name].setAttribute('aria-invalid', String(Boolean(message)));
  if (message && form.elements[name].closest('details')) form.elements[name].closest('details').open = true;
}
function clearErrors() { names.forEach(name => setError(name, '')); }
function validate() {
  const values = Object.fromEntries(new FormData(form));
  const errors = {};
  for (const name of ['event_format', 'category', 'city', 'event_date', 'budget_kzt']) {
    if (!values[name]?.trim()) errors[name] = 'Заполните это поле.';
  }
  if (!errors.budget_kzt && (!Number.isSafeInteger(Number(values.budget_kzt)) || Number(values.budget_kzt) <= 0)) errors.budget_kzt = 'Введите целую сумму больше 0 ₸.';
  if (values.duration_hours && (!Number.isFinite(Number(values.duration_hours)) || Number(values.duration_hours) <= 0)) errors.duration_hours = 'Введите число часов больше 0.';
  if (form.elements.duration_hours.validity.badInput) errors.duration_hours = 'Введите корректное число часов.';
  const minimum = MOCK_MODE ? filters.event_date_range.min : [today(), filters.event_date_range.min].sort().at(-1);
  form.elements.event_date.min = minimum;
  if (!errors.event_date && (!/^\d{4}-\d{2}-\d{2}$/.test(values.event_date) || !Number.isFinite(Date.parse(values.event_date)))) errors.event_date = 'Укажите корректную дату.';
  if (!errors.event_date && (values.event_date < minimum || values.event_date > filters.event_date_range.max)) errors.event_date = `Выберите дату с ${displayDate(minimum)} по ${displayDate(filters.event_date_range.max)}.`;
  for (const name of names) setError(name, errors[name] || '');
  formState.refresh();
  if (Object.keys(errors).length) { form.elements[Object.keys(errors)[0]].focus(); return null; }
  return {
    city: values.city, event_date: values.event_date, event_format: values.event_format,
    category: values.category, budget_kzt: Number(values.budget_kzt),
    duration_hours: values.duration_hours ? Number(values.duration_hours) : null,
    language: values.language || null,
  };
}
function message(container, title, text, error = false) {
  container.classList.add('message-state');
  const icon = document.createElement('div'); icon.className = 'state-illustration'; icon.textContent = error ? '↺' : '✳'; icon.setAttribute('aria-hidden', 'true');
  container.append(icon);
  const heading = document.createElement('h3'); heading.textContent = title;
  const paragraph = document.createElement('p'); paragraph.textContent = text;
  container.append(heading, paragraph);
  if (!error) container.append(button('Изменить пожелания', () => {
    form.elements.category.focus();
    form.elements.category.scrollIntoView?.({ block: 'center', behavior: 'auto' });
  }));
}
async function showResult(render, animate = false) {
  const previous = result.querySelector('.result-view');
  const next = document.createElement('div'); next.className = 'result-view';
  render(next);
  const reducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? true;
  if (!animate || !previous || reducedMotion) {
    result.replaceChildren(next);
    return;
  }
  // Keep both views in the same grid cell for the cross-fade. Only the new view
  // remains in the accessibility tree; the outgoing layer cannot receive input.
  previous.inert = true;
  previous.setAttribute('aria-hidden', 'true');
  previous.classList.add('view-exit');
  next.classList.add('view-enter');
  result.append(next);
  await new Promise(resolve => setTimeout(resolve, 240));
  previous.remove();
  next.classList.remove('view-enter');
}
function button(label, action) {
  const node = document.createElement('button'); node.type = 'button'; node.className = 'retry'; node.textContent = label;
  node.addEventListener('click', action); return node;
}
function markStale() { stale.hidden = !hasResult || formKey() === lastSubmittedKey; }
function fillExample(key) {
  const values = MOCK_REQUESTS[key] || MOCK_REQUESTS.success;
  for (const name of names) form.elements[name].value = values[name] ?? '';
  form.querySelector('.preferences').open = Boolean(values.language || values.duration_hours);
  clearErrors(); markStale(); formState.changed();
}
async function submit(request) {
  if (pending) return;
  pending = true; fields.disabled = true; scenario.disabled = true;
  stale.hidden = true; summary.hidden = false;
  const p = request.payload;
  const shown = MOCK_MODE ? MOCK_REQUESTS[request.scenario] || MOCK_REQUESTS.success : p;
  summary.textContent = [MOCK_MODE ? 'Сценарий демо' : null, shown.city, shown.category, shown.event_format,
    displayDate(shown.event_date), `до ${new Intl.NumberFormat('ru-RU').format(shown.budget_kzt)} ₸`,
    shown.language, shown.duration_hours ? `${shown.duration_hours} ч` : null].filter(Boolean).join(' · ');
  status.textContent = 'Подбираем подрядчиков.';
  result.setAttribute('aria-busy', 'true');
  await showResult(view => renderSkeletons(view, true), true);
  let invalidField;
  try {
    const data = await recommend(p, request.scenario);
    if (data.outcome === 'matches') await showResult(view => renderRecommendations(view, data), true);
    else await showResult(view => message(view, data.outcome === 'category_absent' ? 'В городе нет этой категории' : 'Нет подходящих вариантов', data.message), true);
    status.textContent = data.message;
  } catch (error) {
    status.textContent = error.message;
    clearErrors();
    for (const [name, text] of Object.entries(error.fieldErrors || {})) {
      if (names.includes(name)) { setError(name, text); invalidField ||= name; }
    }
    await showResult(view => {
      message(view, 'Попробуем ещё раз?', error.message, true);
      if (!invalidField) view.append(button('Повторить', () => submit(request)));
    }, true);
  } finally {
    pending = false; fields.disabled = false; scenario.disabled = false;
    result.setAttribute('aria-busy', 'false'); hasResult = true;
    formState.refresh();
    lastSubmittedKey = request.key; markStale();
    if (invalidField) form.elements[invalidField].focus();
    else document.querySelector('#results-title').focus({ preventScroll: true });
  }
}
function options(name, values, placeholder) {
  const select = form.elements[name]; select.replaceChildren(new Option(placeholder, ''));
  values.forEach(value => select.add(new Option(value, value)));
}
async function loadFilters() {
  filterStatus.replaceChildren(); filterStatus.textContent = 'Загружаем параметры каталога…';
  fields.disabled = true; scenario.disabled = true;
  try {
    filters = await getFilters();
    options('city', filters.cities, 'Выберите город');
    options('event_format', filters.event_formats, 'Какой у вас повод?');
    options('category', filters.categories, 'Выберите специалиста');
    options('language', filters.languages, 'Любой');
    const minimum = MOCK_MODE ? filters.event_date_range.min : [today(), filters.event_date_range.min].sort().at(-1);
    form.elements.event_date.min = minimum; form.elements.event_date.max = filters.event_date_range.max;
    document.querySelector('#date-help').textContent = `Календарь: ${displayDate(filters.event_date_range.min)}–${displayDate(filters.event_date_range.max)}`;
    if (minimum > filters.event_date_range.max) {
      filterStatus.textContent = 'Календарь каталога закончился. Для реального подбора нужны новые данные; демо доступно по ссылке сверху.';
      return;
    }
    filterStatus.textContent = ''; fields.disabled = false; scenario.disabled = false;
    if (!formState.restore() && MOCK_MODE) fillExample(scenario.value);
    formState.refresh();
  } catch (error) {
    filterStatus.textContent = error.message + ' ';
    filterStatus.append(button('Повторить загрузку', loadFilters));
  }
}
form.addEventListener('submit', event => {
  event.preventDefault(); if (pending || !filters) return;
  const payload = validate(); if (!payload) return;
  submit({ payload, scenario: scenario.value, key: formKey() });
});
form.addEventListener('input', event => {
  if (names.includes(event.target.name)) {
    setError(event.target.name, '');
    formState.changed();
  }
  markStale();
});
form.addEventListener('change', event => {
  if (names.includes(event.target.name)) formState.changed();
  markStale();
});
scenario.addEventListener('change', () => { fillExample(scenario.value); markStale(); });
form.querySelectorAll('[data-example]').forEach(node => node.addEventListener('click', () => {
  if (MOCK_MODE) scenario.value = node.dataset.example;
  fillExample(node.dataset.example);
}));
showResult(view => renderSkeletons(view));
loadFilters();
