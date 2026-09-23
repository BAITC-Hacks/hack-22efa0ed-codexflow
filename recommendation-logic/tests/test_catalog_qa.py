"""Deep QA checks against the real hackathon catalog, not mock data only."""

from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
import unittest

from src.recommendation import RecommendationRequest, load_providers, recommend


DATASET = Path(__file__).parents[1] / "data" / "providers.csv"


class CatalogQualityAssuranceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.providers = load_providers(DATASET)
        cls.by_id = {provider.id: provider for provider in cls.providers}

    def test_dataset_has_expected_integrity(self):
        self.assertEqual(len(self.providers), 66)
        self.assertEqual(len(self.by_id), 66, "Provider IDs must be unique")
        self.assertEqual(sum(provider.synthetic for provider in self.providers), 13)
        for provider in self.providers:
            self.assertTrue(provider.name)
            self.assertTrue(provider.categories)
            self.assertTrue(provider.event_formats)
            self.assertTrue(provider.languages)
            self.assertGreater(provider.price_from_kzt, 0)
            for busy_date in provider.busy_dates:
                date.fromisoformat(busy_date)

    def test_every_real_catalog_query_is_safe_and_deterministic(self):
        """Exercise each profile as the source of a valid request."""
        for source in self.providers:
            request = RecommendationRequest(
                city=source.city,
                event_date="2026-10-15",
                event_format=source.event_formats[0],
                category=source.categories[0],
                budget_kzt=6_000_000,
                duration_hours=3,
                language=source.languages[0],
            )
            result = recommend(self.providers, request)
            self.assertEqual(result, recommend(self.providers, request))
            self.assertLessEqual(len(result["cards"]), 3)

            ranking = []
            for card in result["cards"]:
                provider = self.by_id[card["id"]]
                self.assertEqual(card["city"], request.city)
                self.assertIn(request.category, provider.categories)
                self.assertNotIn(request.event_date, provider.busy_dates)
                self.assertLessEqual(provider.price_from_kzt, request.budget_kzt)
                self.assertIn(request.event_format, provider.event_formats)
                self.assertIn(request.language, provider.languages)
                if provider.max_hours is not None:
                    self.assertGreaterEqual(provider.max_hours, request.duration_hours)
                self.assertEqual(card["synthetic"], provider.synthetic)
                self.assertIn(request.event_date, card["explanation"])
                self.assertEqual(card["explanation"].count("."), 2)
                ranking.append((provider.price_from_kzt, provider.id))
            self.assertEqual(ranking, sorted(ranking))

    def test_all_three_required_outcomes_are_explicit(self):
        absent = recommend(
            self.providers,
            RecommendationRequest("Алматы", "2026-10-15", "корпоратив", "Несуществующая категория", 500_000),
        )
        no_match = recommend(
            self.providers,
            RecommendationRequest("Алматы", "2026-10-15", "корпоратив", "Ведущий", 1),
        )
        matched = recommend(
            self.providers,
            RecommendationRequest("Алматы", "2026-10-15", "корпоратив", "Ведущий", 6_000_000),
        )
        self.assertEqual(absent["outcome"], "category_absent")
        self.assertIn("нет подрядчиков", absent["message"])
        self.assertEqual(no_match["outcome"], "no_match")
        self.assertIn("бюджет", no_match["message"])
        self.assertEqual(matched["outcome"], "matches")

    def test_date_changes_can_change_results_and_are_explained(self):
        """Find a real category where availability causes a different ranking."""
        groups = defaultdict(list)
        for provider in self.providers:
            for category in provider.categories:
                groups[(provider.city, category)].append(provider)

        calendar = [date(2026, 9, 23) + timedelta(days=offset) for offset in range(100)]
        found_pair = None
        for (city, category), group in groups.items():
            event_format = group[0].event_formats[0]
            outputs = {}
            for event_date in calendar:
                request = RecommendationRequest(city, event_date.isoformat(), event_format, category, 6_000_000)
                result = recommend(self.providers, request)
                ids = tuple(card["id"] for card in result["cards"])
                if result["outcome"] == "matches" and ids:
                    outputs.setdefault(ids, (request, result))
            if len(outputs) > 1:
                (_, first), (_, second) = list(outputs.values())[:2]
                found_pair = (first, second)
                break

        self.assertIsNotNone(found_pair, "The supplied calendar should alter at least one recommendation")
        for result in found_pair:
            self.assertTrue(result["cards"])
            request_date = result["cards"][0]["explanation"].split(" ")[1]
            self.assertTrue(all(request_date in card["explanation"] for card in result["cards"]))

    def test_cards_in_one_result_have_non_interchangeable_explanations(self):
        requests = [
            RecommendationRequest("Алматы", "2026-10-15", "корпоратив", "Ведущий", 6_000_000),
            RecommendationRequest("Астана", "2026-10-20", "свадьба", "Фотограф", 6_000_000),
            RecommendationRequest("Алматы", "2026-11-01", "свадьба", "Банкетный зал", 6_000_000),
        ]
        for request in requests:
            cards = recommend(self.providers, request)["cards"]
            explanations = [card["explanation"] for card in cards]
            self.assertEqual(len(explanations), len(set(explanations)))


if __name__ == "__main__":
    unittest.main()
