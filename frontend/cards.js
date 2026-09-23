function element(tag, className, text) {
  const node = document.createElement(tag);
  node.className = className;
  if (text != null) node.textContent = text;
  return node;
}
export function renderRecommendations(container, data) {
  container.replaceChildren();
  container.classList.add('has-cards');
  container.append(element('p', 'result-summary', data.message));
  const grid = element('div', 'cards');
  data.cards.forEach((item, index) => {
    const card = element('article', 'card');
    const top = element('div', 'card-top');
    top.append(element('span', 'category', item.categories.join(' · ')), element('span', 'rank', `0${index + 1}`));
    card.append(top, element('h3', '', item.name));
    card.append(element('p', 'card-meta', `${item.city} · от ${new Intl.NumberFormat('ru-RU').format(item.price_from_kzt)} ₸`));
    const reason = element('div', 'reason');
    reason.append(element('span', 'reason-label', 'Почему подходит'), element('p', '', item.explanation));
    card.append(reason);
    const provenance = [];
    if (item.synthetic) provenance.push('Синтетический профиль');
    if (item.price_imputed) provenance.push('Цена проставлена при подготовке датасета');
    if (item.city_imputed) provenance.push('Город проставлен при подготовке датасета');
    if (provenance.length) card.append(element('p', 'provenance', provenance.join(' · ')));
    grid.append(card);
  });
  container.append(grid);
}
