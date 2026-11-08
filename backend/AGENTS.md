# backend/AGENTS.md — API e gestão hospitalar (dono: Erik)

Stack: Python 3.11+, FastAPI, SQLModel (SQLite no começo), PyJWT, pytest, httpx.

## Comandos

```bash
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q
uvicorn app.main:app --reload
```

## Padrões

Padrões de código (SOLID, Factory, Strategy, Observer, Adapter, injeção): [`docs/padroes-de-projeto.md`](../docs/padroes-de-projeto.md). Aqui valem, em especial:

- **Dependências pelo construtor (DIP):** o comando recebe `session`, `user`, `payload` e, opcionalmente, a política de prioridade e o criador de movimentação. Nada de criar `Session` dentro do comando.
- **Strategy:** `app/priority.py` (`PriorityPolicy`, `policy_for`) define ranking e se exige aprovação. Não compare `Priority.critica` fora dele.
- **Factory Method:** `app/movements.py` (`MovementCreator`) é o único lugar que muda `quantity` ou `reserved`. Tipo novo de movimentação = classe nova.
- **Observer:** eventos de entrega e de estoque baixo entram na semana 2.

- **Command:** cada ação do domínio (criar, cancelar, aprovar entrega) é uma classe em `app/commands/` com método `execute()`. Os routers só validam a entrada, chamam o comando e traduzem exceções do domínio em HTTP.
- **Estoque só por `Movimentacao`** (`RESERVA`, `BAIXA`, `CREDITO`, `ESTORNO`). `quantity` do movimento é sempre positiva; o tipo diz a direção.
- **Prioridade:** `critica` < `media` < `rotina`; dentro da mesma prioridade, FIFO por `id`.
- **JWT:** somente HS256; exigir `exp`, `sub`, `role`, `jti`. Segredo em `GERALDO_JWT_SECRET`.
- Mensagens de erro em português, no formato "o que houve + o que fazer".

## O que não tocar

`docs/contracts/` (mudança só por PR com aviso ao Samuel). Respostas da API devem bater com `docs/contracts/openapi.yaml`; o teste de contrato do Pedro (`backend/tests/test_contract.py`) falha se não baterem.

## Variáveis de ambiente

`GERALDO_DATABASE_URL`, `GERALDO_JWT_SECRET`, `GERALDO_JWT_MINUTES`, `GERALDO_DEMO_PASSWORD` (senha dos usuários de demonstração), `GERALDO_AUTO_SEED`.
