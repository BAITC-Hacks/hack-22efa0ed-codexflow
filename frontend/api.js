import { API_URL, USE_MOCK, REQUEST_TIMEOUT_MS } from './config.js';
import { MOCK_RESPONSES } from './mocks.js';

function validateResponse(data) {
  if (!data || !Array.isArray(data.recommendations) ||
      !(data.fallback_message === null || typeof data.fallback_message === 'string') ||
      data.recommendations.some(item => !item || typeof item.contractor_id !== 'string' || !item.contractor_id.trim() || typeof item.match_reason !== 'string' || !item.match_reason.trim() || !(item.caveats === null || typeof item.caveats === 'string')) ||
      (!data.recommendations.length && !data.fallback_message?.trim())) {
    throw new Error('Сервис вернул неполный ответ. Повторите запрос или сообщите команде.');
  }
  return data;
}

export async function recommend(payload, scenario = 'success') {
  if (USE_MOCK) {
    await new Promise(resolve => setTimeout(resolve, 700));
    if (scenario === 'error') throw new Error('Демонстрация ошибки соединения. Попробуйте повторить запрос.');
    return validateResponse(structuredClone(MOCK_RESPONSES[scenario]));
  }
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const response = await fetch(API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });
    if (!response.ok) throw new Error(`Сервис временно не смог выполнить запрос (HTTP ${response.status}). Попробуйте ещё раз.`);
    let data;
    try { data = await response.json(); }
    catch { throw new Error('Сервис вернул ответ в неверном формате. Попробуйте ещё раз.'); }
    return validateResponse(data);
  } catch (error) {
    if (error.name === 'AbortError') throw new Error('Сервис не ответил за 15 секунд. Повторите запрос.');
    if (error instanceof TypeError) throw new Error('Не удалось связаться с сервисом. Проверьте соединение и повторите запрос.');
    throw error;
  } finally { clearTimeout(timeout); }
}
