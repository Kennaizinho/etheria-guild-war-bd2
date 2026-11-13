"""Teste concorrente da restrição UNIQUE e transação ACID.

Exige WRITE_API_KEY e web em execução. Envia simultaneamente o mesmo ID,
mas dados válidos. Espera exatamente um HTTP 201 e os demais HTTP 409.
"""
import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
url = os.environ.get('BASE_URL', 'http://localhost:8080').rstrip('/') + '/api/batalhas'
key = os.environ['WRITE_API_KEY']
battle = json.loads((ROOT / 'batalhas.json').read_text(encoding='utf-8'))[0].copy()
battle['id_batalha'] = 'teste_concorrencia_' + uuid4().hex


def send(_):
    request = Request(url, data=json.dumps(battle).encode('utf-8'), method='POST',
                      headers={'Content-Type': 'application/json', 'X-API-Key': key})
    try:
        with urlopen(request, timeout=30) as response:
            response.read()
            return response.status
    except HTTPError as error:
        return error.code


if __name__ == '__main__':
    # O identificador muda por execução para que o teste possa ser repetido.
    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(send, range(5)))
    print('Resultados concorrentes:', results)
    expected = sorted(results) == [201, 409, 409, 409, 409]
    print('PASSOU' if expected else 'FALHOU: use um identificador de teste novo')
    raise SystemExit(0 if expected else 1)
