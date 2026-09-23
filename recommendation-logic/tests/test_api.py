import unittest

from fastapi.testclient import TestClient

from src.api import app


client = TestClient(app)


class ApiTests(unittest.TestCase):
    def test_health_reports_loaded_catalog(self):
        response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "profiles_loaded": 66})

    def test_filters_are_populated_from_catalog(self):
        response = client.get("/filters")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("Алматы", body["cities"])
        self.assertIn("Ведущий", body["categories"])
        self.assertIn("корпоратив", body["event_formats"])
        self.assertEqual(body["event_date_range"], {"min": "2026-09-23", "max": "2026-12-31"})

    def test_recommendations_returns_frontend_ready_cards(self):
        response = client.post(
            "/recommendations",
            json={
                "city": "Алматы",
                "event_date": "2026-10-15",
                "event_format": "корпоратив",
                "category": "Ведущий",
                "budget_kzt": 6_000_000,
                "duration_hours": 4,
                "language": "русский",
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["outcome"], "matches")
        self.assertLessEqual(len(body["cards"]), 3)
        self.assertIn("explanation", body["cards"][0])

    def test_invalid_payload_returns_422(self):
        response = client.post(
            "/recommendations",
            json={
                "city": "Алматы",
                "event_date": "not-a-date",
                "event_format": "корпоратив",
                "category": "Ведущий",
                "budget_kzt": 0,
            },
        )
        self.assertEqual(response.status_code, 422)

    def test_no_match_is_a_successful_business_response(self):
        response = client.post(
            "/recommendations",
            json={
                "city": "Алматы",
                "event_date": "2026-10-15",
                "event_format": "корпоратив",
                "category": "Ведущий",
                "budget_kzt": 1,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["outcome"], "no_match")


if __name__ == "__main__":
    unittest.main()
