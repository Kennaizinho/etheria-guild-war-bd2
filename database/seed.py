"""Importa dados reais do backup (1.969 batalhas), sem inventar 100 mil registros.

Idempotente: executá-lo novamente não duplica batalhas, guildas nem membros.
O PostgreSQL deve ter sido criado com database/01..04*.sql.
"""
import json
import os
from datetime import datetime
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def names_from_images(directory):
    if not directory.exists():
        return set()
    names = {p.stem for p in directory.iterdir() if p.suffix.lower() in ('.webp', '.png')}
    names = {n for n in names if not (' ' in n and n.replace(' ', '') in names)}
    return names - {'noncard', 'nocard'}


def seed():
    battles = read_json(ROOT / 'batalhas.json')
    guilds = [read_json(ROOT / 'dados_guildas' / (name + '.json'))
              for name in ('jantus', 'oblivion')]
    if not all(len(b[side]['composicao']) == 3 for b in battles
               for side in ('atacante', 'defensor')):
        raise ValueError('Histórico contém batalha sem três posições por lado')

    image_base = ROOT / 'static' / 'img'
    catalog = {
        'heroi': names_from_images(image_base / 'PersonagensFullBody'),
        'carta': names_from_images(image_base / 'Cards'),
        'pet': names_from_images(image_base / 'Pets'),
    }
    players = set()
    for g in guilds:
        players.update(m['nickname'] for m in g['membros'])
    for b in battles:
        for side in ('atacante', 'defensor'):
            players.add(b[side]['nome'])
            for slot in b[side]['composicao']:
                for t, attr in (('heroi', 'heroi'), ('carta', 'carta'), ('pet', 'pet')):
                    catalog[t].add(slot[attr])
    if not all(catalog.values()):
        raise ValueError('Catálogos incompletos')

    with psycopg.connect(os.environ.get('DATABASE_URL', '')) as conn:
        with conn.cursor() as cur:
            cur.executemany(
                'INSERT INTO jogador (nickname) VALUES (%s) ON CONFLICT (nickname) DO NOTHING',
                [(p,) for p in sorted(players)],
            )
            for name, values in catalog.items():
                cur.executemany(
                    f'INSERT INTO {name} (nome) VALUES (%s) ON CONFLICT (nome) DO NOTHING',
                    [(v,) for v in sorted(values)],
                )
            cur.executemany(
                'INSERT INTO guilda (codigo, nome) VALUES (%s, %s) '
                'ON CONFLICT (codigo) DO UPDATE SET nome = EXCLUDED.nome',
                [(g['id_guilda'], g['nome_guilda']) for g in guilds],
            )
            cur.execute('SELECT id_jogador, nickname FROM jogador')
            player_ids = {name: identity for identity, name in cur.fetchall()}
            cur.execute('SELECT id_guilda, codigo FROM guilda')
            guild_ids = {code: identity for identity, code in cur.fetchall()}
            for guild in guilds:
                cur.executemany(
                    'INSERT INTO membro_guilda '
                    '(id_membro, id_guilda, id_jogador, cargo, avatar) '
                    'VALUES (%s,%s,%s,%s,%s) ON CONFLICT (id_membro) DO UPDATE SET '
                    'id_guilda=EXCLUDED.id_guilda, id_jogador=EXCLUDED.id_jogador, '
                    'cargo=EXCLUDED.cargo, avatar=EXCLUDED.avatar',
                    [(m['id'], guild_ids[guild['id_guilda']], player_ids[m['nickname']],
                      m.get('cargo', 'membro'), m.get('avatar', 'Airon'))
                     for m in guild['membros']],
                )

            for kind in ('heroi', 'carta', 'pet'):
                cur.execute(f'SELECT id_{kind}, nome FROM {kind}')
                catalog[kind] = {name: identity for identity, name in cur.fetchall()}

            cur.executemany(
                'INSERT INTO batalha '
                '(codigo, data_batalha, resultado, id_atacante, id_defensor) '
                'VALUES (%s,%s,%s,%s,%s) ON CONFLICT (codigo) DO NOTHING',
                [(b['id_batalha'], datetime.strptime(b['data'], '%d/%m/%Y').date(),
                  b['resultado'], player_ids[b['atacante']['nome']],
                  player_ids[b['defensor']['nome']]) for b in battles],
            )
            cur.execute('SELECT id_batalha, codigo FROM batalha')
            battle_ids = {code: identity for identity, code in cur.fetchall()}
            # ON CONFLICT faz o seed ser reiniciável sem criar composições duplicadas.
            rows = []
            for b in battles:
                for side in ('atacante', 'defensor'):
                    for number, slot in enumerate(b[side]['composicao'], start=1):
                        rows.append((battle_ids[b['id_batalha']], side, number,
                                     catalog['heroi'][slot['heroi']],
                                     catalog['carta'][slot['carta']],
                                     catalog['pet'][slot['pet']]))
            cur.executemany(
                'INSERT INTO composicao_batalha '
                '(id_batalha,lado,slot,id_heroi,id_carta,id_pet) '
                'VALUES (%s,%s,%s,%s,%s,%s) '
                'ON CONFLICT (id_batalha,lado,slot) DO NOTHING', rows,
            )
    print(f'Seed concluído: {len(battles)} batalhas de origem, '
          f'{len(players)} jogadores distintos, {len(rows)} posições. '
          'Repetições não criam registros duplicados.')


if __name__ == '__main__':
    seed()
