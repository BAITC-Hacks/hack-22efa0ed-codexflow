import { language, t } from './i18n.js';

let initialized = false;

// Adapt the shared assistant's controls without changing its chat or API logic.
export function initializeAssistantUI() {
  if (initialized) return;
  initialized = true;
  let root;
  let observer;
  let note;

  function refresh() {
    if (!root) return;
    for (const [selector, source] of [
      ['.ca-launch', 'Помочь с подбором'],
      ['#ca-title', 'Подбор подрядчиков'],
      ['.ca-header p:not(.ca-locale-note)', 'Опишите событие — я уточню детали'],
      ['.ca-send', 'Отправить'],
    ]) {
      const control = root.querySelector(selector);
      if (control) control.textContent = t(source);
    }
    root.querySelector('.ca-close')?.setAttribute('aria-label', t('Закрыть чат'));
    root.querySelector('.ca-input')?.setAttribute('aria-label', t('Сообщение помощнику'));
    note.textContent = t('Чат пока работает на русском');
    note.hidden = language() === 'ru';
  }

  function bind() {
    root = document.querySelector('#contractor-assistant-root');
    if (!root) return false;
    observer?.disconnect();
    // All transcript text stays exactly as received or typed. The assistant's
    // Russian example placeholder is preserved too; only its label is localized.
    root.setAttribute('data-i18n-ignore', '');
    for (const source of root.querySelectorAll('.ca-messages, .ca-status')) {
      source.setAttribute('data-original', '');
      source.lang = 'ru';
    }
    note = document.createElement('p');
    note.className = 'ca-locale-note';
    note.setAttribute('role', 'note');
    const heading = root.querySelector('.ca-header > div');
    heading?.append(note);
    refresh();
    return true;
  }

  document.addEventListener('localechange', refresh);
  if (!bind()) {
    // The widget may mount after this module; stop observing once it is bound.
    observer = new MutationObserver(bind);
    observer.observe(document.documentElement, { childList: true, subtree: true });
  }
}
