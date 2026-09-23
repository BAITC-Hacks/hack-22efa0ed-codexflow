"""Regression checks for merging the team's catalog and assistant integration."""
import json
import unittest
from dataclasses import asdict
from unittest.mock import patch

from fastapi.testclient import TestClient
from src.api import app, FRONTEND_PATH, PROVIDERS
from src.ai_explanations import AIExplainer, AISettings


class TeamUpdateTests(unittest.TestCase):
    def test_assistant_compound_duration_and_any_language(self):
        with TestClient(app) as client:
            first = client.post('/assistant/chat', json={'message': 'Свадьба в Алматы 7 октября, ведущий, бюджет 1 млн, на казахском'}).json()
            for text, expected in [('на 2 часа 30 минут', 2.5), ('до 4 часов', 4), ('на 30 минут', .5)]:
                with self.subTest(text=text):
                    turn = client.post('/assistant/chat', json={'message': text, 'context': first['context']}).json()
                    self.assertTrue(turn['complete'])
                    self.assertEqual(turn['context']['duration_hours'], expected)
                    self.assertEqual(turn['context']['budget_kzt'], 1000000)
            cleared = client.post('/assistant/chat', json={'message': 'Язык любой', 'context': first['context']}).json()
            self.assertTrue(cleared['complete'])
            self.assertIsNone(cleared['context']['language'])
            for text in ['на 168 часов 30 минут', 'на -2 часа', 'на 2 часа -30 минут']:
                bad = client.post('/assistant/chat', json={'message': text, 'context': first['context']}).json()
                self.assertFalse(bad['complete'])
                self.assertIsNone(bad['context']['duration_hours'])

    def test_assistant_corrects_invalid_hours_without_losing_date(self):
        with TestClient(app) as client:
            first = client.post('/assistant/chat', json={'message': 'Свадьба в Алматы 7 октября, ведущий, бюджет 1 млн, на 200 часов'}).json()
            self.assertFalse(first['complete'])
            self.assertIn('час', first['reply'])
            self.assertEqual(first['context']['event_date'], '2026-10-07')
            self.assertIsNone(first['context']['duration_hours'])
            second = client.post('/assistant/chat', json={'message': 'на 4 часа', 'context': first['context']}).json()
            self.assertTrue(second['complete'])
            self.assertEqual(second['context']['duration_hours'], 4)

    def test_invalid_date_correction_does_not_reuse_old_date(self):
        with TestClient(app) as client:
            first = client.post('/assistant/chat', json={'message': 'Свадьба в Алматы 7 октября, ведущий, бюджет 1 млн'}).json()
            second = client.post('/assistant/chat', json={'message': '32 ноября', 'context': first['context']}).json()
            self.assertFalse(second['complete'])
            self.assertIsNone(second['context']['event_date'])

    def test_assistant_bounds_and_huge_budget(self):
        with TestClient(app) as client:
            response = client.post('/assistant/chat', json={'message': 'бюджет ' + '9' * 500})
            self.assertEqual(response.status_code, 200)
            self.assertFalse(response.json()['complete'])
            self.assertIsNone(response.json()['context']['budget_kzt'])
            self.assertEqual(client.post('/assistant/chat', content=b'{"message":"x","message":"y"}', headers={'Content-Type':'application/json'}).status_code, 400)
            self.assertEqual(client.post('/assistant/chat', content=b'x' * 17000, headers={'Content-Type':'application/json'}).status_code, 413)

    def test_assistant_does_not_call_model_by_default(self):
        with TestClient(app) as client, patch('src.api.get_explainer', side_effect=AssertionError('Unexpected AI call')):
            response = client.post('/assistant/chat', json={'message': 'Свадьба в Алматы 7 октября, ведущий, бюджет 1 млн'})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.json()['complete'])

    def test_display_catalog_matches_backend_data(self):
        source = (FRONTEND_PATH / 'catalog-data.js').read_text(encoding='utf-8')
        snapshot = json.loads(source.split('export const providers = ', 1)[1].strip().removesuffix(';'))
        actual = {item['id']: item for item in snapshot}
        self.assertEqual(len(snapshot), len(PROVIDERS))
        self.assertEqual(set(actual), {p.id for p in PROVIDERS})
        for provider in PROVIDERS:
            for field, value in asdict(provider).items():
                with self.subTest(id=provider.id, field=field):
                    displayed = actual[provider.id][field]
                    if isinstance(value, (tuple, frozenset)):
                        self.assertEqual(sorted(displayed), sorted(value))
                    else:
                        self.assertEqual(displayed, value)

    def test_chat_uses_same_matcher_and_preserves_explanations(self):
        with TestClient(app) as client, patch('src.api.get_explainer', return_value=AIExplainer(AISettings())):
            chat = client.post('/assistant/chat', json={'message': 'Нужен ведущий на свадьбу в Алматы 7 октября, бюджет 1 млн, на казахском', 'context': {}})
            self.assertEqual(chat.status_code, 200)
            body = chat.json()
            self.assertTrue(body['complete'])
            matching = client.post('/recommendations', json=body['context'])
            self.assertEqual(matching.status_code, 200)
            self.assertEqual(body['recommendation'], matching.json())

    def test_team_assets_and_chat_validation(self):
        with TestClient(app) as client:
            for path in ['/assistant-assets/widget.js', '/assistant-assets/widget.css',
                         '/ui/i18n.js', '/ui/theme.js', '/ui/catalog.js', '/ui/catalog-data.js']:
                self.assertEqual(client.get(path).status_code, 200, path)
            self.assertEqual(client.post('/assistant/chat', json={'message': 'x' * 2001}).status_code, 422)
            response = client.post('/assistant/chat', json={'message': 'Алматы, 7 октября, свадьба'})
            self.assertEqual(response.status_code, 200)
            self.assertFalse(response.json()['complete'])
            self.assertIsNone(response.json()['recommendation'])
