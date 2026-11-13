"""Benchmark reproduzível sem remover índices ou modificar dados do usuário.

Executar: docker compose exec web python scripts/benchmark.py --iterations 20
Mede: Postgres com índices habilitados x plano sequencial forçado; API Redis MISS x HIT.
"""
import argparse
import json
import math
import os
import statistics
import time
from urllib.request import urlopen

import psycopg
import redis


QUERY = '''
SELECT id_batalha, data_batalha, resultado
FROM batalha WHERE id_atacante=%s
ORDER BY data_batalha DESC, id_batalha DESC LIMIT 50
'''


def benchmark_sql(iterations):
    with psycopg.connect(os.environ.get('DATABASE_URL', ''), autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute('''SELECT id_atacante FROM batalha GROUP BY id_atacante
                           ORDER BY COUNT(*) DESC LIMIT 1''')
            row = cur.fetchone()
            if row is None:
                return {'aviso': 'Nenhuma batalha carregada.'}
            attacker = row[0]
            measures = {}
            for mode in ('indices_permitidos', 'varredura_sequencial_forcada'):
                timings = []
                plan = None
                for _ in range(iterations):
                    with conn.transaction():
                        if mode == 'varredura_sequencial_forcada':
                            cur.execute('SET LOCAL enable_indexscan = off')
                            cur.execute('SET LOCAL enable_bitmapscan = off')
                            cur.execute('SET LOCAL enable_indexonlyscan = off')
                        cur.execute('EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) ' + QUERY,
                                    (attacker,))
                        plan = cur.fetchone()[0][0]
                        timings.append(float(plan['Execution Time']))
                measures[mode] = {
                    'media_ms': round(statistics.mean(timings), 3),
                    'min_ms': round(min(timings), 3),
                    'max_ms': round(max(timings), 3),
                    'tipo_plano': plan['Plan']['Node Type'],
                }
            return measures


def benchmark_cache(iterations, base):
    r = redis.Redis.from_url(os.environ.get('REDIS_URL', 'redis://localhost:6379/0'),
                             decode_responses=True)
    version = r.get('etheria:v1:version:batalhas') or '0'
    key = 'etheria:v1:defesas:gerais:v1:v' + version
    r.delete(key)  # apaga SOMENTE a chave de teste, nunca FLUSHDB.
    timings = []
    for _ in range(iterations + 1):
        start = time.perf_counter()
        with urlopen(base.rstrip('/') + '/api/defesas-gerais', timeout=60) as response:
            status = response.headers.get('X-Cache', '')
            response.read()
        timings.append((status, round((time.perf_counter() - start) * 1000, 3)))
    return {'primeira_chamada': {'cache': timings[0][0], 'latencia_ms': timings[0][1]},
            'chamadas_seguintes': {
                'estados': dict((state, sum(1 for status, _ in timings[1:] if status == state))
                                for state, _ in timings[1:]),
                'media_ms': round(statistics.mean(t for _, t in timings[1:]), 3),
                'p95_ms': round(sorted(t for _, t in timings[1:])[
                    max(0, math.ceil(iterations * .95) - 1)], 3)}}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--iterations', type=int, default=20)
    parser.add_argument('--url', default='http://localhost:8080')
    args = parser.parse_args()
    if args.iterations < 2:
        parser.error('--iterations precisa ser >= 2')
    print(json.dumps({'sql': benchmark_sql(args.iterations),
                      'redis': benchmark_cache(args.iterations, args.url)},
                     ensure_ascii=False, indent=2))
