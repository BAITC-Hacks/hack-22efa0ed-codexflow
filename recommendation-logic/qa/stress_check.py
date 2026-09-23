"""Bounded, repeatable local QA. No real AI calls; starts/stops its own server.

Run from recommendation-logic: python qa/stress_check.py --output PATH.json
"""
from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from dataclasses import asdict, replace
from datetime import date, timedelta
import json
import os
from pathlib import Path
import random
import socket
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import httpx
from fastapi.testclient import TestClient
from src.api import app, PROVIDERS
from src.ai_explanations import AIExplainer, AISettings
from src.recommendation import RecommendationRequest, recommend

BASE = dict(city='Алматы', event_date='2026-10-07', event_format='свадьба',
            category='Ведущий', budget_kzt=1000000, language='казахский')


def timing(samples):
    ordered = sorted(samples)
    return {name: round(ordered[min(len(ordered)-1, int((len(ordered)-1)*q))]*1000, 3)
            for name, q in [('p50_ms', .5), ('p95_ms', .95), ('p99_ms', .99), ('max_ms', 1)]}


def oracle(request):
    """Independent filtering/sorting oracle for canonical generated requests."""
    scoped = [p for p in PROVIDERS if p.city == request.city and request.category in p.categories]
    eligible = [p for p in scoped if request.event_date not in p.busy_dates
                and p.price_from_kzt <= request.budget_kzt and request.event_format in p.event_formats
                and (request.language is None or request.language in p.languages)
                and (request.duration_hours is None or p.max_hours is None or request.duration_hours <= p.max_hours)]
    expected = sorted(eligible, key=lambda p: (p.price_from_kzt, p.id))[:3]
    return [p.id for p in expected], len(scoped), len(eligible)


def domain_stress(count):
    rng = random.Random(79)
    latencies, errors, outcomes = [], [], Counter()
    for index in range(count):
        p = rng.choice(PROVIDERS)
        request = RecommendationRequest(p.city, (date(2026, 9, 23)+timedelta(days=index % 100)).isoformat(),
            rng.choice(p.event_formats), rng.choice(p.categories),
            rng.choice([1, max(1, p.price_from_kzt-1), p.price_from_kzt, p.price_from_kzt+1, 10000000]),
            rng.choice([None, .5, 4, 4.5, 8, 24]), rng.choice([None, *p.languages]))
        started = time.perf_counter()
        result = recommend(PROVIDERS, request)
        latencies.append(time.perf_counter()-started)
        outcomes[result['outcome']] += 1
        ids, scoped, eligible = oracle(request)
        expected_outcome = 'category_absent' if scoped == 0 else 'matches' if eligible else 'no_match'
        valid = ([c['id'] for c in result['cards']] == ids and result['outcome'] == expected_outcome
                 and result['stats']['eligible'] == eligible and result['stats']['catalog_candidates'] == scoped)
        if index % 20 == 0:
            valid &= result == recommend(reversed(PROVIDERS), request)
        if not valid and len(errors) < 10:
            errors.append({'request': asdict(request), 'result': result, 'expected_ids': ids})
    return {'requests': count, 'seed': 79, 'outcomes': dict(outcomes), 'errors': errors, **timing(latencies)}


def edge_cases():
    bodies = {
        'nan_duration': json.dumps(BASE | {'duration_hours': float('nan')}),
        'infinite_duration': json.dumps(BASE | {'duration_hours': float('inf')}),
        'valid_json_overflow_exponent': json.dumps(BASE)[:-1]+', "duration_hours": 1e309}',
        'nan_budget': json.dumps(BASE | {'budget_kzt': float('nan')}),
        'lone_surrogate_city': json.dumps(BASE | {'city': '\ud800'}),
        '100k_character_city': json.dumps(BASE | {'city': 'x'*100000}),
        '400_digit_budget': json.dumps(BASE | {'budget_kzt': 10**400}),
        'negative_budget': json.dumps(BASE | {'budget_kzt': -1}),
        'boolean_budget': json.dumps(BASE | {'budget_kzt': True}),
        'wrong_date': json.dumps(BASE | {'event_date': '2026-11-31'}),
        'array_instead_of_object': '[]',
        'broken_json': '{',
    }
    rows = []
    with TestClient(app, raise_server_exceptions=False) as client:
        for name, body in bodies.items():
            start = time.perf_counter()
            response = client.post('/recommendations', content=body, headers={'Content-Type': 'application/json'})
            rows.append({'case': name, 'status': response.status_code, 'response_bytes': len(response.content),
                         'duration_ms': round((time.perf_counter()-start)*1000, 3)})
    # Capture exact exception classes without logging user input or credentials.
    with TestClient(app) as client:
        for row in rows:
            if row['status'] == 500:
                try:
                    client.post('/recommendations', content=bodies[row['case']], headers={'Content-Type': 'application/json'})
                except Exception as error:
                    row['exception'] = type(error).__name__
                    row['error_summary'] = str(error)[:180]
    return rows


def scaling():
    rows = []
    for multiplier in (1, 10, 100):
        providers = [replace(p, id=f'{p.id}-{i:03}') for i in range(multiplier) for p in PROVIDERS]
        samples = []
        for _ in range(30):
            start = time.perf_counter()
            result = recommend(providers, RecommendationRequest(**BASE))
            samples.append(time.perf_counter()-start)
            assert len(result['cards']) == 3
        rows.append({'profiles': len(providers), 'requests': len(samples), **timing(samples)})
    return rows


async def network_load(url, concurrency, count):
    cases = [BASE, BASE | {'event_date': '2026-10-03'}, BASE | {'budget_kzt': 1},
             BASE | {'category': 'Флорист', 'language': 'русский', 'budget_kzt': 250000},
             BASE | {'city': 'Зарубежье', 'category': 'Флорист'}]
    expected = [recommend(PROVIDERS, RecommendationRequest(**case)) for case in cases]
    gate = asyncio.Semaphore(concurrency)
    times, codes, errors = [], Counter(), Counter()
    async with httpx.AsyncClient(base_url=url, timeout=10,
            limits=httpx.Limits(max_connections=concurrency, max_keepalive_connections=concurrency)) as client:
        async def one(index):
            async with gate:
                start = time.perf_counter()
                try:
                    response = await client.post('/recommendations', json=cases[index % len(cases)])
                    codes[str(response.status_code)] += 1
                    if response.status_code != 200 or response.json() != expected[index % len(cases)]:
                        errors['contract_or_result_mismatch'] += 1
                except Exception as error:
                    errors[type(error).__name__] += 1
                times.append(time.perf_counter()-start)
        start = time.perf_counter()
        await asyncio.gather(*(one(i) for i in range(count)))
        elapsed = time.perf_counter()-start
        health = await client.get('/health')
    return {'concurrency': concurrency, 'requests': count, 'status_codes': dict(codes),
            'errors': dict(errors), 'health_after': health.status_code,
            'elapsed_seconds': round(elapsed, 3), 'requests_per_second': round(count/elapsed, 1), **timing(times)}


async def ai_stress():
    # Mock only: transport cannot reach the Internet and key is fake.
    async def handler(request):
        await asyncio.sleep(.25)
        schema = json.loads(request.content)['text']['format']['schema']
        selection = {key: 0 for key in schema['required']}
        return httpx.Response(200, json={'status': 'completed', 'output': [
            {'type': 'message', 'content': [{'type': 'output_text', 'text': json.dumps(selection)}]}]})

    async def wave(distinct):
        service = AIExplainer(AISettings(True, 'fake-stress-test', max_calls=100), transport=httpx.MockTransport(handler))
        async def one(i):
            req = RecommendationRequest(**(BASE | {'budget_kzt': 1000000+i if distinct else 1000000}))
            original = recommend(PROVIDERS, req)
            start = time.perf_counter()
            result, source, reason = await service.enhance(original, PROVIDERS, req)
            assert [c['id'] for c in result['cards']] == [c['id'] for c in original['cards']]
            return time.perf_counter()-start, source, reason
        results = await asyncio.gather(*(one(i) for i in range(32)))
        return {'concurrency': 32, 'mock_latency_ms': 250, 'distinct_requests': distinct,
                'sources': dict(Counter(row[1] for row in results)),
                'reasons': dict(Counter(row[2] for row in results)), 'model_calls': service._calls,
                **timing([row[0] for row in results])}

    same = await wave(False)
    different = await wave(True)
    service = AIExplainer(AISettings(True, 'fake-stress-test'), transport=httpx.MockTransport(handler))
    req = RecommendationRequest(**BASE)
    original = recommend(PROVIDERS, req)
    await service.enhance(original, PROVIDERS, req)
    for city in ('алматы', 'АЛМАТЫ', ' Алматы '):
        variant = replace(req, city=city)
        await service.enhance(recommend(PROVIDERS, variant), PROVIDERS, variant)
    variant_calls = service._calls
    # Demonstrate cache lookup behind global lock: unrelated slow work blocks hot results.
    async with service._lock:
        original_settings = service.settings
        service.settings = replace(original_settings, timeout_seconds=.1)
        _, blocked_source, blocked_reason = await service.enhance(original, PROVIDERS, req)
    return {'same_request_wave': same, 'different_request_wave': different,
            'equivalent_city_variants_model_calls': variant_calls,
            'cached_result_behind_busy_lock': {'source': blocked_source, 'reason': blocked_reason}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--domain-count', type=int, default=10000)
    args = parser.parse_args()
    report = {'python': sys.version.split()[0], 'catalog_profiles': len(PROVIDERS), 'real_ai_calls': 0}
    print('Phase 1: domain oracle, malformed inputs, catalog scaling', flush=True)
    report['domain'] = domain_stress(args.domain_count)
    report['edge_cases'] = edge_cases()
    report['scaling'] = scaling()
    print('Phase 2: actual loopback HTTP, isolated single-worker server', flush=True)
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        port = listener.getsockname()[1]
    env = dict(os.environ, AI_EXPLANATIONS_ENABLED='false', OPENAI_API_KEY='')
    with tempfile.TemporaryFile() as log:
        process = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'src.api:app', '--host', '127.0.0.1',
            '--port', str(port), '--log-level', 'error', '--no-access-log'], cwd=ROOT, env=env,
            stdout=log, stderr=log, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        try:
            url = f'http://127.0.0.1:{port}'
            for _ in range(100):
                if process.poll() is not None:
                    raise RuntimeError('Isolated server failed to start')
                try:
                    if httpx.get(url+'/health', timeout=.5).status_code == 200:
                        break
                except httpx.HTTPError:
                    time.sleep(.1)
            else:
                raise RuntimeError('Server startup timeout')
            report['http'] = []
            for concurrency in (1, 8, 32, 64):
                row = asyncio.run(network_load(url, concurrency, 500))
                report['http'].append(row)
                print(json.dumps(row), flush=True)
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
    print('Phase 3: simulated AI concurrency and cache', flush=True)
    report['ai_mock'] = asyncio.run(ai_stress())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=True, indent=2), flush=True)


if __name__ == '__main__':
    main()
