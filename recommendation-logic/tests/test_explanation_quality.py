"""Grounding and masked-name checks; human semantic review is still necessary."""
from dataclasses import replace
import unittest
from src.api import PROVIDERS
from src.ai_explanations import evidence_candidates
from src.recommendation import RecommendationRequest, recommend, description_evidence, explanation_with_evidence
from test_recommendation import provider

HOSTS = RecommendationRequest('Алматы', '2026-10-07', 'свадьба', 'Ведущий', 1000000, language='казахский')

class ExplanationQualityTests(unittest.TestCase):
    def test_hosts_explain_different_reasons_without_names(self):
        cards = recommend(PROVIDERS, HOSTS)['cards']
        expected = ['казахском, русском и английском', 'Опыт ведения свадеб 13 лет', 'европейская подача']
        masked = []
        for card, signal in zip(cards, expected):
            text = card['explanation']
            for candidate in cards:
                text = text.replace(candidate['name'], '[имя]')
            self.assertIn(signal, text)
            masked.append(text)
            self.assertIn('итоговую стоимость нужно уточнить', text)
        self.assertEqual(len({t.split('. ')[0] for t in masked}), 3)

    def test_florists_show_volume_vs_palette(self):
        request = replace(HOSTS, category='Флорист', event_date='2026-10-04', budget_kzt=250000, language='русский')
        cards = recommend(PROVIDERS, request)['cards']
        self.assertIn('1000 заказов', cards[0]['explanation'])
        self.assertIn('под цветовую палитру', cards[1]['explanation'])
        self.assertIn('на 50 000 ₸ ниже', cards[0]['explanation'])
        self.assertIn('совпадает с вашим лимитом', cards[1]['explanation'])
        self.assertTrue(cards[0]['price_imputed'])
        self.assertTrue(cards[1]['synthetic'])

    def test_format_changes_evidence_not_source_facts(self):
        p = provider(event_formats=('свадьба', 'конференция'), description=(
            'Для свадеб готовим сценарий с историей молодожёнов. '
            'Для конференций готовим сценарий с презентациями и обсуждением докладов.'))
        wedding = recommend([p], replace(HOSTS, language=None))['cards'][0]['explanation']
        conference = recommend([p], replace(HOSTS, event_format='конференция', language=None))['cards'][0]['explanation']
        self.assertIn('историей молодожёнов', wedding)
        self.assertIn('обсуждением докладов', conference)

    def test_quotes_are_source_fragments_and_two_sentences(self):
        for p in PROVIDERS:
            request = RecommendationRequest(p.city, '2026-10-15', p.event_formats[0], p.categories[0], 10000000)
            for card in recommend(PROVIDERS, request)['cards']:
                source = next(item for item in PROVIDERS if item.id == card['id'])
                text = card['explanation']
                self.assertEqual(text.count('.'), 2)
                if text.startswith('Акцент профиля'):
                    excerpt = text.split('«', 1)[1].split('».', 1)[0]
                    self.assertIn(excerpt, ' '.join(source.description.split()))
                self.assertNotRegex(text.lower(), r'гарантированно|лучший выбор|идеальный выбор')

    def test_ai_and_rules_exclude_marketing(self):
        text = 'Мы в топ-10 и гарантируем идеальный праздник. Опыт ведения свадеб 13 лет.'
        self.assertEqual(description_evidence(text), ['Опыт ведения свадеб 13 лет'])
        self.assertEqual(evidence_candidates(text), description_evidence(text))

    def test_untrusted_evidence_cannot_invent_claim(self):
        p = provider(description='Опыт ведения свадеб 13 лет.', event_formats=('свадьба',))
        text = explanation_with_evidence(p, replace(HOSTS, language=None), 'Обслужил 9000 свадеб бесплатно')
        self.assertNotIn('9000', text)
        self.assertIn('13 лет', text)

    def test_identical_profiles_get_honest_limitation(self):
        people = [provider(id='A', name='Первый'), provider(id='B', name='Второй')]
        result = recommend(people, replace(HOSTS, event_format='корпоратив', language=None))
        self.assertEqual(result['cards'][0]['explanation'], result['cards'][1]['explanation'])
        self.assertIn('недостаточно, чтобы обоснованно различить', result['message'])

    def test_null_hours_not_unlimited_attendance(self):
        result = recommend([provider(max_hours=None)], replace(HOSTS, event_format='корпоратив', language=None, duration_hours=12))
        text = result['cards'][0]['explanation']
        self.assertIn('не привязана к часам присутствия', text)
        self.assertIn('сроки выполнения нужно согласовать', text)
        self.assertNotIn('без ограничений', text)

    def test_partial_results_explain_date_and_ranking(self):
        people = [provider(id='a'), provider(id='b', busy_dates=frozenset({HOSTS.event_date})), provider(id='c')]
        result = recommend(people, replace(HOSTS, event_format='корпоратив', language=None))
        self.assertIn('из-за занятости на ' + HOSTS.event_date, result['message'])
        self.assertIn('не по оценке качества', result['message'])

    def test_empty_result_suggests_action_without_relaxing_filters(self):
        busy = recommend(PROVIDERS, replace(HOSTS, event_date='2026-10-03'))
        self.assertEqual(busy['cards'], [])
        self.assertIn('проверить другую дату', busy['message'])
        self.assertIn('после изменения условий нужен новый подбор', busy['message'])
