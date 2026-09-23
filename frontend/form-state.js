import { MOCK_REQUESTS } from './mocks.js';

const currency = value => `${new Intl.NumberFormat('ru-RU').format(value)} ₸`;

export function createFormState(form, names, mockMode, scenario) {
  const storageKey = `povod:order:${mockMode ? 'demo' : 'live'}:v1`;
  const progress = document.querySelector('#form-progress');
  const progressText = document.querySelector('#progress-text');
  const draftStatus = document.querySelector('#draft-status');
  const required = [...form.querySelectorAll('[required]')];
  const budget = form.elements.budget_kzt;
  const slider = document.querySelector('#budget-slider');
  const budgetValue = document.querySelector('#budget-value');
  const sliderMax = document.querySelector('#budget-slider-max');

  function refresh() {
    const completed = required.filter(field => field.value.trim() && field.validity.valid && field.getAttribute('aria-invalid') !== 'true').length;
    progress.max = required.length;
    progress.value = completed;
    document.querySelectorAll('[data-example]').forEach(chip => {
      const preset = MOCK_REQUESTS[chip.dataset.example];
      const selected = preset && names.every(name => form.elements[name].value === String(preset[name] ?? ''));
      chip.setAttribute('aria-pressed', String(selected));
    });
    progressText.textContent = `${completed} из ${required.length} заполнено`;
    progress.setAttribute('aria-valuetext', progressText.textContent);
    const amount = Number(budget.value);
    const valid = budget.value !== '' && Number.isSafeInteger(amount) && amount > 0;
    slider.max = valid ? String(Math.max(5000000, amount)) : '5000000';
    slider.value = valid ? String(amount) : '1';
    slider.setAttribute('aria-valuetext', valid ? `До ${currency(amount)}` : 'Бюджет не задан');
    budgetValue.textContent = valid ? `до ${currency(amount)}` : 'Бюджет не задан';
    sliderMax.textContent = currency(Number(slider.max));
    slider.style.setProperty('--range-fill', `${(Number(slider.value) - 1) / (Number(slider.max) - 1) * 100}%`);
  }
  function save() {
    const values = Object.fromEntries(names.map(name => [name, form.elements[name].value]));
    try {
      localStorage.setItem(storageKey, JSON.stringify({ version: 1, values, scenario: scenario.value }));
      draftStatus.textContent = 'Черновик сохранён на этом устройстве';
    } catch {
      draftStatus.textContent = 'Автосохранение недоступно в этом браузере';
    }
  }
  function restore() {
    try {
      const raw = localStorage.getItem(storageKey);
      if (!raw) return false;
      const draft = JSON.parse(raw);
      if (draft?.version !== 1 || !draft.values || typeof draft.values !== 'object') return false;
      let restored = false;
      for (const name of names) {
        if (typeof draft.values[name] !== 'string') continue;
        form.elements[name].value = draft.values[name];
        restored = true;
      }
      if (mockMode && [...scenario.options].some(option => option.value === draft.scenario)) scenario.value = draft.scenario;
      if (restored) draftStatus.textContent = 'Черновик восстановлен на этом устройстве';
      if (form.elements.duration_hours.value || form.elements.language.value) form.querySelector('.preferences').open = true;
      refresh();
      return restored;
    } catch {
      draftStatus.textContent = 'Не удалось восстановить черновик. Можно заполнить форму заново.';
      return false;
    }
  }
  function changed() { refresh(); save(); }
  slider.addEventListener('input', () => {
    budget.value = slider.value;
    budget.dispatchEvent(new Event('input', { bubbles: true }));
  });
  refresh();
  return { refresh, changed, restore };
}
