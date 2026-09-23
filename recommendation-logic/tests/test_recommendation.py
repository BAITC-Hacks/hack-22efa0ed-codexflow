import unittest

from src.recommendation import Provider, RecommendationRequest, recommend


def provider(**overrides):
    values = {
        "id": "HK-001",
        "name": "Тестовый подрядчик",
        "categories": ("Ведущий",),
        "city": "Алматы",
        "price_from_kzt": 100_000,
        "event_formats": ("корпоратив",),
        "languages": ("русский",),
        "max_hours": 6,
        "busy_dates": frozenset(),
        "description": "Тестовый профиль",
        "synthetic": False,
    }
    values.update(overrides)
    return Provider(**values)


REQUEST = RecommendationRequest(
    city="Алматы",
    event_date="2026-11-14",
    event_format="корпоратив",
    category="Ведущий",
    budget_kzt=200_000,
    duration_hours=5,
    language="русский",
)


class RecommendationTests(unittest.TestCase):
    def test_excludes_busy_provider_and_ranks_by_price(self):
        result = recommend(
            [
                provider(id="HK-002", price_from_kzt=120_000),
                provider(id="HK-001", price_from_kzt=90_000, busy_dates=frozenset({REQUEST.event_date})),
                provider(id="HK-003", price_from_kzt=80_000),
            ],
            REQUEST,
        )
        self.assertEqual(result["outcome"], "matches")
        self.assertEqual([card["id"] for card in result["cards"]], ["HK-003", "HK-002"])
        self.assertIn("заняты", result["message"])

    def test_is_deterministic_when_prices_are_equal(self):
        result = recommend([provider(id="HK-020"), provider(id="HK-010")], REQUEST)
        self.assertEqual([card["id"] for card in result["cards"]], ["HK-010", "HK-020"])

    def test_explains_absent_city_category(self):
        result = recommend([provider(city="Астана")], REQUEST)
        self.assertEqual(result["outcome"], "category_absent")
        self.assertIn("нет подрядчиков", result["message"])

    def test_explains_no_matching_candidates(self):
        result = recommend(
            [
                provider(id="HK-001", busy_dates=frozenset({REQUEST.event_date})),
                provider(id="HK-002", price_from_kzt=250_000),
            ],
            REQUEST,
        )
        self.assertEqual(result["outcome"], "no_match")
        self.assertIn("заняты", result["message"])
        self.assertIn("бюджет", result["message"])

    def test_checks_optional_language_and_duration(self):
        result = recommend(
            [
                provider(id="HK-001", languages=("казахский",)),
                provider(id="HK-002", max_hours=4),
            ],
            REQUEST,
        )
        self.assertEqual(result["outcome"], "no_match")
        self.assertIn("языке", result["message"])
        self.assertIn("длительности", result["message"])

    def test_explains_small_catalog_when_no_one_was_rejected(self):
        result = recommend([provider()], REQUEST)
        self.assertEqual(result["outcome"], "matches")
        self.assertIn("в этой категории", result["message"])

    def test_exact_budget_and_unlimited_hours_are_allowed(self):
        result = recommend(
            [provider(price_from_kzt=200_000, max_hours=None)],
            RecommendationRequest(
                city="Алматы",
                event_date="2026-11-14",
                event_format="корпоратив",
                category="Ведущий",
                budget_kzt=200_000,
                duration_hours=12,
                language="русский",
            ),
        )
        self.assertEqual(result["outcome"], "matches")

    def test_rejects_invalid_request_values(self):
        with self.assertRaises(ValueError):
            recommend([provider()], RecommendationRequest("Алматы", "not-a-date", "корпоратив", "Ведущий", 1))
        with self.assertRaises(ValueError):
            recommend([provider()], RecommendationRequest("Алматы", "2026-11-14", "корпоратив", "Ведущий", 0))
        with self.assertRaises(ValueError):
            recommend(
                [provider()],
                RecommendationRequest("Алматы", "2026-11-14", "корпоратив", "Ведущий", 1, duration_hours=0),
            )


if __name__ == "__main__":
    unittest.main()
