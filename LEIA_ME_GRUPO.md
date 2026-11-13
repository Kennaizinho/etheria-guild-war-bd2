# Etheria Guild War — projeto para compartilhar com a equipe

Esta é uma cópia do projeto de Banco de Dados II **sem a configuração de hospedagem no Discloud** (`discloud.config`).

- Os códigos do frontend, Flask, serviços, PostgreSQL e Redis foram mantidos.
- Os scripts SQL, testes, dados originais, Dockerfile e docker-compose.yml foram mantidos para atender às exigências da disciplina.
- `requirements.txt` foi mantido porque é uma **lista de dependências Python**, não uma pasta de bibliotecas instaladas. É necessário para preparar o ambiente (inclusive o Docker).
- O `gunicorn` permanece listado em requirements.txt porque também é utilizado pelo Dockerfile; não é exclusivo do Discloud.
- Nenhuma pasta `venv`, `.venv`, `__pycache__` ou bibliotecas instaladas está incluída.

**Como executar localmente (com Docker):**

1. Instale o Docker Desktop.
2. Copie `.env.example` para `.env` e edite as senhas e a chave de escrita.
3. Execute `docker compose up --build -d` na pasta do projeto.
4. Acesse `http://localhost:8080`.

Veja `README.md` para os demais comandos, os endpoints e os testes. A inicialização integrada ainda deve ser validada na máquina da equipe.
