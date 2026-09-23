const STORAGE_KEY = 'povod:theme';
const THEME_NAMES = new Set(['light', 'dark']);

function readPreference() {
  try {
    const value = localStorage.getItem(STORAGE_KEY);
    return THEME_NAMES.has(value) ? value : null;
  } catch {
    return null;
  }
}

/** Keep the theme local to this browser; no API or form values are changed. */
export function initializeTheme({ getLabel } = {}) {
  const root = document.documentElement;
  const toggle = document.querySelector('#theme-toggle');
  const system = window.matchMedia?.('(prefers-color-scheme: dark)');
  let preference = readPreference();
  let current;

  function refreshControl() {
    if (!toggle) return;
    const isDark = current === 'dark';
    const label = getLabel?.(isDark) || (isDark
      ? 'Переключить на светлую тему'
      : 'Переключить на тёмную тему');
    toggle.textContent = isDark ? '☀' : '☾';
    toggle.setAttribute('aria-label', label);
    toggle.setAttribute('title', label);
    // The accessible name describes the next action, rather than a toggle state.
    toggle.dataset.theme = current;
  }

  function applyTheme() {
    current = preference || (system?.matches ? 'dark' : 'light');
    root.dataset.theme = current;
    root.style.colorScheme = current;
    refreshControl();
  }

  function onToggle() {
    preference = current === 'dark' ? 'light' : 'dark';
    try { localStorage.setItem(STORAGE_KEY, preference); } catch { /* Browsing without storage still works. */ }
    applyTheme();
  }

  function onSystemChange() {
    if (!preference) applyTheme();
  }

  function onStorage(event) {
    if (event.key !== STORAGE_KEY && event.key !== null) return;
    preference = readPreference();
    applyTheme();
  }

  toggle?.addEventListener('click', onToggle);
  system?.addEventListener?.('change', onSystemChange);
  window.addEventListener('storage', onStorage);
  document.addEventListener('localechange', refreshControl);
  applyTheme();

  return {
    refresh: refreshControl,
    destroy() {
      toggle?.removeEventListener('click', onToggle);
      system?.removeEventListener?.('change', onSystemChange);
      window.removeEventListener('storage', onStorage);
      document.removeEventListener('localechange', refreshControl);
    },
  };
}
