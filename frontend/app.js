import { t, locale, language, initializeLocale, translateTree } from './i18n.js';
import { initializeTheme } from './theme.js';
import { initializeCatalog } from './catalog.js';
import { initializeAssistantUI } from './assistant-ui.js';
import { initializeMotion } from './motion.js';
import { MOCK_MODE } from './config.js';
import { getFilters, recommend } from './api.js';
import { renderRecommendations, renderSkeletons } from './cards.js';
import { MOCK_REQUESTS } from './mocks.js';
import { createFormState } from './form-state.js';

initializeLocale();
translateTree(document);
const theme = initializeTheme({ getLabel: isDark => t(isDark ? 'Переключить на светлую тему' : 'Переключить на тёмную тему') });

const form = document.querySelector('#order-form');
const result = document.querySelector('#result');
const fields = document.querySelector('#fields');
const scenario = document.querySelector('#scenario');
const filterStatus = document.querySelector('#filters-status');
const status = document.querySelector('#request-status');
const stale = document.querySelector('#stale-notice');
const names = ['event_format', 'category', 'city', 'event_date', 'budget_kzt', 'duration_hours', 'language'];
const formState = createFormState(form, names, MOCK_MODE, scenario);
let pending = false;
let filters;
let hasResult = false;
let lastSubmittedKey = null;
let currentRenderer = null;
let recapOrder = null;
let filterMessage = null;
let requestError = null;
const fieldMessages = {};
const errorText = error => t(error.rawMessage || error.message, error.messageVars || {});
const formKey = () => JSON.stringify(names.map(name => form.elements[name].value).concat(scenario.value));
const modeLink = document.querySelector('#mode-link');
modeLink.textContent = t(MOCK_MODE ? 'Перейти к сервису' : 'Открыть демо');
modeLink.href = MOCK_MODE ? '?demo=0' : '?demo=1';
document.querySelector('#demo').hidden = !MOCK_MODE;

const editSearch = document.querySelector('#edit-search');
const searchRecap = document.querySelector('#search-recap');
function expandSearch(focus = true) {
  fields.hidden = false;
  form.classList.remove('is-compact');
  form.querySelector('.form-heading h2').textContent = t('Расскажите о событии');
  editSearch.setAttribute('aria-expanded', 'true');
  editSearch.hidden = true; searchRecap.hidden = true;
  if (focus) {
    form.elements.category.focus();
    form.scrollIntoView?.({ block: 'start', behavior: 'auto' });
  }
}
function collapseSearch(order) {
  recapOrder = order;
  fields.hidden = true;
  form.classList.add('is-compact');
  form.querySelector('.form-heading h2').textContent = t(MOCK_MODE ? 'Параметры демо-сценария' : 'Параметры вашего события');
  editSearch.setAttribute('aria-expanded', 'false');
  const totalMinutes = order.duration_hours == null ? null : Math.round(order.duration_hours * 60);
  const duration = totalMinutes === null ? t('Не указана') : totalMinutes === 0 ? t('Менее 1 мин') :
    [Math.floor(totalMinutes / 60) ? t('{hours} ч', { hours: Math.floor(totalMinutes / 60) }) : '', totalMinutes % 60 ? t('{minutes} мин', { minutes: totalMinutes % 60 }) : ''].filter(Boolean).join(' ');
  const entries = [
    ['Город', t(order.city)],
    ['Кого ищем', t(order.category)],
    ['Событие', t(order.event_format.charAt(0).toUpperCase() + order.event_format.slice(1))],
    ['Дата', new Intl.DateTimeFormat(locale(), { day: 'numeric', month: 'long', year: 'numeric' }).format(new Date(`${order.event_date}T12:00:00`))],
    ['Бюджет', t('До {price} ₸', { price: new Intl.NumberFormat(locale()).format(order.budget_kzt) })],
    ['Язык', t(order.language || 'Любой')],
    ['Длительность', duration],
  ];
  searchRecap.replaceChildren();
  entries.forEach(([label, value]) => {
    const item = document.createElement('div'); item.className = 'recap-item';
    const term = document.createElement('dt'); term.textContent = t(label);
    const description = document.createElement('dd'); description.textContent = value;
    item.append(term, description); searchRecap.append(item);
  });
  searchRecap.hidden = false; editSearch.hidden = false;
}
editSearch.addEventListener('click', () => expandSearch());

function today() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}
function displayDate(value) { return value.split('-').reverse().join('.'); }
function setError(name, message) {
  if (!names.includes(name)) return;
  fieldMessages[name] = message;
  document.getElementById(`${name}-error`).textContent = typeof message === 'object' ? t(message.source, message.vars) : t(message);
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
  if (!errors.event_date && (values.event_date < minimum || values.event_date > filters.event_date_range.max)) errors.event_date = { source: 'Выберите дату с {min} по {max}.', vars: { min: displayDate(minimum), max: displayDate(filters.event_date_range.max) } };
  for (const name of names) setError(name, errors[name] || '');
  formState.refresh();
  if (Object.keys(errors).length) { expandSearch(false); form.elements[Object.keys(errors)[0]].focus(); return null; }
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
  const heading = document.createElement('h3'); heading.textContent = t(title);
  const paragraph = document.createElement('p'); paragraph.textContent = error ? t(text) : text;
  if (!error) { paragraph.dataset.original = ''; paragraph.lang = 'ru'; }
  container.append(heading, paragraph);
  if (!error && language() !== 'ru') { const note = document.createElement('small'); note.className = 'source-language'; note.textContent = t('Текст сервиса на русском'); container.append(note); }
  if (!error) container.append(button('Изменить пожелания', () => {
    expandSearch();
  }));
}
async function showResult(render, animate = false) {
  currentRenderer = render;
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
  const node = document.createElement('button'); node.type = 'button'; node.className = 'retry'; node.textContent = t(label);
  node.addEventListener('click', action); return node;
}
function markStale() { stale.hidden = !hasResult || formKey() === lastSubmittedKey; }
function fillExample(key) {
  expandSearch(false);
  const values = MOCK_REQUESTS[key] || MOCK_REQUESTS.success;
  for (const name of names) form.elements[name].value = values[name] ?? '';
  form.querySelector('.preferences').open = Boolean(values.language || values.duration_hours);
  clearErrors(); markStale(); formState.changed();
}
async function submit(request) {
  if (pending) return;
  requestError = null;
  document.querySelector('.results').hidden = false;
  pending = true; fields.disabled = true; scenario.disabled = true;
  editSearch.disabled = true;
  const submitLabel = form.querySelector('.primary > span');
  submitLabel.textContent = t('Подбираем варианты…');
  stale.hidden = true;
  const p = request.payload;
  const shown = MOCK_MODE ? MOCK_REQUESTS[request.scenario] || MOCK_REQUESTS.success : p;
  status.textContent = t('Подбираем подрядчиков.');
  status.lang = language();
  result.setAttribute('aria-busy', 'true');
  await showResult(view => renderSkeletons(view, true), true);
  let invalidField;
  try {
    const data = await recommend(p, request.scenario);
    if (data.outcome === 'matches') await showResult(view => renderRecommendations(view, data), true);
    else await showResult(view => message(view, data.outcome === 'category_absent' ? 'В городе нет этой категории' : 'Нет подходящих вариантов', data.message), true);
    status.textContent = data.message;
    status.lang = 'ru';
    collapseSearch(shown);
  } catch (error) {
    requestError = error;
    status.textContent = errorText(error);
    status.lang = language();
    clearErrors();
    for (const [name, text] of Object.entries(error.fieldErrors || {})) {
      if (names.includes(name)) { setError(name, text); invalidField ||= name; }
    }
    await showResult(view => {
      message(view, 'Попробуем ещё раз?', errorText(error), true);
      if (!invalidField) view.append(button('Повторить', () => submit(request)));
    }, true);
  } finally {
    pending = false; fields.disabled = false; scenario.disabled = false;
    editSearch.disabled = false;
    form.querySelector('.primary > span').textContent = t('Подобрать подрядчиков');
    result.setAttribute('aria-busy', 'false'); hasResult = true;
    formState.refresh();
    lastSubmittedKey = request.key; markStale();
    if (invalidField) { expandSearch(false); form.elements[invalidField].focus(); }
    else {
      document.querySelector('#results-title').focus({ preventScroll: true });
      document.querySelector('.results').scrollIntoView?.({ block: 'start', behavior: 'auto' });
    }
  }
}
function options(name, values, placeholder) {
  const select = form.elements[name]; select.replaceChildren(new Option(t(placeholder), ''));
  values.forEach(value => select.add(new Option(t(value), value)));
}
function showFilterMessage(source, retry = false, vars = {}) {
  filterMessage = { source, retry, vars };
  filterStatus.replaceChildren(document.createTextNode(t(source, vars)));
  if (retry) filterStatus.append(document.createTextNode(' '), button('Повторить загрузку', loadFilters));
}
async function loadFilters() {
  showFilterMessage('Загружаем параметры каталога…');
  fields.disabled = true; scenario.disabled = true;
  try {
    filters = await getFilters();
    options('city', filters.cities, 'Выберите город');
    options('event_format', filters.event_formats, 'Какой у вас повод?');
    options('category', filters.categories, 'Выберите специалиста');
    options('language', filters.languages, 'Любой');
    const minimum = MOCK_MODE ? filters.event_date_range.min : [today(), filters.event_date_range.min].sort().at(-1);
    form.elements.event_date.min = minimum; form.elements.event_date.max = filters.event_date_range.max;
    document.querySelector('#date-help').textContent = t('Календарь: {min}–{max}', { min: displayDate(filters.event_date_range.min), max: displayDate(filters.event_date_range.max) });
    if (minimum > filters.event_date_range.max) {
      showFilterMessage('Календарь каталога закончился. Для реального подбора нужны новые данные; демо доступно по ссылке сверху.');
      return;
    }
    showFilterMessage(''); fields.disabled = false; scenario.disabled = false;
    if (!formState.restore() && MOCK_MODE) fillExample(scenario.value);
    formState.refresh();
  } catch (error) {
    showFilterMessage(error.rawMessage || error.message, true, error.messageVars);
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
document.addEventListener('localechange', () => {
  translateTree(document);
  theme.refresh();
  modeLink.textContent = t(MOCK_MODE ? 'Перейти к сервису' : 'Открыть демо');
  if (filterMessage) showFilterMessage(filterMessage.source, filterMessage.retry, filterMessage.vars);
  if (filters) {
    const selected = Object.fromEntries(names.map(name => [name, form.elements[name].value]));
    options('city', filters.cities, 'Выберите город');
    options('event_format', filters.event_formats, 'Какой у вас повод?');
    options('category', filters.categories, 'Выберите специалиста');
    options('language', filters.languages, 'Любой');
    for (const name of names) form.elements[name].value = selected[name];
    document.querySelector('#date-help').textContent = t('Календарь: {min}–{max}', { min: displayDate(filters.event_date_range.min), max: displayDate(filters.event_date_range.max) });
  }
  for (const [name, message] of Object.entries(fieldMessages)) setError(name, message);
  formState.refresh();
  if (recapOrder && form.classList.contains('is-compact')) collapseSearch(recapOrder);
  else form.querySelector('.form-heading h2').textContent = t('Расскажите о событии');
  if (currentRenderer) showResult(currentRenderer);
  if (pending || requestError) {
    status.textContent = requestError ? errorText(requestError) : t('Подбираем подрядчиков.');
    status.lang = language();
  }
  form.querySelector('.primary > span').textContent = t(pending ? 'Подбираем варианты…' : 'Подобрать подрядчиков');
});
initializeCatalog();
initializeAssistantUI();
loadFilters();
initializeMotion();
