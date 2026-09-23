// Production and /ui preview use the same origin as the API. A separate local
// frontend on 5173 retains the team's development workflow (API on 8000).
const localDev = ['localhost', '127.0.0.1'].includes(window.location.hostname) && window.location.port === '5173' &&
  !/^\/ui(?:\/|$)/.test(window.location.pathname);
const apiOrigin = localDev ? `${window.location.protocol}//${window.location.hostname}:8000` : window.location.origin;
export const API_URL = new URL('/recommendations', apiOrigin).href;
export const FILTERS_URL = new URL('/filters', API_URL).href;
export const USE_MOCK = false;
const demo = new URLSearchParams(window.location.search).get('demo');
export const MOCK_MODE = demo === '0' ? false : USE_MOCK || demo === '1';
export const REQUEST_TIMEOUT_MS = 15000;
