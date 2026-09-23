function element(tag, className, text) {
  const node = document.createElement(tag);
  node.className = className;
  if (text != null) node.textContent = text;
  return node;
}
const categoryStyles = [
  { names: ['Флорист', 'Декоратор'], icon: '✿', tone: 'botanical' },
  { names: ['Фотограф', 'Видеограф', 'Фото и видеобудки'], icon: '▣', tone: 'creative' },
  { names: ['Банкетный зал', 'Ресторан', 'Отель', 'Загородная площадка'], icon: '⌂', tone: 'venue' },
];
function categoryBadge(categories) {
  const style = categoryStyles.find(group => categories.some(name => group.names.includes(name))) || { icon: '✦', tone: 'event' };
  const badge = element('span', `category category-${style.tone}`);
  const icon = element('span', 'category-icon', style.icon); icon.setAttribute('aria-hidden', 'true');
  badge.append(icon, element('span', '', categories.join(' · ')));
  return badge;
}
export function renderSkeletons(container, loading = false) {
  container.replaceChildren();
  container.classList.add('has-cards', 'skeleton-state');
  container.classList.toggle('is-loading', loading);
  container.append(element('h3', 'skeleton-heading', loading ? 'Подбираем вашу команду' : 'Здесь появится ваша подборка'));
  container.append(element('p', 'skeleton-caption', loading ? 'Проверяем условия и готовим объяснение для каждого варианта.' : 'Заполните форму — покажем до трёх вариантов и объясним, почему они подходят.'));
  const grid = element('div', 'skeleton-preview'); grid.setAttribute('aria-hidden', 'true');
  for (let i = 0; i < 3; i++) {
    const card = element('div', 'skeleton-card');
    for (const part of ['badge', 'title', 'meta', 'reason']) card.append(element('span', `skeleton-line skeleton-${part}`));
    grid.append(card);
  }
  container.append(grid);
}
export function renderRecommendations(container, data) {
  container.replaceChildren();
  container.classList.remove('skeleton-state', 'is-loading');
  container.classList.add('has-cards');
  container.append(element('p', 'result-summary', data.message));
  const grid = element('div', 'cards');
  data.cards.forEach((item, index) => {
    const card = element('article', 'card');
    card.style.setProperty('--card-delay', `${index * 120}ms`);
    const top = element('div', 'card-top');
    top.append(categoryBadge(item.categories), element('span', 'rank', `0${index + 1}`));
    card.append(top, element('h3', '', item.name));
    card.append(element('p', 'card-meta', `${item.city} · от ${new Intl.NumberFormat('ru-RU').format(item.price_from_kzt)} ₸`));
    const reason = element('div', 'reason');
    const reasonLabel = element('span', 'reason-label');
    const star = element('span', 'reason-star', '✳'); star.setAttribute('aria-hidden', 'true');
    reasonLabel.append(star, document.createTextNode(' Почему подходит'));
    reason.append(reasonLabel, element('p', '', item.explanation));
    card.append(reason);
    if (typeof item.caveats === 'string' && item.caveats.trim()) {
      const caveat = element('aside', 'caveat');
      const heading = element('strong', 'caveat-heading');
      const icon = element('span', '', '⚠'); icon.setAttribute('aria-hidden', 'true');
      heading.append(icon, document.createTextNode(' Что учесть'));
      caveat.append(heading, element('p', '', item.caveats)); card.append(caveat);
    }
    const provenance = [];
    if (item.synthetic) provenance.push('Синтетический профиль');
    if (item.price_imputed) provenance.push('Цена проставлена при подготовке датасета');
    if (item.city_imputed) provenance.push('Город проставлен при подготовке датасета');
    if (provenance.length) card.append(element('p', 'provenance', provenance.join(' · ')));
    const action = element('button', 'card-action', 'Связаться'); action.type = 'button';
    const availability = element('p', 'availability-note', 'Доступно в полной версии. Сейчас сервис помогает подобрать подрядчика.');
    availability.id = `availability-${index}`; availability.hidden = true; availability.setAttribute('role', 'status');
    action.setAttribute('aria-expanded', 'false'); action.setAttribute('aria-controls', availability.id);
    action.addEventListener('click', () => {
      availability.hidden = !availability.hidden;
      action.setAttribute('aria-expanded', String(!availability.hidden));
    });
    card.append(action, availability);
    grid.append(card);
  });
  container.append(grid);
}
