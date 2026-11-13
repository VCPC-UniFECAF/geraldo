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
- **Observer:** `app/events.py` (`Subject`, `AuditLog`, `LowStockAlert`) avisa cada mudança de entrega, de saldo e da emergência; `app/telemetry.py` (`TelemetryHub`) alimenta o WebSocket `/ws/telemetry`, que recebe o token em `?token=<JWT>` (o navegador não manda cabeçalho no WebSocket).
- **Fluxo do estoque:** criar entrega faz `RESERVA` na origem; confirmar o recebimento faz `BAIXA` na origem e `CREDITO` no destino; cancelar ou falhar faz `ESTORNO`. Só `app/movements.py` mexe no saldo.
- **Trava do estoque:** `app/stock_lock.py` (`stock_lock`, `serialized`) serializa os comandos que mexem em saldo ou na fila (um Lock por processo, injetado pelo construtor). Vale para **um só worker**; com vários, use `UPDATE` condicional no banco. Os criadores de `app/movements.py` também recusam saldo ou reservado negativo.
- **Hora injetada:** `app/clock.py` (`Clock`, `OffPeakWindow`); a `rotina` só sai da fila das 20h às 6h (veja `GERALDO_OFF_PEAK_HOURS`).

- **Command:** cada ação do domínio (criar, cancelar, aprovar entrega) é uma classe em `app/commands/` com método `execute()`. Os routers só validam a entrada, chamam o comando e traduzem exceções do domínio em HTTP.
- **Estoque só por `Movimentacao`** (`RESERVA`, `BAIXA`, `CREDITO`, `ESTORNO`). `quantity` do movimento é sempre positiva; o tipo diz a direção.
- **Prioridade:** `critica` < `media` < `rotina`; dentro da mesma prioridade, FIFO por `id`.
- **JWT:** somente HS256; exigir `exp`, `sub`, `role`, `jti`. Segredo em `GERALDO_JWT_SECRET`.
- Mensagens de erro em português, no formato "o que houve + o que fazer".

## O que não tocar

`docs/contracts/` (mudança só por PR com aviso ao Samuel). Respostas da API devem bater com `docs/contracts/openapi.yaml`; o teste de contrato do Pedro (`backend/tests/test_contract.py`) falha se não baterem.

## Variáveis de ambiente

`GERALDO_DATABASE_URL`, `GERALDO_JWT_SECRET` (mínimo de 32 caracteres), `GERALDO_JWT_MINUTES`, `GERALDO_DEMO_PASSWORD` (senha dos usuários de demonstração), `GERALDO_ROBOT_PASSWORD` (senha do usuário `robo`; sem ela vale a `GERALDO_DEMO_PASSWORD`), `GERALDO_AUTO_SEED`, `GERALDO_CORS_ORIGINS` (origens do navegador, separadas por vírgula; padrão: o Vite em `localhost:5173` e `4173`) e `GERALDO_OFF_PEAK_HOURS` (janela de baixo pico da rotina, `inicio-fim` em horas; padrão `20-6`; `0-24` libera o dia todo na demonstração).

Em desenvolvimento, fixe `GERALDO_JWT_SECRET`: sem ele cada `uvicorn --reload` gera um segredo novo e invalida os tokens (o robô de mentira faz login de novo sozinho, mas o painel pede login). Sem `GERALDO_DEMO_PASSWORD` o seed usa uma senha pública e o servidor avisa no startup (`WARNING`); nunca exponha assim. O log de acesso do uvicorn mascara o `?token=` do WebSocket; um proxy reverso na frente precisa mascarar a query também. A seed tem dois farmacêuticos (`farmaceutico1` e `farmaceutico2`) para a assinatura dupla.
