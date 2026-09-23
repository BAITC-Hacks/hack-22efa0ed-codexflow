import asyncio
from copy import deepcopy
from dataclasses import replace
import json
import unittest
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

from src.api import app, PROVIDERS
from src.ai_explanations import AIExplainer, AISettings, evidence_candidates
from src.recommendation import RecommendationRequest, recommend


REQUEST = RecommendationRequest('Алматы', '2026-10-07', 'свадьба', 'Ведущий', 1_000_000, language='казахский')


class AIExplanationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.base = recommend(PROVIDERS, REQUEST)
        self.calls = []

    def service(self, *, body=None, status=200, settings=None):
        def handler(request):
            self.calls.append(request)
            sent = json.loads(request.content)
            choices = {key: 0 for key in sent['text']['format']['schema']['required']}
            default = {'status': 'completed', 'output': [{'type': 'message', 'content': [
                {'type': 'output_text', 'text': json.dumps(choices)}]}]}
            return httpx.Response(status, json=body if body is not None else default)
        return AIExplainer(settings or AISettings(True, 'fake-test-key'), transport=httpx.MockTransport(handler))

    async def test_only_explanations_change_and_input_is_not_mutated(self):
        original = deepcopy(self.base)
        result, source, reason = await self.service().enhance(self.base, PROVIDERS, REQUEST)
        self.assertEqual((source, reason), ('ai', 'ok'))
        self.assertEqual(self.base, original)
        for actual, expected in zip(result['cards'], original['cards']):
            self.assertEqual({k: v for k, v in actual.items() if k != 'explanation'},
                             {k: v for k, v in expected.items() if k != 'explanation'})
            provider = next(p for p in PROVIDERS if p.id == actual['id'])
            if evidence_candidates(provider.description):
                self.assertIn(evidence_candidates(provider.description)[0], actual['explanation'])
            self.assertIn(REQUEST.event_date, actual['explanation'])
        for key in ('outcome', 'message', 'stats'):
            self.assertEqual(result[key], original[key])
        sent = json.loads(self.calls[0].content)
        self.assertFalse(sent['store'])
        self.assertTrue(sent['text']['format']['strict'])
        self.assertEqual(str(self.calls[0].url), 'https://api.openai.com/v1/responses')

    async def test_disabled_and_missing_key_do_not_call_network(self):
        for settings, expected in [(AISettings(), 'disabled'), (AISettings(True), 'missing_key')]:
            result, _, reason = await self.service(settings=settings).enhance(self.base, PROVIDERS, REQUEST)
            self.assertEqual(reason, expected)
            self.assertEqual(result, self.base)
        self.assertEqual(self.calls, [])

    async def test_empty_outcomes_skip_ai(self):
        for request in (replace(REQUEST, budget_kzt=1), replace(REQUEST, category='Нет такой категории')):
            base = recommend(PROVIDERS, request)
            result, source, reason = await self.service().enhance(base, PROVIDERS, request)
            self.assertEqual((result, source, reason), (base, 'rules', 'empty_result'))
        self.assertEqual(self.calls, [])

    async def test_cache_is_single_flight_and_returns_independent_copies(self):
        service = self.service()
        first, second = await asyncio.gather(service.enhance(self.base, PROVIDERS, REQUEST),
                                             service.enhance(self.base, PROVIDERS, REQUEST))
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(first[1], 'ai')
        self.assertEqual(second[1], 'ai_cache')
        first[0]['cards'][0]['name'] = 'changed'
        third = await service.enhance(self.base, PROVIDERS, REQUEST)
        self.assertNotEqual(third[0]['cards'][0]['name'], 'changed')

    async def test_description_change_invalidates_cache(self):
        service = self.service()
        await service.enhance(self.base, PROVIDERS, REQUEST)
        changed = [replace(p, description=p.description + ' Отдельное оформление для свадьбы.') for p in PROVIDERS]
        await service.enhance(recommend(changed, REQUEST), changed, REQUEST)
        self.assertEqual(len(self.calls), 2)

    async def test_invalid_refusal_and_incomplete_outputs_fall_back(self):
        invalid = [[], {'status': 'incomplete'}, {'status': 'completed', 'output': [None]},
                   {'status': 'completed', 'output': [{'type': 'message', 'content': [{'type': 'refusal'}]}]}]
        ids = [c['id'] for c in self.base['cards']]
        for selection in ({}, {'unknown': 0}, {key: True for key in ids}, {key: -1 for key in ids},
                          {key: 9999 for key in ids}, {key: 'Выдуманная цена' for key in ids}):
            invalid.append({'status': 'completed', 'output': [{'type': 'message', 'content': [
                {'type': 'output_text', 'text': json.dumps(selection)}]}]})
        for body in invalid:
            with self.subTest(body=body):
                result, source, reason = await self.service(body=body).enhance(self.base, PROVIDERS, REQUEST)
                self.assertEqual((result, source, reason), (self.base, 'fallback', 'invalid_response'))

    async def test_upstream_errors_are_safe_fallbacks(self):
        for status in (401, 429, 500):
            result, source, reason = await self.service(status=status).enhance(self.base, PROVIDERS, REQUEST)
            self.assertEqual((result, source, reason), (self.base, 'fallback', 'upstream_http'))

    async def test_network_failure_is_safe(self):
        def fail(request):
            raise httpx.ConnectError('sensitive internal error', request=request)
        service = AIExplainer(AISettings(True, 'secret'), transport=httpx.MockTransport(fail))
        result, source, reason = await service.enhance(self.base, PROVIDERS, REQUEST)
        self.assertEqual((result, source, reason), (self.base, 'fallback', 'network'))
        self.assertNotIn('secret', repr(service.settings))

    async def test_total_timeout_including_queue_and_recovery(self):
        service = self.service(settings=AISettings(True, 'fake', timeout_seconds=0.02))
        await service._lock.acquire()
        try:
            result, source, reason = await service.enhance(self.base, PROVIDERS, REQUEST)
            self.assertEqual((result, source, reason), (self.base, 'fallback', 'timeout'))
        finally:
            service._lock.release()
        self.assertEqual(self.calls, [])
        self.assertEqual((await service.enhance(self.base, PROVIDERS, REQUEST))[1], 'ai')

    async def test_network_timeout_cancels_in_flight_call(self):
        async def slow(request):
            await asyncio.sleep(1)
            raise AssertionError('request should be cancelled')
        service = AIExplainer(AISettings(True, 'fake', timeout_seconds=0.02), transport=httpx.MockTransport(slow))
        result, source, reason = await service.enhance(self.base, PROVIDERS, REQUEST)
        self.assertEqual((result, source, reason), (self.base, 'fallback', 'timeout'))
        self.assertFalse(service._lock.locked())

    async def test_attempt_budget_and_cached_results(self):
        service = self.service(settings=AISettings(True, 'fake', max_calls=1))
        await service.enhance(self.base, PROVIDERS, REQUEST)
        self.assertEqual((await service.enhance(self.base, PROVIDERS, REQUEST))[1], 'ai_cache')
        other = replace(REQUEST, budget_kzt=1_100_000)
        self.assertEqual((await service.enhance(recommend(PROVIDERS, other), PROVIDERS, other))[2], 'call_limit')
        self.assertEqual(len(self.calls), 1)

    async def test_no_usable_evidence_skips_network(self):
        providers = [replace(p, description='') for p in PROVIDERS]
        result, source, reason = await self.service().enhance(recommend(providers, REQUEST), providers, REQUEST)
        self.assertEqual((source, reason), ('rules', 'no_evidence'))
        self.assertEqual(self.calls, [])

    def test_candidate_bounds_and_source_fidelity(self):
        source = 'Опыт проведения свадеб 12 лет. Индивидуальный сценарий для каждой свадьбы!'
        for sentence in evidence_candidates(source):
            self.assertIn(sentence, source)
        self.assertEqual(evidence_candidates('Длинное ' * 100), [])
        self.assertEqual(evidence_candidates('<script> плохой текст </script>'), [])


class AIEndpointTests(unittest.TestCase):
    def test_opt_in_success_and_cache_through_http_contract(self):
        calls = []
        def handler(request):
            calls.append(request)
            schema = json.loads(request.content)['text']['format']['schema']
            choices = {key: value['enum'][-1] for key, value in schema['properties'].items()}
            return httpx.Response(200, json={'status': 'completed', 'output': [
                {'type': 'message', 'content': [{'type': 'output_text', 'text': json.dumps(choices)}]}]})
        service = AIExplainer(AISettings(True, 'fake'), transport=httpx.MockTransport(handler))
        baseline = recommend(PROVIDERS, REQUEST)
        with patch('src.api.get_explainer', return_value=service), TestClient(app) as client:
            for source in ('ai', 'ai_cache'):
                response = client.post('/recommendations?ai_explanations=true', json=REQUEST.__dict__)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.headers['X-Explanation-Source'], source)
                body = response.json()
                self.assertEqual(set(body), set(baseline))
                self.assertEqual([c['id'] for c in body['cards']], [c['id'] for c in baseline['cards']])
                for card in body['cards']:
                    provider = next(p for p in PROVIDERS if p.id == card['id'])
                    candidates = evidence_candidates(provider.description)
                    if candidates:
                        self.assertIn(candidates[-1], card['explanation'])
        self.assertEqual(len(calls), 1)

    def test_default_endpoint_never_initializes_ai(self):
        with patch('src.api.get_explainer') as factory, TestClient(app) as client:
            response = client.post('/recommendations', json=REQUEST.__dict__)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), recommend(PROVIDERS, REQUEST))
            self.assertEqual(response.headers['X-Explanation-Source'], 'rules')
            factory.assert_not_called()

    def test_opt_in_endpoint_preserves_contract_on_missing_key(self):
        with patch('src.api.get_explainer', return_value=AIExplainer(AISettings(True))), TestClient(app) as client:
            response = client.post('/recommendations?ai_explanations=true', json=REQUEST.__dict__)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), recommend(PROVIDERS, REQUEST))
            self.assertEqual(response.headers['X-Explanation-Source'], 'fallback')
            self.assertEqual(response.headers['X-AI-Reason'], 'missing_key')


if __name__ == '__main__':
    unittest.main()
