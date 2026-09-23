import { USE_MOCK } from './config.js';
import { recommend } from './api.js';
import { renderRecommendations } from './cards.js';

const form = document.querySelector('#order-form');
const result = document.querySelector('#result');
const fields = document.querySelector('#fields');
const scenario = document.querySelector('#scenario');
let pending = false;
let lastRequest;
document.querySelector('#demo').hidden = !USE_MOCK;

function today() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}
form.elements.date.min = today();

function validate() {
  const values = Object.fromEntries(new FormData(form));
  const errors = {};
  for (const name of ['event_type', 'city', 'date', 'budget_min', 'budget_max', 'guests_count']) {
    if (!values[name]?.trim()) errors[name] = 'Заполните это поле.';
  }
  for (const name of ['budget_min', 'budget_max']) {
    if (!errors[name] && (!Number.isFinite(Number(values[name])) || Number(values[name]) < 0)) errors[name] = 'Введите сумму от 0 ₸.';
  }
  if (!errors.budget_min && !errors.budget_max && Number(values.budget_min) > Number(values.budget_max)) errors.budget_max = 'Максимум должен быть не меньше минимума.';
  if (!errors.guests_count && (!Number.isSafeInteger(Number(values.guests_count)) || Number(values.guests_count) < 1)) errors.guests_count = 'Введите целое число гостей от 1.';
  if (!errors.date && (!/^\d{4}-\d{2}-\d{2}$/.test(values.date) || !Number.isFinite(Date.parse(values.date)))) errors.date = 'Укажите корректную дату.';
  if (!errors.date && values.date < today()) errors.date = 'Дата не может быть в прошлом.';
  for (const name of ['event_type', 'city', 'date', 'budget_min', 'budget_max', 'guests_count']) {
    document.getElementById(`${name}-error`).textContent = errors[name] || '';
    form.elements[name].setAttribute('aria-invalid', String(Boolean(errors[name])));
  }
  if (Object.keys(errors).length) { form.elements[Object.keys(errors)[0]].focus(); return null; }
  return { order: {
    event_type: values.event_type.trim(), city: values.city.trim(), date: values.date,
    budget: { min: Number(values.budget_min), max: Number(values.budget_max), currency: 'KZT' },
    guests_count: Number(values.guests_count),
    tags: values.tags.split(',').map(tag => tag.trim()).filter(Boolean),
    notes: values.notes.trim(),
  } };
}

function message(title, text) {
  result.classList.remove('has-cards');
  result.replaceChildren();
  const heading = document.createElement('h3'); heading.textContent = title;
  const paragraph = document.createElement('p'); paragraph.textContent = text;
  result.append(heading, paragraph);
}

async function submit(request) {
  if (pending) return;
  pending = true;
  fields.disabled = true;
  scenario.disabled = true;
  result.setAttribute('aria-busy', 'true');
  message('Подбираем подрядчиков', 'Это может занять несколько секунд.');
  const spinner = document.createElement('div'); spinner.className = 'spinner'; spinner.setAttribute('aria-hidden', 'true'); result.prepend(spinner);
  try {
    const data = await recommend(request.payload, request.scenario);
    if (!data.recommendations.length) message('Нет результата', data.fallback_message);
    else renderRecommendations(result, data);
  } catch (error) {
    message('Не удалось получить подборку', error.message);
    const retry = document.createElement('button'); retry.type = 'button'; retry.className = 'retry'; retry.textContent = 'Повторить';
    retry.addEventListener('click', () => submit(request)); result.append(retry);
  } finally {
    pending = false; fields.disabled = false; scenario.disabled = false;
    result.setAttribute('aria-busy', 'false');
  }
}

form.addEventListener('submit', event => {
  event.preventDefault();
  if (pending) return;
  const payload = validate();
  if (!payload) return;
  lastRequest = { payload, scenario: scenario.value };
  submit(lastRequest);
});
