"""Carga HTTP de leituras: calcula throughput, p50, p95 e falhas sem 100 mil registros.

Uso: docker compose exec web python scripts/carga.py --users 12 --requests 120
"""
import argparse
import json
import math
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import urlopen


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://localhost:8080/api/defesas-gerais')
    parser.add_argument('--users', type=int, default=12, help='Número de clientes simultâneos')
    parser.add_argument('--requests', type=int, default=120)
    args = parser.parse_args()
    if not (1 <= args.users <= 100 and 1 <= args.requests <= 10000):
        parser.error('users deve ser 1..100 e requests 1..10000')

    def measure(_):
        start = time.perf_counter()
        try:
            with urlopen(args.url, timeout=30) as response:
                response.read()
                return (response.status, response.headers.get('X-Cache', 'N/A'),
                        (time.perf_counter() - start) * 1000)
        except Exception as error:
            return (0, type(error).__name__, (time.perf_counter() - start) * 1000)

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.users) as pool:
        responses = list(pool.map(measure, range(args.requests)))
    elapsed = time.perf_counter() - started
    ordered = sorted(round(t, 3) for _, _, t in responses)
    good = sum(1 for status, _, _ in responses if status == 200)
    report = {
        'clientes_simultaneos': args.users,
        'requisicoes': args.requests,
        'sucesso_http_200': good,
        'falhas': args.requests-good,
        'duracao_s': round(elapsed,3),
        'throughput_req_s': round(args.requests/elapsed,2),
        'latencia_media_ms': round(statistics.mean(ordered),3),
        'p50_ms': ordered[math.ceil(len(ordered)*.50)-1],
        'p95_ms': ordered[math.ceil(len(ordered)*.95)-1],
        'max_ms': ordered[-1],
        'cache_hit': sum(1 for _,status,_ in responses if status == 'HIT'),
    }
    print(json.dumps(report,ensure_ascii=False,indent=2))
    raise SystemExit(0 if good == args.requests else 1)


if __name__ == '__main__':
    main()
