"""One-command live LOCAL demo check, stdlib only; never requests AI."""
import argparse
import json
from pathlib import Path
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, ProxyHandler, HTTPRedirectHandler

CASES_PATH = Path(__file__).resolve().parents[1] / 'examples' / 'demo-cases.json'


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def check_case(case, status, body):
    if status != case['expected_status']:
        raise AssertionError(f"HTTP {status}, expected {case['expected_status']}")
    if status == 422:
        fields = [item.get('loc') for item in body.get('detail', [])]
        if ['body', case['expected_error_field']] not in fields:
            raise AssertionError('Missing field-specific validation error')
        return
    if body.get('outcome') != case['expected_outcome']:
        raise AssertionError('Unexpected outcome')
    cards = body.get('cards', [])
    if [card['id'] for card in cards] != case['expected_ids']:
        raise AssertionError('Unexpected contractor IDs/order')
    if body.get('stats', {}).get('eligible') != case['expected_eligible']:
        raise AssertionError('Unexpected eligible count')
    if case['message_contains'] not in body.get('message', ''):
        raise AssertionError('Missing explanation of the result')
    for card in cards:
        if not card.get('explanation') or case['request']['event_date'] not in card['explanation']:
            raise AssertionError('Missing dated card explanation')
        if any(type(card.get(flag)) is not bool for flag in ('synthetic', 'city_imputed', 'price_imputed')):
            raise AssertionError('Missing data provenance flags')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://127.0.0.1:8000')
    args = parser.parse_args()
    parsed = urlsplit(args.base_url)
    if (parsed.scheme != 'http' or parsed.hostname not in ('127.0.0.1', 'localhost', '::1')
            or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ('', '/')):
        parser.error('Use an explicit local HTTP origin without path, credentials or query.')
    base = args.base_url.rstrip('/')
    opener = build_opener(ProxyHandler({}), NoRedirect())
    def call(path, payload=None):
        data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode('utf-8')
        request = Request(base + path, data=data, headers={'Content-Type': 'application/json'})
        start = time.perf_counter()
        try:
            response = opener.open(request, timeout=10)
        except HTTPError as error:
            response = error
        with response:
            body = json.loads(response.read(256 * 1024))
            return response.status, body, time.perf_counter()-start
    failures = 0
    try:
        status, health, _ = call('/health')
        if status != 200 or health != {'status': 'ok', 'profiles_loaded': 66}:
            raise AssertionError('Health/catalog check failed')
        status, filters, _ = call('/filters')
        if status != 200 or filters.get('event_date_range') != {'min': '2026-09-23', 'max': '2026-12-31'}:
            raise AssertionError('Calendar/filter check failed')
        cases = json.loads(CASES_PATH.read_text(encoding='utf-8'))
        for case in cases:
            try:
                status, body, seconds = call('/recommendations', case['request'])
                check_case(case, status, body)
                if seconds > 10:
                    raise AssertionError('Response exceeded 10 seconds')
                print(f"PASS | {case['name']} | HTTP {status} | {seconds*1000:.1f} ms")
            except (AssertionError, ValueError, URLError, OSError) as error:
                failures += 1
                print(f"FAIL | {case['name']} | {type(error).__name__}: {error}")
        first = cases[0]
        status, repeated, _ = call('/recommendations', first['request'])
        check_case(first, status, repeated)
        print('PASS | Repeated request preserves expected order')
    except (AssertionError, ValueError, URLError, OSError) as error:
        print(f'FAIL | {type(error).__name__}: {error}')
        return 1
    print(f'Finished: {failures} failed cases; AI not requested.')
    return 1 if failures else 0


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
