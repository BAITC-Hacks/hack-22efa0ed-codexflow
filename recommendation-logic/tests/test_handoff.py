import json
import unittest
from fastapi.testclient import TestClient
from src.api import app
from qa.demo_check import CASES_PATH, check_case


class HandoffContractTests(unittest.TestCase):
    def test_all_shared_demo_fixtures_match_api(self):
        with TestClient(app) as client:
            cases = json.loads(CASES_PATH.read_text(encoding='utf-8'))
            self.assertEqual(len(cases), 6)
            for case in cases:
                with self.subTest(case=case['name']):
                    response = client.post('/recommendations', json=case['request'])
                    check_case(case, response.status_code, response.json())

    def test_demo_check_detects_wrong_order_not_just_http_success(self):
        case = json.loads(CASES_PATH.read_text(encoding='utf-8'))[0]
        with TestClient(app) as client:
            body = client.post('/recommendations', json=case['request']).json()
        body['cards'].reverse()
        with self.assertRaises(AssertionError):
            check_case(case, 200, body)

    def test_demo_check_detects_missing_explanation(self):
        case = json.loads(CASES_PATH.read_text(encoding='utf-8'))[0]
        with TestClient(app) as client:
            body = client.post('/recommendations', json=case['request']).json()
        body['cards'][0]['explanation'] = ''
        with self.assertRaises(AssertionError):
            check_case(case, 200, body)
