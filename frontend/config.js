// Backend runs on port 8000. Serve frontend on 5173 (allowed by backend CORS).
// From repository root: python3 -m http.server 5173 --directory frontend
export const API_URL = 'http://127.0.0.1:8000/recommendations';
export const FILTERS_URL = new URL('/filters', API_URL).href;
export const USE_MOCK = false;
const demo = new URLSearchParams(window.location.search).get('demo');
export const MOCK_MODE = demo === '0' ? false : USE_MOCK || demo === '1';
export const REQUEST_TIMEOUT_MS = 15000;
