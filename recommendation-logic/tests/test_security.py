"""Input and concurrency regressions, all offline and deterministic."""
import asyncio
from dataclasses import replace
import json
import unittest

import httpx
from fastapi.testclient import TestClient
from src.api import app, PROVIDERS
from src.ai_explanations import AIExplainer, AISettings
from src.http_safety import InputSafetyMiddleware, MAX_BODY_BYTES
from src.recommendation import (RecommendationRequest, recommend, MAX_TEXT_LENGTH,
                                MAX_BUDGET_KZT, MAX_DURATION_HOURS)
from qa.test_known_weaknesses import InputWeaknesses, CacheWeaknesses

BASE = dict(city='Алматы', event_date='2026-10-07', event_format='свадьба',
            category='Ведущий', budget_kzt=1000000, language='казахский')


class HTTPSecurityTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app, raise_server_exceptions=False)
        self.addCleanup(self.client.close)

    def test_nonfinite_values_never_become_server_errors(self):
        for field in ('duration_hours', 'budget_kzt', 'city'):
            for token in ('NaN', 'Infinity', '-Infinity', '1e309', '-1e309'):
                body = json.dumps({k: v for k, v in BASE.items() if k != field})[:-1] + f',"{field}":{token}}}'
                with self.subTest(field=field, token=token):
                    response = self.client.post('/recommendations', content=body, headers={'Content-Type': 'application/json'})
                    self.assertIn(response.status_code, (400, 422))

    def test_unicode_controls_rejected_in_each_text_field(self):
        for field in ('city', 'event_format', 'category', 'language'):
            for value in ('\ud800', 'a\x00b', 'a\u202eb', '\udfff', 'a\u200bb'):
                payload = BASE | {field: value}
                response = self.client.post('/recommendations', content=json.dumps(payload), headers={'Content-Type': 'application/json'})
                self.assertEqual(response.status_code, 422)
                self.assertNotIn('input', response.json()['detail'][0])
                with self.assertRaises(ValueError):
                    recommend(PROVIDERS, RecommendationRequest(**payload))

    def test_field_bounds_match_domain_and_api(self):
        cases = [('city', 'x'*(MAX_TEXT_LENGTH+1)), ('category', 'x'*(MAX_TEXT_LENGTH+1)),
                 ('event_format', 'x'*(MAX_TEXT_LENGTH+1)), ('language', 'x'*(MAX_TEXT_LENGTH+1)),
                 ('budget_kzt', MAX_BUDGET_KZT+1), ('duration_hours', MAX_DURATION_HOURS+.5)]
        for field, value in cases:
            payload = BASE | {field: value}
            with self.assertRaises(ValueError):
                recommend(PROVIDERS, RecommendationRequest(**payload))
            self.assertEqual(self.client.post('/recommendations', json=payload).status_code, 422)
        self.assertEqual(self.client.post('/recommendations', json=BASE | {
            'budget_kzt': MAX_BUDGET_KZT, 'duration_hours': MAX_DURATION_HOURS}).status_code, 200)
        self.assertEqual(self.client.post('/recommendations', json=BASE | {'city': 'x'*MAX_TEXT_LENGTH}).status_code, 200)

    def test_safe_errors_do_not_echo_payload_or_context(self):
        secret = 'do-not-reflect-me'
        response = self.client.post('/recommendations', json=BASE | {'budget_kzt': secret})
        self.assertEqual(response.status_code, 422)
        self.assertNotIn(secret, response.text)
        self.assertEqual(set(response.json()['detail'][0]), {'loc', 'msg', 'type'})

    def test_duplicate_keys_and_malformed_json_are_rejected(self):
        for body in ('{"city":"Алматы","city":"Астана"}', '{', '['*5000+'0'+']'*5000, '{"a":'+ '9'*5000+'}'):
            response = self.client.post('/recommendations', content=body.encode(), headers={'Content-Type': 'application/json'})
            self.assertEqual(response.status_code, 400)

    def test_invalid_encoding_and_content_type(self):
        for body, headers, expected in [(b'\xff', {'Content-Type': 'application/json'}, 400),
            (b'{}', {'Content-Type': 'text/plain'}, 415),
            (b'{}', {'Content-Type': 'application/json', 'Content-Encoding': 'gzip'}, 415)]:
            self.assertEqual(self.client.post('/recommendations', content=body, headers=headers).status_code, expected)

    def test_body_limit_and_recovery(self):
        response = self.client.post('/recommendations', json=BASE | {'city': 'x'*MAX_BODY_BYTES})
        self.assertEqual(response.status_code, 413)
        self.assertLess(len(response.content), 300)
        self.assertEqual(self.client.post('/recommendations', json=BASE).status_code, 200)

    def test_security_headers_and_cors(self):
        response = self.client.post('/recommendations', json=BASE, headers={'Origin': 'http://localhost:5173'})
        self.assertEqual(response.headers['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(response.headers['Cache-Control'], 'no-store')
        self.assertEqual(response.headers['Access-Control-Allow-Origin'], 'http://localhost:5173')
        for payload in (BASE | {'budget_kzt': -1}, BASE | {'city': 'x'*20000}):
            response = self.client.post('/recommendations', json=payload, headers={'Origin': 'http://localhost:5173'})
            self.assertEqual(response.headers['Access-Control-Allow-Origin'], 'http://localhost:5173')
        preflight = self.client.options('/recommendations', headers={
            'Origin': 'https://untrusted.invalid', 'Access-Control-Request-Method': 'POST'})
        self.assertEqual(preflight.status_code, 400)
        self.assertNotIn('Access-Control-Allow-Origin', preflight.headers)

    def test_private_files_not_served(self):
        for path in ('/.env', '/ui/.env', '/ui/.git/config', '/ui/%2e%2e/recommendation-logic/.env', '/ui/src/api.py'):
            self.assertEqual(self.client.get(path).status_code, 404)

    def test_openapi_documents_bounds(self):
        fields = self.client.get('/openapi.json').json()['components']['schemas']['RecommendationPayload']['properties']
        self.assertEqual(fields['city']['maxLength'], MAX_TEXT_LENGTH)
        self.assertEqual(fields['budget_kzt']['maximum'], MAX_BUDGET_KZT)


class StreamingInputTests(unittest.IsolatedAsyncioTestCase):
    async def test_chunked_body_cannot_bypass_size_limit(self):
        async def content():
            for _ in range(5):
                yield b'x'*4096
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
            response = await client.post('/recommendations', content=content(), headers={'Content-Type': 'application/json'})
            self.assertEqual(response.status_code, 413)

    async def call_middleware(self, headers, receiver, timeout=.1):
        messages, calls = [], []
        async def inner(scope, receive, send):
            calls.append(True)
        async def send(message):
            messages.append(message)
        middleware = InputSafetyMiddleware(inner, body_timeout=timeout)
        await middleware({'type': 'http', 'method': 'POST', 'path': '/recommendations', 'headers': headers}, receiver, send)
        return messages, calls

    async def test_bad_content_lengths(self):
        async def body():
            return {'type': 'http.request', 'body': b'{}'}
        for lengths in ([b'-1'], [b'1', b'2'], [b'999999999999999999'], [b'1']):
            headers = [(b'content-type', b'application/json')] + [(b'content-length', v) for v in lengths]
            messages, calls = await self.call_middleware(headers, body)
            self.assertIn(messages[0]['status'], (400, 413))
            self.assertEqual(calls, [])

    async def test_slow_body_times_out(self):
        async def slow():
            await asyncio.sleep(1)
        messages, calls = await self.call_middleware([(b'content-type', b'application/json')], slow, timeout=.02)
        self.assertEqual(messages[0]['status'], 408)
        self.assertEqual(calls, [])

    async def test_disconnected_client_does_not_call_app(self):
        async def disconnected():
            return {'type': 'http.disconnect'}
        messages, calls = await self.call_middleware([(b'content-type', b'application/json')], disconnected)
        self.assertEqual((messages, calls), ([], []))


class AIConcurrencyTests(unittest.IsolatedAsyncioTestCase):
    def service(self, **kwargs):
        self.active = self.peak = self.calls = 0
        self.release = asyncio.Event()
        self.four_started = asyncio.Event()
        async def handler(request):
            self.calls += 1
            self.active += 1
            self.peak = max(self.peak, self.active)
            if self.active == kwargs.get('concurrency', 4):
                self.four_started.set()
            try:
                await self.release.wait()
                schema = json.loads(request.content)['text']['format']['schema']
                return httpx.Response(200, json={'status': 'completed', 'output': [{'type': 'message', 'content': [
                    {'type': 'output_text', 'text': json.dumps({key: 0 for key in schema['required']})}]}]})
            finally:
                self.active -= 1
        return AIExplainer(AISettings(True, 'fake-test-key', **kwargs), transport=httpx.MockTransport(handler))

    async def run_request(self, service, i=0):
        req = RecommendationRequest(**(BASE | {'budget_kzt': 1000000+i}))
        return await service.enhance(recommend(PROVIDERS, req), PROVIDERS, req)

    async def test_distinct_calls_run_in_parallel_but_are_bounded(self):
        service = self.service()
        tasks = [asyncio.create_task(self.run_request(service, i)) for i in range(12)]
        await asyncio.wait_for(self.four_started.wait(), 1)
        self.assertEqual(self.peak, 4)
        self.release.set()
        results = await asyncio.gather(*tasks)
        self.assertTrue(all(row[1] == 'ai' for row in results))
        self.assertEqual(self.calls, 12)
        self.assertEqual(self.peak, 4)
        self.assertEqual(service._pending, {})

    async def test_admission_limit_falls_back_without_extra_model_calls(self):
        service = self.service(concurrency=1, max_pending=2)
        first = asyncio.create_task(self.run_request(service, 0))
        await asyncio.wait_for(self.four_started.wait(), 1)
        second = asyncio.create_task(self.run_request(service, 1))
        await asyncio.sleep(0)
        result = await self.run_request(service, 2)
        self.assertEqual(result[1:], ('fallback', 'busy'))
        self.assertEqual(len(service._pending), 2)
        self.release.set()
        await asyncio.gather(first, second)
        self.assertEqual(self.calls, 2)

    async def test_disconnect_does_not_cancel_other_waiter(self):
        service = self.service(concurrency=1)
        first = asyncio.create_task(self.run_request(service))
        await asyncio.wait_for(self.four_started.wait(), 1)
        second = asyncio.create_task(self.run_request(service))
        await asyncio.sleep(0)
        first.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await first
        self.release.set()
        result = await second
        self.assertEqual(result[1], 'ai_cache')
        self.assertEqual(self.calls, 1)

    async def test_budget_cannot_be_exceeded_concurrently(self):
        service = self.service(max_calls=2)
        self.release.set()
        results = await asyncio.gather(*(self.run_request(service, i) for i in range(12)))
        self.assertEqual(self.calls, 2)
        self.assertEqual(sum(row[1] == 'ai' for row in results), 2)
        self.assertEqual(sum(row[2] == 'call_limit' for row in results), 10)

    async def test_numeric_equivalence_uses_one_cache_entry(self):
        service = self.service()
        self.release.set()
        for duration in (4, 4.0):
            req = RecommendationRequest(**BASE, duration_hours=duration)
            await service.enhance(recommend(PROVIDERS, req), PROVIDERS, req)
        self.assertEqual(self.calls, 1)
