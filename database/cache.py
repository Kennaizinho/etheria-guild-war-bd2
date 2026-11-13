"""Redis: Cache-Aside com TTL, tratamento de indisponibilidade e versionamento."""
import hashlib
import json
import os

import redis
from redis.exceptions import RedisError

PREFIX = 'etheria:v1:'
_client = None


def client():
    global _client
    if _client is None:
        _client = redis.Redis.from_url(os.environ.get('REDIS_URL', 'redis://localhost:6379/0'),
                                      socket_connect_timeout=0.5, socket_timeout=0.5,
                                      decode_responses=True)
    return _client


def battle_version():
    try:
        return client().get(PREFIX + 'version:batalhas') or '0'
    except RedisError:
        return None


def make_key(family, version=None):
    if version is None:
        return PREFIX + family
    return PREFIX + family + ':v' + str(version)


def cached_value(family, ttl, compute, depends_on_battles=True):
    """Retorna (resultado, 'HIT'|'MISS'|'BYPASS').

    Se Redis não responder, o produtor ainda consulta PostgreSQL.
    """
    version = battle_version() if depends_on_battles else None
    if depends_on_battles and version is None:
        return compute(), 'BYPASS'
    key = make_key(family, version)
    try:
        value = client().get(key)
        if value is not None:
            return json.loads(value), 'HIT'
    except (RedisError, json.JSONDecodeError):
        return compute(), 'BYPASS'
    data = compute()
    try:
        client().setex(key, ttl, json.dumps(data, ensure_ascii=False))
    except RedisError:
        return data, 'BYPASS'
    return data, 'MISS'


def invalidate_battles():
    """Deve ser chamada SOMENTE após commit bem-sucedido no PostgreSQL.
    Mudança de versão invalida atomicamente todas as famílias derivadas.
    """
    try:
        client().incr(PREFIX + 'version:batalhas')
        return True
    except RedisError:
        return False  # TTL limita eventual inconsistência se Redis oscilar.


def fingerprint(names):
    normalized = '|'.join(sorted(names))
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()[:24]


def is_alive():
    try:
        return bool(client().ping())
    except RedisError:
        return False
