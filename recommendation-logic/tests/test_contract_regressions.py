"""Regression tests for the API/domain boundary, including invalid inputs."""

from unittest import TestCase
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.api import app, PROVIDERS
from src.recommendation import RecommendationRequest, recommend, _description_excerpt
from test_recommendation import provider


BASE = dict(city="Алматы", event_date="2026-10-15", event_format="корпоратив",
            category="Ведущий", budget_kzt=6_000_000)


class ContractRegressionTests(TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_invalid_fields_rejected_by_both_layers(self):
        cases = [
            ("event_date", "2026-09-22"), ("event_date", "2027-01-01"),
            ("event_date", "20261015"), ("event_date", "2026-W42-4"),
            ("event_date", "2026-11-31"), ("event_date", 1792022400),
            ("event_date", "2026-10-15T00:00:00"), ("event_date", None),
            ("city", "   "), ("city", 42), ("category", "\t"),
            ("event_format", "\n"), ("language", "   "), ("language", False),
            ("budget_kzt", True), ("budget_kzt", "6000000"),
            ("budget_kzt", 5.5), ("budget_kzt", 6000000.0),
            ("budget_kzt", 0), ("budget_kzt", -1), ("budget_kzt", None),
            ("duration_hours", True), ("duration_hours", "4.5"),
            ("duration_hours", 0), ("duration_hours", -0.1),
        ]
        for field, value in cases:
            with self.subTest(field=field, value=value):
                payload = BASE | {field: value}
                with self.assertRaises(ValueError):
                    recommend(PROVIDERS, RecommendationRequest(**payload))
                response = self.client.post("/recommendations", json=payload)
                self.assertEqual(response.status_code, 422)
                self.assertIsInstance(response.json()["detail"], list)
                self.assertIn(["body", field], [e["loc"] for e in response.json()["detail"]])

    def test_nonfinite_duration_rejected(self):
        from src.api import RecommendationPayload
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    recommend(PROVIDERS, RecommendationRequest(**(BASE | {"duration_hours": value})))
                with self.assertRaises(ValueError):
                    RecommendationPayload(**(BASE | {"duration_hours": value}))

    def test_busy_dates_at_both_calendar_boundaries_stay_excluded(self):
        p = provider(busy_dates=frozenset({"2026-09-23", "2026-12-31"}))
        with patch("src.api.PROVIDERS", [p]):
            limits = self.client.get("/filters").json()["event_date_range"]
            for day in limits.values():
                payload = BASE | {"event_date": day}
                expected = recommend([p], RecommendationRequest(**payload))
                result = self.client.post("/recommendations", json=payload)
                self.assertEqual(result.status_code, 200)
                self.assertEqual(result.json(), expected)
                self.assertEqual(result.json()["outcome"], "no_match")
                self.assertEqual(result.json()["stats"]["rejected"], {"busy": 1})

    def test_filter_range_does_not_depend_on_bookings(self):
        with patch("src.api.PROVIDERS", []):
            response = self.client.get("/filters")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["event_date_range"],
                         {"min": "2026-09-23", "max": "2026-12-31"})

    def test_whitespace_normalization_and_optional_nulls_match(self):
        payload = BASE | {"city": " Алматы ", "category": " Ведущий ",
                          "event_format": " корпоратив ", "language": " русский ",
                          "duration_hours": 4.5}
        expected = recommend(PROVIDERS, RecommendationRequest(**payload))
        self.assertEqual(self.client.post("/recommendations", json=payload).json(), expected)
        self.assertEqual(expected, recommend(PROVIDERS, RecommendationRequest(
            **(BASE | {"language": "русский", "duration_hours": 4.5}))))
        self.assertEqual(self.client.post("/recommendations", json=BASE).json(),
                         self.client.post("/recommendations", json=BASE | {
                             "language": None, "duration_hours": None}).json())

    def test_fractional_hours_use_actual_limit_in_both_layers(self):
        candidates = [provider(id="short", max_hours=4), provider(id="long", max_hours=5)]
        payload = BASE | {"duration_hours": 4.5}
        with patch("src.api.PROVIDERS", candidates):
            result = self.client.post("/recommendations", json=payload)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json(), recommend(candidates, RecommendationRequest(**payload)))
        self.assertEqual([c["id"] for c in result.json()["cards"]], ["long"])
        self.assertIn("4,5 ч", result.json()["cards"][0]["explanation"])

    def test_unknown_and_missing_fields_are_validation_errors(self):
        for payload in (BASE | {"languag": "казахский"},
                        {k: v for k, v in BASE.items() if k != "city"}):
            self.assertEqual(self.client.post("/recommendations", json=payload).status_code, 422)

    def test_all_outcomes_have_one_response_contract(self):
        for change, outcome in (({}, "matches"), ({"budget_kzt": 1}, "no_match"),
                                ({"category": "Несуществующая"}, "category_absent")):
            with self.subTest(outcome=outcome):
                result = self.client.post("/recommendations", json=BASE | change)
                self.assertEqual(result.status_code, 200)
                body = result.json()
                self.assertEqual(body["outcome"], outcome)
                self.assertEqual(set(body["stats"]), {"catalog_candidates", "eligible", "rejected"})
                self.assertEqual(body, recommend(PROVIDERS, RecommendationRequest(**(BASE | change))))

    def test_catalog_requests_have_identical_direct_and_http_results(self):
        for p in PROVIDERS:
            with self.subTest(provider=p.id):
                payload = BASE | dict(city=p.city, category=p.categories[0],
                                     event_format=p.event_formats[0], language=p.languages[0])
                response = self.client.post("/recommendations", json=payload)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), recommend(PROVIDERS, RecommendationRequest(**payload)))

    def test_openapi_describes_cards_outcomes_and_stats(self):
        schema = self.client.get("/openapi.json").json()
        ref = schema["paths"]["/recommendations"]["post"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
        response = schema["components"]["schemas"][ref.rsplit("/", 1)[-1]]
        self.assertEqual(set(response["required"]), {"outcome", "cards", "message", "stats"})
        self.assertEqual(response["properties"]["cards"]["maxItems"], 3)
        self.assertIn("explanation", schema["components"]["schemas"]["RecommendationCard"]["required"])

    def test_description_truncation_preserves_words_and_marks_omission(self):
        description = "Авторское оформление мероприятий цветами и индивидуальный подход к каждой площадке с учётом пожеланий заказчика"
        excerpt = _description_excerpt(description)
        self.assertTrue(excerpt.endswith("…"))
        prefix = excerpt[:-1]
        self.assertTrue(description.startswith(prefix + " "))

    def test_reasons_are_stable_when_catalog_order_changes(self):
        candidates = [provider(id="one", price_from_kzt=7000000),
                      provider(id="two", busy_dates=frozenset({BASE["event_date"]}))]
        req = RecommendationRequest(**BASE)
        self.assertEqual(recommend(candidates, req), recommend(reversed(candidates), req))

    def test_team_demo_cases_and_source_flags(self):
        cases = [
            (dict(category="Ведущий", event_date="2026-10-07", budget_kzt=1_000_000,
                  language="казахский"), "matches", 3, 4),
            (dict(category="Ведущий", event_date="2026-10-03", budget_kzt=1_000_000,
                  language="казахский"), "no_match", 0, 0),
            (dict(category="Флорист", event_date="2026-10-04", budget_kzt=250_000,
                  language="русский"), "matches", 2, 2),
            (dict(category="Флорист", event_date="2026-10-04", budget_kzt=100_000,
                  language="русский"), "no_match", 0, 0),
        ]
        for changes, outcome, count, eligible in cases:
            with self.subTest(changes=changes):
                body = self.client.post("/recommendations", json=BASE | {
                    "event_format": "свадьба"} | changes).json()
                self.assertEqual(body["outcome"], outcome)
                self.assertEqual(len(body["cards"]), count)
                self.assertEqual(body["stats"]["eligible"], eligible)
                for card in body["cards"]:
                    source = next(p for p in PROVIDERS if p.id == card["id"])
                    for flag in ("synthetic", "price_imputed", "city_imputed"):
                        self.assertEqual(card[flag], getattr(source, flag))
                if changes["budget_kzt"] == 250_000:
                    chopper = next(card for card in body["cards"] if card["name"] == "Тони Тони Чоппер")
                    self.assertTrue(chopper["price_imputed"])
