-- Trigger de restrição diferida: cada batalha DEVE ter exatamente 3 slots
-- do atacante e 3 do defensor quando a transação termina (COMMIT).
CREATE OR REPLACE FUNCTION fn_verificar_seis_posicoes() RETURNS TRIGGER
LANGUAGE plpgsql AS $$
DECLARE
    alvo BIGINT;
    n_atacante INTEGER;
    n_defensor INTEGER;
BEGIN
    alvo := CASE WHEN TG_TABLE_NAME = 'batalha' THEN NEW.id_batalha ELSE OLD.id_batalha END;
    -- Em DELETE CASCADE da batalha, não se valida um registro já removido.
    IF NOT EXISTS (SELECT 1 FROM batalha WHERE id_batalha = alvo) THEN
        RETURN NULL;
    END IF;
    SELECT COUNT(*) FILTER (WHERE lado = 'atacante'),
           COUNT(*) FILTER (WHERE lado = 'defensor')
    INTO n_atacante, n_defensor
    FROM composicao_batalha WHERE id_batalha = alvo;
    IF n_atacante <> 3 OR n_defensor <> 3 THEN
        RAISE EXCEPTION 'Batalha % incompleta: atacante=%, defensor=% (esperado: 3 e 3)',
            alvo, n_atacante, n_defensor USING ERRCODE = '23514';
    END IF;
    RETURN NULL;
END;
$$;

DROP TRIGGER IF EXISTS trg_batalha_completa ON batalha;
CREATE CONSTRAINT TRIGGER trg_batalha_completa
    AFTER INSERT OR UPDATE ON batalha
    DEFERRABLE INITIALLY DEFERRED
    FOR EACH ROW EXECUTE FUNCTION fn_verificar_seis_posicoes();

DROP TRIGGER IF EXISTS trg_composicao_removida ON composicao_batalha;
CREATE CONSTRAINT TRIGGER trg_composicao_removida
    AFTER DELETE OR UPDATE ON composicao_batalha
    DEFERRABLE INITIALLY DEFERRED
    FOR EACH ROW EXECUTE FUNCTION fn_verificar_seis_posicoes();

-- Rotina armazenada de registro. Recebe um objeto JSONB com exatamente
-- 3 posições por lado e resolve as FKs dos catálogos em SQL.
CREATE OR REPLACE FUNCTION fn_registrar_batalha(
    p_codigo TEXT, p_data DATE, p_resultado TEXT,
    p_atacante TEXT, p_defensor TEXT, p_composicoes JSONB
) RETURNS BIGINT
LANGUAGE plpgsql AS $$
DECLARE
    v_atacante BIGINT;
    v_defensor BIGINT;
    v_batalha BIGINT;
    v_lado TEXT;
    v_slot JSONB;
    v_pos INTEGER;
    v_heroi BIGINT;
    v_carta BIGINT;
    v_pet BIGINT;
BEGIN
    IF p_codigo IS NULL OR btrim(p_codigo) = '' OR p_codigo !~ '^[a-zA-Z0-9_-]{1,100}$' THEN
        RAISE EXCEPTION 'Código da batalha inválido' USING ERRCODE = '22023';
    END IF;
    IF p_resultado NOT IN ('Vitória','Derrota') OR p_resultado IS NULL THEN
        RAISE EXCEPTION 'Resultado inválido' USING ERRCODE = '22023';
    END IF;
    IF p_atacante IS NULL OR p_defensor IS NULL OR
       btrim(p_atacante) = '' OR btrim(p_defensor) = '' OR p_atacante = p_defensor THEN
        RAISE EXCEPTION 'Atacante e defensor precisam ser distintos e identificados' USING ERRCODE = '22023';
    END IF;
    IF jsonb_typeof(p_composicoes) IS DISTINCT FROM 'object' OR
       jsonb_typeof(p_composicoes->'atacante') IS DISTINCT FROM 'array' OR
       jsonb_typeof(p_composicoes->'defensor') IS DISTINCT FROM 'array' OR
       jsonb_array_length(p_composicoes->'atacante') <> 3 OR
       jsonb_array_length(p_composicoes->'defensor') <> 3 THEN
        RAISE EXCEPTION 'São exigidos exatamente 3 slots por lado' USING ERRCODE = '22023';
    END IF;

    INSERT INTO jogador (nickname) VALUES (p_atacante)
        ON CONFLICT (nickname) DO UPDATE SET nickname = EXCLUDED.nickname
        RETURNING id_jogador INTO v_atacante;
    INSERT INTO jogador (nickname) VALUES (p_defensor)
        ON CONFLICT (nickname) DO UPDATE SET nickname = EXCLUDED.nickname
        RETURNING id_jogador INTO v_defensor;

    INSERT INTO batalha (codigo, data_batalha, resultado, id_atacante, id_defensor)
    VALUES (p_codigo, p_data, p_resultado, v_atacante, v_defensor)
    RETURNING id_batalha INTO v_batalha;

    FOREACH v_lado IN ARRAY ARRAY['atacante','defensor'] LOOP
        FOR v_pos IN 0..2 LOOP
            v_slot := p_composicoes->v_lado->v_pos;
            SELECT id_heroi INTO v_heroi FROM heroi WHERE nome = v_slot->>'heroi';
            SELECT id_carta INTO v_carta FROM carta WHERE nome = v_slot->>'carta';
            SELECT id_pet INTO v_pet FROM pet WHERE nome = v_slot->>'pet';
            IF v_heroi IS NULL OR v_carta IS NULL OR v_pet IS NULL THEN
                RAISE EXCEPTION 'Catálogo inexistente na posição % do lado %', v_pos+1, v_lado
                    USING ERRCODE = '23503';
            END IF;
            INSERT INTO composicao_batalha
                (id_batalha, lado, slot, id_heroi, id_carta, id_pet)
            VALUES (v_batalha, v_lado, v_pos+1, v_heroi, v_carta, v_pet);
        END LOOP;
    END LOOP;
    RETURN v_batalha;
END;
$$;
