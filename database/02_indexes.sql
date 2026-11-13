-- Índices para perfis, histórico e recomendação.
-- PKs e UNIQUEs criam índices automaticamente no PostgreSQL.
CREATE INDEX IF NOT EXISTS idx_batalha_atacante_data
    ON batalha (id_atacante, data_batalha DESC, id_batalha DESC);
CREATE INDEX IF NOT EXISTS idx_batalha_defensor_data
    ON batalha (id_defensor, data_batalha DESC, id_batalha DESC);
CREATE INDEX IF NOT EXISTS idx_membro_guilda
    ON membro_guilda (id_guilda, cargo);
CREATE INDEX IF NOT EXISTS idx_composicao_defesa_heroi
    ON composicao_batalha (id_heroi, id_batalha)
    WHERE lado = 'defensor';
CREATE INDEX IF NOT EXISTS idx_composicao_batalha_lado
    ON composicao_batalha (id_batalha, lado);
