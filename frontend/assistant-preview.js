import { assistantTurn } from './api.js';
import { MOCK_MODE } from './config.js';
import { t } from './i18n.js';

export const EVENT_TEMPLATES = {
  wedding: 'Свадьба в Алматы 7 октября 2026. Нужен ведущий на казахском, бюджет до 1 млн тенге.',
  corporate: 'Корпоратив в Алматы 14 ноября 2026. Нужен фотограф на 4 часа, бюджет до 500 тысяч тенге.',
  birthday: 'День рождения в Астане 12 ноября 2026. Нужен фотограф, бюджет до 300 тысяч тенге.',
};
const labels = { city: 'Город', event_date: 'Дата', event_format: 'Событие', category: 'Кого ищем',
  budget_kzt: 'Бюджет', duration_hours: 'Длительность', language: 'Язык' };

export function initializeAssistantPreview(onUseForm, onApply, parse = assistantTurn) {
  const $ = id => document.querySelector(`#${id}`);
  const trigger = $('describe-event'), panel = $('event-assistant-panel'), input = $('event-description');
  const reply = $('assistant-reply'), understood = $('assistant-understood'), apply = $('assistant-apply');
  const fields = $('assistant-fields');
  let context = {}, pending = false, complete = false;
  function close(restoreFocus = true) {
    panel.hidden = true;
    trigger.setAttribute('aria-expanded', 'false');
    if (restoreFocus) trigger.focus();
  }
  function renderContext() {
    understood.replaceChildren();
    for (const [name, label] of Object.entries(labels)) {
      if (context[name] == null) continue;
      const row = document.createElement('div'), term = document.createElement('dt'), value = document.createElement('dd');
      term.textContent = t(label);
      value.textContent = name === 'budget_kzt' ? `${Number(context[name]).toLocaleString('ru-RU')} ₸`
        : name === 'duration_hours' ? `${context[name]} ч` : t(String(context[name]));
      row.append(term, value); understood.append(row);
    }
    understood.hidden = !Object.values(context).some(value => value != null);
  }
  function reset() {
    context = {}; complete = false; apply.hidden = true; input.value = ''; renderContext();
    reply.textContent = 'Новая заявка. Опишите город, дату, повод, специалиста и бюджет.';
  }
  trigger.addEventListener('click', () => {
    if (!panel.hidden) { close(); return; }
    panel.hidden = false;
    trigger.setAttribute('aria-expanded', 'true');
    input.focus({ preventScroll: true });
  });
  panel.addEventListener('keydown', event => {
    if (event.key === 'Escape') { event.preventDefault(); close(); }
  });
  document.querySelector('#assistant-preview-close').addEventListener('click', () => close());
  document.querySelector('#assistant-use-form').addEventListener('click', () => {
    close(false);
    onUseForm();
  });
  $('assistant-reset').addEventListener('click', () => { if (!pending) { reset(); input.focus(); } });
  panel.querySelectorAll('[data-assistant-template]').forEach(button => button.addEventListener('click', () => {
    if (pending) return;
    reset(); input.value = EVENT_TEMPLATES[button.dataset.assistantTemplate]; input.focus();
    reply.textContent = 'Это пример. Измените его под своё событие и нажмите «Разобрать описание».';
  }));
  input.addEventListener('input', () => { complete = false; apply.hidden = true; });
  $('event-description-form').addEventListener('submit', async event => {
    event.preventDefault();
    const message = input.value.trim();
    if (pending || !message || MOCK_MODE) return;
    pending = true; fields.disabled = true; complete = false; apply.hidden = true;
    panel.setAttribute('aria-busy', 'true'); reply.textContent = 'Проверяю параметры события…';
    try {
      const data = await parse(message, context);
      context = data.context; complete = data.complete; input.value = '';
      renderContext(); apply.hidden = !complete;
      reply.textContent = complete ? 'Условия собраны. Проверьте их ниже и нажмите «Применить и подобрать». Можно написать уточнение — например, «бюджет 500 тысяч».' : data.reply;
    } catch (error) {
      reply.textContent = `${error.message} Текст сохранён — можно повторить попытку.`;
    } finally {
      pending = false; fields.disabled = false; panel.setAttribute('aria-busy', 'false');
      if (!panel.hidden) (complete ? apply : input).focus({ preventScroll: true });
    }
  });
  apply.addEventListener('click', async () => {
    if (pending || !complete || input.value.trim()) return;
    apply.disabled = true;
    try {
      if (await onApply({ ...context })) close(false);
      else reply.textContent = 'Форма пока не готова или выполняется другой подбор. Повторите через несколько секунд.';
    } finally { apply.disabled = false; }
  });
  document.addEventListener('localechange', renderContext);
  if (MOCK_MODE) {
    fields.disabled = true;
    reply.textContent = 'В демо показаны сохранённые ответы. Перейдите к сервису по ссылке сверху, чтобы разобрать своё описание.';
  }
  trigger.disabled = false;
}
