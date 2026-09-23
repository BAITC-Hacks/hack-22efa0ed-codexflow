import { CATALOG } from './catalog.js';

function element(tag, className, text) {
  const node = document.createElement(tag);
  node.className = className;
  if (text != null) node.textContent = text;
  return node;
}

export function renderRecommendations(container, data) {
  container.replaceChildren();
  container.classList.add('has-cards');
  container.append(element('p', 'result-summary', `Ваша подборка · ${Math.min(data.recommendations.length, 3)} варианта`));
  const grid = element('div', 'cards');
  data.recommendations.slice(0, 3).forEach((item, index) => {
    const details = Object.hasOwn(CATALOG, item.contractor_id) ? CATALOG[item.contractor_id] : null;
    const card = element('article', 'card');
    const top = element('div', 'card-top');
    top.append(element('span', 'category', details ? details.categories.join(' · ') : 'Подрядчик'), element('span', 'rank', `0${index + 1}`));
    card.append(top, element('h3', '', details?.name || `Подрядчик ${item.contractor_id}`));
    if (details) {
      const price = details.price_from_kzt === null ? 'Цена не указана' : `от ${new Intl.NumberFormat('ru-RU').format(details.price_from_kzt)} ₸`;
      card.append(element('p', 'card-meta', `${details.city} · ${price}`));
      const tags = element('div', 'tags');
      details.tags.forEach(tag => tags.append(element('span', 'tag', tag)));
      card.append(tags);
    } else card.append(element('p', 'card-meta', 'Детали этого подрядчика пока отсутствуют в локальном каталоге.'));
    const reason = element('div', 'reason');
    reason.append(element('span', 'reason-label', 'Почему подходит'), element('p', '', item.match_reason));
    card.append(reason);
    if (item.caveats) {
      const caveat = element('div', 'caveat');
      caveat.append(element('strong', '', 'Что учесть'), element('p', '', item.caveats));
      card.append(caveat);
    }
    if (details) {
      const provenance = [];
      if (details.synthetic) provenance.push('Синтетический профиль');
      if (details.price_imputed) provenance.push('Цена проставлена при подготовке датасета');
      if (details.city_imputed) provenance.push('Город проставлен при подготовке датасета');
      if (provenance.length) card.append(element('p', 'provenance', provenance.join(' · ')));
    }
    grid.append(card);
  });
  container.append(grid);
  if (data.fallback_message) container.append(element('p', 'fallback-note', data.fallback_message));
}
