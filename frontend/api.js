import { t } from './i18n.js';
import { API_URL, FILTERS_URL, MOCK_MODE, REQUEST_TIMEOUT_MS } from './config.js';
import { MOCK_RESPONSES, MOCK_FILTERS } from './mocks.js';

export class ApiError extends Error {
  constructor(message, fieldErrors = {}, messageVars = {}) { super(t(message, messageVars)); this.rawMessage = message; this.messageVars = messageVars; this.fieldErrors = fieldErrors; }
}
const plain = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const strings = value => Array.isArray(value) && value.every(item => typeof item === 'string' && item.trim());
const text = value => typeof value === 'string' && value.trim();

function validateRecommendations(data) {
  if (!plain(data) || !['matches', 'category_absent', 'no_match'].includes(data.outcome) ||
      !Array.isArray(data.cards) || data.cards.length > 3 || !text(data.message) ||
      (data.outcome === 'matches') !== (data.cards.length > 0) ||
      data.cards.some(card => !plain(card) || !text(card.id) || !text(card.name) ||
        !strings(card.categories) || !text(card.city) || !Number.isFinite(card.price_from_kzt) || card.price_from_kzt < 0 ||
        !text(card.explanation) || (card.caveats != null && typeof card.caveats !== 'string') || ['synthetic', 'price_imputed', 'city_imputed'].some(key => typeof card[key] !== 'boolean'))) {
    throw new ApiError('Сервис вернул неполный ответ. Попробуйте повторить запрос.');
  }
  return data;
}
function validateFilters(data) {
  if (!plain(data) || ['cities', 'categories', 'event_formats', 'languages'].some(key => !strings(data[key]) || !data[key].length) ||
      !plain(data.event_date_range) || !/^\d{4}-\d{2}-\d{2}$/.test(data.event_date_range.min) ||
      !/^\d{4}-\d{2}-\d{2}$/.test(data.event_date_range.max) || data.event_date_range.min > data.event_date_range.max) {
    throw new ApiError('Не удалось получить параметры каталога. Попробуйте ещё раз.');
  }
  return data;
}
async function request(url, payload) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const response = await fetch(url, {
      method: payload ? 'POST' : 'GET',
      headers: payload ? { 'Content-Type': 'application/json', Accept: 'application/json' } : { Accept: 'application/json' },
      ...(payload ? { body: JSON.stringify(payload) } : {}), signal: controller.signal,
    });
    if (response.status === 422) {
      const data = await response.json().catch(() => null);
      const fields = {};
      if (Array.isArray(data?.detail)) for (const error of data.detail) {
        const key = Array.isArray(error.loc) ? error.loc.at(-1) : null;
        if (typeof key === 'string' && typeof error.msg === 'string') fields[key] = error.msg;
      }
      throw new ApiError('Сервис не принял параметры. Проверьте отмеченные поля и повторите подбор.', fields);
    }
    if (!response.ok) throw new ApiError('Сервис временно недоступен (HTTP {status}). Попробуйте ещё раз.', {}, { status: response.status });
    try { return await response.json(); }
    catch { throw new ApiError('Сервис вернул ответ в неверном формате. Попробуйте ещё раз.'); }
  } catch (error) {
    if (error.name === 'AbortError') throw new ApiError('Сервис не ответил за 15 секунд. Повторите запрос.');
    if (error instanceof TypeError) throw new ApiError('Не удалось связаться с сервисом. Проверьте подключение и убедитесь, что сервис подбора запущен.');
    throw error;
  } finally { clearTimeout(timer); }
}
export async function getFilters() {
  return validateFilters(MOCK_MODE ? structuredClone(MOCK_FILTERS) : await request(FILTERS_URL));
}
export async function recommend(payload, scenario = 'success') {
  if (!MOCK_MODE) return validateRecommendations(await request(API_URL, payload));
  await new Promise(resolve => setTimeout(resolve, 700));
  if (scenario === 'error') throw new ApiError('Демонстрация ошибки соединения. Попробуйте повторить запрос.');
  return validateRecommendations(structuredClone(MOCK_RESPONSES[scenario]));
}
