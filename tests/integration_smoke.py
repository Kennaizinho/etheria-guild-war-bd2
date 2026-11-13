"""Smoke-test de endpoints no Docker. Requer web, PostgreSQL e Redis ativos."""
import json
import os
import unittest
from urllib.request import urlopen

BASE = os.environ.get('BASE_URL', 'http://localhost:8080')


def api(path):
    with urlopen(BASE.rstrip('/') + path, timeout=30) as response:
        return response.status, response.headers, json.load(response)


class IntegrationTests(unittest.TestCase):
    def test_health(self):
        status, _, data = api('/health')
        self.assertEqual(status, 200)
        self.assertEqual(data['postgresql'], 'ok')
        self.assertEqual(data['redis'], 'ok')

    def test_guild(self):
        _, _, data = api('/api/guilda/jantus')
        self.assertEqual(data['nome_guilda'], 'JANTUS')
        self.assertGreater(len(data['membros']), 0)

    def test_member_profile(self):
        _, _, data = api('/api/perfil/j_01')
        self.assertIn('winrate_geral', data)

    def test_battle_data(self):
        _, _, data = api('/api/batalhas/NatusVinceri')
        self.assertGreater(len(data), 0)
        self.assertEqual(len(data[0]['atacante']['composicao']), 3)

    def test_entities(self):
        _, _, data = api('/api/entidades')
        self.assertTrue(all(data.get(key) for key in ('herois','cartas','pets')))

    def test_cache(self):
        _, _, first = api('/api/defesas-gerais')
        _, headers, second = api('/api/defesas-gerais')
        self.assertEqual(first, second)
        self.assertEqual(headers.get('X-Cache'), 'HIT')


if __name__ == '__main__':
    unittest.main()
