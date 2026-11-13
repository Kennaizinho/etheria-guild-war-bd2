"""Etheria Guild War - Flask + PostgreSQL (fonte oficial) + Redis (cache).

Mantém os endpoints utilizados pelo frontend original. Os arquivos JSON são
insumos de migração, não são usados para responder requisições web.
"""
import hmac
import os
from pathlib import Path

import psycopg
from flask import Flask, jsonify, render_template, request

from database import cache, repository
from services import agrupar_ataques, calcular_defesas, formatar_mapa_sugestoes, normalize_battle

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024
BASE = Path(__file__).resolve().parent
LIMITE_DEFESAS_GLOBAIS = 50


def imagens_webp_completas():
    root = BASE / 'static' / 'img'
    for directory in ('PersonagensHeadIcon', 'PersonagensFullBody', 'Pets', 'Cards'):
        folder = root / directory
        webp = {p.stem for p in folder.glob('*.webp')}
        legacy = {p.stem for pattern in ('*.png', '*.jpg', '*.jpeg') for p in folder.glob(pattern)}
        if not webp or (legacy and not legacy.issubset(webp)):
            return False
    return True


PREFERIR_WEBP = imagens_webp_completas()


def url_avatar(name):
    folder = BASE / 'static' / 'img' / 'PersonagensHeadIcon'
    for ext in ('.webp', '.png'):
        if (folder / f'{name}{ext}').is_file():
            return f'/static/img/PersonagensHeadIcon/{name}{ext}'
    return f'/static/img/PersonagensHeadIcon/{name}.webp'


def resumir_defesas():
    return calcular_defesas(repository.get_battles(), LIMITE_DEFESAS_GLOBAIS)


def cached_response(family, ttl, compute, depends_on_battles=True):
    result, state = cache.cached_value(family, ttl, compute, depends_on_battles)
    response = jsonify(result)
    response.headers['X-Cache'] = state
    return response


@app.after_request
def aplicar_cache_imagens(response):
    if request.path.startswith('/static/img/') and response.status_code == 200:
        response.cache_control.public = True
        response.cache_control.max_age = 7 * 24 * 60 * 60
    return response


@app.errorhandler(psycopg.errors.UniqueViolation)
def conflito(error):
    return jsonify({'erro': 'Registro já existente ou tentativa concorrente duplicada.'}), 409


@app.errorhandler(psycopg.errors.CheckViolation)
@app.errorhandler(psycopg.errors.ForeignKeyViolation)
@app.errorhandler(psycopg.errors.InvalidParameterValue)
def integridade(error):
    return jsonify({'erro': 'Dados rejeitados pelas regras de integridade do banco.'}), 422


@app.errorhandler(psycopg.Error)
def falha_banco(error):
    app.logger.exception('Erro de conexão/consulta PostgreSQL')
    return jsonify({'erro': 'PostgreSQL indisponível ou falha na consulta.'}), 503


@app.route('/')
def home():
    return render_template('index.html', preferir_webp=PREFERIR_WEBP)


@app.route('/perfil/<id_membro>')
def pagina_perfil(id_membro):
    return render_template('perfil.html', id_membro=id_membro, preferir_webp=PREFERIR_WEBP)


@app.route('/health')
def health():
    sql_ok = False
    try:
        sql_ok = repository.is_alive()
    except (psycopg.Error, KeyError):
        pass
    redis_ok = cache.is_alive()
    body = {'postgresql': 'ok' if sql_ok else 'indisponivel',
            'redis': 'ok' if redis_ok else 'indisponivel',
            'status': 'ok' if sql_ok and redis_ok else 'degradado' if sql_ok else 'erro'}
    return jsonify(body), 200 if sql_ok else 503


@app.route('/api/guilda/<nome_guilda>')
def buscar_guilda(nome_guilda):
    if not nome_guilda.isalnum():
        return jsonify({'erro': 'Guilda inválida.'}), 400
    guild = repository.get_guild(nome_guilda)
    return jsonify(guild) if guild is not None else (jsonify({'erro': 'Guilda não encontrada.'}), 404)


@app.route('/api/perfil/<id_membro>')
def dados_perfil(id_membro):
    def compute():
        profile = repository.get_profile(id_membro)
        if profile is None:
            return None
        return {'id': profile['id'], 'nickname': profile['nickname'],
                'cargo': profile['cargo'], 'icone': url_avatar(profile['avatar']),
                'guilda': profile['guilda'],
                'winrate_geral': f"{profile['winrate']:.1f}%"}
    result, state = cache.cached_value(f'perfil:{id_membro}', 300, compute)
    if result is None:
        return jsonify({'erro': 'Membro não encontrado.'}), 404
    response = jsonify(result)
    response.headers['X-Cache'] = state
    return response


@app.route('/api/batalhas/<nickname>')
def buscar_batalhas(nickname):
    return cached_response(f'batalhas:jogador:{cache.fingerprint([nickname])}', 180,
                           lambda: repository.get_battles(nickname))


@app.route('/api/defesas-gerais')
def defesas_gerais():
    return cached_response('defesas:gerais:v1', 120, resumir_defesas)


@app.route('/api/entidades')
def obter_entidades():
    return cached_response('entidades:estaticas:v1', 3600, repository.get_entities,
                           depends_on_battles=False)


@app.route('/api/sugerir-ataque', methods=['POST'])
def sugerir_ataque():
    defense = request.get_json(silent=True)
    empty = {'tipo': 'nenhum', 'dados': []}
    if not isinstance(defense, list) or len(defense) != 3 or not all(
        isinstance(slot, dict) and isinstance(slot.get('heroi'), str) and slot['heroi'].strip()
        for slot in defense
    ):
        return jsonify(empty)
    heroes = sorted(slot['heroi'] for slot in defense)

    def compute():
        exact = repository.get_battles(matched_heroes=heroes, minimum_matches=3)
        if exact:
            return {'tipo': 'exato', 'dados': formatar_mapa_sugestoes(agrupar_ataques(exact))}
        # Correspondência de pelo menos dois heróis, como o algoritmo original.
        partial = repository.get_battles(matched_heroes=heroes, minimum_matches=2)
        if partial:
            return {'tipo': 'parcial', 'dados': formatar_mapa_sugestoes(agrupar_ataques(partial))}
        return empty

    return cached_response('sugestao:defesa:' + cache.fingerprint(heroes), 300, compute)


@app.route('/api/batalhas', methods=['POST'])
def cadastrar_batalha():
    expected = os.environ.get('WRITE_API_KEY', '')
    key = request.headers.get('X-API-Key', '')
    if not expected:
        return jsonify({'erro': 'Configure WRITE_API_KEY para habilitar escrita.'}), 503
    if not hmac.compare_digest(key, expected):
        return jsonify({'erro': 'Chave de acesso inválida.'}), 401
    try:
        data = normalize_battle(request.get_json(silent=True))
    except ValueError as error:
        return jsonify({'erro': str(error)}), 400
    identity = repository.create_battle(data)  # commit + validação ACID na saída
    invalidated = cache.invalidate_battles()  # somente APÓS o commit
    return jsonify({'mensagem': 'Batalha registrada.', 'id_batalha': data['id_batalha'],
                    'id_interno': identity, 'cache_invalidado': invalidated}), 201


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)), debug=False)
