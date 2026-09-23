"""Same-origin frontend packaging and input-contract regression checks."""
import re
import unittest

from fastapi.testclient import TestClient
from src.api import app, FRONTEND_PATH
from src.recommendation import MAX_BUDGET_KZT, MAX_DURATION_HOURS


class FrontendContractTests(unittest.TestCase):
    def test_frontend_entry_and_modules_are_served(self):
        with TestClient(app) as client:
            response = client.get('/ui/')
            self.assertEqual(response.status_code, 200)
            self.assertIn('id="order-form"', response.text)
            for name in ['app.js', 'api.js', 'config.js', 'validation.js', 'cards.js', 'form-state.js', 'mocks.js', 'motion.js', 'styles.css', 'fonts.css', 'assistant-preview.js', 'guide.js']:
                with self.subTest(asset=name):
                    self.assertEqual(client.get('/ui/' + name).status_code, 200)

    def test_fonts_and_licenses_are_available_locally(self):
        with TestClient(app) as client:
            html = client.get('/ui/').text
            self.assertIn('./fonts.css', html)
            css = client.get('/ui/fonts.css').text
            for family in ['Manrope', 'GolosText', 'Lora']:
                path = f'assets/fonts/{family}-Variable.ttf'
                self.assertIn(path, css)
                self.assertIn(path, html)
                response = client.get('/ui/' + path)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.content[:4], b'\x00\x01\x00\x00')
                license_response = client.get(f'/ui/assets/fonts/{family}-OFL.txt')
                self.assertEqual(license_response.status_code, 200)
                self.assertIn('SIL OPEN FONT LICENSE', license_response.text)
            italic = client.get('/ui/assets/fonts/Lora-Italic.ttf')
            self.assertEqual(italic.status_code, 200)
            self.assertEqual(italic.content[:4], b'\x00\x01\x00\x00')
            self.assertIn('assets/fonts/Lora-Italic.ttf', css)
            self.assertIn('assets/fonts/Lora-Italic.ttf', html)

    def test_static_mount_does_not_expose_repository(self):
        with TestClient(app) as client:
            for path in ['/ui/.git/config', '/ui/%2e%2e/recommendation-logic/.env', '/recommendation-logic/data/providers.csv']:
                self.assertEqual(client.get(path).status_code, 404)

    def test_frontend_limits_match_backend(self):
        source = (FRONTEND_PATH / 'validation.js').read_text(encoding='utf-8')
        for name, expected in [('MAX_BUDGET_KZT', MAX_BUDGET_KZT), ('MAX_DURATION_HOURS', MAX_DURATION_HOURS)]:
            literal = re.search(rf'export const {name} = ([\d_]+);', source).group(1)
            self.assertEqual(int(literal.replace('_', '')), expected)
