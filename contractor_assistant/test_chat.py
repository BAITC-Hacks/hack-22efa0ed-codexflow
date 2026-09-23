"""Regression tests for the standalone contractor assistant.

Run from the repository root:
    PYTHONPATH=recommendation-logic python -m unittest contractor_assistant.test_chat -v
"""
import unittest

from contractor_assistant.chat import assistant_turn
from src.recommendation import Provider


def sample_catalog():
    common = dict(
        categories=("Фотограф",),
        city="Астана",
        event_formats=("день рождения", "свадьба"),
        languages=("русский",),
        max_hours=8,
        busy_dates=frozenset(),
        description="Опыт работы 5 лет. Репортажная съёмка и портреты.",
        synthetic=False,
    )
    return [
        Provider(id=f"P-{price}", name=f"Фотограф {price}", price_from_kzt=price, **common)
        for price in (100_000, 150_000, 200_000, 250_000)
    ]


class AssistantTurnTests(unittest.TestCase):
    def setUp(self):
        self.providers = sample_catalog()

    def test_short_request_recognizes_city_date_and_event_and_asks_for_rest(self):
        turn = assistant_turn(self.providers, "Астана, 12 ноября, день рождения")

        self.assertFalse(turn["complete"])
        self.assertEqual(turn["context"]["city"], "Астана")
        self.assertEqual(turn["context"]["event_date"], "2026-11-12")
        self.assertEqual(turn["context"]["event_format"], "день рождения")
        self.assertIsNone(turn["context"]["category"])
        self.assertIsNone(turn["context"]["budget_kzt"])
        self.assertIn("категорию", turn["reply"])
        self.assertIn("бюджет", turn["reply"])

    def test_follow_up_completes_request_using_saved_context_and_catalog(self):
        first = assistant_turn(self.providers, "Астана, 12 ноября, день рождения")
        second = assistant_turn(
            self.providers,
            "Нужен фотограф, бюджет до 300 тыс. тенге",
            first["context"],
        )

        self.assertTrue(second["complete"])
        self.assertEqual(second["context"]["category"], "Фотограф")
        self.assertEqual(second["context"]["budget_kzt"], 300_000)
        self.assertEqual(second["recommendation"]["outcome"], "matches")
        self.assertEqual(len(second["recommendation"]["cards"]), 3)
        self.assertTrue(all(card["city"] == "Астана" for card in second["recommendation"]["cards"]))

    def test_invalid_day_does_not_crash_or_create_a_recommendation(self):
        turn = assistant_turn(self.providers, "Астана, 32 ноября, день рождения")

        self.assertFalse(turn["complete"])
        self.assertIsNone(turn["recommendation"])
        self.assertIsNone(turn["context"]["event_date"])
        self.assertIn("дату", turn["reply"])

    def test_date_outside_catalog_calendar_is_rejected(self):
        turn = assistant_turn(
            self.providers,
            "Астана, 12 марта 2026, день рождения, фотограф, бюджет 300 тыс.",
        )

        self.assertFalse(turn["complete"])
        self.assertIsNone(turn["recommendation"])
        self.assertIn("23.09.2026", turn["reply"])

    def test_non_positive_budget_is_not_accepted(self):
        turn = assistant_turn(
            self.providers,
            "Астана, 12 ноября, день рождения, фотограф, бюджет 0",
        )

        self.assertFalse(turn["complete"])
        self.assertIsNone(turn["recommendation"])
        self.assertIsNone(turn["context"]["budget_kzt"])
        self.assertIn("больше нуля", turn["reply"])

    def test_empty_message_returns_a_helpful_prompt(self):
        turn = assistant_turn(self.providers, "")

        self.assertFalse(turn["complete"])
        self.assertIsNone(turn["recommendation"])
        self.assertIn("город, дату и повод", turn["reply"])


if __name__ == "__main__":
    unittest.main()
