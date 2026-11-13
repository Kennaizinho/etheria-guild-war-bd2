-- VIEW 1: estatísticas oficiais de ataques de cada jogador.
CREATE OR REPLACE VIEW vw_desempenho_jogador AS
SELECT j.id_jogador, j.nickname,
       COUNT(b.id_batalha)::INTEGER AS total_ataques,
       COUNT(b.id_batalha) FILTER (WHERE b.resultado = 'Vitória')::INTEGER AS vitorias,
       COALESCE(ROUND(100.0 * COUNT(b.id_batalha) FILTER
           (WHERE b.resultado = 'Vitória') / NULLIF(COUNT(b.id_batalha), 0), 1), 0)::NUMERIC(5,1) AS winrate
FROM jogador j
LEFT JOIN batalha b ON b.id_atacante = j.id_jogador
GROUP BY j.id_jogador, j.nickname;

-- VIEW 2: versão legível das batalhas com os apelidos dos participantes.
CREATE OR REPLACE VIEW vw_batalhas_resumo AS
SELECT b.id_batalha, b.codigo, b.data_batalha, b.resultado,
       a.nickname AS atacante, d.nickname AS defensor, b.criado_em
FROM batalha b
JOIN jogador a ON a.id_jogador = b.id_atacante
JOIN jogador d ON d.id_jogador = b.id_defensor;
