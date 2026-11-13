"""Repositório relacional: a API consulta somente PostgreSQL, nunca os JSONs."""
import os
from contextlib import contextmanager
from datetime import date

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


@contextmanager
def session():
    with psycopg.connect(os.environ.get('DATABASE_URL', ''), row_factory=dict_row,
                         connect_timeout=5) as connection:
        yield connection


def get_guild(name):
    with session() as db:
        with db.cursor() as cursor:
            cursor.execute('SELECT id_guilda,codigo,nome FROM guilda WHERE lower(nome)=%s '
                           'OR lower(codigo)=%s', (name.lower(), name.lower()))
            guild = cursor.fetchone()
            if guild is None:
                return None
            cursor.execute('''
                SELECT m.id_membro AS id, j.nickname, m.cargo, m.avatar
                FROM membro_guilda m
                JOIN jogador j ON j.id_jogador=m.id_jogador
                WHERE m.id_guilda=%s
                ORDER BY CASE m.cargo WHEN 'lider' THEN 0 WHEN 'vice' THEN 1 ELSE 2 END,
                         lower(j.nickname)
            ''', (guild['id_guilda'],))
            return {'id_guilda': guild['codigo'], 'nome_guilda': guild['nome'],
                    'membros': cursor.fetchall()}


def get_profile(member_id):
    with session() as db:
        with db.cursor() as cursor:
            cursor.execute('''
                SELECT m.id_membro AS id, j.nickname, m.cargo, m.avatar,
                       g.nome AS guilda, v.winrate
                FROM membro_guilda m
                JOIN jogador j ON j.id_jogador=m.id_jogador
                JOIN guilda g ON g.id_guilda=m.id_guilda
                JOIN vw_desempenho_jogador v ON v.id_jogador=j.id_jogador
                WHERE m.id_membro=%s
            ''', (member_id,))
            return cursor.fetchone()


def get_entities():
    with session() as db:
        with db.cursor() as cursor:
            result = {}
            for table, key in (('heroi', 'herois'), ('carta', 'cartas'), ('pet', 'pets')):
                cursor.execute(f'SELECT nome FROM {table} ORDER BY nome')
                result[key] = [r['nome'] for r in cursor.fetchall()]
            return result


BATTLE_SELECT = '''
    SELECT b.id_batalha, b.codigo, b.data_batalha, b.resultado,
           a.nickname AS nome_atacante, d.nickname AS nome_defensor
    FROM batalha b
    JOIN jogador a ON a.id_jogador=b.id_atacante
    JOIN jogador d ON d.id_jogador=b.id_defensor
'''


def _assemble_battles(cursor, rows):
    if not rows:
        return []
    ids = [r['id_batalha'] for r in rows]
    cursor.execute('''
        SELECT c.id_batalha,c.lado,c.slot,
               h.nome AS heroi,ca.nome AS carta,p.nome AS pet
        FROM composicao_batalha c
        JOIN heroi h ON h.id_heroi=c.id_heroi
        JOIN carta ca ON ca.id_carta=c.id_carta
        JOIN pet p ON p.id_pet=c.id_pet
        WHERE c.id_batalha=ANY(%s)
        ORDER BY c.id_batalha,c.lado,c.slot
    ''', (ids,))
    compositions = {}
    for c in cursor.fetchall():
        groups = compositions.setdefault(c['id_batalha'], {'atacante': [], 'defensor': []})
        groups[c['lado']].append({'heroi': c['heroi'], 'carta': c['carta'], 'pet': c['pet']})
    result = []
    for b in rows:
        groups = compositions.get(b['id_batalha'], {'atacante': [], 'defensor': []})
        result.append({
            'id_batalha': b['codigo'],
            'data': b['data_batalha'].strftime('%d/%m/%Y'),
            'resultado': b['resultado'],
            'atacante': {'nome': b['nome_atacante'], 'composicao': groups['atacante']},
            'defensor': {'nome': b['nome_defensor'], 'composicao': groups['defensor']},
        })
    return result


def get_battles(nickname=None, matched_heroes=None, minimum_matches=3):
    """Histórico completo, por nickname ou por pelo menos N heróis na defesa."""
    with session() as db:
        with db.cursor() as cursor:
            where = ''
            args = []
            if nickname is not None:
                where = ' WHERE a.nickname=%s OR d.nickname=%s'
                args = [nickname, nickname]
            elif matched_heroes is not None:
                where = ''' WHERE b.id_batalha IN (
                    SELECT c.id_batalha
                    FROM composicao_batalha c
                    JOIN heroi h ON h.id_heroi=c.id_heroi
                    WHERE c.lado='defensor' AND h.nome = ANY(%s::text[])
                    GROUP BY c.id_batalha
                    HAVING COUNT(DISTINCT h.nome) >= %s
                )'''
                args = [matched_heroes, minimum_matches]
            cursor.execute(BATTLE_SELECT + where + ' ORDER BY b.id_batalha', args)
            return _assemble_battles(cursor, cursor.fetchall())


def create_battle(data):
    """Uma única transação com a função SQL + trigger de validação no COMMIT."""
    with session() as db:
        with db.cursor() as cursor:
            cursor.execute('SELECT fn_registrar_batalha(%s,%s,%s,%s,%s,%s)', (
                data['id_batalha'], data['date'], data['resultado'],
                data['atacante']['nome'], data['defensor']['nome'],
                Jsonb({'atacante': data['atacante']['composicao'],
                       'defensor': data['defensor']['composicao']}),
            ))
            identity = cursor.fetchone()['fn_registrar_batalha']
        # commit automático do context manager da conexão, trigger de restrição diferida.
    return identity


def is_alive():
    with session() as db:
        return db.execute('SELECT 1 AS ok').fetchone()['ok'] == 1
