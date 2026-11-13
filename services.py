"""Regras puras de domínio, independentes dos bancos e do Flask."""
from datetime import datetime
from uuid import uuid4


def venceu_ataque(battle):
    return battle['resultado'].lower() == 'vitória'


def assinatura(composition):
    return '|'.join(sorted(f"{s['heroi']}-{s['carta']}-{s['pet']}" for s in composition))


def taxa(wins, total):
    return wins / total * 100 if total else 0


def formatar_mapa_sugestoes(groups):
    results = [dict(composicao=d['composicao'], total=d['total'],
                    vitorias=d['vitorias'], winrate=taxa(d['vitorias'], d['total']))
               for d in groups.values()]
    return sorted(results, key=lambda d: (d['winrate'], d['total']), reverse=True)


def agrupar_ataques(battles):
    groups = {}
    for battle in battles:
        attack = battle['atacante']['composicao']
        group = groups.setdefault(assinatura(attack),
                                  {'composicao': attack, 'total': 0, 'vitorias': 0})
        group['total'] += 1
        group['vitorias'] += venceu_ataque(battle)
    return groups


def calcular_defesas(battles, limit=50):
    groups = {}
    for battle in battles:
        defense = battle['defensor']['composicao']
        group = groups.setdefault(assinatura(defense), {
            'composicao': defense, 'total': 0, 'vitorias': 0, 'ataques_sofridos': []
        })
        defense_won = not venceu_ataque(battle)
        group['total'] += 1
        group['vitorias'] += defense_won
        group['ataques_sofridos'].append({
            'atacante_nome': battle['atacante']['nome'],
            'atacante_composicao': battle['atacante']['composicao'],
            'defesa_venceu': defense_won, 'data': battle['data'],
        })
    results = [dict(composicao=d['composicao'], total=d['total'],
                    vitorias=d['vitorias'], winrate=taxa(d['vitorias'], d['total']),
                    ataques_sofridos=d['ataques_sofridos'][::-1])
               for d in groups.values()]
    return sorted(results, key=lambda d: (d['total'], d['winrate']),
                  reverse=True)[:limit]


def normalize_battle(payload):
    if not isinstance(payload, dict):
        raise ValueError('Envie um objeto JSON para registrar uma batalha.')
    result = payload.get('resultado')
    if result not in ('Vitória', 'Derrota'):
        raise ValueError('resultado deve ser Vitória ou Derrota.')
    raw_date = payload.get('data')
    try:
        parsed_date = datetime.strptime(raw_date, '%d/%m/%Y').date()
    except (ValueError, TypeError):
        raise ValueError('data deve usar o formato DD/MM/AAAA.') from None
    code = payload.get('id_batalha') or 'api_' + uuid4().hex
    if not isinstance(code, str) or not code or len(code) > 100 or not all(
        char.isascii() and (char.isalnum() or char in '_-') for char in code
    ):
        raise ValueError('id_batalha deve conter até 100 caracteres ASCII (letras, números, - ou _).')
    for side in ('atacante', 'defensor'):
        participant = payload.get(side)
        if not isinstance(participant, dict):
            raise ValueError(f'Lado {side} inválido.')
        name = participant.get('nome')
        if not isinstance(name, str) or not 0 < len(name.strip()) <= 150:
            raise ValueError(f'Nome de {side} inválido.')
        slots = participant.get('composicao')
        if not isinstance(slots, list) or len(slots) != 3:
            raise ValueError(f'{side} deve possuir exatamente três posições.')
        for slot in slots:
            if not isinstance(slot, dict) or any(
                not isinstance(slot.get(k), str) or not 0 < len(slot[k].strip()) <= 150
                for k in ('heroi', 'carta', 'pet')
            ):
                raise ValueError(f'Posição de {side} contém herói, carta ou pet inválido.')
        if len({slot['heroi'] for slot in slots}) != 3:
            raise ValueError(f'{side} deve possuir três heróis distintos.')
    if payload['atacante']['nome'] == payload['defensor']['nome']:
        raise ValueError('Atacante e defensor devem ser distintos.')
    return dict(payload, id_batalha=code, date=parsed_date)
