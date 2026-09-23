// Keep these public input limits aligned with RecommendationPayload (contract test).
export const MAX_BUDGET_KZT = 1_000_000_000;
export const MAX_DURATION_HOURS = 168;

export function validateValues(values, range) {
  const errors = {};
  for (const name of ['event_format', 'category', 'city', 'event_date', 'budget_kzt']) {
    if (!values[name]?.trim()) errors[name] = 'Заполните это поле.';
  }
  const budget = Number(values.budget_kzt);
  if (!errors.budget_kzt && (!Number.isSafeInteger(budget) || budget <= 0 || budget > MAX_BUDGET_KZT)) {
    errors.budget_kzt = 'Введите целую сумму от 1 до 1 000 000 000 ₸.';
  }
  if (values.duration_hours) {
    const hours = Number(values.duration_hours);
    if (!Number.isFinite(hours) || hours <= 0 || hours > MAX_DURATION_HOURS) {
      errors.duration_hours = 'Введите длительность больше 0 и не более 168 часов.';
    }
  }
  const timestamp = Date.parse(values.event_date);
  if (!errors.event_date && (!/^\d{4}-\d{2}-\d{2}$/.test(values.event_date) || !Number.isFinite(timestamp) ||
      new Date(timestamp).toISOString().slice(0, 10) !== values.event_date)) {
    errors.event_date = 'Укажите корректную дату.';
  }
  if (!errors.event_date && (values.event_date < range.min || values.event_date > range.max)) {
    const display = value => value.split('-').reverse().join('.');
    errors.event_date = `Выберите дату с ${display(range.min)} по ${display(range.max)}.`;
  }
  return errors;
}
