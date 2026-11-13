# Etheria Guild War - Projeto de Banco de Dados II

Plataforma Flask de análise de guildas e combates em Etheria: Restart. A interface original foi preservada. A fonte oficial passou de JSON para **PostgreSQL**; o **Redis** guarda caches temporários. O arquivo `batalhas.json` é usado **somente para importação inicial**.

## O que foi implementado

- 3FN e FKs: guilda, jogador, membro_guilda, batalha, composicao_batalha, heroi, carta, pet;
- CHECK, UNIQUE, PK, FK e trigger de restrição **DEFERRABLE** para 3 posições de cada lado;
- função SQL `fn_registrar_batalha` com transação e rollback em falha;
- duas views: `vw_desempenho_jogador` e `vw_batalhas_resumo`;
- índices para histórico de jogador, guildas e combinação dos heróis defensivos;
- cache Redis com padrão Cache-Aside, TTL e invalidação por versão após COMMIT;
- API Flask com endpoints existentes e novo `POST /api/batalhas` protegido por chave;
- Docker Compose para PostgreSQL 16, Redis 7, importador automático e backend;
- importação idempotente de **1.969 batalhas reais** com **11.814 posições** (sem gerar 100.000 registros);
- testes unitários, script de teste concorrente e benchmark com/sem índice disponível e Redis frio/quente.

## Executar o projeto

**Pré-requisito:** Docker Desktop (Windows/Mac) ou Docker Engine + plugin Compose (Linux).

No terminal, dentro da pasta do projeto:

```bash
cp .env.example .env
# No Windows PowerShell, use: Copy-Item .env.example .env
# Edite .env e defina POSTGRES_PASSWORD e WRITE_API_KEY.
docker compose up --build -d
```

Acesse **http://localhost:8080**. O Compose cria o esquema SQL automaticamente quando o volume do PostgreSQL é novo, importa o histórico em `seed` e só inicia a aplicação depois da conclusão do importador.

Inspecione o ambiente:

```bash
docker compose ps
docker compose logs seed
docker compose logs web
curl http://localhost:8080/health
```

O endpoint `/health` informa se PostgreSQL e Redis estão acessíveis. Se o Redis cair, as consultas usam PostgreSQL sem cache. Se PostgreSQL cair, o backend não deve considerar os JSON como substitutos.

**Aviso:** scripts em `/docker-entrypoint-initdb.d` executam apenas na criação de um volume PostgreSQL novo. Para atualizar um banco existente, aplique as migrações manualmente. Não execute `docker compose down -v` em ambiente com dados importantes, pois isso apagaria o volume.

## Endpoints compatíveis com a interface antiga

| Método e rota | Função |
|---|---|
| `GET /` | Página principal |
| `GET /perfil/<id_membro>` | Página do perfil |
| `GET /api/guilda/jantus` | Guilda e membros a partir do PostgreSQL |
| `GET /api/perfil/j_01` | Perfil e winrate calculado a partir da View |
| `GET /api/batalhas/NatusVinceri` | Histórico de ataques e defesas |
| `GET /api/defesas-gerais` | Ranking global de defesas |
| `GET /api/entidades` | Catálogo de heróis, cartas e pets |
| `POST /api/sugerir-ataque` | Recomendações com match de 3, depois 2 heróis |
| `POST /api/batalhas` | Inserção ACID autenticada e invalidação de cache |
| `GET /health` | Saúde dos dois bancos |

### Testar cache

```bash
curl -i http://localhost:8080/api/defesas-gerais
curl -i http://localhost:8080/api/defesas-gerais
```

O header `X-Cache` será **MISS** na primeira consulta (sem dados previamente cacheados) e **HIT** na próxima; pode aparecer **BYPASS** se Redis não estiver disponível. Chaves globais de batalhas ganham versão nova após um cadastro válido. O tempo de vida não equivale a garantia absoluta de consistência, pois falhas de comunicação entre o COMMIT do PostgreSQL e o Redis exigiriam uma solução transacional adicional (outbox/retries) para invalidação rigorosa.

### Registrar batalha real via API

O JSON é idêntico ao formato usado em `batalhas.json`: um objeto com `id_batalha` (opcional), `data` no formato DD/MM/AAAA, `resultado` (Vitória/Derrota), `atacante` e `defensor` com nome e três elementos de composição (heroi, carta, pet). Os nomes de herói/carta/pet devem existir no catálogo.

No PowerShell, um exemplo utilizando o primeiro registro apenas para estrutura (troque o ID por um novo):

```powershell
$b = Get-Content batalhas.json -Raw | ConvertFrom-Json
$payload = $b[0]
$payload.id_batalha = "teste_001"
$json = $payload | ConvertTo-Json -Depth 10
Invoke-RestMethod -Uri http://localhost:8080/api/batalhas -Method Post `
  -ContentType 'application/json' -Headers @{ 'X-API-Key' = 'SUA_CHAVE_DE_ESCRITA' } `
  -Body ([System.Text.Encoding]::UTF8.GetBytes($json))
```

Repetir o mesmo `id_batalha` retorna **409** por UNIQUE. Enviar uma composição incompleta retorna **400** na validação Python; tentar violar uma FK ou a regra de seis posições na camada SQL provoca rollback e erro. Essa rota permite testar ACID e a atualização dos resultados.

**Segurança:** o valor local padrão da chave no Compose é apenas um auxílio de demonstração. Defina uma chave forte em `.env` e não publique a API de escrita sem proteção adicional, TLS e controle de acesso em produção.

## Testes

### Testes locais sem bancos

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
```

### Testes com bancos ativos

```bash
docker compose exec web python -m unittest discover -s tests -p 'integration_smoke.py' -v
docker compose exec web python scripts/benchmark.py --iterations 20
docker compose exec web python scripts/concorrencia.py
docker compose exec web python scripts/carga.py --users 12 --requests 120
```

Benchmark SQL: compara o otimizador com índices habilitados versus **varredura sequencial forçada** usando `SET LOCAL enable_indexscan=off` (não remove índices reais). Esse método mostra impacto de planos alternativos, mas não substitui um teste em duas tabelas fisicamente indexadas/não indexadas com volumes iguais. A quantidade de registros neste backup é pequena; o planejador pode escolher varredura sequencial mesmo com índices habilitados, e é possível não observar ganho. Compare os planos e medidas reais, não presuma resultado.

Benchmark Redis: apaga apenas a chave específica de defesas globais do cache, registra o primeiro MISS e mede as chamadas seguintes, incluindo p95. O teste concorrente envia cinco gravações do mesmo código simultaneamente e espera uma confirmação e quatro conflitos (201 + 4x409), preservando a integridade.

SQLs de demonstração: `database/05_demo_queries.sql`. As credenciais de conexão são transmitidas pelas variáveis padrão do PostgreSQL (`PGHOST`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`). A variável opcional `DATABASE_URL` também é aceita fora do Compose.

## Organização

- `app.py`: controllers HTTP e integração das funcionalidades;
- `services.py`: regras puras de validação, rankings e agrupamentos;
- `database/repository.py`: consultas SQL parametrizadas e gravação transacional;
- `database/cache.py`: Redis, cache e invalidação;
- `database/01_schema.sql` até `04_functions_triggers.sql`: schema/índices/views/função/triggers;
- `database/seed.py`: importador idempotente de guildas, membros, personagens e combates;
- `scripts/benchmark.py`, `scripts/concorrencia.py`: medições e teste de concorrência;
- `scripts/carga.py`: gerador de carga HTTP com clientes simultâneos, throughput e latência p50/p95;
- `docs/modelo_relacional.png` e `docs/modelo_redis.png`: diagramas atualizados e arquivos .dot editáveis;
- `tests/`: testes unitários e smoke test;
- `templates/`, `static/`: frontend original preservado.

## Escopo e limites

**Os 100.000 registros foram propositalmente excluídos**. O backup inicial contém 1.969 batalhas, 2 guildas e 34 membros cadastrados nas guildas. As páginas do calendário e os códigos promocionais continuam sendo dados locais no JavaScript: não são entidades do domínio transacional escolhido. As consultas de ranking e recomendação foram preservadas (agregação Python sobre dados SQL); Redis reduz recomputação em acessos repetidos. Como o ambiente de criação deste pacote não dispõe de Docker e dos serviços PostgreSQL/Redis, a inicialização integrada, os tempos de execução e os testes de concorrência **precisam ser executados no ambiente com Docker antes da entrega acadêmica**. Não são informadas latências inventadas.
