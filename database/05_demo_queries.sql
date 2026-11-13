-- Exemplos DML e consultas para apresentação (executar via psql).
-- 1. Verificar quantidade original, sem registros artificiais.
SELECT COUNT(*) AS total_batalhas FROM batalha;
SELECT COUNT(*) AS posicoes FROM composicao_batalha;
SELECT COUNT(*) AS total_jogadores FROM jogador;

-- 2. Inspecionar VIEW de desempenho dos jogadores.
SELECT nickname, total_ataques, vitorias, winrate
FROM vw_desempenho_jogador
ORDER BY total_ataques DESC LIMIT 10;

-- 3. Usar VIEW com informações legíveis.
SELECT codigo, data_batalha, resultado, atacante, defensor
FROM vw_batalhas_resumo ORDER BY data_batalha DESC LIMIT 10;

-- 4. Demonstrar índice e plano de execução.
EXPLAIN (ANALYZE, BUFFERS)
SELECT id_batalha, data_batalha, resultado
FROM batalha
WHERE id_atacante = (SELECT id_atacante FROM batalha LIMIT 1)
ORDER BY data_batalha DESC, id_batalha DESC LIMIT 50;

-- 5. Mostrar funções, triggers e índices existentes.
SELECT proname FROM pg_proc WHERE proname LIKE 'fn_%' ORDER BY proname;
SELECT tgname FROM pg_trigger WHERE NOT tgisinternal AND
    tgrelid IN ('batalha'::regclass, 'composicao_batalha'::regclass);
SELECT tablename, indexname FROM pg_indexes
WHERE schemaname='public' AND tablename IN ('batalha','composicao_batalha')
ORDER BY tablename,indexname;

-- 6. Teste de rollback da trigger: SEM criar dados permanentes.
-- Uma batalha com 0 posições falha no COMMIT e será revertida.
-- Use o endpoint POST /api/batalhas para observar um COMMIT válido.
-- Um exemplo isolado de transação inválida:
-- BEGIN;
-- INSERT INTO batalha(codigo,data_batalha,resultado,id_atacante,id_defensor)
-- SELECT 'teste_sem_slots', CURRENT_DATE, 'Vitória',
--        (SELECT id_jogador FROM jogador ORDER BY id_jogador LIMIT 1),
--        (SELECT id_jogador FROM jogador ORDER BY id_jogador OFFSET 1 LIMIT 1);
-- COMMIT; -- deve falhar por faltar as seis composições
