"""Acceptance sweep: every catalog city/category/format across all 100 days."""
import re
import unittest
from datetime import date, timedelta
from src.api import PROVIDERS
from src.recommendation import RecommendationRequest, recommend, description_evidence


class FullCalendarAcceptanceTests(unittest.TestCase):
    def test_all_calendar_queries_have_correct_distinct_grounded_cards(self):
        queries = {(p.city, category, fmt) for p in PROVIDERS
                   for category in p.categories for fmt in p.event_formats}
        lookup = {p.id: p for p in PROVIDERS}
        name_pattern = re.compile('|'.join(re.escape(p.name) for p in PROVIDERS), re.I)
        seen = set()
        for city, category, fmt in sorted(queries):
            scoped = [p for p in PROVIDERS if p.city == city and category in p.categories]
            for day in range(100):
                request = RecommendationRequest(city, (date(2026, 9, 23) + timedelta(days=day)).isoformat(),
                                                fmt, category, 1000000000)
                result = recommend(PROVIDERS, request)
                eligible = [p for p in scoped if request.event_date not in p.busy_dates and fmt in p.event_formats]
                expected = sorted(eligible, key=lambda p: (p.price_from_kzt, p.id))[:3]
                self.assertEqual([c['id'] for c in result['cards']], [p.id for p in expected], request)
                self.assertEqual(result['stats']['eligible'], len(eligible), request)
                self.assertEqual(result['outcome'], 'matches' if eligible else 'no_match', request)
                self.assertTrue(result['message'].strip(), request)
                texts = [name_pattern.sub('[name]', c['explanation']) for c in result['cards']]
                self.assertEqual(len(set(texts)), len(texts), request)
                for card in result['cards']:
                    seen.add(card['id'])
                    self.assertEqual(card['explanation'].count('.'), 2, request)
                    if '— в профиле:' in card['explanation']:
                        self.assertTrue(any(f'— в профиле: «{fact}».' in card['explanation']
                                            for fact in description_evidence(lookup[card['id']].description)), card['id'])
        self.assertEqual(len(queries) * 100, 11200)
        self.assertEqual(seen, set(lookup))
