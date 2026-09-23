"""Formerly failing repros, now also collected by tests/test_security.py.

python -m unittest discover -s qa -p test_known_weaknesses.py -v
These assert required behavior and must stay green; never mark expectedFailure.
"""
import json
import unittest

import httpx
from fastapi.testclient import TestClient
from src.api import app, PROVIDERS
from src.ai_explanations import AIExplainer, AISettings
from src.recommendation import RecommendationRequest, recommend

BASE = dict(city='Алматы', event_date='2026-10-07', event_format='свадьба',
            category='Ведущий', budget_kzt=1000000, language='казахский')


class InputWeaknesses(unittest.TestCase):
    def test_overflowing_json_number_is_client_error_not_500(self):
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post('/recommendations', content=json.dumps(BASE)[:-1]+',"duration_hours":1e309}',
                                   headers={'Content-Type': 'application/json'})
        self.assertIn(response.status_code, (400, 422))

    def test_invalid_unicode_is_client_error_not_500(self):
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post('/recommendations', content=json.dumps(BASE | {'city': '\ud800'}),
                                   headers={'Content-Type': 'application/json'})
        self.assertIn(response.status_code, (400, 422))

    def test_oversized_field_is_rejected(self):
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post('/recommendations', json=BASE | {'city': 'x'*100000})
        self.assertIn(response.status_code, (400, 413, 422))


class CacheWeaknesses(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.calls = 0
        def handler(request):
            self.calls += 1
            schema = json.loads(request.content)['text']['format']['schema']
            selection = {key: 0 for key in schema['required']}
            return httpx.Response(200, json={'status': 'completed', 'output': [
                {'type': 'message', 'content': [{'type': 'output_text', 'text': json.dumps(selection)}]}]})
        self.service = AIExplainer(AISettings(True, 'fake-repro', timeout_seconds=.05),
                                   transport=httpx.MockTransport(handler))

    async def test_equivalent_spelling_reuses_ai_cache(self):
        for city in ('Алматы', 'алматы', 'АЛМАТЫ', ' Алматы '):
            req = RecommendationRequest(**(BASE | {'city': city}))
            await self.service.enhance(recommend(PROVIDERS, req), PROVIDERS, req)
        self.assertEqual(self.calls, 1)

    async def test_hot_cache_does_not_wait_for_unrelated_request_lock(self):
        req = RecommendationRequest(**BASE)
        result = recommend(PROVIDERS, req)
        await self.service.enhance(result, PROVIDERS, req)
        async with self.service._lock:
            _, source, _ = await self.service.enhance(result, PROVIDERS, req)
        self.assertEqual(source, 'ai_cache')


if __name__ == '__main__':
    unittest.main()
