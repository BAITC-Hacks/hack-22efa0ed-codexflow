import { providers } from './catalog-data.js';
import { t, locale, language } from './i18n.js';

const PAGE_SIZE = 12;
const categories = [...new Set(providers.flatMap(provider => provider.categories))];
const cities = [...new Set(providers.map(provider => provider.city))];

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function fact(label, value) {
  const row = element('div', 'catalog-fact');
  row.append(element('dt', '', t(label)), element('dd', '', value));
  return row;
}

function card(provider) {
  const article = element('article', 'catalog-card');
  const category = element('p', 'catalog-card-category', provider.categories.map(value => t(value)).join(' · '));
  const title = element('h3', 'catalog-card-title', provider.name);
  title.lang = 'ru';
  title.dataset.original = 'true';
  const id = element('span', 'catalog-card-id', provider.id);
  const city = element('p', 'catalog-card-city', t(provider.city));
  const price = element('p', 'catalog-card-price', t('От {price} ₸', {
    price: new Intl.NumberFormat(locale()).format(provider.price_from_kzt),
  }));
  const facts = element('dl', 'catalog-facts');
  facts.append(
    fact('Форматы', provider.event_formats.map(value => t(value)).join(', ')),
    fact('Языки', provider.languages.map(value => t(value)).join(', ')),
    fact('На площадке', provider.max_hours === null
      ? t('Без привязки к часам присутствия')
      : t('До {hours} ч', { hours: new Intl.NumberFormat(locale()).format(provider.max_hours) })),
  );

  const more = element('details', 'catalog-card-details');
  more.append(element('summary', '', t('О профиле')));
  if (language() !== 'ru') more.append(element('p', 'catalog-source-note', t('Описание на русском')));
  const description = element('p', 'catalog-description', provider.description);
  description.lang = 'ru';
  description.dataset.original = 'true';
  const availability = element('dl', 'catalog-availability');
  availability.append(fact('Занято дней', t('{busy} из 100 · в декабре {december} из 31', {
    busy: provider.busy_dates.length,
    december: provider.busy_dates.filter(date => date.startsWith('2026-12-')).length,
  })));
  more.append(description, availability);

  article.append(category, title, id, city, price, facts, more);
  const flags = element('div', 'catalog-flags');
  for (const [active, label] of [
    [provider.synthetic, 'Синтетический профиль'],
    [provider.price_imputed, 'Цена дополнена в датасете'],
    [provider.city_imputed, 'Город дополнен в датасете'],
  ]) {
    if (active) flags.append(element('span', 'catalog-flag', t(label)));
  }
  if (flags.childElementCount) article.append(flags);
  return article;
}

export function initializeCatalog() {
  const root = document.getElementById('catalog-root');
  if (!root || root.dataset.initialized) return;
  root.dataset.initialized = 'true';
  root.classList.add('catalog-section');
  root.setAttribute('aria-labelledby', 'catalog-title');

  const state = { category: '', city: '', query: '', limit: PAGE_SIZE };
  let grid, count, moreButton, search, citySelect, filters;

  function refreshResults() {
    const query = state.query.trim().toLocaleLowerCase(locale());
    const matches = providers.filter(provider =>
      (!state.category || provider.categories.includes(state.category)) &&
      (!state.city || provider.city === state.city) &&
      (!query || `${provider.name} ${provider.id}`.toLocaleLowerCase(locale()).includes(query)),
    );
    const shown = matches.slice(0, state.limit);
    count.textContent = t('Показано {shown} из {total}', { shown: shown.length, total: matches.length });
    grid.replaceChildren(...shown.map(card));
    if (!matches.length) {
      const empty = element('div', 'catalog-empty');
      empty.append(element('h3', '', t('Ничего не найдено')),
        element('p', '', t('Попробуйте другую категорию, город или имя.')));
      const reset = element('button', 'catalog-reset', t('Сбросить фильтры'));
      reset.type = 'button';
      reset.addEventListener('click', () => {
        state.category = '';
        state.city = '';
        state.query = '';
        state.limit = PAGE_SIZE;
        render();
        search.focus();
      });
      empty.append(reset);
      grid.append(empty);
    }
    moreButton.hidden = matches.length <= state.limit;
    filters.querySelectorAll('button').forEach(button => {
      button.setAttribute('aria-pressed', String(button.dataset.category === state.category));
    });
  }

  function render() {
    const header = element('div', 'catalog-heading');
    const title = element('h2', '', t('Каталог подрядчиков'));
    title.id = 'catalog-title';
    const total = element('span', 'catalog-total', String(providers.length));
    total.setAttribute('aria-hidden', 'true');
    header.append(title, total);
    const note = element('p', 'catalog-intro', t('Профили из исходного каталога. Доступность на дату проверяется при подборе.'));
    const calendar = element('p', 'catalog-calendar', t('Календарь: {start} — {end}', {
      start: new Intl.DateTimeFormat(locale()).format(new Date(2026, 8, 23)),
      end: new Intl.DateTimeFormat(locale()).format(new Date(2026, 11, 31)),
    }));

    const toolbar = element('div', 'catalog-toolbar');
    const searchLabel = element('label', 'catalog-search-field', t('Найти по имени или ID'));
    search = element('input', 'catalog-search');
    search.type = 'search';
    search.id = 'catalog-search';
    search.autocomplete = 'off';
    search.placeholder = t('Имя или ID подрядчика');
    search.value = state.query;
    search.addEventListener('input', () => {
      state.query = search.value;
      state.limit = PAGE_SIZE;
      refreshResults();
    });
    searchLabel.append(search);

    const cityLabel = element('label', 'catalog-city-field', t('Город каталога'));
    citySelect = element('select', 'catalog-city-select');
    citySelect.id = 'catalog-city';
    for (const value of ['', ...cities]) {
      const option = element('option', '', t(value || 'Все города'));
      option.value = value;
      citySelect.append(option);
    }
    citySelect.value = state.city;
    citySelect.addEventListener('change', () => {
      state.city = citySelect.value;
      state.limit = PAGE_SIZE;
      refreshResults();
    });
    cityLabel.append(citySelect);
    toolbar.append(searchLabel, cityLabel);

    filters = element('div', 'catalog-filters');
    filters.setAttribute('role', 'group');
    filters.setAttribute('aria-label', t('Категория подрядчика'));
    for (const value of ['', ...categories]) {
      const button = element('button', 'catalog-chip', t(value || 'Все категории'));
      button.type = 'button';
      button.dataset.category = value;
      button.addEventListener('click', () => {
        state.category = value;
        state.limit = PAGE_SIZE;
        refreshResults();
      });
      filters.append(button);
    }

    count = element('p', 'catalog-count');
    count.setAttribute('role', 'status');
    count.setAttribute('aria-live', 'polite');
    count.setAttribute('aria-atomic', 'true');
    grid = element('div', 'catalog-grid');
    grid.id = 'catalog-grid';
    moreButton = element('button', 'catalog-more', t('Показать ещё'));
    moreButton.type = 'button';
    moreButton.setAttribute('aria-controls', 'catalog-grid');
    moreButton.addEventListener('click', () => {
      const previousCount = grid.childElementCount;
      state.limit += PAGE_SIZE;
      refreshResults();
      const nextCard = grid.children[previousCount];
      if (nextCard) {
        nextCard.tabIndex = -1;
        nextCard.focus({ preventScroll: true });
      }
    });
    root.replaceChildren(header, note, calendar, toolbar, filters, count, grid, moreButton);
    refreshResults();
  }

  render();
  document.addEventListener('localechange', render);
}
