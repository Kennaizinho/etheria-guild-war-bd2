"""Testes locais independentes de PostgreSQL, Redis e Flask."""
import json
import unittest
from pathlib import Path

from services import (agrupar_ataques, assinatura, calcular_defesas,
                      formatar_mapa_sugestoes, normalize_battle, taxa)

BASE = Path(__file__).resolve().parents[1]
BATTLES = json.loads((BASE / 'batalhas.json').read_text(encoding='utf-8'))


class DomainTests(unittest.TestCase):
    def test_backup_has_expected_content(self):
        self.assertEqual(len(BATTLES), 1969)
        self.assertEqual(len({b['id_batalha'] for b in BATTLES}), 1969)
        self.assertEqual(sum(len(b[s]['composicao']) for b in BATTLES
                             for s in ('atacante', 'defensor')), 11814)

    def test_rate_no_zero_division(self):
        self.assertEqual(taxa(0, 0), 0)
        self.assertEqual(taxa(7, 10), 70.0)

    def test_signature_independent_of_slot_order(self):
        c = BATTLES[0]['defensor']['composicao']
        self.assertEqual(assinatura(c), assinatura(list(reversed(c))))

    def test_ranking_preserves_history_total(self):
        ranked = calcular_defesas(BATTLES, limit=10000)
        self.assertEqual(sum(row['total'] for row in ranked), len(BATTLES))
        self.assertTrue(all(0 <= row['winrate'] <= 100 for row in ranked))

    def test_aggregated_attacks(self):
        grouped = agrupar_ataques(BATTLES[:10])
        results = formatar_mapa_sugestoes(grouped)
        self.assertEqual(sum(row['total'] for row in results), 10)
        self.assertTrue(all(0 <= row['vitorias'] <= row['total'] for row in results))

    def test_valid_payload(self):
        data = normalize_battle(BATTLES[0])
        self.assertEqual(data['id_batalha'], 'bat_001')
        self.assertEqual(data['date'].isoformat(), '2026-08-30')

    def test_missing_composition_rejected(self):
        data = json.loads(json.dumps(BATTLES[0]))
        data['defensor']['composicao'].pop()
        with self.assertRaisesRegex(ValueError, 'três posições'):
            normalize_battle(data)

    def test_bad_date_rejected(self):
        data = json.loads(json.dumps(BATTLES[0]))
        data['data'] = '2026-30-08'
        with self.assertRaisesRegex(ValueError, 'DD/MM/AAAA'):
            normalize_battle(data)

    def test_duplicate_hero_rejected(self):
        data = json.loads(json.dumps(BATTLES[0]))
        data['atacante']['composicao'][1]['heroi'] = data['atacante']['composicao'][0]['heroi']
        with self.assertRaisesRegex(ValueError, 'distintos'):
            normalize_battle(data)

    def test_invalid_result_rejected(self):
        data = json.loads(json.dumps(BATTLES[0]))
        data['resultado'] = 'Empate'
        with self.assertRaisesRegex(ValueError, 'Vitória ou Derrota'):
            normalize_battle(data)


if __name__ == '__main__':
    unittest.main()
