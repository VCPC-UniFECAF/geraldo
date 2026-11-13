# Semana 3 (2/4): backend completo, robô de mentira e teste de contrato — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Um backend FastAPI completo (login, estoque por `Movimentacao`, entregas com assinatura dupla, cancelar, confirmar recebimento, endpoints do robô, telemetria em HTTP e WebSocket, emergência pelo painel), mais o robô de mentira e o teste de contrato que o provam contra `docs/contracts/openapi.yaml`.

**Architecture:** As tarefas 1 a 5 executam, por referência, as tarefas 1 a 5 do plano do Erik da semana 1 (código completo lá). Depois, cada ação do domínio é um Command em `app/commands/` (DIP pelo construtor), a prioridade é Strategy (`app/priority.py`), a movimentação de estoque é Factory Method (`app/movements.py`), os avisos são Observer (`app/events.py`, `app/telemetry.py`) e a hora entra injetada (`app/clock.py`). Os routers só validam a entrada, chamam o comando e traduzem as exceções do domínio em HTTP.

**Tech Stack:** Python 3.11+ (3.12 na máquina), FastAPI, SQLModel (SQLite), PyJWT (HS256), pytest, httpx, PyYAML, jsonschema, uvicorn.

**Spec:** `docs/superpowers/specs/2026-11-13-semana3-completa-design.md` (seções 3, 4, 5 e 6). Base: `docs/superpowers/plans/2026-11-05-semana1-erik-backend.md` (tarefas 1 a 5) e `docs/superpowers/plans/2026-11-05-semana1-pedro-qualidade.md` (tarefas 2 e 3). Contratos: `docs/contracts/openapi.yaml`, `docs/contracts/jwt.md`, `docs/contracts/robot-protocol.md`.

**Branch:** `feat/semana3-backend`, criada a partir de `feat/semana3-robo` (o plano 1 já pôs `POST /robot/estop`, `GET /robot/estop` e o schema `EstopState` no `docs/contracts/openapi.yaml`). Nada de `git push` nem PR sem o líder.

## Global Constraints

- **AGENTS.md:** contrato primeiro; nenhum segredo no repositório; nada direto na `main`; todo código novo com teste; texto de interface em português; padrões em `docs/padroes-de-projeto.md` (injeção pelo construtor, Strategy/Factory no lugar de `if/elif` por tipo, funções puras).
- **Commits:** em português, `tipo: o que mudou`, terminando com `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`. Descrições de PR terminam com `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
- **ROS e Gazebo:** todo comando de simulação com `ROS_DOMAIN_ID=77` e `GZ_PARTITION=verif` (outra sessão pode estar rodando; não a toque). Nunca `pkill -f` nem `pgrep -f` (derrubam o próprio shell): usar PID. `gz sim` e o dispatcher exigem `kill -9`.
- **Git:** nunca `git stash` solto; caminhos absolutos do worktree; nada de `push` nem de PR sem o líder.
- **Design system (web e app):** sem hex solto; vermelho só para prioridade crítica, perigo, parada de emergência, estoque abaixo do mínimo e erro; um botão primário por tela; alvo de toque mínimo de 44 px; números com `tabular-nums`; ícones `lucide-react`; texto em português, *sentence case*.
- **Backend:** JWT só HS256, exigindo `exp`, `sub`, `role` e `jti`; segredo em `GERALDO_JWT_SECRET`; estoque só por `Movimentacao`; prioridade `critica` < `media` < `rotina`, FIFO por `id`; mensagens de erro em português no formato "o que houve + o que fazer".
- **Versões:** Python 3.12 (3.11+ no backend), ROS 2 Jazzy, Gazebo Harmonic 8, Node 24, React 19, Vite 8, Tailwind v3, Electron (última estável de pelo menos 2 semanas).

## Convenções deste plano

- Raiz da worktree: `/home/samuel/projects/fecaf/geraldo/.claude/worktrees/semana3` (os caminhos do plano são relativos a ela). Comandos do backend rodam em `backend/` com o venv ativo: `cd /home/samuel/projects/fecaf/geraldo/.claude/worktrees/semana3/backend && . .venv/bin/activate`.
- Commits: um por tarefa, só com os arquivos da tarefa (`git add <arquivos>`, nunca `git add -A`), no formato `git commit -m "<mensagem>" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"`.
- A contagem de testes (`N passed`) de cada tarefa é a do `python -m pytest -q` inteiro em `backend/` depois dela. O aviso `StarletteDeprecationWarning` sobre `httpx` é esperado e inofensivo.
- Arquivos "Replace" são substituídos **inteiros** pelo conteúdo mostrado.
- Nada de segredo no repositório: senhas de demonstração são valores claramente falsos e vêm do ambiente (`GERALDO_DEMO_PASSWORD`; o usuário `robo` usa `GERALDO_ROBOT_PASSWORD` e, se ela não existir, a mesma senha de demonstração).

## Decisões de domínio (valem para as tarefas 6 a 21)

| Ação | Quem | Status | Movimentação de estoque |
|---|---|---|---|
| `POST /deliveries` | medico, enfermeiro, farmaceutico, admin | nasce `NA_FILA` (crítica: `PENDENTE_APROVACAO`) | `RESERVA` na origem |
| `POST /deliveries/{id}/approve` | só farmaceutico, e **não** quem pediu | `PENDENTE_APROVACAO` → `NA_FILA` | — |
| `POST /robot/next-task` | robo | `NA_FILA` → `EM_ROTA`; `rotina` só em baixo pico | — |
| `POST /robot/events` `LOADED` | robo | segue `EM_ROTA` | — |
| `POST /robot/events` `ARRIVED` | robo | `EM_ROTA` → `AGUARDANDO_RECEBIMENTO` | — |
| `POST /deliveries/{id}/confirm-receipt` | quem pediu ou admin | `AGUARDANDO_RECEBIMENTO` → `ENTREGUE` | `BAIXA` na origem e `CREDITO` no destino |
| `POST /robot/events` `UNLOCKED` | robo | só depois do `ENTREGUE`; não muda nada (antes disso, 409) | — |
| `POST /deliveries/{id}/cancel` | quem pediu ou admin | de `PENDENTE_APROVACAO`, `NA_FILA`, `EM_ROTA` ou `AGUARDANDO_RECEBIMENTO` → `CANCELADA` | `ESTORNO` na origem |
| `POST /robot/events` `FAILED` | robo | de `EM_ROTA` ou `AGUARDANDO_RECEBIMENTO` → `FALHOU` | `ESTORNO` na origem |

- Evento do robô que não cabe no status atual responde `409` (o robô só registra no log e segue; ver `robot-protocol.md`, seção 3).
- Baixo pico da `rotina`: das 20h às 6h, hora local do servidor. Configurável por `GERALDO_OFF_PEAK_HOURS` (`inicio-fim`, em horas; `0-24` libera o dia todo, útil na demonstração). Os testes rodam sempre "em baixo pico".
- WebSocket `ws://127.0.0.1:8000/ws/telemetry?token=<JWT>`: o navegador não manda cabeçalho no WebSocket, então o token vai na query (clientes de linha de comando podem usar `Authorization: Bearer`). Token ausente ou inválido: a conexão é recusada (código 1008). Ao conectar, o cliente já recebe o último estado.
- `GET /telemetry` antes da primeira telemetria devolve robô `IDLE`, pose 0, bateria 0, listas vazias e `updated_at` em `1970-01-01T00:00:00Z` (o painel lê isso como "sem sinal").
- `POST /robot/telemetry` aceita e ignora o `updated_at` do robô; `route` tem no máximo 50 pontos e `obstacles` no máximo 20 itens `{x, y, radius}` em metros.
- `GET /me`, `GET /locations` e `GET /stock` já nascem nas tarefas 3 e 4 (plano do Erik) e são conferidos contra o contrato na Tarefa 19.

## Mapa de arquivos

| Arquivo | Responsabilidade | Tarefa |
|---|---|---|
| `backend/app/movements.py` | `MovementCreator` e as 4 movimentações (Factory Method) | 4, 6 |
| `backend/app/events.py` | Observer: `Subject`, eventos, `AuditLog`, `LowStockAlert` | 7 |
| `backend/app/commands/errors.py`, `common.py` | erros de domínio com status HTTP; visibilidade e estorno compartilhados | 8 |
| `backend/app/commands/cancel_delivery.py`, `approve_delivery.py`, `confirm_receipt.py` | Commands de entrega | 8, 9, 12 |
| `backend/app/clock.py`, `commands/next_task.py` | relógio injetado, janela de baixo pico, próxima tarefa do robô | 10 |
| `backend/app/commands/robot_event.py` | transições dos eventos do robô | 11 |
| `backend/app/routers/delivery_actions.py`, `robot.py`, `movements.py`, `telemetry.py`, `estop.py` | HTTP das ações novas | 8 a 15 |
| `backend/app/telemetry.py`, `estop.py` | último estado do robô (Observer para o WebSocket) e emergência | 14, 15 |
| `backend/app/errors.py` | erros de validação em português | 16 |
| `backend/tests/test_contract.py` | contrato de cada resposta | 19 |
| `tools/mock_robot.py` | robô de mentira | 20 |
| `backend/e2e_smoke.sh` | ponta a ponta com o servidor de verdade | 21 |

---

### Task 1: Projeto FastAPI e health check (plano do Erik)

Execute a Task 1 de `/home/samuel/projects/fecaf/geraldo/.claude/worktrees/semana3/docs/superpowers/plans/2026-11-05-semana1-erik-backend.md` (linhas 27 a 115) exatamente como está.

**Files:**
- Create: `backend/requirements.txt`, `backend/pytest.ini`, `backend/app/__init__.py`, `backend/app/main.py`
- Test: `backend/tests/__init__.py`, `backend/tests/test_health.py`

**Interfaces:**
- Produces: `app.main.app` e `GET /health` (fora do contrato).

- [ ] **Step 1: Branch.** `git switch feat/semana3-robo && git switch -c feat/semana3-backend` (se a branch do plano 1 ainda não existir, pare e avise o líder).
- [ ] **Step 2: Executar** os passos 1 a 6 da Task 1 do plano do Erik. `backend/.venv` já é ignorado pelo `.gitignore`.
- [ ] **Step 3: Conferir.** Comando: `cd backend && python -m pytest -q`. Resultado esperado: `1 passed`.

**Correções para ficar coerente com o contrato atual:** nenhuma. Só o commit muda: use a mensagem do plano do Erik com o trailer `Co-Authored-By` (ver Convenções).

---

### Task 2: Configuração, modelos, banco, hash de senha e seed (plano do Erik)

Execute a Task 2 de `/home/samuel/projects/fecaf/geraldo/.claude/worktrees/semana3/docs/superpowers/plans/2026-11-05-semana1-erik-backend.md` (linhas 118 a 555) exatamente como está.

**Files:**
- Create: `backend/app/config.py`, `backend/app/models.py`, `backend/app/db.py`, `backend/app/security.py`, `backend/app/seed.py`, `backend/seeds/itens.json`, `backend/seeds/estoque.json`
- Create (fixtures): `backend/tests/fixtures/seeds/locais.json`, `backend/tests/fixtures/seeds/itens.json`, `backend/tests/fixtures/seeds/estoque.json`
- Test: `backend/tests/conftest.py`, `backend/tests/test_seed.py`, `backend/tests/test_password.py`

**Interfaces:**
- Produces: `app.config.settings`; enums `Role`, `Priority`, `DeliveryStatus`, `MovementType`; tabelas `User`, `Location`, `Item`, `Stock`, `Delivery`, `DeliveryItem`, `Movement`; `make_engine`, `create_db`, `get_session`; `hash_password`, `verify_password`; `seed(session, seeds_dir=SEEDS)` e `DEMO_USERS` (inclui o usuário `robo`).

- [ ] **Step 1: Executar** os passos 1 a 6 da Task 2 do plano do Erik.
- [ ] **Step 2: Conferir.** Comando: `cd backend && python -m pytest -q`. Resultado esperado: `7 passed`.

**Correções para ficar coerente com o contrato atual:**
- `backend/seeds/locais.json` **já existe** no repositório (gerado pelo robô, com os 11 locais e os `waypoint`); não o recrie nem o altere. Só crie `itens.json` e `estoque.json`.
- Os valores de demonstração (senha `demo-only-change-me` por padrão, saldos) são falsos de propósito; a senha real de demonstração vem de `GERALDO_DEMO_PASSWORD`. A senha do usuário `robo` ganha variável própria na Tarefa 18.

---

### Task 3: Login, JWT e papéis (plano do Erik)

Execute a Task 3 de `/home/samuel/projects/fecaf/geraldo/.claude/worktrees/semana3/docs/superpowers/plans/2026-11-05-semana1-erik-backend.md` (linhas 558 a 952) exatamente como está.

**Files:**
- Create: `backend/app/schemas.py`, `backend/app/deps.py`, `backend/app/routers/__init__.py`, `backend/app/routers/auth.py`
- Modify: `backend/app/security.py`, `backend/app/main.py`, `backend/tests/conftest.py`
- Test: `backend/tests/test_auth.py`

**Interfaces:**
- Produces: `create_token(user) -> str`, `decode_token(token) -> dict` (HS256, exige `exp`, `sub`, `role`, `jti`); `get_current_user`, `require_roles(*roles)`; `POST /auth/login`, `GET /me`; fixtures `client` e `auth(username)`.

- [ ] **Step 1: Executar** os passos 1 a 6 da Task 3 do plano do Erik.
- [ ] **Step 2: Conferir.** Comando: `cd backend && python -m pytest -q`. Resultado esperado: `16 passed`.

**Correções para ficar coerente com o contrato atual:** nenhuma (`/auth/login` e `/me` batem com o `openapi.yaml`; o `Error` do contrato tem `detail` em texto). Os limites de tamanho dos campos e o formato do erro `422` chegam na Tarefa 16.

---

### Task 4: Locais, estoque e criação de entrega com reserva (plano do Erik, com uma correção)

Execute a Task 4 de `/home/samuel/projects/fecaf/geraldo/.claude/worktrees/semana3/docs/superpowers/plans/2026-11-05-semana1-erik-backend.md` (linhas 955 a 1536) exatamente como está, **e depois aplique a correção abaixo** (o contrato vence).

**Files:**
- Create: `backend/app/priority.py`, `backend/app/movements.py`, `backend/app/queries.py`, `backend/app/commands/__init__.py`, `backend/app/commands/create_delivery.py`, `backend/app/routers/catalog.py`, `backend/app/routers/deliveries.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_catalog.py`, `backend/tests/test_deliveries.py`, `backend/tests/test_priority.py`, `backend/tests/test_movements.py`, `backend/tests/test_create_delivery_command.py`

**Interfaces:**
- Produces: `PriorityPolicy` e `policy_for(priority)`; `MovementCreator` e `ReservaCreator`; `CreateDelivery(session, user, payload, *, policy_for=policy_for, reserva=None).execute() -> Delivery`; exceções `DeliveryError` (com `.status_code`), `UnknownLocation`, `UnknownItem`, `SameLocation`, `InsufficientStock`; `delivery_out(session, delivery) -> DeliveryOut`; `GET /locations`, `GET /stock`, `POST /deliveries`, `GET /deliveries`, `GET /deliveries/{id}`.

- [ ] **Step 1: Executar** os passos 1 a 6 da Task 4 do plano do Erik (resultado do passo 5 lá: `38 passed`).
- [ ] **Step 2: Correção do contrato, teste primeiro.** O `openapi.yaml` atual diz que o papel `robo` também consulta `GET /deliveries/{id}` (somente leitura; `docs/contracts/robot-protocol.md`, seção 7, item 1), mas o plano do Erik devolve `404` para ele, e toda entrega terminaria em `FAILED` depois de 5 minutos. Acrescente ao fim de `backend/tests/test_deliveries.py`:

```python
def test_the_robot_can_read_any_delivery_but_does_not_list_them(client, auth):
    delivery_id = client.post("/deliveries", json=payload(), headers=auth("medico1")).json()["id"]
    assert client.get(f"/deliveries/{delivery_id}", headers=auth("robo")).status_code == 200
    assert client.get("/deliveries", headers=auth("robo")).json() == []
```

- [ ] **Step 3: Rodar e ver falhar.** Comando: `cd backend && python -m pytest tests/test_deliveries.py -q`. Resultado esperado: 1 failed (`assert 404 == 200`).
- [ ] **Step 4: Corrigir `backend/app/routers/deliveries.py`.** Logo abaixo de `SEE_ALL = (Role.admin, Role.farmaceutico)` acrescente a linha:

```python
READ_ONE = (*SEE_ALL, Role.robo)  # o robô só consulta uma entrega, para esperar o ENTREGUE (robot-protocol.md, seção 7)
```

E em `get_delivery`, troque `user.role not in SEE_ALL` por `user.role not in READ_ONE`, ficando:

```python
    if delivery is None or (user.role not in READ_ONE and delivery.requested_by != user.id):
```

(`GET /deliveries`, a lista, continua com `SEE_ALL`.)

- [ ] **Step 5: Rodar e ver passar.** Comando: `cd backend && python -m pytest -q`. Resultado esperado: `39 passed`.
- [ ] **Step 6: Commit** (com o trailer): `git add backend && git commit -m "feat(backend): locais, estoque e criacao de entrega com reserva (Command)" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"`.

---

### Task 5: Fila de prioridade e `/robot/next-task` (plano do Erik)

Execute a Task 5 de `/home/samuel/projects/fecaf/geraldo/.claude/worktrees/semana3/docs/superpowers/plans/2026-11-05-semana1-erik-backend.md` (linhas 1539 a 1677) exatamente como está, **exceto o passo 6** (sem `git push` e sem abrir PR; só o commit).

**Files:**
- Create: `backend/app/routers/robot.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_robot_queue.py`

**Interfaces:**
- Consumes: `require_roles`, `delivery_out`, `policy_for`, modelos (Tarefas 2 a 4).
- Produces: `POST /robot/next-task` (papel `robo`): `200` com `RobotTask` (entrega + `origin_waypoint` e `dest_waypoint`, e a entrega vira `EM_ROTA`) ou `204` se a fila estiver vazia; ordem `critica` < `media` < `rotina`, depois `id`.

- [ ] **Step 1: Executar** os passos 1 a 5 da Task 5 do plano do Erik. O passo 5 (conferir à mão com `uvicorn`) é opcional aqui, pois a Tarefa 21 sobe o servidor de verdade; se o fizer, guarde o PID e encerre com `kill -9 <PID>`.
- [ ] **Step 2: Conferir.** Comando: `cd backend && python -m pytest -q`. Resultado esperado: `44 passed` (os 43 do plano do Erik mais o teste da correção da Tarefa 4).
- [ ] **Step 3: Commit** (com o trailer): `git add backend && git commit -m "feat(backend): fila de prioridade e /robot/next-task" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"`.

**Correções para ficar coerente com o contrato atual:** o `next-task` do plano do Erik escolhe a entrega sem olhar a hora e devolve `409` se faltar `waypoint`, que o contrato não prevê; a Tarefa 10 troca esse trecho por um Command com relógio injetado (rotina só em baixo pico; entregas sem `waypoint` são ignoradas). O contrato do `next-task` (`200`, `204`, `401`, `403`) já é respeitado.

---

### Task 6: Movimentações completas (Factory Method)

**Files:**
- Modify: `backend/app/movements.py`
- Test: `backend/tests/test_movements.py`

**Interfaces:**
- Consumes: `MovementCreator`, `ReservaCreator`, `Stock`, `Movement`, `MovementType` (Tarefas 2 e 4).
- Produces: `BaixaCreator` (consome reserva e saldo), `CreditoCreator` (soma ao saldo), `EstornoCreator` (desfaz a reserva), todos com `register(stock, *, delivery_id: int | None, quantity: int) -> Movement`; `creator_for(type: MovementType) -> MovementCreator`. `BaixaCreator` e `EstornoCreator` levantam `ValueError` se a reserva for menor que a quantidade. Só `MovementCreator` muda `quantity` e `reserved`.

- [ ] **Step 1: Substituir o teste.** Replace `backend/tests/test_movements.py`:

```python
import pytest

from app.models import MovementType, Stock
from app.movements import BaixaCreator, CreditoCreator, EstornoCreator, ReservaCreator, creator_for


def make_stock(quantity: int = 10, reserved: int = 1) -> Stock:
    return Stock(location_id="farmacia", item_id="dipirona-500mg", quantity=quantity, reserved=reserved)


def test_reserva_raises_reserved_and_returns_the_record():
    stock = make_stock()
    movement = ReservaCreator().register(stock, delivery_id=7, quantity=3)
    assert (stock.quantity, stock.reserved) == (10, 4)
    assert (movement.type, movement.item_id, movement.location_id, movement.quantity, movement.delivery_id) == (
        MovementType.RESERVA,
        "dipirona-500mg",
        "farmacia",
        3,
        7,
    )


def test_baixa_consumes_the_reservation_and_the_balance():
    stock = make_stock(quantity=10, reserved=4)
    movement = BaixaCreator().register(stock, delivery_id=7, quantity=3)
    assert (stock.quantity, stock.reserved) == (7, 1)
    assert movement.type == MovementType.BAIXA and movement.quantity == 3


def test_credito_adds_to_the_balance_only():
    stock = make_stock(quantity=2, reserved=0)
    movement = CreditoCreator().register(stock, delivery_id=7, quantity=3)
    assert (stock.quantity, stock.reserved) == (5, 0)
    assert movement.type == MovementType.CREDITO


def test_estorno_releases_the_reservation_and_keeps_the_balance():
    stock = make_stock(quantity=10, reserved=4)
    movement = EstornoCreator().register(stock, delivery_id=7, quantity=4)
    assert (stock.quantity, stock.reserved) == (10, 0)
    assert movement.type == MovementType.ESTORNO


@pytest.mark.parametrize("creator", [BaixaCreator(), EstornoCreator()])
def test_cannot_release_more_than_what_is_reserved(creator):
    stock = make_stock(quantity=10, reserved=1)
    with pytest.raises(ValueError, match="reservado"):
        creator.register(stock, delivery_id=7, quantity=2)
    assert (stock.quantity, stock.reserved) == (10, 1)


@pytest.mark.parametrize("creator", [ReservaCreator(), BaixaCreator(), CreditoCreator(), EstornoCreator()])
@pytest.mark.parametrize("quantity", [0, -2])
def test_quantity_must_be_positive_and_stock_stays_untouched(creator, quantity):
    stock = make_stock()
    with pytest.raises(ValueError):
        creator.register(stock, delivery_id=1, quantity=quantity)
    assert (stock.quantity, stock.reserved) == (10, 1)


def test_creator_for_returns_one_creator_per_type():
    for type in MovementType:
        assert creator_for(type).type == type
```

- [ ] **Step 2: Rodar e ver falhar.** Comando: `cd backend && python -m pytest tests/test_movements.py -q`. Resultado esperado: erro de coleta `ImportError: cannot import name 'BaixaCreator' from 'app.movements'`.

- [ ] **Step 3: Implementar.** Replace `backend/app/movements.py`:

```python
from abc import ABC, abstractmethod

from app.models import Movement, MovementType, Stock


class MovementCreator(ABC):  # FACTORY METHOD + TEMPLATE METHOD: o único lugar que muda o saldo
    @property
    @abstractmethod
    def type(self) -> MovementType: ...

    @abstractmethod
    def apply(self, stock: Stock, quantity: int) -> None:
        """Efeito deste tipo de movimentação no saldo."""

    def register(self, stock: Stock, *, delivery_id: int | None, quantity: int) -> Movement:
        if quantity <= 0:
            raise ValueError("A quantidade da movimentação deve ser positiva.")
        self.apply(stock, quantity)
        return Movement(
            delivery_id=delivery_id,
            type=self.type,
            item_id=stock.item_id,
            location_id=stock.location_id,
            quantity=quantity,
        )


def _must_have_reserved(stock: Stock, quantity: int) -> None:
    if stock.reserved < quantity:
        raise ValueError(
            f"Só há {stock.reserved} reservado de {stock.item_id} em {stock.location_id}; não dá para liberar {quantity}. "
            "Confira as movimentações da entrega."
        )


class ReservaCreator(MovementCreator):
    """Separa a quantidade para uma entrega: o saldo continua, o disponível diminui."""

    type = MovementType.RESERVA

    def apply(self, stock: Stock, quantity: int) -> None:
        stock.reserved += quantity


class BaixaCreator(MovementCreator):
    """A mercadoria saiu da origem: consome a reserva e o saldo."""

    type = MovementType.BAIXA

    def apply(self, stock: Stock, quantity: int) -> None:
        _must_have_reserved(stock, quantity)
        stock.reserved -= quantity
        stock.quantity -= quantity


class CreditoCreator(MovementCreator):
    """A mercadoria chegou ao destino: soma ao saldo."""

    type = MovementType.CREDITO

    def apply(self, stock: Stock, quantity: int) -> None:
        stock.quantity += quantity


class EstornoCreator(MovementCreator):
    """Desfaz a reserva (entrega cancelada ou que falhou): o saldo não muda."""

    type = MovementType.ESTORNO

    def apply(self, stock: Stock, quantity: int) -> None:
        _must_have_reserved(stock, quantity)
        stock.reserved -= quantity


_CREATORS = {creator.type: creator for creator in (ReservaCreator(), BaixaCreator(), CreditoCreator(), EstornoCreator())}


def creator_for(type: MovementType) -> MovementCreator:  # FACTORY: tipo novo = classe nova + uma linha acima
    return _CREATORS[type]
```

- [ ] **Step 4: Rodar e ver passar.** Comando: `cd backend && python -m pytest -q`. Resultado esperado: `56 passed`.

- [ ] **Step 5: Commit.**

```bash
git add backend/app/movements.py backend/tests/test_movements.py
git commit -m "feat(backend): BaixaCreator, CreditoCreator e EstornoCreator (Factory Method)" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Observer de eventos (entrega, estoque baixo, emergência)

**Files:**
- Create: `backend/app/events.py`
- Modify: `backend/app/commands/create_delivery.py`, `backend/app/routers/deliveries.py`, `backend/app/main.py`
- Test: `backend/tests/test_events.py`

**Interfaces:**
- Consumes: `CreateDelivery`, `DeliveryStatus` (Tarefas 2 e 4).
- Produces (em `app.events`): `DeliveryChanged(delivery_id: int, old_status: DeliveryStatus | None, new_status: DeliveryStatus, actor: str)`; `StockChanged(location_id: str, item_id: str, quantity: int, reserved: int, minimum: int)`; `EstopChanged(active: bool, actor: str)`; `Subject` (`add_observer(observer)`, `remove_observer(observer)`, `notify(event)`; o observador tem `update(event)`); `AuditLog` e `LowStockAlert` (`.alerts: list[str]`, alerta quando `quantity < minimum`); o singleton `events` e `get_events() -> Subject` (dependência FastAPI). `CreateDelivery(..., events: Subject | None = None)` passa a avisar `DeliveryChanged` (com `old_status=None`) e um `StockChanged` por item reservado, depois do commit.

- [ ] **Step 1: Escrever o teste.** Create `backend/tests/test_events.py`:

```python
from sqlmodel import select

from app.commands.create_delivery import CreateDelivery
from app.events import AuditLog, DeliveryChanged, EstopChanged, LowStockAlert, StockChanged, Subject
from app.models import DeliveryStatus, Priority, User
from app.schemas import DeliveryCreate, DeliveryItemIn


class Spy:
    def __init__(self) -> None:
        self.events = []

    def update(self, event) -> None:
        self.events.append(event)


def test_subject_notifies_every_observer_and_stops_after_remove():
    subject, a, b = Subject(), Spy(), Spy()
    subject.add_observer(a)
    subject.add_observer(b)
    subject.notify("x")
    subject.remove_observer(b)
    subject.notify("y")
    assert a.events == ["x", "y"] and b.events == ["x"]


def test_low_stock_alert_only_fires_below_the_minimum():
    alert = LowStockAlert()
    alert.update(StockChanged("banco_sangue", "bolsa-sangue-o-neg", quantity=6, reserved=0, minimum=10))
    alert.update(StockChanged("farmacia", "dipirona-500mg", quantity=420, reserved=0, minimum=100))
    alert.update(StockChanged("farmacia", "luva-procedimento", quantity=40, reserved=0, minimum=40))
    assert len(alert.alerts) == 1
    assert "bolsa-sangue-o-neg" in alert.alerts[0] and "Reponha" in alert.alerts[0]


def test_audit_log_writes_delivery_and_estop_events(caplog):
    caplog.set_level("INFO", logger="geraldo.audit")
    log = AuditLog()
    log.update(DeliveryChanged(7, None, DeliveryStatus.NA_FILA, "medico1"))
    log.update(EstopChanged(True, "admin"))
    log.update(StockChanged("farmacia", "dipirona-500mg", 1, 0, 0))  # ignorado
    assert [r.getMessage() for r in caplog.records] == [
        "entrega 7: nova -> NA_FILA (por medico1)",
        "parada de emergência LIGADA por admin",
    ]


def test_create_delivery_notifies_the_delivery_and_the_reserved_stock(session):
    user = session.exec(select(User).where(User.username == "medico1")).one()
    spy, subject = Spy(), Subject()
    subject.add_observer(spy)
    payload = DeliveryCreate(origin_id="farmacia", items=[DeliveryItemIn(item_id="dipirona-500mg", quantity=2)], priority=Priority.media)

    delivery = CreateDelivery(session, user, payload, events=subject).execute()

    assert spy.events == [
        DeliveryChanged(delivery.id, None, DeliveryStatus.NA_FILA, "medico1"),
        StockChanged("farmacia", "dipirona-500mg", quantity=420, reserved=2, minimum=100),
    ]
```

- [ ] **Step 2: Rodar e ver falhar.** Comando: `cd backend && python -m pytest tests/test_events.py -q`. Resultado esperado: erro de coleta `ModuleNotFoundError: No module named 'app.events'`.

- [ ] **Step 3: Implementar o Observer.** Create `backend/app/events.py`:

```python
import logging
from dataclasses import dataclass

from app.models import DeliveryStatus


@dataclass(frozen=True)
class DeliveryChanged:
    """Uma entrega nasceu (old_status None) ou mudou de status."""

    delivery_id: int
    old_status: DeliveryStatus | None
    new_status: DeliveryStatus
    actor: str


@dataclass(frozen=True)
class StockChanged:
    """O saldo de um item em um local mudou (por causa de uma movimentação)."""

    location_id: str
    item_id: str
    quantity: int
    reserved: int
    minimum: int


@dataclass(frozen=True)
class EstopChanged:
    """O painel ligou ou desligou a parada de emergência."""

    active: bool
    actor: str


class Subject:  # OBSERVER (mesmos nomes da disciplina)
    def __init__(self) -> None:
        self._observers: list = []

    def add_observer(self, observer) -> None:
        self._observers.append(observer)

    def remove_observer(self, observer) -> None:
        self._observers.remove(observer)

    def notify(self, event) -> None:
        for observer in list(self._observers):
            observer.update(event)


class AuditLog:  # OBSERVER: trilha de auditoria no log do servidor
    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger or logging.getLogger("geraldo.audit")

    def update(self, event) -> None:
        if isinstance(event, DeliveryChanged):
            old = event.old_status.value if event.old_status else "nova"
            self._logger.info("entrega %s: %s -> %s (por %s)", event.delivery_id, old, event.new_status.value, event.actor)
        elif isinstance(event, EstopChanged):
            self._logger.warning("parada de emergência %s por %s", "LIGADA" if event.active else "desligada", event.actor)


class LowStockAlert:  # OBSERVER: avisa quando o saldo fica abaixo do mínimo
    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger or logging.getLogger("geraldo.stock")
        self.alerts: list[str] = []

    def update(self, event) -> None:
        if isinstance(event, StockChanged) and event.quantity < event.minimum:
            message = f"Estoque baixo: {event.item_id} em {event.location_id} tem {event.quantity} (mínimo {event.minimum}). Reponha."
            self.alerts.append(message)
            self._logger.warning(message)


# Assinante único do processo; main.py liga AuditLog e LowStockAlert nele. Os testes injetam um Subject próprio.
events = Subject()


def get_events() -> Subject:
    return events
```

- [ ] **Step 4: Fazer o comando avisar.** Replace `backend/app/commands/create_delivery.py` (a mudança sobre o plano do Erik é o parâmetro `events` e os avisos no fim de `_create`):

```python
from sqlmodel import Session

from app.events import DeliveryChanged, StockChanged, Subject
from app.models import Delivery, DeliveryItem, Item, Location, Stock, User
from app.movements import MovementCreator, ReservaCreator
from app.priority import policy_for
from app.schemas import DeliveryCreate


class DeliveryError(Exception):
    status_code = 400


class UnknownLocation(DeliveryError):
    status_code = 422


class UnknownItem(DeliveryError):
    status_code = 422


class SameLocation(DeliveryError):
    status_code = 422


class InsufficientStock(DeliveryError):
    status_code = 409


class CreateDelivery:
    """Comando CriarEntrega: valida, reserva o estoque na origem e registra a movimentação.

    As dependências entram pelo construtor (DIP): a política de prioridade e o criador de
    movimentação têm padrão real, e o teste passa um substituto.
    """

    def __init__(
        self,
        session: Session,
        user: User,
        payload: DeliveryCreate,
        *,
        policy_for=policy_for,
        reserva: MovementCreator | None = None,
        events: Subject | None = None,
    ) -> None:
        self.session = session
        self.user = user
        self.payload = payload
        self._policy_for = policy_for
        self._reserva = reserva or ReservaCreator()
        self._events = events if events is not None else Subject()

    def execute(self) -> Delivery:
        dest_id = self._destination()
        self._check_locations(dest_id)
        wanted = self._wanted_items()
        stocks = self._check_stock(wanted)
        return self._create(dest_id, wanted, stocks)

    def _destination(self) -> str:
        dest_id = self.payload.dest_id or self.user.local_id
        if dest_id is None:
            raise UnknownLocation("Informe o destino: seu usuário não tem um local padrão.")
        return dest_id

    def _check_locations(self, dest_id: str) -> None:
        for loc_id in (self.payload.origin_id, dest_id):
            location = self.session.get(Location, loc_id)
            if location is None:
                raise UnknownLocation(f"Local desconhecido: {loc_id}. Escolha um local da lista.")
            if location.waypoint is None:
                raise UnknownLocation(f"O local {location.name} não recebe entregas do robô. Escolha outro.")
        if self.payload.origin_id == dest_id:
            raise SameLocation("Origem e destino são o mesmo local. Escolha destinos diferentes.")

    def _wanted_items(self) -> dict[str, int]:
        wanted: dict[str, int] = {}
        for line in self.payload.items:
            wanted[line.item_id] = wanted.get(line.item_id, 0) + line.quantity
        return wanted

    def _check_stock(self, wanted: dict[str, int]) -> dict[str, Stock]:
        origin_id = self.payload.origin_id
        stocks: dict[str, Stock] = {}
        for item_id, qty in wanted.items():
            if self.session.get(Item, item_id) is None:
                raise UnknownItem(f"Item desconhecido: {item_id}. Escolha um item da lista.")
            stock = self.session.get(Stock, (origin_id, item_id))
            available = 0 if stock is None else stock.quantity - stock.reserved
            if available < qty:
                raise InsufficientStock(
                    f"Estoque insuficiente de {item_id} em {origin_id}: disponível {available}, pedido {qty}. Reduza a quantidade."
                )
            stocks[item_id] = stock
        return stocks

    def _create(self, dest_id: str, wanted: dict[str, int], stocks: dict[str, Stock]) -> Delivery:
        policy = self._policy_for(self.payload.priority)
        delivery = Delivery(
            origin_id=self.payload.origin_id,
            dest_id=dest_id,
            priority=self.payload.priority,
            status=policy.initial_status,
            requested_by=self.user.id,
        )
        self.session.add(delivery)
        self.session.flush()
        for item_id, qty in wanted.items():
            stock = stocks[item_id]
            self.session.add(DeliveryItem(delivery_id=delivery.id, item_id=item_id, quantity=qty))
            self.session.add(self._reserva.register(stock, delivery_id=delivery.id, quantity=qty))
            self.session.add(stock)
        self.session.commit()
        self.session.refresh(delivery)
        self._events.notify(DeliveryChanged(delivery.id, None, delivery.status, self.user.username))
        for stock in stocks.values():
            self._events.notify(StockChanged(stock.location_id, stock.item_id, stock.quantity, stock.reserved, stock.minimum))
        return delivery
```

- [ ] **Step 5: Passar o `Subject` no router.** Replace `backend/app/routers/deliveries.py`:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.commands.create_delivery import CreateDelivery, DeliveryError
from app.db import get_session
from app.deps import get_current_user, require_roles
from app.events import Subject, get_events
from app.models import Delivery, Role, User
from app.queries import delivery_out
from app.schemas import DeliveryCreate, DeliveryOut

router = APIRouter()
SEE_ALL = (Role.admin, Role.farmaceutico)
READ_ONE = (*SEE_ALL, Role.robo)  # o robô só consulta uma entrega, para esperar o ENTREGUE (robot-protocol.md, seção 7)


@router.post("/deliveries", response_model=DeliveryOut, status_code=201)
def create_delivery(
    body: DeliveryCreate,
    user: User = Depends(require_roles(Role.medico, Role.enfermeiro, Role.farmaceutico, Role.admin)),
    session: Session = Depends(get_session),
    events: Subject = Depends(get_events),
) -> DeliveryOut:
    try:
        delivery = CreateDelivery(session, user, body, events=events).execute()
    except DeliveryError as err:
        raise HTTPException(status_code=err.status_code, detail=str(err))
    return delivery_out(session, delivery)


@router.get("/deliveries", response_model=list[DeliveryOut])
def list_deliveries(user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    query = select(Delivery).order_by(Delivery.id)
    if user.role not in SEE_ALL:
        query = query.where(Delivery.requested_by == user.id)
    return [delivery_out(session, d) for d in session.exec(query).all()]


@router.get("/deliveries/{delivery_id}", response_model=DeliveryOut)
def get_delivery(delivery_id: int, user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    delivery = session.get(Delivery, delivery_id)
    if delivery is None or (user.role not in READ_ONE and delivery.requested_by != user.id):
        raise HTTPException(status_code=404, detail="Entrega não encontrada.")
    return delivery_out(session, delivery)
```

- [ ] **Step 6: Ligar os observadores.** Replace `backend/app/main.py`:

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlmodel import Session

from app.config import settings
from app.db import create_db, engine
from app.events import AuditLog, LowStockAlert, events
from app.routers import auth, catalog, deliveries, robot
from app.seed import seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.auto_seed:
        create_db()
        with Session(engine) as session:
            seed(session)
    yield


events.add_observer(AuditLog())
events.add_observer(LowStockAlert())

app = FastAPI(title="G.E.R.A.L.D.O. API", version="0.1.0", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(catalog.router)
app.include_router(deliveries.router)
app.include_router(robot.router)


@app.get("/health", include_in_schema=False)
def health() -> dict:
    return {"status": "ok"}
```

- [ ] **Step 7: Rodar e ver passar.** Comando: `cd backend && python -m pytest -q`. Resultado esperado: `60 passed`.

- [ ] **Step 8: Commit.**

```bash
git add backend/app/events.py backend/app/commands/create_delivery.py backend/app/routers/deliveries.py backend/app/main.py backend/tests/test_events.py
git commit -m "feat(backend): Observer de eventos de entrega, estoque baixo e emergencia" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Cancelar entrega (Command, estorno da reserva)

**Files:**
- Create: `backend/app/commands/errors.py`, `backend/app/commands/common.py`, `backend/app/commands/cancel_delivery.py`, `backend/app/routers/delivery_actions.py`
- Modify: `backend/app/main.py`, `backend/tests/conftest.py`
- Test: `backend/tests/test_cancel_delivery.py`

**Interfaces:**
- Consumes: `DeliveryError`, `EstornoCreator`, `Subject`, `DeliveryChanged`, `StockChanged`, `delivery_out`, `require_roles` (Tarefas 3, 4, 6 e 7).
- Produces:
  - `app.commands.errors`: `NotFound` (404), `NotAllowed` (403), `InvalidState` (409), todas subclasses de `DeliveryError`.
  - `app.commands.common`: `SEE_ALL = (Role.admin, Role.farmaceutico)`; `load_visible(session, user, delivery_id) -> Delivery` (404 se não existe ou se não é de quem pede e o papel não vê tudo); `delivery_lines(session, delivery) -> list[DeliveryItem]`; `release_reservation(session, delivery, estorno: MovementCreator) -> list[Stock]` (um `ESTORNO` por item, sem commit); `notify_stocks(events, stocks)`.
  - `CancelDelivery(session, user, delivery_id, *, estorno=None, events=None).execute() -> Delivery`.
  - `POST /deliveries/{delivery_id}/cancel` (papéis medico, enfermeiro, farmaceutico, admin; só quem pediu ou o admin cancela, outro papel que vê a entrega leva `403`; entrega fora de `PENDENTE_APROVACAO`, `NA_FILA`, `EM_ROTA`, `AGUARDANDO_RECEBIMENTO` leva `409`).
  - Nos testes: fixture `spy` (observador que anota os eventos do app) e a classe `SpyObserver`, em `tests/conftest.py`.

- [ ] **Step 1: Estender o `conftest.py`.** Replace `backend/tests/conftest.py` (acrescenta o import de `Subject`/`get_events`, a classe `SpyObserver` e a fixture `spy`):

```python
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.config import settings
from app.db import create_db, get_session, make_engine
from app.events import Subject, get_events
from app.main import app
from app.seed import seed

FIXTURES = Path(__file__).parent / "fixtures" / "seeds"
PASSWORD = "senha-de-teste"


@pytest.fixture(autouse=True)
def test_settings():
    names = ("jwt_secret", "jwt_minutes", "demo_password", "password_iterations", "auto_seed")
    old = {n: getattr(settings, n) for n in names}
    settings.jwt_secret = "segredo-de-teste-com-mais-de-32-bytes-0123456789"
    settings.jwt_minutes = 60
    settings.demo_password = PASSWORD
    settings.password_iterations = 1000
    settings.auto_seed = False
    yield
    for n, v in old.items():
        setattr(settings, n, v)


@pytest.fixture
def engine():
    eng = make_engine("sqlite://")
    create_db(eng)
    with Session(eng) as s:
        seed(s, FIXTURES)
    return eng


@pytest.fixture
def session(engine):
    with Session(engine) as s:
        yield s


@pytest.fixture
def client(engine):
    def override():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def auth(client):
    def login(username: str) -> dict:
        r = client.post("/auth/login", json={"username": username, "password": PASSWORD})
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    return login


class SpyObserver:
    def __init__(self) -> None:
        self.events = []

    def update(self, event) -> None:
        self.events.append(event)


@pytest.fixture
def spy(client):
    """Troca o Subject de eventos do app por um próprio e devolve o observador que anota tudo."""
    subject, observer = Subject(), SpyObserver()
    subject.add_observer(observer)
    app.dependency_overrides[get_events] = lambda: subject
    yield observer
    app.dependency_overrides.pop(get_events, None)
```

- [ ] **Step 2: Escrever o teste.** Create `backend/tests/test_cancel_delivery.py`:

```python
from sqlmodel import select

from app.commands.cancel_delivery import CancelDelivery
from app.commands.create_delivery import CreateDelivery
from app.events import DeliveryChanged, StockChanged
from app.models import DeliveryStatus, Movement, MovementType, Priority, User
from app.movements import EstornoCreator
from app.schemas import DeliveryCreate, DeliveryItemIn

BODY = {"origin_id": "farmacia", "items": [{"item_id": "dipirona-500mg", "quantity": 10}], "priority": "media"}


def create(client, auth, user="medico1", **over) -> int:
    r = client.post("/deliveries", json={**BODY, **over}, headers=auth(user))
    assert r.status_code == 201, r.text
    return r.json()["id"]


def farmacia(client, auth) -> dict:
    return client.get("/stock", params={"location_id": "farmacia"}, headers=auth("medico1")).json()[0]


def test_requester_cancels_and_the_reservation_returns_to_the_available_balance(client, auth, session, spy):
    delivery_id = create(client, auth)
    spy.events.clear()
    r = client.post(f"/deliveries/{delivery_id}/cancel", headers=auth("medico1"))
    assert r.status_code == 200 and r.json()["status"] == "CANCELADA"
    assert (farmacia(client, auth)["quantity"], farmacia(client, auth)["reserved"]) == (420, 0)
    types = [m.type for m in session.exec(select(Movement).order_by(Movement.id)).all()]
    assert types == [MovementType.RESERVA, MovementType.ESTORNO]
    assert spy.events == [
        DeliveryChanged(delivery_id, DeliveryStatus.NA_FILA, DeliveryStatus.CANCELADA, "medico1"),
        StockChanged("farmacia", "dipirona-500mg", quantity=420, reserved=0, minimum=100),
    ]


def test_admin_can_cancel_someone_elses_delivery(client, auth):
    delivery_id = create(client, auth)
    assert client.post(f"/deliveries/{delivery_id}/cancel", headers=auth("admin")).json()["status"] == "CANCELADA"


def test_a_pending_critical_delivery_can_be_cancelled(client, auth):
    body = {"origin_id": "banco_sangue", "items": [{"item_id": "bolsa-sangue-o-neg", "quantity": 2}], "priority": "critica"}
    delivery_id = client.post("/deliveries", json=body, headers=auth("medico1")).json()["id"]
    assert client.post(f"/deliveries/{delivery_id}/cancel", headers=auth("medico1")).json()["status"] == "CANCELADA"


def test_cancelling_twice_is_409_and_does_not_estorno_twice(client, auth, session):
    delivery_id = create(client, auth)
    assert client.post(f"/deliveries/{delivery_id}/cancel", headers=auth("medico1")).status_code == 200
    r = client.post(f"/deliveries/{delivery_id}/cancel", headers=auth("medico1"))
    assert r.status_code == 409 and "CANCELADA" in r.json()["detail"]
    assert farmacia(client, auth)["reserved"] == 0
    assert len(session.exec(select(Movement).where(Movement.type == MovementType.ESTORNO)).all()) == 1


def test_a_delivery_already_on_its_way_can_still_be_cancelled(client, auth):
    delivery_id = create(client, auth)
    client.post("/robot/next-task", headers=auth("robo"))
    assert client.post(f"/deliveries/{delivery_id}/cancel", headers=auth("medico1")).json()["status"] == "CANCELADA"


def test_who_can_cancel(client, auth):
    delivery_id = create(client, auth)
    url = f"/deliveries/{delivery_id}/cancel"
    assert client.post(url).status_code == 401
    assert client.post(url, headers=auth("robo")).status_code == 403
    assert client.post(url, headers=auth("medico2")).status_code == 404  # não vê a entrega dos outros
    r = client.post(url, headers=auth("farmaceutico1"))  # vê, mas não é de quem pediu nem admin
    assert r.status_code == 403 and "Peça a quem fez o pedido" in r.json()["detail"]
    assert client.post("/deliveries/9999/cancel", headers=auth("admin")).status_code == 404


class SpyEstorno(EstornoCreator):
    def __init__(self) -> None:
        self.calls = []

    def register(self, stock, *, delivery_id, quantity):
        self.calls.append((stock.item_id, quantity))
        return super().register(stock, delivery_id=delivery_id, quantity=quantity)


def test_command_uses_the_injected_estorno_creator(session):
    user = session.exec(select(User).where(User.username == "medico1")).one()
    payload = DeliveryCreate(origin_id="farmacia", items=[DeliveryItemIn(item_id="dipirona-500mg", quantity=4)], priority=Priority.media)
    delivery = CreateDelivery(session, user, payload).execute()
    spy = SpyEstorno()

    CancelDelivery(session, user, delivery.id, estorno=spy).execute()

    assert spy.calls == [("dipirona-500mg", 4)]
```

- [ ] **Step 3: Rodar e ver falhar.** Comando: `cd backend && python -m pytest tests/test_cancel_delivery.py -q`. Resultado esperado: erro de coleta `ModuleNotFoundError: No module named 'app.commands.cancel_delivery'`.

- [ ] **Step 4: Implementar os erros e o que os comandos compartilham.** Create `backend/app/commands/errors.py`:

```python
from app.commands.create_delivery import DeliveryError


class NotFound(DeliveryError):
    status_code = 404


class NotAllowed(DeliveryError):
    status_code = 403


class InvalidState(DeliveryError):
    status_code = 409
```

Create `backend/app/commands/common.py`:

```python
"""Pedaços que os comandos de entrega compartilham (funções simples, sem estado)."""
from sqlmodel import Session, select

from app.commands.errors import NotFound
from app.events import StockChanged, Subject
from app.models import Delivery, DeliveryItem, Role, Stock, User
from app.movements import MovementCreator

SEE_ALL = (Role.admin, Role.farmaceutico)


def load_visible(session: Session, user: User, delivery_id: int) -> Delivery:
    """Entrega que o usuário pode ver; senão 404 (não revelamos que ela existe)."""
    delivery = session.get(Delivery, delivery_id)
    if delivery is None or (user.role not in SEE_ALL and delivery.requested_by != user.id):
        raise NotFound("Entrega não encontrada. Confira o número e tente de novo.")
    return delivery


def delivery_lines(session: Session, delivery: Delivery) -> list[DeliveryItem]:
    return list(session.exec(select(DeliveryItem).where(DeliveryItem.delivery_id == delivery.id).order_by(DeliveryItem.id)).all())


def release_reservation(session: Session, delivery: Delivery, estorno: MovementCreator) -> list[Stock]:
    """Devolve ao disponível tudo que a entrega tinha reservado na origem (um ESTORNO por item)."""
    stocks = []
    for line in delivery_lines(session, delivery):
        stock = session.get(Stock, (delivery.origin_id, line.item_id))
        session.add(estorno.register(stock, delivery_id=delivery.id, quantity=line.quantity))
        session.add(stock)
        stocks.append(stock)
    return stocks


def notify_stocks(events: Subject, stocks: list[Stock]) -> None:
    for stock in stocks:
        events.notify(StockChanged(stock.location_id, stock.item_id, stock.quantity, stock.reserved, stock.minimum))
```

- [ ] **Step 5: Implementar o comando.** Create `backend/app/commands/cancel_delivery.py`:

```python
from sqlmodel import Session

from app.commands.common import load_visible, notify_stocks, release_reservation
from app.commands.errors import InvalidState, NotAllowed
from app.events import DeliveryChanged, Subject
from app.models import Delivery, DeliveryStatus, Role, User
from app.movements import EstornoCreator, MovementCreator

CANCELLABLE = (
    DeliveryStatus.PENDENTE_APROVACAO,
    DeliveryStatus.NA_FILA,
    DeliveryStatus.EM_ROTA,
    DeliveryStatus.AGUARDANDO_RECEBIMENTO,
)


class CancelDelivery:
    """Comando CancelarEntrega: só quem pediu (ou o admin) cancela; a reserva volta ao disponível (ESTORNO)."""

    def __init__(
        self,
        session: Session,
        user: User,
        delivery_id: int,
        *,
        estorno: MovementCreator | None = None,
        events: Subject | None = None,
    ) -> None:
        self.session = session
        self.user = user
        self.delivery_id = delivery_id
        self._estorno = estorno or EstornoCreator()
        self._events = events if events is not None else Subject()

    def execute(self) -> Delivery:
        delivery = load_visible(self.session, self.user, self.delivery_id)
        if self.user.role != Role.admin and delivery.requested_by != self.user.id:
            raise NotAllowed("Só quem pediu a entrega ou um administrador pode cancelá-la. Peça a quem fez o pedido.")
        if delivery.status not in CANCELLABLE:
            raise InvalidState(
                f"A entrega está {delivery.status.value} e não pode mais ser cancelada. Confira o status na lista de entregas."
            )
        old_status = delivery.status
        stocks = release_reservation(self.session, delivery, self._estorno)
        delivery.status = DeliveryStatus.CANCELADA
        self.session.add(delivery)
        self.session.commit()
        self.session.refresh(delivery)
        self._events.notify(DeliveryChanged(delivery.id, old_status, delivery.status, self.user.username))
        notify_stocks(self._events, stocks)
        return delivery
```

- [ ] **Step 6: Implementar o router e ligá-lo.** Create `backend/app/routers/delivery_actions.py`:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.commands.cancel_delivery import CancelDelivery
from app.commands.create_delivery import DeliveryError
from app.db import get_session
from app.deps import require_roles
from app.events import Subject, get_events
from app.models import Role, User
from app.queries import delivery_out
from app.schemas import DeliveryOut

router = APIRouter()
REQUESTERS = (Role.medico, Role.enfermeiro, Role.farmaceutico, Role.admin)


@router.post("/deliveries/{delivery_id}/cancel", response_model=DeliveryOut)
def cancel_delivery(
    delivery_id: int,
    user: User = Depends(require_roles(*REQUESTERS)),
    session: Session = Depends(get_session),
    events: Subject = Depends(get_events),
) -> DeliveryOut:
    try:
        delivery = CancelDelivery(session, user, delivery_id, events=events).execute()
    except DeliveryError as err:
        raise HTTPException(status_code=err.status_code, detail=str(err))
    return delivery_out(session, delivery)
```

Replace `backend/app/main.py`:

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlmodel import Session

from app.config import settings
from app.db import create_db, engine
from app.events import AuditLog, LowStockAlert, events
from app.routers import auth, catalog, deliveries, delivery_actions, robot
from app.seed import seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.auto_seed:
        create_db()
        with Session(engine) as session:
            seed(session)
    yield


events.add_observer(AuditLog())
events.add_observer(LowStockAlert())

app = FastAPI(title="G.E.R.A.L.D.O. API", version="0.1.0", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(catalog.router)
app.include_router(deliveries.router)
app.include_router(delivery_actions.router)
app.include_router(robot.router)


@app.get("/health", include_in_schema=False)
def health() -> dict:
    return {"status": "ok"}
```

- [ ] **Step 7: Rodar e ver passar.** Comando: `cd backend && python -m pytest -q`. Resultado esperado: `67 passed`.

- [ ] **Step 8: Commit.**

```bash
git add backend/app/commands/errors.py backend/app/commands/common.py backend/app/commands/cancel_delivery.py backend/app/routers/delivery_actions.py backend/app/main.py backend/tests/conftest.py backend/tests/test_cancel_delivery.py
git commit -m "feat(backend): cancelar entrega com estorno da reserva (Command)" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Aprovar entrega crítica (assinatura dupla)

**Files:**
- Create: `backend/app/commands/approve_delivery.py`
- Modify: `backend/app/priority.py`, `backend/app/routers/delivery_actions.py`
- Test: `backend/tests/test_approve_delivery.py`

**Interfaces:**
- Consumes: `load_visible`, `InvalidState`, `NotAllowed`, `policy_for`, `DeliveryChanged` (Tarefas 4, 7 e 8).
- Produces: `PriorityPolicy.needs_approval` (propriedade: `initial_status == PENDENTE_APROVACAO`; não compare `Priority.critica` fora de `app/priority.py`); `ApproveDelivery(session, user, delivery_id, *, policy_for=policy_for, events=None).execute() -> Delivery`; `POST /deliveries/{delivery_id}/approve` (só `farmaceutico`; `NA_FILA` ao aprovar; `403` se for quem pediu a entrega, porque a assinatura é dupla; `409` se a entrega não está `PENDENTE_APROVACAO` ou não precisa de aprovação). Limitação conhecida: o seed tem um só farmacêutico, então uma crítica pedida por ele mesmo precisa de outro farmacêutico (ou de outro usuário criado no banco).

- [ ] **Step 1: Escrever o teste.** Create `backend/tests/test_approve_delivery.py`:

```python
import pytest
from sqlmodel import select

from app.commands.approve_delivery import ApproveDelivery
from app.commands.create_delivery import CreateDelivery
from app.commands.errors import InvalidState
from app.events import DeliveryChanged
from app.models import DeliveryStatus, Priority, Role, User
from app.schemas import DeliveryCreate, DeliveryItemIn

CRITICAL = {"origin_id": "banco_sangue", "items": [{"item_id": "bolsa-sangue-o-neg", "quantity": 2}], "priority": "critica"}
MEDIA = {"origin_id": "farmacia", "items": [{"item_id": "dipirona-500mg", "quantity": 1}], "priority": "media"}


def create(client, auth, user, body) -> int:
    r = client.post("/deliveries", json=body, headers=auth(user))
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_pharmacist_approval_puts_the_critical_delivery_in_the_queue(client, auth, spy):
    delivery_id = create(client, auth, "medico1", CRITICAL)
    assert client.post("/robot/next-task", headers=auth("robo")).status_code == 204
    r = client.post(f"/deliveries/{delivery_id}/approve", headers=auth("farmaceutico1"))
    assert r.status_code == 200 and r.json()["status"] == "NA_FILA"
    assert DeliveryChanged(delivery_id, DeliveryStatus.PENDENTE_APROVACAO, DeliveryStatus.NA_FILA, "farmaceutico1") in spy.events
    assert client.post("/robot/next-task", headers=auth("robo")).json()["id"] == delivery_id


def test_only_a_pharmacist_approves(client, auth):
    delivery_id = create(client, auth, "medico1", CRITICAL)
    url = f"/deliveries/{delivery_id}/approve"
    assert client.post(url).status_code == 401
    for user in ("medico1", "enfermeiro1", "admin", "robo"):
        assert client.post(url, headers=auth(user)).status_code == 403, user


def test_the_requester_cannot_approve_their_own_delivery(client, auth):
    delivery_id = create(client, auth, "farmaceutico1", CRITICAL)
    r = client.post(f"/deliveries/{delivery_id}/approve", headers=auth("farmaceutico1"))
    assert r.status_code == 403 and "outra pessoa" in r.json()["detail"]


def test_approving_twice_or_a_delivery_that_needs_no_approval_is_409(client, auth):
    critical_id = create(client, auth, "medico1", CRITICAL)
    media_id = create(client, auth, "medico1", MEDIA)
    assert client.post(f"/deliveries/{critical_id}/approve", headers=auth("farmaceutico1")).status_code == 200
    again = client.post(f"/deliveries/{critical_id}/approve", headers=auth("farmaceutico1"))
    assert again.status_code == 409 and "NA_FILA" in again.json()["detail"]
    assert client.post(f"/deliveries/{media_id}/approve", headers=auth("farmaceutico1")).status_code == 409


def test_unknown_delivery_is_404(client, auth):
    assert client.post("/deliveries/9999/approve", headers=auth("farmaceutico1")).status_code == 404


def test_command_uses_the_injected_policy(session):
    medico = session.exec(select(User).where(User.username == "medico1")).one()
    pharmacist = session.exec(select(User).where(User.role == Role.farmaceutico)).one()
    payload = DeliveryCreate(origin_id="farmacia", items=[DeliveryItemIn(item_id="dipirona-500mg", quantity=1)], priority=Priority.critica)
    delivery = CreateDelivery(session, medico, payload).execute()

    class NoApprovalNeeded:
        needs_approval = False

    with pytest.raises(InvalidState, match="não espera aprovação"):
        ApproveDelivery(session, pharmacist, delivery.id, policy_for=lambda _: NoApprovalNeeded()).execute()
    assert ApproveDelivery(session, pharmacist, delivery.id).execute().status == DeliveryStatus.NA_FILA
```

- [ ] **Step 2: Rodar e ver falhar.** Comando: `cd backend && python -m pytest tests/test_approve_delivery.py -q`. Resultado esperado: erro de coleta `ModuleNotFoundError: No module named 'app.commands.approve_delivery'`.

- [ ] **Step 3: Acrescentar `needs_approval` à Strategy.** Replace `backend/app/priority.py`:

```python
from abc import ABC, abstractmethod

from app.models import DeliveryStatus, Priority


class PriorityPolicy(ABC):  # STRATEGY: cada prioridade sabe sua posição na fila e como a entrega nasce
    @property
    @abstractmethod
    def priority(self) -> Priority: ...

    @property
    @abstractmethod
    def rank(self) -> int:
        """Menor número sai primeiro da fila."""

    @property
    @abstractmethod
    def initial_status(self) -> DeliveryStatus: ...

    @property
    def needs_approval(self) -> bool:
        """Exige a assinatura do farmacêutico antes de entrar na fila."""
        return self.initial_status == DeliveryStatus.PENDENTE_APROVACAO


class Critical(PriorityPolicy):
    priority = Priority.critica
    rank = 0
    initial_status = DeliveryStatus.PENDENTE_APROVACAO  # exige a assinatura do farmacêutico


class Standard(PriorityPolicy):
    priority = Priority.media
    rank = 1
    initial_status = DeliveryStatus.NA_FILA


class Routine(PriorityPolicy):
    priority = Priority.rotina
    rank = 2
    initial_status = DeliveryStatus.NA_FILA


_POLICIES = {policy.priority: policy for policy in (Critical(), Standard(), Routine())}


def policy_for(priority: Priority) -> PriorityPolicy:  # FACTORY: nova prioridade = classe nova + uma linha acima
    return _POLICIES[priority]
```

- [ ] **Step 4: Implementar o comando.** Create `backend/app/commands/approve_delivery.py`:

```python
from sqlmodel import Session

from app.commands.common import load_visible
from app.commands.errors import InvalidState, NotAllowed
from app.events import DeliveryChanged, Subject
from app.models import Delivery, DeliveryStatus, User
from app.priority import policy_for


class ApproveDelivery:
    """Comando AprovarEntrega: a assinatura dupla da prioridade crítica.

    Quem aprova precisa ser outra pessoa além de quem pediu (por isso "dupla"); o papel
    farmacêutico é conferido no router.
    """

    def __init__(
        self,
        session: Session,
        user: User,
        delivery_id: int,
        *,
        policy_for=policy_for,
        events: Subject | None = None,
    ) -> None:
        self.session = session
        self.user = user
        self.delivery_id = delivery_id
        self._policy_for = policy_for
        self._events = events if events is not None else Subject()

    def execute(self) -> Delivery:
        delivery = load_visible(self.session, self.user, self.delivery_id)
        waiting = delivery.status == DeliveryStatus.PENDENTE_APROVACAO
        if not (waiting and self._policy_for(delivery.priority).needs_approval):
            raise InvalidState(
                f"A entrega está {delivery.status.value} e não espera aprovação. Só entregas críticas pendentes são aprovadas."
            )
        if delivery.requested_by == self.user.id:
            raise NotAllowed(
                "A assinatura dupla exige outra pessoa: quem pediu a entrega não pode aprová-la. Peça a outro farmacêutico."
            )
        old_status = delivery.status
        delivery.status = DeliveryStatus.NA_FILA
        self.session.add(delivery)
        self.session.commit()
        self.session.refresh(delivery)
        self._events.notify(DeliveryChanged(delivery.id, old_status, delivery.status, self.user.username))
        return delivery
```

- [ ] **Step 5: Acrescentar a rota.** Replace `backend/app/routers/delivery_actions.py`:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.commands.approve_delivery import ApproveDelivery
from app.commands.cancel_delivery import CancelDelivery
from app.commands.create_delivery import DeliveryError
from app.db import get_session
from app.deps import require_roles
from app.events import Subject, get_events
from app.models import Role, User
from app.queries import delivery_out
from app.schemas import DeliveryOut

router = APIRouter()
REQUESTERS = (Role.medico, Role.enfermeiro, Role.farmaceutico, Role.admin)


@router.post("/deliveries/{delivery_id}/cancel", response_model=DeliveryOut)
def cancel_delivery(
    delivery_id: int,
    user: User = Depends(require_roles(*REQUESTERS)),
    session: Session = Depends(get_session),
    events: Subject = Depends(get_events),
) -> DeliveryOut:
    try:
        delivery = CancelDelivery(session, user, delivery_id, events=events).execute()
    except DeliveryError as err:
        raise HTTPException(status_code=err.status_code, detail=str(err))
    return delivery_out(session, delivery)


@router.post("/deliveries/{delivery_id}/approve", response_model=DeliveryOut)
def approve_delivery(
    delivery_id: int,
    user: User = Depends(require_roles(Role.farmaceutico)),
    session: Session = Depends(get_session),
    events: Subject = Depends(get_events),
) -> DeliveryOut:
    try:
        delivery = ApproveDelivery(session, user, delivery_id, events=events).execute()
    except DeliveryError as err:
        raise HTTPException(status_code=err.status_code, detail=str(err))
    return delivery_out(session, delivery)
```

- [ ] **Step 6: Rodar e ver passar.** Comando: `cd backend && python -m pytest -q`. Resultado esperado: `73 passed`.

- [ ] **Step 7: Commit.**

```bash
git add backend/app/commands/approve_delivery.py backend/app/priority.py backend/app/routers/delivery_actions.py backend/tests/test_approve_delivery.py
git commit -m "feat(backend): aprovar entrega critica (assinatura dupla do farmaceutico)" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 10: `POST /robot/next-task` pula a rotina fora do baixo pico (relógio injetado)

**Files:**
- Create: `backend/app/clock.py`, `backend/app/commands/next_task.py`
- Modify: `backend/app/config.py`, `backend/app/priority.py`, `backend/app/routers/robot.py`, `backend/tests/conftest.py`
- Test: `backend/tests/test_next_task_off_peak.py`

**Interfaces:**
- Consumes: `policy_for`, `DeliveryChanged`, `Location.waypoint`, `settings` (Tarefas 2, 4, 7 e 9).
- Produces:
  - `app.clock`: protocolo `Clock` (`now() -> datetime`), `SystemClock` (hora local), `FixedClock(moment)`, `OffPeakWindow(start_hour: int, end_hour: int).contains(moment) -> bool` (atravessa a meia-noite quando `start > end`; `0` a `24` vale o dia todo), `get_clock() -> Clock` e `get_off_peak() -> OffPeakWindow` (dependências FastAPI; os testes trocam por `app.dependency_overrides`).
  - `settings.off_peak_start` e `settings.off_peak_end` (de `GERALDO_OFF_PEAK_HOURS`, padrão `20-6`).
  - `PriorityPolicy.off_peak_only` (`True` só na rotina).
  - `NextTask(session, clock, off_peak, *, policy_for=policy_for, events=None, actor="robo").execute() -> Dispatch | None` com `Dispatch(delivery, origin_waypoint: str, dest_waypoint: str)`. Escolhe por `(rank, id)` entre as `NA_FILA` cujos dois locais têm `waypoint`, descartando a rotina fora do baixo pico.
  - `POST /robot/next-task` continua igual para o chamador (`200` `RobotTask`, `204`, `401`, `403`).
  - O `conftest.py` passa a forçar "sempre em baixo pico" (`0-24`) em todos os testes; o teste da janela troca isso por conta própria.

- [ ] **Step 1: Deixar os testes independentes da hora.** Replace `backend/tests/conftest.py`:

```python
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.config import settings
from app.db import create_db, get_session, make_engine
from app.events import Subject, get_events
from app.main import app
from app.seed import seed

FIXTURES = Path(__file__).parent / "fixtures" / "seeds"
PASSWORD = "senha-de-teste"


@pytest.fixture(autouse=True)
def test_settings():
    names = ("jwt_secret", "jwt_minutes", "demo_password", "password_iterations", "auto_seed")
    old = {n: getattr(settings, n) for n in names}
    settings.jwt_secret = "segredo-de-teste-com-mais-de-32-bytes-0123456789"
    settings.jwt_minutes = 60
    settings.demo_password = PASSWORD
    settings.password_iterations = 1000
    settings.auto_seed = False
    yield
    for n, v in old.items():
        setattr(settings, n, v)


@pytest.fixture
def engine():
    eng = make_engine("sqlite://")
    create_db(eng)
    with Session(eng) as s:
        seed(s, FIXTURES)
    return eng


@pytest.fixture
def session(engine):
    with Session(engine) as s:
        yield s


@pytest.fixture
def client(engine):
    def override():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def auth(client):
    def login(username: str) -> dict:
        r = client.post("/auth/login", json={"username": username, "password": PASSWORD})
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    return login


class SpyObserver:
    def __init__(self) -> None:
        self.events = []

    def update(self, event) -> None:
        self.events.append(event)


@pytest.fixture
def spy(client):
    """Troca o Subject de eventos do app por um próprio e devolve o observador que anota tudo."""
    subject, observer = Subject(), SpyObserver()
    subject.add_observer(observer)
    app.dependency_overrides[get_events] = lambda: subject
    yield observer
    app.dependency_overrides.pop(get_events, None)


@pytest.fixture(autouse=True)
def always_off_peak(monkeypatch):
    """Por padrão os testes rodam "em baixo pico", para não depender da hora da máquina."""
    monkeypatch.setattr(settings, "off_peak_start", 0)
    monkeypatch.setattr(settings, "off_peak_end", 24)
```

- [ ] **Step 2: Escrever o teste.** Create `backend/tests/test_next_task_off_peak.py`:

```python
from datetime import datetime

import pytest
from sqlmodel import select

from app.clock import FixedClock, OffPeakWindow, get_clock
from app.commands.create_delivery import CreateDelivery
from app.commands.next_task import NextTask
from app.config import settings
from app.events import DeliveryChanged, Subject
from app.main import app
from app.models import Delivery, DeliveryStatus, Priority, User
from app.schemas import DeliveryCreate, DeliveryItemIn
from tests.conftest import SpyObserver


@pytest.mark.parametrize(
    "start, end, hour, expected",
    [(20, 6, 22, True), (20, 6, 3, True), (20, 6, 6, False), (20, 6, 14, False), (20, 6, 20, True), (9, 17, 12, True), (9, 17, 17, False), (0, 24, 13, True)],
)
def test_off_peak_window_handles_midnight_wraparound(start, end, hour, expected):
    assert OffPeakWindow(start, end).contains(datetime(2026, 11, 13, hour, 30)) is expected


def make(session, username: str, priority: Priority) -> int:
    user = session.exec(select(User).where(User.username == username)).one()
    payload = DeliveryCreate(origin_id="farmacia", items=[DeliveryItemIn(item_id="dipirona-500mg", quantity=1)], priority=priority)
    return CreateDelivery(session, user, payload).execute().id


def test_routine_is_skipped_at_peak_and_dispatched_off_peak(session):
    routine = make(session, "medico1", Priority.rotina)
    media = make(session, "medico1", Priority.media)
    window = OffPeakWindow(20, 6)
    peak, night = FixedClock(datetime(2026, 11, 13, 14, 0)), FixedClock(datetime(2026, 11, 13, 22, 0))

    assert NextTask(session, peak, window).execute().delivery.id == media
    assert NextTask(session, peak, window).execute() is None  # só sobrou a rotina
    assert session.get(Delivery, routine).status == DeliveryStatus.NA_FILA
    assert NextTask(session, night, window).execute().delivery.id == routine


def test_command_notifies_the_status_change(session):
    delivery_id = make(session, "medico1", Priority.media)
    spy, subject = SpyObserver(), Subject()
    subject.add_observer(spy)
    NextTask(session, FixedClock(datetime(2026, 11, 13, 22, 0)), OffPeakWindow(20, 6), events=subject, actor="robo").execute()
    assert spy.events == [DeliveryChanged(delivery_id, DeliveryStatus.NA_FILA, DeliveryStatus.EM_ROTA, "robo")]


def test_endpoint_uses_the_injected_clock_and_the_configured_window(client, auth, monkeypatch):
    monkeypatch.setattr(settings, "off_peak_start", 20)
    monkeypatch.setattr(settings, "off_peak_end", 6)
    body = {"origin_id": "farmacia", "items": [{"item_id": "dipirona-500mg", "quantity": 1}], "priority": "rotina"}
    delivery_id = client.post("/deliveries", json=body, headers=auth("medico1")).json()["id"]

    app.dependency_overrides[get_clock] = lambda: FixedClock(datetime(2026, 11, 13, 14, 0))
    assert client.post("/robot/next-task", headers=auth("robo")).status_code == 204
    app.dependency_overrides[get_clock] = lambda: FixedClock(datetime(2026, 11, 13, 23, 0))
    task = client.post("/robot/next-task", headers=auth("robo"))
    app.dependency_overrides.pop(get_clock)

    assert task.status_code == 200 and task.json()["id"] == delivery_id and task.json()["status"] == "EM_ROTA"
```

- [ ] **Step 3: Rodar e ver falhar.** Comando: `cd backend && python -m pytest tests/test_next_task_off_peak.py -q`. Resultado esperado: erro de coleta `ModuleNotFoundError: No module named 'app.clock'`.

- [ ] **Step 4: Implementar a configuração, o relógio e a Strategy.** Replace `backend/app/config.py`:

```python
import os
import secrets


class Settings:
    """Configuração lida do ambiente. Atributos mutáveis para os testes."""

    def __init__(self) -> None:
        self.database_url = os.environ.get("GERALDO_DATABASE_URL", "sqlite:///./geraldo.db")
        # sem segredo no ambiente, gera um aleatório (tokens deixam de valer ao reiniciar)
        self.jwt_secret = os.environ.get("GERALDO_JWT_SECRET") or secrets.token_hex(32)
        self.jwt_minutes = int(os.environ.get("GERALDO_JWT_MINUTES", "60"))
        self.demo_password = os.environ.get("GERALDO_DEMO_PASSWORD", "demo-only-change-me")
        self.password_iterations = 200_000
        self.auto_seed = os.environ.get("GERALDO_AUTO_SEED", "1") == "1"
        # janela de baixo pico, "início-fim" em horas (padrão 20-6; "0-24" libera a rotina o dia todo, útil na demo)
        self.off_peak_start, self.off_peak_end = (int(h) for h in os.environ.get("GERALDO_OFF_PEAK_HOURS", "20-6").split("-"))


settings = Settings()
```

Create `backend/app/clock.py`:

```python
from datetime import datetime
from typing import Protocol

from app.config import settings


class Clock(Protocol):  # a hora entra pelo construtor/dependência; o teste passa uma hora fixa
    def now(self) -> datetime: ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now().astimezone()  # hora local do hospital


class FixedClock:
    def __init__(self, moment: datetime) -> None:
        self._moment = moment

    def now(self) -> datetime:
        return self._moment


class OffPeakWindow:
    """Horário de baixo pico, em horas cheias [start, end). Atravessa a meia-noite quando start > end (20 a 6)."""

    def __init__(self, start_hour: int, end_hour: int) -> None:
        self.start_hour = start_hour
        self.end_hour = end_hour

    def contains(self, moment: datetime) -> bool:
        hour = moment.hour
        if self.start_hour <= self.end_hour:
            return self.start_hour <= hour < self.end_hour
        return hour >= self.start_hour or hour < self.end_hour


def get_clock() -> Clock:
    return SystemClock()


def get_off_peak() -> OffPeakWindow:
    return OffPeakWindow(settings.off_peak_start, settings.off_peak_end)
```

Replace `backend/app/priority.py`:

```python
from abc import ABC, abstractmethod

from app.models import DeliveryStatus, Priority


class PriorityPolicy(ABC):  # STRATEGY: cada prioridade sabe sua posição na fila e como a entrega nasce
    @property
    @abstractmethod
    def priority(self) -> Priority: ...

    @property
    @abstractmethod
    def rank(self) -> int:
        """Menor número sai primeiro da fila."""

    @property
    @abstractmethod
    def initial_status(self) -> DeliveryStatus: ...

    off_peak_only: bool = False
    """Só sai da fila em horário de baixo pico (a rotina)."""

    @property
    def needs_approval(self) -> bool:
        """Exige a assinatura do farmacêutico antes de entrar na fila."""
        return self.initial_status == DeliveryStatus.PENDENTE_APROVACAO


class Critical(PriorityPolicy):
    priority = Priority.critica
    rank = 0
    initial_status = DeliveryStatus.PENDENTE_APROVACAO  # exige a assinatura do farmacêutico


class Standard(PriorityPolicy):
    priority = Priority.media
    rank = 1
    initial_status = DeliveryStatus.NA_FILA


class Routine(PriorityPolicy):
    priority = Priority.rotina
    rank = 2
    initial_status = DeliveryStatus.NA_FILA
    off_peak_only = True


_POLICIES = {policy.priority: policy for policy in (Critical(), Standard(), Routine())}


def policy_for(priority: Priority) -> PriorityPolicy:  # FACTORY: nova prioridade = classe nova + uma linha acima
    return _POLICIES[priority]
```

- [ ] **Step 5: Implementar o comando e o router.** Create `backend/app/commands/next_task.py`:

```python
from dataclasses import dataclass

from sqlmodel import Session, select

from app.clock import Clock, OffPeakWindow
from app.events import DeliveryChanged, Subject
from app.models import Delivery, DeliveryStatus, Location
from app.priority import policy_for


@dataclass(frozen=True)
class Dispatch:
    delivery: Delivery
    origin_waypoint: str
    dest_waypoint: str


class NextTask:
    """Comando PróximaTarefa: escolhe a entrega que o robô leva agora e a coloca EM_ROTA.

    Ordem: crítica, média, rotina; dentro da prioridade, a mais antiga (menor id). A rotina só
    sai em baixo pico: o robô não consegue devolver uma tarefa que já saiu da fila.
    """

    def __init__(
        self,
        session: Session,
        clock: Clock,
        off_peak: OffPeakWindow,
        *,
        policy_for=policy_for,
        events: Subject | None = None,
        actor: str = "robo",
    ) -> None:
        self.session = session
        self._clock = clock
        self._off_peak = off_peak
        self._policy_for = policy_for
        self._events = events if events is not None else Subject()
        self._actor = actor

    def execute(self) -> Dispatch | None:
        off_peak_now = self._off_peak.contains(self._clock.now())
        candidates = []
        for delivery in self.session.exec(select(Delivery).where(Delivery.status == DeliveryStatus.NA_FILA)).all():
            policy = self._policy_for(delivery.priority)
            origin, dest = self.session.get(Location, delivery.origin_id), self.session.get(Location, delivery.dest_id)
            has_waypoints = origin is not None and dest is not None and origin.waypoint and dest.waypoint
            if has_waypoints and (off_peak_now or not policy.off_peak_only):
                candidates.append((policy.rank, delivery.id, delivery, origin.waypoint, dest.waypoint))
        if not candidates:
            return None
        _, _, delivery, origin_waypoint, dest_waypoint = min(candidates, key=lambda c: c[:2])
        delivery.status = DeliveryStatus.EM_ROTA
        self.session.add(delivery)
        self.session.commit()
        self.session.refresh(delivery)
        self._events.notify(DeliveryChanged(delivery.id, DeliveryStatus.NA_FILA, delivery.status, self._actor))
        return Dispatch(delivery, origin_waypoint, dest_waypoint)
```

Replace `backend/app/routers/robot.py`:

```python
from fastapi import APIRouter, Depends, Response
from sqlmodel import Session

from app.clock import Clock, OffPeakWindow, get_clock, get_off_peak
from app.commands.next_task import NextTask
from app.db import get_session
from app.deps import require_roles
from app.events import Subject, get_events
from app.models import Role, User
from app.queries import delivery_out
from app.schemas import RobotTaskOut

router = APIRouter()


@router.post("/robot/next-task", response_model=RobotTaskOut, responses={204: {"description": "Fila vazia"}})
def next_task(
    user: User = Depends(require_roles(Role.robo)),
    session: Session = Depends(get_session),
    clock: Clock = Depends(get_clock),
    off_peak: OffPeakWindow = Depends(get_off_peak),
    events: Subject = Depends(get_events),
):
    dispatch = NextTask(session, clock, off_peak, events=events, actor=user.username).execute()
    if dispatch is None:
        return Response(status_code=204)
    return RobotTaskOut(
        **delivery_out(session, dispatch.delivery).model_dump(),
        origin_waypoint=dispatch.origin_waypoint,
        dest_waypoint=dispatch.dest_waypoint,
    )
```

- [ ] **Step 6: Rodar e ver passar.** Comando: `cd backend && python -m pytest -q`. Resultado esperado: `84 passed` (inclui os 5 testes de fila da Tarefa 5, que continuam verdes).

- [ ] **Step 7: Commit.**

```bash
git add backend/app/clock.py backend/app/commands/next_task.py backend/app/config.py backend/app/priority.py backend/app/routers/robot.py backend/tests/conftest.py backend/tests/test_next_task_off_peak.py
git commit -m "feat(backend): next-task pula rotina fora do baixo pico (relogio injetado)" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 11: `POST /robot/events` (LOADED, ARRIVED, UNLOCKED, FAILED)

**Files:**
- Create: `backend/app/commands/robot_event.py`
- Modify: `backend/app/schemas.py`, `backend/app/routers/robot.py`
- Test: `backend/tests/test_robot_events.py`

**Interfaces:**
- Consumes: `release_reservation`, `notify_stocks`, `NotFound`, `InvalidState`, `EstornoCreator`, `DeliveryChanged` (Tarefas 6 a 8).
- Produces:
  - `app.schemas.RobotEventType` (`LOADED`, `ARRIVED`, `UNLOCKED`, `FAILED`) e `RobotEventIn(delivery_id: int, event: RobotEventType, reason: str | None = None)` (`reason` até 200 caracteres).
  - `app.commands.robot_event.TRANSITIONS` (tabela evento → status em que vale → `Step(new_status, releases_reservation)`) e `RegisterRobotEvent(session, payload, *, estorno=None, events=None, actor="robo").execute() -> Delivery`. Entrega inexistente: `404`; evento que não cabe no status: `409` (`"O evento X não se aplica a uma entrega Y. Confira o status da entrega antes de enviar o evento."`).
  - `POST /robot/events` (só `robo`): `200` com a entrega. `LOADED` mantém `EM_ROTA`; `ARRIVED` leva a `AGUARDANDO_RECEBIMENTO`; `UNLOCKED` só vale com a entrega `ENTREGUE` (**tolerado depois do `ENTREGUE`**, não muda nada) e antes disso responde `409`; `FAILED` leva a `FALHOU` e estorna a reserva.
  - O teste de `UNLOCKED` depois do `ENTREGUE` mora na Tarefa 12, porque precisa do `confirm-receipt`.

- [ ] **Step 1: Escrever o teste.** Create `backend/tests/test_robot_events.py`:

```python
import pytest
from sqlmodel import select

from app.events import DeliveryChanged, StockChanged
from app.models import DeliveryStatus, Movement, MovementType

BODY = {"origin_id": "farmacia", "items": [{"item_id": "dipirona-500mg", "quantity": 10}], "priority": "media"}


def in_route(client, auth) -> int:
    delivery_id = client.post("/deliveries", json=BODY, headers=auth("medico1")).json()["id"]
    assert client.post("/robot/next-task", headers=auth("robo")).json()["id"] == delivery_id
    return delivery_id


def event(client, auth, delivery_id, name, reason=None, user="robo"):
    return client.post("/robot/events", json={"delivery_id": delivery_id, "event": name, "reason": reason}, headers=auth(user))


def status(client, auth, delivery_id) -> str:
    return client.get(f"/deliveries/{delivery_id}", headers=auth("medico1")).json()["status"]


def test_loaded_keeps_the_delivery_on_its_way(client, auth):
    delivery_id = in_route(client, auth)
    r = event(client, auth, delivery_id, "LOADED")
    assert r.status_code == 200 and r.json()["status"] == "EM_ROTA"


def test_arrived_moves_the_delivery_to_awaiting_receipt(client, auth, spy):
    delivery_id = in_route(client, auth)
    spy.events.clear()
    event(client, auth, delivery_id, "LOADED")
    r = event(client, auth, delivery_id, "ARRIVED")
    assert r.status_code == 200 and r.json()["status"] == "AGUARDANDO_RECEBIMENTO"
    assert spy.events == [DeliveryChanged(delivery_id, DeliveryStatus.EM_ROTA, DeliveryStatus.AGUARDANDO_RECEBIMENTO, "robo")]


def test_unlocked_before_the_receipt_is_409(client, auth):
    delivery_id = in_route(client, auth)
    event(client, auth, delivery_id, "ARRIVED")
    r = event(client, auth, delivery_id, "UNLOCKED")
    assert r.status_code == 409 and "AGUARDANDO_RECEBIMENTO" in r.json()["detail"]


@pytest.mark.parametrize("stage", ["EM_ROTA", "AGUARDANDO_RECEBIMENTO"])
def test_failed_marks_falhou_and_releases_the_reservation(client, auth, session, spy, stage):
    delivery_id = in_route(client, auth)
    if stage == "AGUARDANDO_RECEBIMENTO":
        event(client, auth, delivery_id, "ARRIVED")
    spy.events.clear()
    r = event(client, auth, delivery_id, "FAILED", "não chegou ao destino")
    assert r.status_code == 200 and r.json()["status"] == "FALHOU"
    stock = client.get("/stock", params={"location_id": "farmacia"}, headers=auth("medico1")).json()[0]
    assert (stock["quantity"], stock["reserved"]) == (420, 0)
    assert [m.type for m in session.exec(select(Movement).order_by(Movement.id)).all()] == [MovementType.RESERVA, MovementType.ESTORNO]
    assert spy.events == [
        DeliveryChanged(delivery_id, DeliveryStatus(stage), DeliveryStatus.FALHOU, "robo"),
        StockChanged("farmacia", "dipirona-500mg", quantity=420, reserved=0, minimum=100),
    ]


def test_events_that_do_not_fit_the_status_are_409(client, auth):
    delivery_id = client.post("/deliveries", json=BODY, headers=auth("medico1")).json()["id"]  # NA_FILA
    for name in ("LOADED", "ARRIVED", "UNLOCKED", "FAILED"):
        r = event(client, auth, delivery_id, name)
        assert r.status_code == 409 and "NA_FILA" in r.json()["detail"], name
    assert status(client, auth, delivery_id) == "NA_FILA"


def test_event_after_the_delivery_was_cancelled_is_409_and_keeps_it_cancelled(client, auth):
    delivery_id = in_route(client, auth)
    client.post(f"/deliveries/{delivery_id}/cancel", headers=auth("medico1"))
    assert event(client, auth, delivery_id, "FAILED", "entrega cancelada").status_code == 409
    assert status(client, auth, delivery_id) == "CANCELADA"


def test_repeated_arrived_is_409(client, auth):
    delivery_id = in_route(client, auth)
    assert event(client, auth, delivery_id, "ARRIVED").status_code == 200
    assert event(client, auth, delivery_id, "ARRIVED").status_code == 409


def test_unknown_delivery_unknown_event_and_roles(client, auth):
    assert event(client, auth, 9999, "LOADED").status_code == 404
    assert client.post("/robot/events", json={"delivery_id": 1, "event": "EXPLODED"}, headers=auth("robo")).status_code == 422
    assert event(client, auth, 1, "LOADED", user="medico1").status_code == 403
    assert client.post("/robot/events", json={"delivery_id": 1, "event": "LOADED"}).status_code == 401
```

- [ ] **Step 2: Rodar e ver falhar.** Comando: `cd backend && python -m pytest tests/test_robot_events.py -q`. Resultado esperado: falhas `assert 404 == 200` (a rota ainda não existe).

- [ ] **Step 3: Acrescentar os schemas do evento.** Replace `backend/app/schemas.py`:

```python
from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models import DeliveryStatus, MovementType, Priority, Role


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"


class MeResponse(BaseModel):
    id: int
    username: str
    role: Role
    local_id: str | None = None


class LocationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    kind: str
    has_stock: bool
    waypoint: str | None = None


class StockOut(BaseModel):
    location_id: str
    item_id: str
    item_name: str
    quantity: int
    reserved: int
    minimum: int


class DeliveryItemIn(BaseModel):
    item_id: str
    quantity: int = Field(gt=0)


class DeliveryCreate(BaseModel):
    origin_id: str
    dest_id: str | None = None
    items: list[DeliveryItemIn] = Field(min_length=1)
    priority: Priority


class DeliveryOut(BaseModel):
    id: int
    origin_id: str
    dest_id: str
    items: list[DeliveryItemIn]
    priority: Priority
    status: DeliveryStatus
    requested_by: int
    created_at: datetime


class RobotTaskOut(DeliveryOut):
    origin_waypoint: str
    dest_waypoint: str


class MovementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    delivery_id: int | None
    type: MovementType
    item_id: str
    location_id: str
    quantity: int
    created_at: datetime


class RobotEventType(str, Enum):
    LOADED = "LOADED"
    ARRIVED = "ARRIVED"
    UNLOCKED = "UNLOCKED"
    FAILED = "FAILED"


class RobotEventIn(BaseModel):
    delivery_id: int
    event: RobotEventType
    reason: str | None = Field(default=None, max_length=200)
```

- [ ] **Step 4: Implementar o comando.** Create `backend/app/commands/robot_event.py`:

```python
from typing import NamedTuple

from sqlmodel import Session

from app.commands.common import notify_stocks, release_reservation
from app.commands.errors import InvalidState, NotFound
from app.events import DeliveryChanged, Subject
from app.models import Delivery, DeliveryStatus
from app.movements import EstornoCreator, MovementCreator
from app.schemas import RobotEventIn, RobotEventType

EM_ROTA = DeliveryStatus.EM_ROTA
AGUARDANDO = DeliveryStatus.AGUARDANDO_RECEBIMENTO


class Step(NamedTuple):
    new_status: DeliveryStatus
    releases_reservation: bool = False


# Tabela de transições: evento -> status em que ele vale -> o que acontece. Evento novo = linhas novas.
TRANSITIONS: dict[RobotEventType, dict[DeliveryStatus, Step]] = {
    RobotEventType.LOADED: {EM_ROTA: Step(EM_ROTA)},
    RobotEventType.ARRIVED: {EM_ROTA: Step(AGUARDANDO)},
    # a tampa só é liberada depois do ENTREGUE (docs/contracts/robot-protocol.md, passo 7): sem mudar o status
    RobotEventType.UNLOCKED: {DeliveryStatus.ENTREGUE: Step(DeliveryStatus.ENTREGUE)},
    RobotEventType.FAILED: {EM_ROTA: Step(DeliveryStatus.FALHOU, True), AGUARDANDO: Step(DeliveryStatus.FALHOU, True)},
}


class RegisterRobotEvent:
    """Comando RegistrarEventoDoRobô: aplica LOADED, ARRIVED, UNLOCKED ou FAILED à entrega."""

    def __init__(
        self,
        session: Session,
        payload: RobotEventIn,
        *,
        estorno: MovementCreator | None = None,
        events: Subject | None = None,
        actor: str = "robo",
    ) -> None:
        self.session = session
        self.payload = payload
        self._estorno = estorno or EstornoCreator()
        self._events = events if events is not None else Subject()
        self._actor = actor

    def execute(self) -> Delivery:
        delivery = self.session.get(Delivery, self.payload.delivery_id)
        if delivery is None:
            raise NotFound("Entrega não encontrada. Confira o delivery_id do evento.")
        step = TRANSITIONS[self.payload.event].get(delivery.status)
        if step is None:
            raise InvalidState(
                f"O evento {self.payload.event.value} não se aplica a uma entrega {delivery.status.value}. "
                "Confira o status da entrega antes de enviar o evento."
            )
        old_status = delivery.status
        stocks = release_reservation(self.session, delivery, self._estorno) if step.releases_reservation else []
        delivery.status = step.new_status
        self.session.add(delivery)
        self.session.commit()
        self.session.refresh(delivery)
        if delivery.status != old_status:
            self._events.notify(DeliveryChanged(delivery.id, old_status, delivery.status, self._actor))
        notify_stocks(self._events, stocks)
        return delivery
```

- [ ] **Step 5: Acrescentar a rota.** Replace `backend/app/routers/robot.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session

from app.clock import Clock, OffPeakWindow, get_clock, get_off_peak
from app.commands.create_delivery import DeliveryError
from app.commands.next_task import NextTask
from app.commands.robot_event import RegisterRobotEvent
from app.db import get_session
from app.deps import require_roles
from app.events import Subject, get_events
from app.models import Role, User
from app.queries import delivery_out
from app.schemas import DeliveryOut, RobotEventIn, RobotTaskOut

router = APIRouter()


@router.post("/robot/next-task", response_model=RobotTaskOut, responses={204: {"description": "Fila vazia"}})
def next_task(
    user: User = Depends(require_roles(Role.robo)),
    session: Session = Depends(get_session),
    clock: Clock = Depends(get_clock),
    off_peak: OffPeakWindow = Depends(get_off_peak),
    events: Subject = Depends(get_events),
):
    dispatch = NextTask(session, clock, off_peak, events=events, actor=user.username).execute()
    if dispatch is None:
        return Response(status_code=204)
    return RobotTaskOut(
        **delivery_out(session, dispatch.delivery).model_dump(),
        origin_waypoint=dispatch.origin_waypoint,
        dest_waypoint=dispatch.dest_waypoint,
    )


@router.post("/robot/events", response_model=DeliveryOut)
def robot_event(
    body: RobotEventIn,
    user: User = Depends(require_roles(Role.robo)),
    session: Session = Depends(get_session),
    events: Subject = Depends(get_events),
) -> DeliveryOut:
    try:
        delivery = RegisterRobotEvent(session, body, events=events, actor=user.username).execute()
    except DeliveryError as err:
        raise HTTPException(status_code=err.status_code, detail=str(err))
    return delivery_out(session, delivery)
```

- [ ] **Step 6: Rodar e ver passar.** Comando: `cd backend && python -m pytest -q`. Resultado esperado: `93 passed`.

- [ ] **Step 7: Commit.**

```bash
git add backend/app/commands/robot_event.py backend/app/schemas.py backend/app/routers/robot.py backend/tests/test_robot_events.py
git commit -m "feat(backend): POST /robot/events (LOADED, ARRIVED, UNLOCKED, FAILED)" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 12: Confirmar recebimento (baixa na origem, crédito no destino)

**Files:**
- Create: `backend/app/commands/confirm_receipt.py`
- Modify: `backend/app/routers/delivery_actions.py`
- Test: `backend/tests/test_confirm_receipt.py`

**Interfaces:**
- Consumes: `load_visible`, `delivery_lines`, `notify_stocks`, `NotAllowed`, `InvalidState`, `BaixaCreator`, `CreditoCreator` (Tarefas 6, 8 e 11).
- Produces: `ConfirmReceipt(session, user, delivery_id, *, baixa=None, credito=None, events=None).execute() -> Delivery`; `POST /deliveries/{delivery_id}/confirm-receipt` (papéis medico, enfermeiro, farmaceutico, admin; só quem pediu ou o admin confirma, senão `403`; fora de `AGUARDANDO_RECEBIMENTO` responde `409`). Efeito: status `ENTREGUE`; para cada item, `BAIXA` na origem e `CREDITO` no destino (a linha de estoque do destino nasce com saldo 0 e mínimo 0 se ainda não existia).

- [ ] **Step 1: Escrever o teste.** Create `backend/tests/test_confirm_receipt.py`:

```python
from sqlmodel import select

from app.events import DeliveryChanged, StockChanged
from app.models import DeliveryStatus, Movement, MovementType

BODY = {"origin_id": "farmacia", "items": [{"item_id": "dipirona-500mg", "quantity": 10}], "priority": "media"}


def arrived(client, auth, **over) -> int:
    delivery_id = client.post("/deliveries", json={**BODY, **over}, headers=auth("medico1")).json()["id"]
    client.post("/robot/next-task", headers=auth("robo"))
    client.post("/robot/events", json={"delivery_id": delivery_id, "event": "ARRIVED"}, headers=auth("robo"))
    return delivery_id


def stock(client, auth, location_id) -> list[dict]:
    return client.get("/stock", params={"location_id": location_id}, headers=auth("medico1")).json()


def test_confirming_moves_the_stock_from_origin_to_destination(client, auth, session, spy):
    delivery_id = arrived(client, auth)
    spy.events.clear()

    r = client.post(f"/deliveries/{delivery_id}/confirm-receipt", headers=auth("medico1"))

    assert r.status_code == 200 and r.json()["status"] == "ENTREGUE"
    origin = stock(client, auth, "farmacia")[0]
    assert (origin["quantity"], origin["reserved"]) == (410, 0)
    dest = stock(client, auth, "consultorio1")[0]  # já existia com saldo 0 e mínimo 20
    assert (dest["item_id"], dest["quantity"], dest["reserved"], dest["minimum"]) == ("dipirona-500mg", 10, 0, 20)
    moves = session.exec(select(Movement).order_by(Movement.id)).all()
    assert [(m.type, m.location_id, m.quantity) for m in moves] == [
        (MovementType.RESERVA, "farmacia", 10),
        (MovementType.BAIXA, "farmacia", 10),
        (MovementType.CREDITO, "consultorio1", 10),
    ]
    assert spy.events[0] == DeliveryChanged(delivery_id, DeliveryStatus.AGUARDANDO_RECEBIMENTO, DeliveryStatus.ENTREGUE, "medico1")
    assert StockChanged("farmacia", "dipirona-500mg", quantity=410, reserved=0, minimum=100) in spy.events


def test_the_destination_stock_line_is_created_when_it_did_not_exist(client, auth):
    delivery_id = arrived(client, auth, dest_id="consultorio2")  # o consultório 2 não tem dipirona cadastrada
    client.post(f"/deliveries/{delivery_id}/confirm-receipt", headers=auth("medico1"))
    dest = stock(client, auth, "consultorio2")
    assert [(s["item_id"], s["quantity"], s["reserved"], s["minimum"]) for s in dest if s["item_id"] == "dipirona-500mg"] == [("dipirona-500mg", 10, 0, 0)]


def test_credit_adds_to_an_existing_destination_balance(client, auth):
    delivery_id = arrived(client, auth, origin_id="banco_sangue", items=[{"item_id": "bolsa-sangue-o-neg", "quantity": 1}], dest_id="consultorio1")
    client.post(f"/deliveries/{delivery_id}/confirm-receipt", headers=auth("medico1"))
    assert stock(client, auth, "banco_sangue")[0]["quantity"] == 5
    second = arrived(client, auth, origin_id="banco_sangue", items=[{"item_id": "bolsa-sangue-o-neg", "quantity": 2}], dest_id="consultorio1")
    client.post(f"/deliveries/{second}/confirm-receipt", headers=auth("medico1"))
    assert [s["quantity"] for s in stock(client, auth, "consultorio1") if s["item_id"] == "bolsa-sangue-o-neg"] == [3]


def test_unlocked_after_entregue_is_accepted(client, auth):
    delivery_id = arrived(client, auth)
    client.post(f"/deliveries/{delivery_id}/confirm-receipt", headers=auth("medico1"))
    r = client.post("/robot/events", json={"delivery_id": delivery_id, "event": "UNLOCKED"}, headers=auth("robo"))
    assert r.status_code == 200 and r.json()["status"] == "ENTREGUE"


def test_confirming_twice_does_not_move_the_stock_twice(client, auth):
    delivery_id = arrived(client, auth)
    assert client.post(f"/deliveries/{delivery_id}/confirm-receipt", headers=auth("medico1")).status_code == 200
    r = client.post(f"/deliveries/{delivery_id}/confirm-receipt", headers=auth("medico1"))
    assert r.status_code == 409 and "ENTREGUE" in r.json()["detail"]
    assert stock(client, auth, "farmacia")[0]["quantity"] == 410


def test_cannot_confirm_before_the_robot_arrives(client, auth):
    delivery_id = client.post("/deliveries", json=BODY, headers=auth("medico1")).json()["id"]
    client.post("/robot/next-task", headers=auth("robo"))  # EM_ROTA
    r = client.post(f"/deliveries/{delivery_id}/confirm-receipt", headers=auth("medico1"))
    assert r.status_code == 409 and "Espere o aviso de chegada" in r.json()["detail"]
    assert stock(client, auth, "farmacia")[0]["quantity"] == 420


def test_who_can_confirm(client, auth):
    delivery_id = arrived(client, auth)
    url = f"/deliveries/{delivery_id}/confirm-receipt"
    assert client.post(url).status_code == 401
    assert client.post(url, headers=auth("robo")).status_code == 403
    assert client.post(url, headers=auth("medico2")).status_code == 404  # não vê a entrega dos outros
    r = client.post(url, headers=auth("farmaceutico1"))  # vê, mas não foi quem pediu
    assert r.status_code == 403 and "Peça a quem fez o pedido" in r.json()["detail"]
    assert client.post("/deliveries/9999/confirm-receipt", headers=auth("medico1")).status_code == 404
    assert client.post(url, headers=auth("admin")).status_code == 200  # o admin pode confirmar no lugar do solicitante
```

- [ ] **Step 2: Rodar e ver falhar.** Comando: `cd backend && python -m pytest tests/test_confirm_receipt.py -q`. Resultado esperado: falhas `assert 404 == 200` (a rota ainda não existe).

- [ ] **Step 3: Implementar o comando.** Create `backend/app/commands/confirm_receipt.py`:

```python
from sqlmodel import Session

from app.commands.common import delivery_lines, load_visible, notify_stocks
from app.commands.errors import InvalidState, NotAllowed
from app.events import DeliveryChanged, Subject
from app.models import Delivery, DeliveryStatus, Role, Stock, User
from app.movements import BaixaCreator, CreditoCreator, MovementCreator


class ConfirmReceipt:
    """Comando ConfirmarRecebimento: o solicitante recebeu; a entrega termina e o estoque se move.

    Na origem, BAIXA (consome a reserva e o saldo); no destino, CREDITO (soma ao saldo; a linha de
    estoque do destino nasce zerada se ainda não existia). O robô libera a tampa ao ver o ENTREGUE.
    """

    def __init__(
        self,
        session: Session,
        user: User,
        delivery_id: int,
        *,
        baixa: MovementCreator | None = None,
        credito: MovementCreator | None = None,
        events: Subject | None = None,
    ) -> None:
        self.session = session
        self.user = user
        self.delivery_id = delivery_id
        self._baixa = baixa or BaixaCreator()
        self._credito = credito or CreditoCreator()
        self._events = events if events is not None else Subject()

    def execute(self) -> Delivery:
        delivery = load_visible(self.session, self.user, self.delivery_id)
        if self.user.role != Role.admin and delivery.requested_by != self.user.id:
            raise NotAllowed("Só quem pediu a entrega pode confirmar o recebimento. Peça a quem fez o pedido.")
        if delivery.status != DeliveryStatus.AGUARDANDO_RECEBIMENTO:
            raise InvalidState(
                f"A entrega está {delivery.status.value}: o recebimento só pode ser confirmado depois que o robô chegar. "
                "Espere o aviso de chegada."
            )
        stocks = []
        for line in delivery_lines(self.session, delivery):
            origin = self.session.get(Stock, (delivery.origin_id, line.item_id))
            dest = self.session.get(Stock, (delivery.dest_id, line.item_id)) or Stock(location_id=delivery.dest_id, item_id=line.item_id)
            self.session.add(self._baixa.register(origin, delivery_id=delivery.id, quantity=line.quantity))
            self.session.add(self._credito.register(dest, delivery_id=delivery.id, quantity=line.quantity))
            self.session.add_all([origin, dest])
            stocks += [origin, dest]
        delivery.status = DeliveryStatus.ENTREGUE
        self.session.add(delivery)
        self.session.commit()
        self.session.refresh(delivery)
        self._events.notify(DeliveryChanged(delivery.id, DeliveryStatus.AGUARDANDO_RECEBIMENTO, delivery.status, self.user.username))
        notify_stocks(self._events, stocks)
        return delivery
```

- [ ] **Step 4: Acrescentar a rota.** Replace `backend/app/routers/delivery_actions.py`:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.commands.approve_delivery import ApproveDelivery
from app.commands.cancel_delivery import CancelDelivery
from app.commands.confirm_receipt import ConfirmReceipt
from app.commands.create_delivery import DeliveryError
from app.db import get_session
from app.deps import require_roles
from app.events import Subject, get_events
from app.models import Role, User
from app.queries import delivery_out
from app.schemas import DeliveryOut

router = APIRouter()
REQUESTERS = (Role.medico, Role.enfermeiro, Role.farmaceutico, Role.admin)


@router.post("/deliveries/{delivery_id}/cancel", response_model=DeliveryOut)
def cancel_delivery(
    delivery_id: int,
    user: User = Depends(require_roles(*REQUESTERS)),
    session: Session = Depends(get_session),
    events: Subject = Depends(get_events),
) -> DeliveryOut:
    try:
        delivery = CancelDelivery(session, user, delivery_id, events=events).execute()
    except DeliveryError as err:
        raise HTTPException(status_code=err.status_code, detail=str(err))
    return delivery_out(session, delivery)


@router.post("/deliveries/{delivery_id}/approve", response_model=DeliveryOut)
def approve_delivery(
    delivery_id: int,
    user: User = Depends(require_roles(Role.farmaceutico)),
    session: Session = Depends(get_session),
    events: Subject = Depends(get_events),
) -> DeliveryOut:
    try:
        delivery = ApproveDelivery(session, user, delivery_id, events=events).execute()
    except DeliveryError as err:
        raise HTTPException(status_code=err.status_code, detail=str(err))
    return delivery_out(session, delivery)


@router.post("/deliveries/{delivery_id}/confirm-receipt", response_model=DeliveryOut)
def confirm_receipt(
    delivery_id: int,
    user: User = Depends(require_roles(*REQUESTERS)),
    session: Session = Depends(get_session),
    events: Subject = Depends(get_events),
) -> DeliveryOut:
    try:
        delivery = ConfirmReceipt(session, user, delivery_id, events=events).execute()
    except DeliveryError as err:
        raise HTTPException(status_code=err.status_code, detail=str(err))
    return delivery_out(session, delivery)
```

- [ ] **Step 5: Rodar e ver passar.** Comando: `cd backend && python -m pytest -q`. Resultado esperado: `100 passed`.

- [ ] **Step 6: Commit.**

```bash
git add backend/app/commands/confirm_receipt.py backend/app/routers/delivery_actions.py backend/tests/test_confirm_receipt.py
git commit -m "feat(backend): confirmar recebimento com baixa na origem e credito no destino" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 13: `GET /movements`

**Files:**
- Create: `backend/app/routers/movements.py`
- Modify: `backend/app/queries.py`, `backend/app/main.py`
- Test: `backend/tests/test_movements_endpoint.py`

**Interfaces:**
- Consumes: `SEE_ALL`, `Movement`, `MovementOut` (Tarefas 3 e 8).
- Produces: `app.queries.movements_for(session, user, *, delivery_id=None, location_id=None) -> list[Movement]` (ordenado por `id`; admin e farmacêutico veem tudo, os demais só as movimentações das entregas que pediram; o `robo` recebe lista vazia); `GET /movements?delivery_id=&location_id=` (qualquer usuário logado).

- [ ] **Step 1: Escrever o teste.** Create `backend/tests/test_movements_endpoint.py`:

```python
BODY = {"origin_id": "farmacia", "items": [{"item_id": "dipirona-500mg", "quantity": 10}], "priority": "media"}


def delivered(client, auth, user="medico1") -> int:
    delivery_id = client.post("/deliveries", json=BODY, headers=auth(user)).json()["id"]
    client.post("/robot/next-task", headers=auth("robo"))
    client.post("/robot/events", json={"delivery_id": delivery_id, "event": "ARRIVED"}, headers=auth("robo"))
    client.post(f"/deliveries/{delivery_id}/confirm-receipt", headers=auth(user))
    return delivery_id


def test_history_lists_the_movements_in_order_with_the_contract_fields(client, auth):
    delivery_id = delivered(client, auth)
    r = client.get("/movements", headers=auth("farmaceutico1"))
    assert r.status_code == 200
    body = r.json()
    assert [(m["type"], m["location_id"], m["quantity"], m["delivery_id"]) for m in body] == [
        ("RESERVA", "farmacia", 10, delivery_id),
        ("BAIXA", "farmacia", 10, delivery_id),
        ("CREDITO", "consultorio1", 10, delivery_id),
    ]
    assert set(body[0]) == {"id", "delivery_id", "type", "item_id", "location_id", "quantity", "created_at"}


def test_filters_by_delivery_and_by_location(client, auth):
    first = delivered(client, auth)
    second = delivered(client, auth)
    h = auth("admin")
    by_delivery = client.get("/movements", params={"delivery_id": second}, headers=h).json()
    assert {m["delivery_id"] for m in by_delivery} == {second} and len(by_delivery) == 3
    by_location = client.get("/movements", params={"location_id": "consultorio1"}, headers=h).json()
    assert [m["type"] for m in by_location] == ["CREDITO", "CREDITO"]
    both = client.get("/movements", params={"delivery_id": first, "location_id": "farmacia"}, headers=h).json()
    assert [m["type"] for m in both] == ["RESERVA", "BAIXA"]


def test_regular_users_only_see_the_movements_of_their_own_deliveries(client, auth):
    delivered(client, auth, "medico1")
    assert len(client.get("/movements", headers=auth("medico1")).json()) == 3
    assert client.get("/movements", headers=auth("medico2")).json() == []
    assert client.get("/movements", headers=auth("robo")).json() == []


def test_requires_login(client):
    assert client.get("/movements").status_code == 401
```

- [ ] **Step 2: Rodar e ver falhar.** Comando: `cd backend && python -m pytest tests/test_movements_endpoint.py -q`. Resultado esperado: falhas `assert 404 == 200` (a rota ainda não existe).

- [ ] **Step 3: Implementar a consulta e o router.** Replace `backend/app/queries.py`:

```python
from sqlmodel import Session, select

from app.commands.common import SEE_ALL
from app.models import Delivery, DeliveryItem, Movement, User
from app.schemas import DeliveryItemIn, DeliveryOut


def delivery_out(session: Session, delivery: Delivery) -> DeliveryOut:
    items = session.exec(select(DeliveryItem).where(DeliveryItem.delivery_id == delivery.id).order_by(DeliveryItem.id)).all()
    return DeliveryOut(
        id=delivery.id,
        origin_id=delivery.origin_id,
        dest_id=delivery.dest_id,
        items=[DeliveryItemIn(item_id=i.item_id, quantity=i.quantity) for i in items],
        priority=delivery.priority,
        status=delivery.status,
        requested_by=delivery.requested_by,
        created_at=delivery.created_at,
    )


def movements_for(session: Session, user: User, *, delivery_id: int | None = None, location_id: str | None = None) -> list[Movement]:
    """Histórico de movimentações: admin e farmacêutico veem tudo; os demais, só as das entregas que pediram."""
    query = select(Movement).order_by(Movement.id)
    if user.role not in SEE_ALL:
        query = query.where(Movement.delivery_id.in_(select(Delivery.id).where(Delivery.requested_by == user.id)))
    if delivery_id is not None:
        query = query.where(Movement.delivery_id == delivery_id)
    if location_id is not None:
        query = query.where(Movement.location_id == location_id)
    return list(session.exec(query).all())
```

Create `backend/app/routers/movements.py`:

```python
from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db import get_session
from app.deps import get_current_user
from app.models import User
from app.queries import movements_for
from app.schemas import MovementOut

router = APIRouter()


@router.get("/movements", response_model=list[MovementOut])
def movements(
    delivery_id: int | None = None,
    location_id: str | None = None,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return movements_for(session, user, delivery_id=delivery_id, location_id=location_id)
```

Replace `backend/app/main.py`:

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlmodel import Session

from app.config import settings
from app.db import create_db, engine
from app.events import AuditLog, LowStockAlert, events
from app.routers import auth, catalog, deliveries, delivery_actions, movements, robot
from app.seed import seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.auto_seed:
        create_db()
        with Session(engine) as session:
            seed(session)
    yield


events.add_observer(AuditLog())
events.add_observer(LowStockAlert())

app = FastAPI(title="G.E.R.A.L.D.O. API", version="0.1.0", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(catalog.router)
app.include_router(deliveries.router)
app.include_router(delivery_actions.router)
app.include_router(movements.router)
app.include_router(robot.router)


@app.get("/health", include_in_schema=False)
def health() -> dict:
    return {"status": "ok"}
```

- [ ] **Step 4: Rodar e ver passar.** Comando: `cd backend && python -m pytest -q`. Resultado esperado: `104 passed`.

- [ ] **Step 5: Commit.**

```bash
git add backend/app/queries.py backend/app/routers/movements.py backend/app/main.py backend/tests/test_movements_endpoint.py
git commit -m "feat(backend): GET /movements com filtros por entrega e local" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 14: Telemetria: `POST /robot/telemetry`, `GET /telemetry` e `WS /ws/telemetry`

**Files:**
- Create: `backend/app/telemetry.py`, `backend/app/routers/telemetry.py`
- Modify: `backend/app/schemas.py`, `backend/app/deps.py`, `backend/app/routers/robot.py`, `backend/app/main.py`
- Test: `backend/tests/test_telemetry.py`

**Interfaces:**
- Consumes: `Subject` (Tarefa 7), `Clock`/`SystemClock`/`FixedClock` (Tarefa 10), `require_roles`, `get_current_user` (Tarefa 3).
- Produces:
  - Schemas: `RobotState` (os 7 estados do contrato), `PoseIn`, `PointIn`, `ObstacleIn`, `TelemetryIn` (`robot_state`, `pose`, `battery` de 0 a 100, `delivery_id` opcional, `route` até 50 pontos, `obstacles` até 20 itens `{x, y, radius}`, `updated_at` opcional e ignorado), `TelemetryOut` (igual, com `updated_at` obrigatório). Coordenadas em metros (`-1000` a `1000`), sem `NaN` nem infinito.
  - `app.telemetry.TelemetryHub(clock=None)` (é um `Subject`): `latest() -> TelemetryOut`, `publish(telemetry: TelemetryIn) -> TelemetryOut` (grava a hora de recebimento em UTC e avisa os assinantes); o singleton `hub` e `get_hub() -> TelemetryHub`.
  - `app.deps.user_from_token(token: str, session) -> User | None`; `get_current_user` passa a usá-la.
  - `POST /robot/telemetry` (só `robo`; `204`; `422` para corpo inválido), `GET /telemetry` (qualquer usuário logado; `200` `Telemetry`), `WS /ws/telemetry?token=<JWT>` (ao conectar envia o último estado; depois, um quadro por telemetria nova, mesmo corpo do `Telemetry`; sem token válido, recusa com 1008).

- [ ] **Step 1: Escrever o teste.** Create `backend/tests/test_telemetry.py`:

```python
from datetime import datetime, timezone

import pytest
from starlette.websockets import WebSocketDisconnect

from app.clock import FixedClock
from app.main import app
from app.telemetry import TelemetryHub, get_hub

SAMPLE = {
    "robot_state": "A_CAMINHO",
    "pose": {"x": 14.2, "y": 28.9, "yaw": 0.0},
    "battery": 99.1,
    "delivery_id": 7,
    "route": [{"x": 14.2, "y": 28.9}, {"x": 20.0, "y": 28.9}],
    "obstacles": [{"x": 18.0, "y": 28.9, "radius": 0.4}],
    "updated_at": "2020-01-01T00:00:00+00:00",
}
NOW = datetime(2026, 11, 13, 15, 0, tzinfo=timezone.utc)


@pytest.fixture
def hub(client):
    fresh = TelemetryHub(FixedClock(NOW))
    app.dependency_overrides[get_hub] = lambda: fresh
    yield fresh
    app.dependency_overrides.pop(get_hub, None)


def test_before_any_telemetry_the_panel_gets_a_no_signal_snapshot(client, auth, hub):
    r = client.get("/telemetry", headers=auth("medico1"))
    assert r.status_code == 200
    body = r.json()
    assert (body["robot_state"], body["battery"], body["route"], body["obstacles"]) == ("IDLE", 0, [], [])
    assert body["updated_at"].startswith("1970-01-01")


def test_robot_posts_and_everyone_logged_in_reads_the_last_state(client, auth, hub):
    assert client.post("/robot/telemetry", json=SAMPLE, headers=auth("robo")).status_code == 204
    body = client.get("/telemetry", headers=auth("medico1")).json()
    assert body["robot_state"] == "A_CAMINHO" and body["delivery_id"] == 7
    assert body["route"] == SAMPLE["route"] and body["obstacles"] == SAMPLE["obstacles"]


def test_the_backend_ignores_the_robots_updated_at_and_stamps_the_receipt_time(client, auth, hub):
    client.post("/robot/telemetry", json=SAMPLE, headers=auth("robo"))
    assert client.get("/telemetry", headers=auth("medico1")).json()["updated_at"] == "2026-11-13T15:00:00Z"


def test_optional_fields_default_to_empty(client, auth, hub):
    minimal = {"robot_state": "IDLE", "pose": {"x": 6.5, "y": 26.5, "yaw": -1.5708}, "battery": 100}
    assert client.post("/robot/telemetry", json=minimal, headers=auth("robo")).status_code == 204
    body = client.get("/telemetry", headers=auth("medico1")).json()
    assert (body["delivery_id"], body["route"], body["obstacles"]) == (None, [], [])


@pytest.mark.parametrize(
    "change",
    [
        {"robot_state": "VOANDO"},
        {"battery": 101},
        {"battery": -1},
        {"pose": {"x": 1, "y": 1}},
        {"pose": {"x": 1e9, "y": 1, "yaw": 0}},
        {"route": [{"x": 0, "y": 0}] * 51},
        {"obstacles": [{"x": 0, "y": 0, "radius": 0.3}] * 21},
        {"obstacles": [{"x": 0, "y": 0, "radius": -1}]},
    ],
)
def test_invalid_bodies_are_422_and_leave_the_last_state_alone(client, auth, hub, change):
    r = client.post("/robot/telemetry", json={**SAMPLE, **change}, headers=auth("robo"))
    assert r.status_code == 422
    assert client.get("/telemetry", headers=auth("medico1")).json()["robot_state"] == "IDLE"


def test_roles_and_authentication(client, auth, hub):
    assert client.post("/robot/telemetry", json=SAMPLE).status_code == 401
    for user in ("medico1", "admin", "farmaceutico1"):
        assert client.post("/robot/telemetry", json=SAMPLE, headers=auth(user)).status_code == 403
    assert client.get("/telemetry").status_code == 401


def test_websocket_sends_the_current_state_and_then_every_update(client, auth, hub):
    token = auth("medico1")["Authorization"].removeprefix("Bearer ")
    with client.websocket_connect(f"/ws/telemetry?token={token}") as ws:
        assert ws.receive_json()["robot_state"] == "IDLE"
        client.post("/robot/telemetry", json=SAMPLE, headers=auth("robo"))
        pushed = ws.receive_json()
        assert pushed["robot_state"] == "A_CAMINHO" and pushed["updated_at"] == "2026-11-13T15:00:00Z"
        assert pushed == client.get("/telemetry", headers=auth("medico1")).json()
    assert hub._observers == []  # a conexão fechou e saiu da lista de assinantes


def test_websocket_accepts_the_token_in_the_authorization_header(client, auth, hub):
    with client.websocket_connect("/ws/telemetry", headers=auth("medico1")) as ws:
        assert ws.receive_json()["robot_state"] == "IDLE"


@pytest.mark.parametrize("query", ["", "?token=lixo"])
def test_websocket_without_a_valid_token_is_refused(client, hub, query):
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/ws/telemetry{query}"):
            pass
```

- [ ] **Step 2: Rodar e ver falhar.** Comando: `cd backend && python -m pytest tests/test_telemetry.py -q`. Resultado esperado: erro de coleta `ModuleNotFoundError: No module named 'app.telemetry'`.

- [ ] **Step 3: Acrescentar os schemas.** Replace `backend/app/schemas.py`:

```python
from datetime import datetime
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models import DeliveryStatus, MovementType, Priority, Role


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"


class MeResponse(BaseModel):
    id: int
    username: str
    role: Role
    local_id: str | None = None


class LocationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    kind: str
    has_stock: bool
    waypoint: str | None = None


class StockOut(BaseModel):
    location_id: str
    item_id: str
    item_name: str
    quantity: int
    reserved: int
    minimum: int


class DeliveryItemIn(BaseModel):
    item_id: str
    quantity: int = Field(gt=0)


class DeliveryCreate(BaseModel):
    origin_id: str
    dest_id: str | None = None
    items: list[DeliveryItemIn] = Field(min_length=1)
    priority: Priority


class DeliveryOut(BaseModel):
    id: int
    origin_id: str
    dest_id: str
    items: list[DeliveryItemIn]
    priority: Priority
    status: DeliveryStatus
    requested_by: int
    created_at: datetime


class RobotTaskOut(DeliveryOut):
    origin_waypoint: str
    dest_waypoint: str


class MovementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    delivery_id: int | None
    type: MovementType
    item_id: str
    location_id: str
    quantity: int
    created_at: datetime


class RobotEventType(str, Enum):
    LOADED = "LOADED"
    ARRIVED = "ARRIVED"
    UNLOCKED = "UNLOCKED"
    FAILED = "FAILED"


class RobotEventIn(BaseModel):
    delivery_id: int
    event: RobotEventType
    reason: str | None = Field(default=None, max_length=200)


Meters = Annotated[float, Field(allow_inf_nan=False, ge=-1000, le=1000)]  # o hospital cabe folgado em 2 km


class RobotState(str, Enum):
    IDLE = "IDLE"
    CARREGANDO = "CARREGANDO"
    A_CAMINHO = "A_CAMINHO"
    CHEGOU = "CHEGOU"
    AGUARDANDO_RETIRADA = "AGUARDANDO_RETIRADA"
    VOLTANDO = "VOLTANDO"
    PARADA_EMERGENCIA = "PARADA_EMERGENCIA"


class PoseIn(BaseModel):
    x: Meters
    y: Meters
    yaw: Annotated[float, Field(allow_inf_nan=False, ge=-10, le=10)]  # radianos


class PointIn(BaseModel):
    x: Meters
    y: Meters


class ObstacleIn(BaseModel):
    x: Meters
    y: Meters
    radius: Annotated[float, Field(allow_inf_nan=False, ge=0, le=50)]


class TelemetryIn(BaseModel):
    """Corpo do POST /robot/telemetry. O updated_at do robô é aceito e ignorado: vale a hora de recebimento."""

    robot_state: RobotState
    pose: PoseIn
    battery: Annotated[float, Field(allow_inf_nan=False, ge=0, le=100)]
    delivery_id: int | None = None
    route: list[PointIn] = Field(default_factory=list, max_length=50)
    obstacles: list[ObstacleIn] = Field(default_factory=list, max_length=20)
    updated_at: datetime | None = None


class TelemetryOut(TelemetryIn):
    updated_at: datetime
```

- [ ] **Step 4: Extrair `user_from_token`.** Replace `backend/app/deps.py`:

```python
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from app.db import get_session
from app.models import Role, User
from app.security import decode_token

bearer = HTTPBearer(auto_error=False)


def user_from_token(token: str, session: Session) -> User | None:
    """O usuário dono do token, ou None se o token for inválido, expirado ou de usuário que não existe."""
    try:
        claims = decode_token(token)
    except jwt.PyJWTError:
        return None
    return session.get(User, int(claims["sub"]))


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    session: Session = Depends(get_session),
) -> User:
    if creds is None:
        raise HTTPException(status_code=401, detail="Faça login para continuar.")
    user = user_from_token(creds.credentials, session)
    if user is None:
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada. Entre de novo.")
    return user


def require_roles(*roles: Role):
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Seu perfil não tem permissão para isso.")
        return user

    return checker
```

- [ ] **Step 5: Implementar o hub e os routers.** Create `backend/app/telemetry.py`:

```python
from datetime import datetime, timezone

from app.clock import Clock, SystemClock
from app.events import Subject
from app.schemas import PoseIn, RobotState, TelemetryIn, TelemetryOut

NEVER = datetime(1970, 1, 1, tzinfo=timezone.utc)


class TelemetryHub(Subject):  # OBSERVER: o POST do robô publica; cada WebSocket aberto é um assinante
    """Guarda o último estado do robô (só em memória) e avisa quem assina a cada novo."""

    def __init__(self, clock: Clock | None = None) -> None:
        super().__init__()
        self._clock = clock or SystemClock()
        # antes da primeira telemetria: robô parado, bateria 0 e updated_at em 1970 (o painel lê isso como "sem sinal")
        self._latest = TelemetryOut(robot_state=RobotState.IDLE, pose=PoseIn(x=0, y=0, yaw=0), battery=0, updated_at=NEVER)

    def latest(self) -> TelemetryOut:
        return self._latest

    def publish(self, telemetry: TelemetryIn) -> TelemetryOut:
        data = telemetry.model_dump(exclude={"updated_at"})
        self._latest = TelemetryOut(**data, updated_at=self._clock.now().astimezone(timezone.utc))
        self.notify(self._latest)
        return self._latest


hub = TelemetryHub()


def get_hub() -> TelemetryHub:
    return hub
```

Create `backend/app/routers/telemetry.py`:

```python
import asyncio

from fastapi import APIRouter, Depends, WebSocket
from sqlmodel import Session

from app.db import get_session
from app.deps import get_current_user, user_from_token
from app.models import User
from app.schemas import TelemetryOut
from app.telemetry import TelemetryHub, get_hub

router = APIRouter()


@router.get("/telemetry", response_model=TelemetryOut)
def last_telemetry(_: User = Depends(get_current_user), hub: TelemetryHub = Depends(get_hub)):
    return hub.latest()


class _Subscriber:
    """Assinante do hub para um WebSocket: o POST roda em outra thread, então a entrega passa pelo loop do socket."""

    def __init__(self) -> None:
        self._loop = asyncio.get_running_loop()
        self.queue: asyncio.Queue = asyncio.Queue()

    def update(self, telemetry: TelemetryOut) -> None:
        self._loop.call_soon_threadsafe(self.queue.put_nowait, telemetry.model_dump(mode="json"))


async def _wait_disconnect(ws: WebSocket) -> None:
    while (await ws.receive())["type"] != "websocket.disconnect":
        pass


def _token_of(ws: WebSocket) -> str | None:
    """O navegador não envia cabeçalho no WebSocket: o token vem em ?token=...; clientes de linha de comando usam Authorization."""
    header = ws.headers.get("authorization", "")
    return ws.query_params.get("token") or (header[7:] if header.lower().startswith("bearer ") else None)


@router.websocket("/ws/telemetry")
async def ws_telemetry(ws: WebSocket, hub: TelemetryHub = Depends(get_hub), session: Session = Depends(get_session)):
    token = _token_of(ws)
    user = user_from_token(token, session) if token else None
    if user is None:
        await ws.close(code=1008, reason="Faça login: informe o token em ?token=")
        return
    await ws.accept()
    subscriber = _Subscriber()
    hub.add_observer(subscriber)
    gone = asyncio.create_task(_wait_disconnect(ws))
    try:
        await ws.send_json(hub.latest().model_dump(mode="json"))  # quem entra já recebe o último estado
        while not gone.done():
            getter = asyncio.create_task(subscriber.queue.get())
            await asyncio.wait({getter, gone}, return_when=asyncio.FIRST_COMPLETED)
            if getter.done():
                await ws.send_json(getter.result())
            else:
                getter.cancel()
    finally:
        hub.remove_observer(subscriber)
        gone.cancel()
```

Replace `backend/app/routers/robot.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session

from app.clock import Clock, OffPeakWindow, get_clock, get_off_peak
from app.commands.create_delivery import DeliveryError
from app.commands.next_task import NextTask
from app.commands.robot_event import RegisterRobotEvent
from app.db import get_session
from app.deps import require_roles
from app.events import Subject, get_events
from app.models import Role, User
from app.queries import delivery_out
from app.schemas import DeliveryOut, RobotEventIn, RobotTaskOut, TelemetryIn
from app.telemetry import TelemetryHub, get_hub

router = APIRouter()


@router.post("/robot/next-task", response_model=RobotTaskOut, responses={204: {"description": "Fila vazia"}})
def next_task(
    user: User = Depends(require_roles(Role.robo)),
    session: Session = Depends(get_session),
    clock: Clock = Depends(get_clock),
    off_peak: OffPeakWindow = Depends(get_off_peak),
    events: Subject = Depends(get_events),
):
    dispatch = NextTask(session, clock, off_peak, events=events, actor=user.username).execute()
    if dispatch is None:
        return Response(status_code=204)
    return RobotTaskOut(
        **delivery_out(session, dispatch.delivery).model_dump(),
        origin_waypoint=dispatch.origin_waypoint,
        dest_waypoint=dispatch.dest_waypoint,
    )


@router.post("/robot/events", response_model=DeliveryOut)
def robot_event(
    body: RobotEventIn,
    user: User = Depends(require_roles(Role.robo)),
    session: Session = Depends(get_session),
    events: Subject = Depends(get_events),
) -> DeliveryOut:
    try:
        delivery = RegisterRobotEvent(session, body, events=events, actor=user.username).execute()
    except DeliveryError as err:
        raise HTTPException(status_code=err.status_code, detail=str(err))
    return delivery_out(session, delivery)


@router.post("/robot/telemetry", status_code=204)
def robot_telemetry(
    body: TelemetryIn,
    _: User = Depends(require_roles(Role.robo)),
    hub: TelemetryHub = Depends(get_hub),
) -> Response:
    hub.publish(body)
    return Response(status_code=204)
```

Replace `backend/app/main.py`:

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlmodel import Session

from app.config import settings
from app.db import create_db, engine
from app.events import AuditLog, LowStockAlert, events
from app.routers import auth, catalog, deliveries, delivery_actions, movements, robot, telemetry
from app.seed import seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.auto_seed:
        create_db()
        with Session(engine) as session:
            seed(session)
    yield


events.add_observer(AuditLog())
events.add_observer(LowStockAlert())

app = FastAPI(title="G.E.R.A.L.D.O. API", version="0.1.0", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(catalog.router)
app.include_router(deliveries.router)
app.include_router(delivery_actions.router)
app.include_router(movements.router)
app.include_router(robot.router)
app.include_router(telemetry.router)


@app.get("/health", include_in_schema=False)
def health() -> dict:
    return {"status": "ok"}
```

- [ ] **Step 6: Rodar e ver passar.** Comando: `cd backend && python -m pytest -q`. Resultado esperado: `121 passed`. Rode também `for i in 1 2 3; do python -m pytest tests/test_telemetry.py -q; done`: os 3 resultados devem ser `17 passed` (o WebSocket não pode ser instável).

- [ ] **Step 7: Commit.**

```bash
git add backend/app/telemetry.py backend/app/routers/telemetry.py backend/app/schemas.py backend/app/deps.py backend/app/routers/robot.py backend/app/main.py backend/tests/test_telemetry.py
git commit -m "feat(backend): telemetria do robo, GET /telemetry e WS /ws/telemetry" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 15: Parada de emergência pelo painel (`POST` e `GET /robot/estop`)

**Files:**
- Create: `backend/app/estop.py`, `backend/app/routers/estop.py`
- Modify: `backend/app/schemas.py`, `backend/app/main.py`
- Test: `backend/tests/test_estop.py`

**Interfaces:**
- Consumes: `EstopChanged`, `Subject`, `get_events` (Tarefa 7), `require_roles` (Tarefa 3); o contrato do plano 1 (`EstopState`).
- Produces: `app.schemas.EstopState(active: StrictBool)`; `app.estop.EstopStore` (`.active: bool`, começa `False`; só em memória) e `get_estop() -> EstopStore`; `POST /robot/estop` (papéis `admin` e `farmaceutico`; corpo `{"active": bool}`; `204`; `401`, `403`, `422`) e `GET /robot/estop` (papel `robo`; `200` `{"active": bool}`; `401`, `403`). Cada `POST` avisa `EstopChanged(active, username)`.

- [ ] **Step 1: Escrever o teste.** Create `backend/tests/test_estop.py`:

```python
import pytest

from app.estop import EstopStore, get_estop
from app.events import EstopChanged
from app.main import app


@pytest.fixture(autouse=True)
def fresh_store(client):
    store = EstopStore()
    app.dependency_overrides[get_estop] = lambda: store
    yield store
    app.dependency_overrides.pop(get_estop, None)


def test_starts_off_and_the_robot_reads_the_state(client, auth):
    r = client.get("/robot/estop", headers=auth("robo"))
    assert r.status_code == 200 and r.json() == {"active": False}


@pytest.mark.parametrize("user", ["admin", "farmaceutico1"])
def test_panel_turns_the_emergency_on_and_off(client, auth, user):
    assert client.post("/robot/estop", json={"active": True}, headers=auth(user)).status_code == 204
    assert client.get("/robot/estop", headers=auth("robo")).json() == {"active": True}
    assert client.post("/robot/estop", json={"active": False}, headers=auth(user)).status_code == 204
    assert client.get("/robot/estop", headers=auth("robo")).json() == {"active": False}


def test_the_change_is_announced_to_the_observers(client, auth, spy):
    client.post("/robot/estop", json={"active": True}, headers=auth("farmaceutico1"))
    assert spy.events == [EstopChanged(True, "farmaceutico1")]


def test_roles_and_authentication(client, auth):
    assert client.post("/robot/estop", json={"active": True}).status_code == 401
    assert client.get("/robot/estop").status_code == 401
    for user in ("medico1", "enfermeiro1", "robo"):
        assert client.post("/robot/estop", json={"active": True}, headers=auth(user)).status_code == 403, user
    for user in ("medico1", "admin", "farmaceutico1"):
        assert client.get("/robot/estop", headers=auth(user)).status_code == 403, user


@pytest.mark.parametrize("body", [{}, {"active": "talvez"}, {"active": "true"}, {"active": 1}, {"ativo": True}])
def test_invalid_body_is_422(client, auth, body):
    assert client.post("/robot/estop", json=body, headers=auth("admin")).status_code == 422
```

- [ ] **Step 2: Rodar e ver falhar.** Comando: `cd backend && python -m pytest tests/test_estop.py -q`. Resultado esperado: erro de coleta `ModuleNotFoundError: No module named 'app.estop'`.

- [ ] **Step 3: Implementar.** Replace `backend/app/schemas.py`:

```python
from datetime import datetime
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool

from app.models import DeliveryStatus, MovementType, Priority, Role


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"


class MeResponse(BaseModel):
    id: int
    username: str
    role: Role
    local_id: str | None = None


class LocationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    kind: str
    has_stock: bool
    waypoint: str | None = None


class StockOut(BaseModel):
    location_id: str
    item_id: str
    item_name: str
    quantity: int
    reserved: int
    minimum: int


class DeliveryItemIn(BaseModel):
    item_id: str
    quantity: int = Field(gt=0)


class DeliveryCreate(BaseModel):
    origin_id: str
    dest_id: str | None = None
    items: list[DeliveryItemIn] = Field(min_length=1)
    priority: Priority


class DeliveryOut(BaseModel):
    id: int
    origin_id: str
    dest_id: str
    items: list[DeliveryItemIn]
    priority: Priority
    status: DeliveryStatus
    requested_by: int
    created_at: datetime


class RobotTaskOut(DeliveryOut):
    origin_waypoint: str
    dest_waypoint: str


class MovementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    delivery_id: int | None
    type: MovementType
    item_id: str
    location_id: str
    quantity: int
    created_at: datetime


class RobotEventType(str, Enum):
    LOADED = "LOADED"
    ARRIVED = "ARRIVED"
    UNLOCKED = "UNLOCKED"
    FAILED = "FAILED"


class RobotEventIn(BaseModel):
    delivery_id: int
    event: RobotEventType
    reason: str | None = Field(default=None, max_length=200)


Meters = Annotated[float, Field(allow_inf_nan=False, ge=-1000, le=1000)]  # o hospital cabe folgado em 2 km


class RobotState(str, Enum):
    IDLE = "IDLE"
    CARREGANDO = "CARREGANDO"
    A_CAMINHO = "A_CAMINHO"
    CHEGOU = "CHEGOU"
    AGUARDANDO_RETIRADA = "AGUARDANDO_RETIRADA"
    VOLTANDO = "VOLTANDO"
    PARADA_EMERGENCIA = "PARADA_EMERGENCIA"


class PoseIn(BaseModel):
    x: Meters
    y: Meters
    yaw: Annotated[float, Field(allow_inf_nan=False, ge=-10, le=10)]  # radianos


class PointIn(BaseModel):
    x: Meters
    y: Meters


class ObstacleIn(BaseModel):
    x: Meters
    y: Meters
    radius: Annotated[float, Field(allow_inf_nan=False, ge=0, le=50)]


class TelemetryIn(BaseModel):
    """Corpo do POST /robot/telemetry. O updated_at do robô é aceito e ignorado: vale a hora de recebimento."""

    robot_state: RobotState
    pose: PoseIn
    battery: Annotated[float, Field(allow_inf_nan=False, ge=0, le=100)]
    delivery_id: int | None = None
    route: list[PointIn] = Field(default_factory=list, max_length=50)
    obstacles: list[ObstacleIn] = Field(default_factory=list, max_length=20)
    updated_at: datetime | None = None


class TelemetryOut(TelemetryIn):
    updated_at: datetime


class EstopState(BaseModel):
    active: StrictBool  # só true ou false; "true" e 1 são recusados
```

Create `backend/app/estop.py`:

```python
class EstopStore:
    """Estado da parada de emergência pedida pelo painel (só em memória: ao reiniciar o backend, desligada).

    O robô consulta GET /robot/estop a cada 1 s e junta este estado com o tópico ROS /geraldo/estop.
    """

    def __init__(self) -> None:
        self.active = False


estop = EstopStore()


def get_estop() -> EstopStore:
    return estop
```

Create `backend/app/routers/estop.py`:

```python
from fastapi import APIRouter, Depends, Response

from app.deps import require_roles
from app.estop import EstopStore, get_estop
from app.events import EstopChanged, Subject, get_events
from app.models import Role, User
from app.schemas import EstopState

router = APIRouter()


@router.post("/robot/estop", status_code=204)
def set_estop(
    body: EstopState,
    user: User = Depends(require_roles(Role.admin, Role.farmaceutico)),
    store: EstopStore = Depends(get_estop),
    events: Subject = Depends(get_events),
) -> Response:
    store.active = body.active
    events.notify(EstopChanged(body.active, user.username))
    return Response(status_code=204)


@router.get("/robot/estop", response_model=EstopState)
def read_estop(_: User = Depends(require_roles(Role.robo)), store: EstopStore = Depends(get_estop)) -> EstopState:
    return EstopState(active=store.active)
```

Replace `backend/app/main.py`:

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlmodel import Session

from app.config import settings
from app.db import create_db, engine
from app.events import AuditLog, LowStockAlert, events
from app.routers import auth, catalog, deliveries, delivery_actions, estop, movements, robot, telemetry
from app.seed import seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.auto_seed:
        create_db()
        with Session(engine) as session:
            seed(session)
    yield


events.add_observer(AuditLog())
events.add_observer(LowStockAlert())

app = FastAPI(title="G.E.R.A.L.D.O. API", version="0.1.0", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(catalog.router)
app.include_router(deliveries.router)
app.include_router(delivery_actions.router)
app.include_router(movements.router)
app.include_router(robot.router)
app.include_router(estop.router)
app.include_router(telemetry.router)


@app.get("/health", include_in_schema=False)
def health() -> dict:
    return {"status": "ok"}
```

- [ ] **Step 4: Rodar e ver passar.** Comando: `cd backend && python -m pytest -q`. Resultado esperado: `131 passed`.

- [ ] **Step 5: Commit.**

```bash
git add backend/app/estop.py backend/app/routers/estop.py backend/app/schemas.py backend/app/main.py backend/tests/test_estop.py
git commit -m "feat(backend): parada de emergencia pelo painel (POST e GET /robot/estop)" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 16: Erros de validação em português e limites de entrada (endurecimento)

**Files:**
- Create: `backend/app/errors.py`
- Modify: `backend/app/schemas.py`, `backend/app/main.py`
- Test: `backend/tests/test_validation_errors.py`

**Interfaces:**
- Consumes: os schemas de entrada das Tarefas 3, 4, 11, 14 e 15.
- Produces: `app.errors.describe(error: dict) -> str` (uma frase em português para um erro do pydantic), `app.errors.install(app)` (registra os handlers). Todo erro sai como `{"detail": "<texto>"}` (o schema `Error` do contrato): `422` vira `"Dados inválidos (<campo>: <o que houve>; ...). Corrija e envie de novo."` (sem ecoar o valor enviado, o que também evita `500` com `NaN`); `404`/`405` sem mensagem própria ganham texto em português; erro inesperado vira `500` com mensagem genérica, sem vazar detalhe. Limites novos: `username` 1 a 64 e `password` 1 a 128 caracteres; `origin_id`, `dest_id` e `item_id` de 1 a 64; no máximo 50 itens por entrega; `quantity` de 1 a 10000.

- [ ] **Step 1: Escrever o teste.** Create `backend/tests/test_validation_errors.py`:

```python
import json

import pytest
from fastapi.testclient import TestClient

from app.db import get_session
from app.errors import describe
from app.main import app
from tests.conftest import PASSWORD

BODY = {"origin_id": "farmacia", "items": [{"item_id": "dipirona-500mg", "quantity": 10}], "priority": "media"}


def detail_of(response) -> str:
    assert response.status_code == 422, response.text
    detail = response.json()["detail"]
    assert isinstance(detail, str)  # o schema Error do contrato: detail é texto, não a lista do pydantic
    assert detail.startswith("Dados inválidos") and detail.endswith("Corrija e envie de novo.")
    return detail


def test_missing_fields_say_which_one(client):
    detail = detail_of(client.post("/auth/login", json={"username": "medico1"}))
    assert "password: campo obrigatório" in detail


def test_limits_are_explained_in_portuguese(client, auth):
    h = auth("medico1")
    assert "items.0.quantity: deve ser maior que 0" in detail_of(client.post("/deliveries", json={**BODY, "items": [{"item_id": "x", "quantity": 0}]}, headers=h))
    assert "deve ser no máximo 10000" in detail_of(client.post("/deliveries", json={**BODY, "items": [{"item_id": "x", "quantity": 10_001}]}, headers=h))
    assert "items: grande demais (máximo 50)" in detail_of(client.post("/deliveries", json={**BODY, "items": [{"item_id": "x", "quantity": 1}] * 51}, headers=h))
    assert "origin_id: grande demais (máximo 64)" in detail_of(client.post("/deliveries", json={**BODY, "origin_id": "a" * 65}, headers=h))
    assert "priority: valor fora da lista permitida" in detail_of(client.post("/deliveries", json={**BODY, "priority": "urgentissima"}, headers=h))
    assert "items: curto demais (mínimo 1)" in detail_of(client.post("/deliveries", json={**BODY, "items": []}, headers=h))


def test_huge_passwords_are_refused_before_hashing(client):
    assert "password: grande demais (máximo 128)" in detail_of(client.post("/auth/login", json={"username": "medico1", "password": "x" * 129}))


def test_malformed_json_is_422_not_500(client, auth):
    r = client.post("/deliveries", content="{isto não é json", headers={**auth("medico1"), "content-type": "application/json"})
    assert "o corpo não é um JSON válido" in detail_of(r)


def test_nan_in_the_telemetry_is_422_not_500(client, auth):
    sample = {"robot_state": "IDLE", "pose": {"x": 0, "y": 0, "yaw": 0}, "battery": 50}
    body = json.dumps({**sample, "battery": float("nan")})  # o Python escreve NaN, que não é JSON válido: o servidor aceita e recusa
    r = client.post("/robot/telemetry", content=body, headers={**auth("robo"), "content-type": "application/json"})
    assert "battery:" in detail_of(r)


def test_unknown_error_types_fall_back_to_a_generic_message():
    assert describe({"type": "coisa_nova", "loc": ("body", "x"), "msg": "?"}) == "x: valor inválido"


def test_unknown_path_and_wrong_method_are_portuguese(client, auth):
    r = client.get("/nao-existe", headers=auth("medico1"))
    assert r.status_code == 404 and "Confira a URL" in r.json()["detail"]
    r = client.delete("/me", headers=auth("medico1"))
    assert r.status_code == 405 and "Método não permitido" in r.json()["detail"]


def test_domain_errors_keep_their_own_message(client, auth):
    r = client.get("/deliveries/9999", headers=auth("medico1"))
    assert r.status_code == 404 and r.json()["detail"] == "Entrega não encontrada."


def test_unexpected_errors_do_not_leak_details(engine):
    def broken():
        raise RuntimeError("senha-do-banco=1234")
        yield  # pragma: no cover

    app.dependency_overrides[get_session] = broken
    try:
        r = TestClient(app, raise_server_exceptions=False).post("/auth/login", json={"username": "a", "password": PASSWORD})
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 500
    assert "senha-do-banco" not in r.text and "Tente de novo" in r.json()["detail"]
```

- [ ] **Step 2: Rodar e ver falhar.** Comando: `cd backend && python -m pytest tests/test_validation_errors.py -q`. Resultado esperado: erro de coleta `ImportError` de `app.errors`.

- [ ] **Step 3: Implementar os handlers.** Create `backend/app/errors.py`:

```python
import logging
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

# Texto em português por tipo de erro do pydantic; {…} vem do "ctx" do erro (ex.: o limite que foi passado).
MESSAGES = {
    "missing": "campo obrigatório",
    "string_type": "deve ser um texto",
    "int_type": "deve ser um número inteiro",
    "int_parsing": "deve ser um número inteiro",
    "float_type": "deve ser um número",
    "float_parsing": "deve ser um número",
    "bool_type": "deve ser verdadeiro ou falso",
    "bool_parsing": "deve ser verdadeiro ou falso",
    "enum": "valor fora da lista permitida",
    "literal_error": "valor fora da lista permitida",
    "too_short": "curto demais (mínimo {min_length})",
    "too_long": "grande demais (máximo {max_length})",
    "string_too_short": "curto demais (mínimo {min_length})",
    "string_too_long": "grande demais (máximo {max_length})",
    "greater_than": "deve ser maior que {gt}",
    "greater_than_equal": "deve ser no mínimo {ge}",
    "less_than": "deve ser menor que {lt}",
    "less_than_equal": "deve ser no máximo {le}",
    "finite_number": "deve ser um número finito",
    "model_type": "formato inválido",
    "dict_type": "formato inválido",
    "list_type": "deve ser uma lista",
}
HTTP_MESSAGES = {
    404: "Endereço não encontrado. Confira a URL na documentação (/docs).",
    405: "Método não permitido neste endereço. Confira a documentação (/docs).",
}


def describe(error: dict) -> str:
    """Uma frase em português para um erro de validação do pydantic."""
    if error["type"] == "json_invalid":
        return "o corpo não é um JSON válido"
    field = ".".join(str(part) for part in error["loc"][1:]) or "corpo"
    template = MESSAGES.get(error["type"], "valor inválido")
    try:
        text = template.format(**error.get("ctx", {}))
    except (KeyError, IndexError):
        text = template
    return f"{field}: {text}"


async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    # Nunca devolvemos o "input" do erro: ele pode trazer o valor enviado (e NaN quebra o JSON).
    problems = "; ".join(describe(error) for error in exc.errors()[:3])
    return JSONResponse(status_code=422, content={"detail": f"Dados inválidos ({problems}). Corrija e envie de novo."})


async def http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    default = HTTPStatus(exc.status_code).phrase
    detail = HTTP_MESSAGES.get(exc.status_code, exc.detail) if exc.detail == default else exc.detail
    return JSONResponse(status_code=exc.status_code, content={"detail": detail}, headers=exc.headers)


async def unexpected_error(_: Request, exc: Exception) -> JSONResponse:
    logging.getLogger("geraldo.errors").exception("erro inesperado", exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Erro interno do servidor. Tente de novo; se persistir, avise o suporte."})


def install(app: FastAPI) -> None:
    """Todo erro do backend sai como {"detail": "<o que houve + o que fazer>"} (schema Error do contrato)."""
    app.add_exception_handler(RequestValidationError, validation_error)
    app.add_exception_handler(StarletteHTTPException, http_error)
    app.add_exception_handler(Exception, unexpected_error)
```

- [ ] **Step 4: Aplicar os limites e registrar os handlers.** Replace `backend/app/schemas.py`:

```python
from datetime import datetime
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool

from app.models import DeliveryStatus, MovementType, Priority, Role


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"


class MeResponse(BaseModel):
    id: int
    username: str
    role: Role
    local_id: str | None = None


class LocationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    kind: str
    has_stock: bool
    waypoint: str | None = None


class StockOut(BaseModel):
    location_id: str
    item_id: str
    item_name: str
    quantity: int
    reserved: int
    minimum: int


class DeliveryItemIn(BaseModel):
    item_id: str = Field(min_length=1, max_length=64)
    quantity: int = Field(gt=0, le=10_000)


class DeliveryCreate(BaseModel):
    origin_id: str = Field(min_length=1, max_length=64)
    dest_id: str | None = Field(default=None, min_length=1, max_length=64)
    items: list[DeliveryItemIn] = Field(min_length=1, max_length=50)
    priority: Priority


class DeliveryOut(BaseModel):
    id: int
    origin_id: str
    dest_id: str
    items: list[DeliveryItemIn]
    priority: Priority
    status: DeliveryStatus
    requested_by: int
    created_at: datetime


class RobotTaskOut(DeliveryOut):
    origin_waypoint: str
    dest_waypoint: str


class MovementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    delivery_id: int | None
    type: MovementType
    item_id: str
    location_id: str
    quantity: int
    created_at: datetime


class RobotEventType(str, Enum):
    LOADED = "LOADED"
    ARRIVED = "ARRIVED"
    UNLOCKED = "UNLOCKED"
    FAILED = "FAILED"


class RobotEventIn(BaseModel):
    delivery_id: int
    event: RobotEventType
    reason: str | None = Field(default=None, max_length=200)


Meters = Annotated[float, Field(allow_inf_nan=False, ge=-1000, le=1000)]  # o hospital cabe folgado em 2 km


class RobotState(str, Enum):
    IDLE = "IDLE"
    CARREGANDO = "CARREGANDO"
    A_CAMINHO = "A_CAMINHO"
    CHEGOU = "CHEGOU"
    AGUARDANDO_RETIRADA = "AGUARDANDO_RETIRADA"
    VOLTANDO = "VOLTANDO"
    PARADA_EMERGENCIA = "PARADA_EMERGENCIA"


class PoseIn(BaseModel):
    x: Meters
    y: Meters
    yaw: Annotated[float, Field(allow_inf_nan=False, ge=-10, le=10)]  # radianos


class PointIn(BaseModel):
    x: Meters
    y: Meters


class ObstacleIn(BaseModel):
    x: Meters
    y: Meters
    radius: Annotated[float, Field(allow_inf_nan=False, ge=0, le=50)]


class TelemetryIn(BaseModel):
    """Corpo do POST /robot/telemetry. O updated_at do robô é aceito e ignorado: vale a hora de recebimento."""

    robot_state: RobotState
    pose: PoseIn
    battery: Annotated[float, Field(allow_inf_nan=False, ge=0, le=100)]
    delivery_id: int | None = None
    route: list[PointIn] = Field(default_factory=list, max_length=50)
    obstacles: list[ObstacleIn] = Field(default_factory=list, max_length=20)
    updated_at: datetime | None = None


class TelemetryOut(TelemetryIn):
    updated_at: datetime


class EstopState(BaseModel):
    active: StrictBool  # só true ou false; "true" e 1 são recusados
```

Replace `backend/app/main.py`:

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlmodel import Session

from app.config import settings
from app.db import create_db, engine
from app.errors import install as install_error_handlers
from app.events import AuditLog, LowStockAlert, events
from app.routers import auth, catalog, deliveries, delivery_actions, estop, movements, robot, telemetry
from app.seed import seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.auto_seed:
        create_db()
        with Session(engine) as session:
            seed(session)
    yield


events.add_observer(AuditLog())
events.add_observer(LowStockAlert())

app = FastAPI(title="G.E.R.A.L.D.O. API", version="0.1.0", lifespan=lifespan)
install_error_handlers(app)
app.include_router(auth.router)
app.include_router(catalog.router)
app.include_router(deliveries.router)
app.include_router(delivery_actions.router)
app.include_router(movements.router)
app.include_router(robot.router)
app.include_router(estop.router)
app.include_router(telemetry.router)


@app.get("/health", include_in_schema=False)
def health() -> dict:
    return {"status": "ok"}
```

- [ ] **Step 5: Rodar e ver passar.** Comando: `cd backend && python -m pytest -q`. Resultado esperado: `140 passed` (os testes de `422` das tarefas anteriores continuam verdes: só o texto do `detail` mudou).

- [ ] **Step 6: Commit.**

```bash
git add backend/app/errors.py backend/app/schemas.py backend/app/main.py backend/tests/test_validation_errors.py
git commit -m "feat(backend): erros de validacao em portugues e limites de entrada" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 17: JWT confere papel e `sub`; matriz de papéis; segredo mínimo (endurecimento)

**Files:**
- Modify: `backend/app/deps.py`, `backend/app/main.py`
- Test: `backend/tests/test_security_hardening.py`

**Interfaces:**
- Consumes: `decode_token` (HS256; exige `exp`, `sub`, `role`, `jti`; Tarefa 3) e `user_from_token` (Tarefa 14).
- Produces: `user_from_token` passa a devolver `None` (logo `401`) também quando o `sub` não é um número (antes seria `500`) e quando o `role` do token difere do papel atual do usuário no banco; o servidor se recusa a subir com `GERALDO_JWT_SECRET` de menos de 32 caracteres (`RuntimeError` com o comando para gerar um). Os testes provam: cada claim obrigatório, só HS256 (HS512 com o segredo certo é recusado) e a matriz de papéis de todas as rotas protegidas (papel errado `403`, sem token `401`).

- [ ] **Step 1: Escrever o teste.** Create `backend/tests/test_security_hardening.py`:

```python
import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.models import Role

REQUESTERS = ("medico", "enfermeiro", "farmaceutico", "admin")


def token(user_id: int = 1, **over) -> str:
    claims = {"sub": str(user_id), "role": "medico", "exp": datetime.now(timezone.utc) + timedelta(minutes=5), "jti": uuid.uuid4().hex}
    claims.update(over)
    return jwt.encode(claims, settings.jwt_secret, algorithm="HS256")


def get_me(client, bearer: str) -> int:
    return client.get("/me", headers={"Authorization": f"Bearer {bearer}"}).status_code


def test_a_correctly_signed_token_with_the_right_role_works(client):
    assert get_me(client, token(1)) == 200  # o usuário 1 do seed é o medico1


def test_the_role_in_the_token_must_match_the_users_current_role(client):
    assert get_me(client, token(1, role="admin")) == 401  # medico1 com role admin forjada no claim


def test_a_non_numeric_subject_is_401_not_500(client):
    assert get_me(client, token(sub="abc")) == 401
    assert get_me(client, token(sub="9999")) == 401  # usuário que não existe


@pytest.mark.parametrize("claim", ["exp", "sub", "role", "jti"])
def test_every_required_claim_is_enforced(client, claim):
    claims = {"sub": "1", "role": "medico", "exp": datetime.now(timezone.utc) + timedelta(minutes=5), "jti": uuid.uuid4().hex}
    del claims[claim]
    assert get_me(client, jwt.encode(claims, settings.jwt_secret, algorithm="HS256")) == 401


def test_only_hs256_is_accepted_even_with_the_right_secret(client):
    claims = {"sub": "1", "role": "medico", "exp": datetime.now(timezone.utc) + timedelta(minutes=5), "jti": uuid.uuid4().hex}
    assert get_me(client, jwt.encode(claims, settings.jwt_secret, algorithm="HS512")) == 401


def test_the_server_refuses_to_start_with_a_short_secret():
    settings.jwt_secret = "curto"
    with pytest.raises(RuntimeError, match="GERALDO_JWT_SECRET"):
        with TestClient(app):
            pass


# (método, caminho, papéis permitidos). Quem não está na lista leva 403; sem token, 401.
PROTECTED = [
    ("post", "/deliveries", REQUESTERS),
    ("post", "/deliveries/1/cancel", REQUESTERS),
    ("post", "/deliveries/1/confirm-receipt", REQUESTERS),
    ("post", "/deliveries/1/approve", ("farmaceutico",)),
    ("post", "/robot/next-task", ("robo",)),
    ("post", "/robot/events", ("robo",)),
    ("post", "/robot/telemetry", ("robo",)),
    ("get", "/robot/estop", ("robo",)),
    ("post", "/robot/estop", ("admin", "farmaceutico")),
]
USERS = {"medico": "medico1", "enfermeiro": "enfermeiro1", "farmaceutico": "farmaceutico1", "admin": "admin", "robo": "robo"}


@pytest.mark.parametrize("method, path, allowed", PROTECTED)
def test_role_matrix(client, auth, method, path, allowed):
    assert client.request(method, path, json={}).status_code == 401
    for role in Role:
        if role.value not in allowed:
            status = client.request(method, path, json={}, headers=auth(USERS[role.value])).status_code
            assert status == 403, f"{role.value} em {method.upper()} {path} deveria levar 403, levou {status}"
```

- [ ] **Step 2: Rodar e ver falhar.** Comando: `cd backend && python -m pytest tests/test_security_hardening.py -q`. Resultado esperado: pelo menos `test_the_role_in_the_token_must_match_the_users_current_role` falha (`assert 200 == 401`); `test_a_non_numeric_subject_is_401_not_500` e `test_the_server_refuses_to_start_with_a_short_secret` também.

- [ ] **Step 3: Implementar.** Replace `backend/app/deps.py`:

```python
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from app.db import get_session
from app.models import Role, User
from app.security import decode_token

bearer = HTTPBearer(auto_error=False)


def user_from_token(token: str, session: Session) -> User | None:
    """O usuário dono do token, ou None se o token for inválido, expirado ou de usuário que não existe."""
    try:
        claims = decode_token(token)
        user = session.get(User, int(claims["sub"]))
    except (jwt.PyJWTError, TypeError, ValueError):  # assinatura/algoritmo/claims ruins ou sub que não é um número
        return None
    if user is None or user.role.value != claims["role"]:  # o papel do token precisa ser o papel atual do usuário
        return None
    return user


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    session: Session = Depends(get_session),
) -> User:
    if creds is None:
        raise HTTPException(status_code=401, detail="Faça login para continuar.")
    user = user_from_token(creds.credentials, session)
    if user is None:
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada. Entre de novo.")
    return user


def require_roles(*roles: Role):
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Seu perfil não tem permissão para isso.")
        return user

    return checker
```

Replace `backend/app/main.py`:

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlmodel import Session

from app.config import settings
from app.db import create_db, engine
from app.errors import install as install_error_handlers
from app.events import AuditLog, LowStockAlert, events
from app.routers import auth, catalog, deliveries, delivery_actions, estop, movements, robot, telemetry
from app.seed import seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    if len(settings.jwt_secret) < 32:
        raise RuntimeError("GERALDO_JWT_SECRET precisa ter pelo menos 32 caracteres. Gere um: python -c 'import secrets; print(secrets.token_hex(32))'")
    if settings.auto_seed:
        create_db()
        with Session(engine) as session:
            seed(session)
    yield


events.add_observer(AuditLog())
events.add_observer(LowStockAlert())

app = FastAPI(title="G.E.R.A.L.D.O. API", version="0.1.0", lifespan=lifespan)
install_error_handlers(app)
app.include_router(auth.router)
app.include_router(catalog.router)
app.include_router(deliveries.router)
app.include_router(delivery_actions.router)
app.include_router(movements.router)
app.include_router(robot.router)
app.include_router(estop.router)
app.include_router(telemetry.router)


@app.get("/health", include_in_schema=False)
def health() -> dict:
    return {"status": "ok"}
```

- [ ] **Step 4: Rodar e ver passar.** Comando: `cd backend && python -m pytest -q`. Resultado esperado: `158 passed`. (O `InsecureKeyLengthWarning` do PyJWT no teste de HS512 é esperado.)

- [ ] **Step 5: Commit.**

```bash
git add backend/app/deps.py backend/app/main.py backend/tests/test_security_hardening.py
git commit -m "feat(backend): JWT confere papel e sub, matriz de papeis e segredo minimo" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 18: Senha do robô, CORS, logs do servidor e documentação do backend

**Files:**
- Modify: `backend/app/config.py`, `backend/app/seed.py`, `backend/app/main.py`, `backend/AGENTS.md`
- Test: `backend/tests/test_environment_config.py`

**Interfaces:**
- Consumes: `settings`, `seed`, `DEMO_USERS`, `AuditLog`, `LowStockAlert` (Tarefas 2, 7 e 10).
- Produces: `settings.robot_password` (de `GERALDO_ROBOT_PASSWORD`; `None` se vazia) e `settings.cors_origins` (de `GERALDO_CORS_ORIGINS`, separadas por vírgula; padrão `http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173`, ou seja, o Vite em desenvolvimento e em preview). **Decisão:** o usuário `robo` do seed usa `GERALDO_ROBOT_PASSWORD` quando ela existe; sem ela, usa a mesma `GERALDO_DEMO_PASSWORD` dos outros (como diz `robot-protocol.md`, seção 1). O dispatcher e o `mock_robot.py` leem a mesma variável. CORS só para essas origens, métodos `GET` e `POST`, cabeçalhos `Authorization` e `Content-Type`. `configure_logging()` põe um handler no logger `geraldo` em `INFO`, para a trilha de auditoria e os alertas de estoque baixo aparecerem no terminal do `uvicorn`. Um banco `geraldo.db` já existente **não** troca a senha do `robo`: apague o arquivo (ou use outro `GERALDO_DATABASE_URL`) para semear de novo.

- [ ] **Step 1: Escrever o teste.** Create `backend/tests/test_environment_config.py`:

```python
from sqlmodel import Session, select

from app.config import Settings, settings
from app.db import create_db, make_engine
from app.models import User
from app.security import verify_password
from app.seed import seed
from tests.conftest import FIXTURES, PASSWORD


def seeded_users(monkeypatch, robot_password):
    monkeypatch.setattr(settings, "robot_password", robot_password)
    engine = make_engine("sqlite://")
    create_db(engine)
    with Session(engine) as session:
        seed(session, FIXTURES)
        return {u.username: u.password_hash for u in session.exec(select(User)).all()}


def test_robot_user_has_its_own_password_when_one_is_configured(monkeypatch):
    hashes = seeded_users(monkeypatch, "senha-do-robo")
    assert verify_password("senha-do-robo", hashes["robo"]) and not verify_password(PASSWORD, hashes["robo"])
    assert verify_password(PASSWORD, hashes["medico1"])  # os outros seguem com a senha de demonstração


def test_robot_user_falls_back_to_the_demo_password(monkeypatch):
    hashes = seeded_users(monkeypatch, None)
    assert verify_password(PASSWORD, hashes["robo"])


def test_settings_read_the_environment(monkeypatch):
    monkeypatch.setenv("GERALDO_ROBOT_PASSWORD", "x-robo")
    monkeypatch.setenv("GERALDO_CORS_ORIGINS", "http://a.test, http://b.test")
    monkeypatch.setenv("GERALDO_OFF_PEAK_HOURS", "9-17")
    fresh = Settings()
    assert fresh.robot_password == "x-robo"
    assert fresh.cors_origins == ["http://a.test", "http://b.test"]
    assert (fresh.off_peak_start, fresh.off_peak_end) == (9, 17)


def test_cors_allows_the_web_dev_server_and_nobody_else(client):
    allowed = client.options("/me", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET", "Access-Control-Request-Headers": "authorization"})
    assert allowed.status_code == 200 and allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    refused = client.options("/me", headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in refused.headers


def test_audit_and_stock_logs_have_a_handler_at_info_level():
    import logging

    log = logging.getLogger("geraldo")
    assert log.handlers and log.level == logging.INFO
```

- [ ] **Step 2: Rodar e ver falhar.** Comando: `cd backend && python -m pytest tests/test_environment_config.py -q`. Resultado esperado: `AttributeError: ... has no attribute 'robot_password'`.

- [ ] **Step 3: Implementar.** Replace `backend/app/config.py`:

```python
import os
import secrets


class Settings:
    """Configuração lida do ambiente. Atributos mutáveis para os testes."""

    def __init__(self) -> None:
        self.database_url = os.environ.get("GERALDO_DATABASE_URL", "sqlite:///./geraldo.db")
        # sem segredo no ambiente, gera um aleatório (tokens deixam de valer ao reiniciar)
        self.jwt_secret = os.environ.get("GERALDO_JWT_SECRET") or secrets.token_hex(32)
        self.jwt_minutes = int(os.environ.get("GERALDO_JWT_MINUTES", "60"))
        self.demo_password = os.environ.get("GERALDO_DEMO_PASSWORD", "demo-only-change-me")
        # senha do usuário "robo" no seed; sem ela, vale a mesma senha de demonstração dos outros usuários
        self.robot_password = os.environ.get("GERALDO_ROBOT_PASSWORD") or None
        self.password_iterations = 200_000
        self.auto_seed = os.environ.get("GERALDO_AUTO_SEED", "1") == "1"
        # origens (separadas por vírgula) que o navegador pode usar para chamar a API: o Vite em desenvolvimento e em preview
        default_origins = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173"
        self.cors_origins = [o.strip() for o in os.environ.get("GERALDO_CORS_ORIGINS", default_origins).split(",") if o.strip()]
        # janela de baixo pico, "início-fim" em horas (padrão 20-6; "0-24" libera a rotina o dia todo, útil na demo)
        self.off_peak_start, self.off_peak_end = (int(h) for h in os.environ.get("GERALDO_OFF_PEAK_HOURS", "20-6").split("-"))


settings = Settings()
```

Replace `backend/app/seed.py`:

```python
import json
from pathlib import Path

from sqlmodel import Session, select

from app.config import settings
from app.models import Item, Location, Role, Stock, User
from app.security import hash_password

SEEDS = Path(__file__).resolve().parent.parent / "seeds"

# (username, papel, local padrão). Todos usam GERALDO_DEMO_PASSWORD (o robô, GERALDO_ROBOT_PASSWORD se existir); só para demonstração.
DEMO_USERS = [
    ("medico1", Role.medico, "consultorio1"),
    ("medico2", Role.medico, "consultorio2"),
    ("enfermeiro1", Role.enfermeiro, "enfermaria214"),
    ("farmaceutico1", Role.farmaceutico, "farmacia"),
    ("admin", Role.admin, None),
    ("robo", Role.robo, None),
]


def _password_for(role: Role) -> str:
    if role == Role.robo and settings.robot_password:
        return settings.robot_password
    return settings.demo_password


def _load(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def seed(session: Session, seeds_dir: Path = SEEDS) -> None:
    """Insere o que falta; nunca sobrescreve estoque nem usuários existentes."""
    for loc in _load(seeds_dir / "locais.json"):
        if session.get(Location, loc["id"]) is None:
            session.add(Location(**loc))
    for item in _load(seeds_dir / "itens.json"):
        if session.get(Item, item["id"]) is None:
            session.add(Item(**item))
    session.commit()
    for st in _load(seeds_dir / "estoque.json"):
        if session.get(Stock, (st["location_id"], st["item_id"])) is None:
            session.add(Stock(**st))
    for username, role, local_id in DEMO_USERS:
        if session.exec(select(User).where(User.username == username)).first() is None:
            session.add(User(username=username, password_hash=hash_password(_password_for(role)), role=role, local_id=local_id))
    session.commit()
```

Replace `backend/app/main.py`:

```python
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session

from app.config import settings
from app.db import create_db, engine
from app.errors import install as install_error_handlers
from app.events import AuditLog, LowStockAlert, events
from app.routers import auth, catalog, deliveries, delivery_actions, estop, movements, robot, telemetry
from app.seed import seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    if len(settings.jwt_secret) < 32:
        raise RuntimeError("GERALDO_JWT_SECRET precisa ter pelo menos 32 caracteres. Gere um: python -c 'import secrets; print(secrets.token_hex(32))'")
    if settings.auto_seed:
        create_db()
        with Session(engine) as session:
            seed(session)
    yield


def configure_logging() -> None:
    """A trilha de auditoria e os alertas de estoque saem no terminal do servidor (o uvicorn só configura o log dele)."""
    log = logging.getLogger("geraldo")
    if not log.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s:     [%(name)s] %(message)s"))
        log.addHandler(handler)
        log.setLevel(logging.INFO)


configure_logging()
events.add_observer(AuditLog())
events.add_observer(LowStockAlert())

app = FastAPI(title="G.E.R.A.L.D.O. API", version="0.1.0", lifespan=lifespan)
install_error_handlers(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(auth.router)
app.include_router(catalog.router)
app.include_router(deliveries.router)
app.include_router(delivery_actions.router)
app.include_router(movements.router)
app.include_router(robot.router)
app.include_router(estop.router)
app.include_router(telemetry.router)


@app.get("/health", include_in_schema=False)
def health() -> dict:
    return {"status": "ok"}
```

- [ ] **Step 4: Atualizar `backend/AGENTS.md`.** Troque a linha

```
- **Observer:** eventos de entrega e de estoque baixo entram na semana 2.
```

por

```
- **Observer:** `app/events.py` (`Subject`, `AuditLog`, `LowStockAlert`) avisa cada mudança de entrega, de saldo e da emergência; `app/telemetry.py` (`TelemetryHub`) alimenta o WebSocket `/ws/telemetry`, que recebe o token em `?token=<JWT>` (o navegador não manda cabeçalho no WebSocket).
- **Fluxo do estoque:** criar entrega faz `RESERVA` na origem; confirmar o recebimento faz `BAIXA` na origem e `CREDITO` no destino; cancelar ou falhar faz `ESTORNO`. Só `app/movements.py` mexe no saldo.
- **Hora injetada:** `app/clock.py` (`Clock`, `OffPeakWindow`); a `rotina` só sai da fila das 20h às 6h (veja `GERALDO_OFF_PEAK_HOURS`).
```

E troque a última linha da seção "Variáveis de ambiente" (a que começa com `` `GERALDO_DATABASE_URL` ``) por

```
`GERALDO_DATABASE_URL`, `GERALDO_JWT_SECRET` (mínimo de 32 caracteres), `GERALDO_JWT_MINUTES`, `GERALDO_DEMO_PASSWORD` (senha dos usuários de demonstração), `GERALDO_ROBOT_PASSWORD` (senha do usuário `robo`; sem ela vale a `GERALDO_DEMO_PASSWORD`), `GERALDO_AUTO_SEED`, `GERALDO_CORS_ORIGINS` (origens do navegador, separadas por vírgula; padrão: o Vite em `localhost:5173` e `4173`) e `GERALDO_OFF_PEAK_HOURS` (janela de baixo pico da rotina, `inicio-fim` em horas; padrão `20-6`; `0-24` libera o dia todo na demonstração).
```

- [ ] **Step 5: Rodar e ver passar.** Comando: `cd backend && python -m pytest -q`. Resultado esperado: `163 passed`. Depois, na raiz da worktree: `python3 -m pytest tools -q`. Resultado esperado: tudo verde (o teste de `AGENTS.md` exige que o arquivo continue com o link para `padroes-de-projeto.md`).

- [ ] **Step 6: Commit.**

```bash
git add backend/app/config.py backend/app/seed.py backend/app/main.py backend/AGENTS.md backend/tests/test_environment_config.py
git commit -m "feat(backend): senha propria do robo, CORS, logs de auditoria e AGENTS.md" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 19: Teste de contrato de cada resposta (`backend/tests/test_contract.py`)

Substitui a Task 2 do plano do Pedro (`2026-11-05-semana1-pedro-qualidade.md`, linhas 186 a 279), que só comparava rotas e códigos de sucesso e tinha uma lista `PENDING`. Agora todas as operações existem, e o teste valida o corpo de cada resposta.

**Files:**
- Create: `backend/tests/test_contract.py`
- Modify: `backend/requirements.txt`

**Interfaces:**
- Consumes: `docs/contracts/openapi.yaml` (com `/robot/estop` e `EstopState`, do plano 1), `app.main.app`, `get_hub`, `get_estop`, fixtures `client` e `auth`.
- Produces: o teste falha se (a) o backend expõe uma operação fora do contrato ou deixa de expor uma do contrato, (b) os códigos de sucesso divergem, (c) alguma resposta do roteiro tem status não declarado no contrato ou corpo que não bate com o schema (campo a mais ou a menos, tipo, enum, nulo, limite), (d) o roteiro deixa de chamar alguma operação ou algum código de sucesso do contrato, (e) o quadro do WebSocket não bate com o schema `Telemetry`. O OpenAPI 3.0 é convertido para JSON Schema (resolve `$ref`, trata `nullable`, proíbe propriedades que o contrato não lista).

- [ ] **Step 1: Conferir o contrato do plano 1.** Comando (na raiz da worktree): `grep -c "estop" docs/contracts/openapi.yaml`. Resultado esperado: um número maior que zero. Se for `0`, pare: o plano 1 não foi aplicado nesta branch (contrato primeiro; avise o líder).

- [ ] **Step 2: Acrescentar a dependência.** Acrescente uma linha ao fim de `backend/requirements.txt` e instale:

```
jsonschema>=4
```

Comando: `cd backend && pip install -r requirements.txt`.

- [ ] **Step 3: Escrever o teste.** Create `backend/tests/test_contract.py`:

```python
"""Teste de contrato: o backend responde o que docs/contracts/openapi.yaml promete.

1. As operações do contrato e as do backend são as mesmas, com os mesmos códigos de sucesso.
2. Um roteiro chama CADA operação (sucesso e erros) e valida o status e o corpo de cada resposta
   contra o schema do contrato (campos a mais ou a menos, tipos, enums, nulos e limites).
"""
import re
from pathlib import Path

import jsonschema
import pytest
import yaml

from app.estop import EstopStore, get_estop
from app.main import app
from app.telemetry import TelemetryHub, get_hub
from tests.conftest import PASSWORD

CONTRACT_FILE = Path(__file__).resolve().parents[2] / "docs" / "contracts" / "openapi.yaml"
SPEC = yaml.safe_load(CONTRACT_FILE.read_text(encoding="utf-8"))
METHODS = {"get", "post", "put", "delete", "patch"}


def norm(path: str) -> str:
    """Compara rotas ignorando o nome do parâmetro de caminho ({id} x {delivery_id})."""
    return re.sub(r"\{[^}]+\}", "{}", path)


def operations(spec: dict) -> dict:
    return {(m, norm(p)): op for p, ops in spec["paths"].items() for m, op in ops.items() if m in METHODS}


def success_codes(op: dict) -> list[str]:
    return sorted(str(code) for code in op["responses"] if str(code).startswith("2"))


CONTRACT = operations(SPEC)


def to_jsonschema(node, strict: bool = True):
    """OpenAPI 3.0 -> JSON Schema: resolve $ref, trata nullable e proíbe campos que o contrato não lista."""
    if isinstance(node, list):
        return [to_jsonschema(item, strict) for item in node]
    if not isinstance(node, dict):
        return node
    if "$ref" in node:
        return to_jsonschema(resolve(node["$ref"]), strict)
    out = {}
    for key, value in node.items():
        if key in ("nullable", "example", "description"):
            continue
        if key == "allOf":  # o RobotTask soma campos ao Delivery: cada parte, sozinha, não pode ser estrita
            out[key] = [to_jsonschema(part, strict=False) for part in value]
        elif key == "properties":
            out[key] = {name: to_jsonschema(child) for name, child in value.items()}
        elif key == "items":
            out[key] = to_jsonschema(value)
        else:
            out[key] = value
    if node.get("nullable"):
        out["type"] = [out["type"], "null"]
        if "enum" in out:
            out["enum"] = [*out["enum"], None]
    if strict and "properties" in node and "allOf" not in node:
        out["additionalProperties"] = False
    return out


def resolve(ref: str) -> dict:
    node = SPEC
    for part in ref.lstrip("#/").split("/"):
        node = node[part]
    return node


def response_schema(op: dict, status: int):
    declared = op["responses"].get(str(status)) or op["responses"].get(status)
    assert declared is not None, f"o contrato não declara o status {status} (declarados: {sorted(map(str, op['responses']))})"
    if "$ref" in declared:
        declared = resolve(declared["$ref"])
    content = declared.get("content", {}).get("application/json")
    return to_jsonschema(content["schema"]) if content else None


class Probe:
    """Faz a chamada, confere o status esperado e valida o corpo contra o contrato."""

    def __init__(self, client, auth) -> None:
        self._client, self._auth = client, auth
        self.seen: set[tuple[str, str, int]] = set()

    def __call__(self, method: str, template: str, *, expect: int, as_: str | None = None, json=None, params=None, **path):
        url = template.format(**path)
        response = self._client.request(method, url, json=json, params=params, headers=self._auth(as_) if as_ else {})
        assert response.status_code == expect, f"{method.upper()} {url}: esperado {expect}, veio {response.status_code}: {response.text}"
        schema = response_schema(CONTRACT[(method, norm(template))], expect)
        if expect == 204:
            assert response.content == b"", f"{method.upper()} {url}: o contrato prevê 204 sem corpo, mas veio {response.text!r}"
        else:  # resposta sem schema próprio no contrato (ex.: o 422 do telemetry) segue o schema Error
            jsonschema.Draft7Validator(schema or to_jsonschema(SPEC["components"]["schemas"]["Error"])).validate(response.json())
        self.seen.add((method, norm(template), expect))
        return response


def test_the_backend_exposes_exactly_the_contract_operations():
    implemented = operations(app.openapi())
    assert set(CONTRACT) - set(implemented) == set(), "operações do contrato que o backend não tem"
    assert set(implemented) - set(CONTRACT) == set(), "operações do backend que não estão no contrato"


def test_success_status_codes_follow_the_contract():
    implemented = operations(app.openapi())
    for key, op in CONTRACT.items():
        assert success_codes(implemented[key]) == success_codes(op), key


@pytest.fixture
def fresh_state(client):
    hub, estop = TelemetryHub(), EstopStore()
    app.dependency_overrides[get_hub] = lambda: hub
    app.dependency_overrides[get_estop] = lambda: estop
    yield
    app.dependency_overrides.pop(get_hub, None)
    app.dependency_overrides.pop(get_estop, None)


MEDIA = {"origin_id": "farmacia", "items": [{"item_id": "dipirona-500mg", "quantity": 10}], "priority": "media"}
CRITICA = {"origin_id": "banco_sangue", "items": [{"item_id": "bolsa-sangue-o-neg", "quantity": 2}], "priority": "critica"}
TELEMETRY = {"robot_state": "A_CAMINHO", "pose": {"x": 14.2, "y": 28.9, "yaw": 0.0}, "battery": 99.1, "delivery_id": 7,
             "route": [{"x": 14.2, "y": 28.9}], "obstacles": [{"x": 18.0, "y": 28.9, "radius": 0.4}]}


def event(delivery_id: int, name: str) -> dict:
    return {"delivery_id": delivery_id, "event": name}


def test_every_response_matches_the_contract(client, auth, fresh_state):
    api = Probe(client, auth)

    api("post", "/auth/login", json={"username": "medico1", "password": PASSWORD}, expect=200)
    api("post", "/auth/login", json={"username": "medico1", "password": "errada"}, expect=401)
    api("get", "/me", as_="medico1", expect=200)
    api("get", "/me", expect=401)
    api("get", "/locations", as_="medico1", expect=200)
    api("get", "/locations", expect=401)
    api("get", "/stock", as_="medico1", expect=200)
    api("get", "/stock", as_="medico1", params={"location_id": "farmacia"}, expect=200)
    api("get", "/stock", expect=401)

    # criar, listar e consultar
    media = api("post", "/deliveries", as_="medico1", json=MEDIA, expect=201).json()["id"]
    api("post", "/deliveries", as_="medico1", json={**MEDIA, "items": [{"item_id": "dipirona-500mg", "quantity": 9999}]}, expect=409)
    api("post", "/deliveries", as_="medico1", json={**MEDIA, "items": []}, expect=422)
    api("post", "/deliveries", as_="robo", json=MEDIA, expect=403)
    api("post", "/deliveries", json=MEDIA, expect=401)
    api("get", "/deliveries", as_="medico1", expect=200)
    api("get", "/deliveries", expect=401)
    api("get", "/deliveries/{id}", as_="medico1", id=media, expect=200)
    api("get", "/deliveries/{id}", as_="robo", id=media, expect=200)
    api("get", "/deliveries/{id}", as_="medico1", id=9999, expect=404)
    api("get", "/deliveries/{id}", id=media, expect=401)

    # assinatura dupla da crítica
    critica = api("post", "/deliveries", as_="medico1", json=CRITICA, expect=201).json()
    assert critica["status"] == "PENDENTE_APROVACAO"
    api("post", "/deliveries/{id}/approve", as_="medico1", id=critica["id"], expect=403)
    api("post", "/deliveries/{id}/approve", as_="farmaceutico1", id=9999, expect=404)
    api("post", "/deliveries/{id}/approve", id=critica["id"], expect=401)
    assert api("post", "/deliveries/{id}/approve", as_="farmaceutico1", id=critica["id"], expect=200).json()["status"] == "NA_FILA"
    api("post", "/deliveries/{id}/approve", as_="farmaceutico1", id=critica["id"], expect=409)

    # cancelar
    to_cancel = api("post", "/deliveries", as_="medico2", json=MEDIA, expect=201).json()["id"]
    api("post", "/deliveries/{id}/cancel", as_="robo", id=to_cancel, expect=403)
    api("post", "/deliveries/{id}/cancel", id=to_cancel, expect=401)
    api("post", "/deliveries/{id}/cancel", as_="admin", id=9999, expect=404)
    assert api("post", "/deliveries/{id}/cancel", as_="medico2", id=to_cancel, expect=200).json()["status"] == "CANCELADA"
    api("post", "/deliveries/{id}/cancel", as_="medico2", id=to_cancel, expect=409)

    # o robô: fila (crítica antes da média), eventos
    api("post", "/robot/next-task", as_="medico1", expect=403)
    api("post", "/robot/next-task", expect=401)
    first = api("post", "/robot/next-task", as_="robo", expect=200).json()
    second = api("post", "/robot/next-task", as_="robo", expect=200).json()
    assert (first["id"], second["id"]) == (critica["id"], media)
    assert second["origin_waypoint"] == "farmacia_balcao" and second["dest_waypoint"] == "cons1_entrega"
    api("post", "/robot/next-task", as_="robo", expect=204)

    api("post", "/robot/events", as_="robo", json=event(media, "LOADED"), expect=200)
    api("post", "/robot/events", as_="robo", json=event(media, "ARRIVED"), expect=200)
    api("post", "/robot/events", as_="robo", json=event(media, "ARRIVED"), expect=409)
    api("post", "/robot/events", as_="robo", json=event(9999, "LOADED"), expect=404)
    api("post", "/robot/events", as_="medico1", json=event(media, "LOADED"), expect=403)
    api("post", "/robot/events", json=event(media, "LOADED"), expect=401)
    api("post", "/robot/events", as_="robo", json={**event(critica["id"], "FAILED"), "reason": "não chegou à origem"}, expect=200)

    # confirmar o recebimento
    api("post", "/deliveries/{id}/confirm-receipt", id=media, expect=401)
    api("post", "/deliveries/{id}/confirm-receipt", as_="robo", id=media, expect=403)
    api("post", "/deliveries/{id}/confirm-receipt", as_="medico1", id=9999, expect=404)
    assert api("post", "/deliveries/{id}/confirm-receipt", as_="medico1", id=media, expect=200).json()["status"] == "ENTREGUE"
    api("post", "/deliveries/{id}/confirm-receipt", as_="medico1", id=media, expect=409)
    api("post", "/robot/events", as_="robo", json=event(media, "UNLOCKED"), expect=200)

    # histórico
    api("get", "/movements", as_="admin", expect=200)
    api("get", "/movements", as_="admin", params={"delivery_id": media, "location_id": "farmacia"}, expect=200)
    api("get", "/movements", expect=401)

    # telemetria e emergência
    api("post", "/robot/telemetry", as_="robo", json=TELEMETRY, expect=204)
    api("post", "/robot/telemetry", as_="robo", json={**TELEMETRY, "battery": 150}, expect=422)
    api("post", "/robot/telemetry", as_="medico1", json=TELEMETRY, expect=403)
    api("post", "/robot/telemetry", json=TELEMETRY, expect=401)
    assert api("get", "/telemetry", as_="medico1", expect=200).json()["robot_state"] == "A_CAMINHO"
    api("get", "/telemetry", expect=401)

    api("post", "/robot/estop", as_="admin", json={"active": True}, expect=204)
    api("post", "/robot/estop", as_="admin", json={"active": "talvez"}, expect=422)
    api("post", "/robot/estop", as_="medico1", json={"active": True}, expect=403)
    api("post", "/robot/estop", json={"active": True}, expect=401)
    assert api("get", "/robot/estop", as_="robo", expect=200).json() == {"active": True}
    api("get", "/robot/estop", as_="medico1", expect=403)
    api("get", "/robot/estop", expect=401)

    exercised = {(method, path) for method, path, _ in api.seen}
    assert exercised == set(CONTRACT), f"operações que o roteiro não chamou: {set(CONTRACT) - exercised}"
    declared = {(m, p, int(code)) for (m, p), op in CONTRACT.items() for code in success_codes(op)}
    assert declared <= api.seen, f"códigos de sucesso que o roteiro não viu: {declared - api.seen}"


def test_the_websocket_pushes_the_telemetry_schema(client, auth, fresh_state):
    schema = to_jsonschema(SPEC["components"]["schemas"]["Telemetry"])
    token = auth("medico1")["Authorization"].removeprefix("Bearer ")
    with client.websocket_connect(f"/ws/telemetry?token={token}") as ws:
        jsonschema.Draft7Validator(schema).validate(ws.receive_json())
        client.post("/robot/telemetry", json=TELEMETRY, headers=auth("robo"))
        pushed = ws.receive_json()
        jsonschema.Draft7Validator(schema).validate(pushed)
        assert pushed["robot_state"] == "A_CAMINHO"
```

- [ ] **Step 4: Rodar.** Comando: `cd backend && python -m pytest tests/test_contract.py -q`. Resultado esperado: `4 passed` (não há "ver falhar" aqui: o teste descreve o que as tarefas 3 a 15 já fizeram). Se falhar, leia a mensagem: "operações do backend que não estão no contrato" é rota fora do contrato (avise o líder: ou vira PR no contrato ou a rota sai); "o contrato não declara o status N" é resposta que o contrato não prevê; erro de `jsonschema` mostra o campo que diverge.

- [ ] **Step 5: Provar que o teste pega problemas (mutação rápida).** (a) Em `backend/app/routers/deliveries.py` troque `status_code=201` por `status_code=200`: `python -m pytest tests/test_contract.py -q` deve falhar em `test_success_status_codes_follow_the_contract` e em `test_every_response_matches_the_contract`. Desfaça com `git checkout backend/app/routers/deliveries.py`. (b) Em `backend/app/schemas.py`, na classe `MovementOut`, acrescente a linha `extra: int = 0` depois de `created_at`: o teste deve falhar com `Additional properties are not allowed ('extra' was unexpected)`. Desfaça com `git checkout backend/app/schemas.py`.

- [ ] **Step 6: Rodar tudo.** Comando: `cd backend && python -m pytest -q`. Resultado esperado: `167 passed`.

- [ ] **Step 7: Commit.**

```bash
git add backend/tests/test_contract.py backend/requirements.txt
git commit -m "test(backend): teste de contrato de cada resposta contra o openapi.yaml" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 20: Robô de mentira (`tools/mock_robot.py`)

Substitui a Task 3 do plano do Pedro (`2026-11-05-semana1-pedro-qualidade.md`, linhas 283 a 509): segue a sequência atual de `docs/contracts/robot-protocol.md` (o `UNLOCKED` só depois do `ENTREGUE`, telemetria, tolerância ao `409`).

**Files:**
- Create: `tools/mock_robot.py`, `tools/tests/test_mock_robot.py`, `backend/tests/test_mock_robot_integration.py`

**Interfaces:**
- Consumes: a API do backend (`POST /auth/login`, `POST /robot/next-task`, `POST /robot/events`, `POST /robot/telemetry`, `GET /deliveries/{id}`).
- Produces: `tools.mock_robot.MockRobot(client: httpx.Client, username="robo", password="")` com `login()`, `next_task() -> dict | None`, `report(delivery_id, event, reason=None) -> dict | None` (o `409` só é registrado e devolve `None`), `send_telemetry(state, delivery_id=None, progress=0.0)`, `delivery_status(delivery_id) -> str`, `wait_for_receipt(delivery_id, poll_seconds, timeout_seconds, sleep=time.sleep) -> str` (`ENTREGUE`, `CANCELADA`, `FALHOU` ou `TIMEOUT`) e `run_once(travel_seconds=0.0, report=False, sleep=time.sleep, poll_seconds=2.0, receipt_timeout=300.0) -> dict | None`. Sem `report`, só pega a tarefa e espera o trajeto. Com `report`: telemetria `A_CAMINHO`, `CARREGANDO`, `A_CAMINHO`, `CHEGOU`, `AGUARDANDO_RETIRADA`, `VOLTANDO`, `IDLE`; eventos `LOADED`, `ARRIVED`, espera do `ENTREGUE` consultando `GET /deliveries/{id}`, e então `UNLOCKED` (ou `FAILED` com `entrega cancelada`, `entrega falhou` ou `recebimento não confirmado a tempo`). CLI: `python tools/mock_robot.py --api http://127.0.0.1:8000 --travel 5 --poll 2 --timeout 300 [--report] [--once]`, com a senha em `GERALDO_ROBOT_PASSWORD` (ou `GERALDO_DEMO_PASSWORD`).
- O teste unitário usa `httpx` e é **pulado** no Python do sistema (que não tem `httpx`); ele roda no venv do backend.

- [ ] **Step 1: Escrever os testes.** Create `tools/tests/test_mock_robot.py`:

```python
import json

import pytest

# O Python do sistema (testes da raiz) não tem httpx: o arquivo é pulado lá e roda no venv do backend.
httpx = pytest.importorskip("httpx")

from tools.mock_robot import MockRobot  # noqa: E402

TASK = {"id": 7, "origin_waypoint": "farmacia_balcao", "dest_waypoint": "cons1_entrega", "status": "EM_ROTA"}


class FakeBackend:
    """Backend de mentira (LSP: obedece ao mesmo contrato). Anota as chamadas e responde o que foi combinado."""

    def __init__(self, tasks, statuses=("ENTREGUE",), event_status=200) -> None:
        self.tasks, self.statuses, self.event_status = list(tasks), list(statuses), event_status
        self.calls: list[tuple[str, str, dict | None]] = []
        self.client = httpx.Client(transport=httpx.MockTransport(self.handle), base_url="http://api.test")

    def handle(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content) if request.content else None
        self.calls.append((request.method, request.url.path, body, request.headers.get("authorization")))
        path = request.url.path
        if path == "/auth/login":
            if body["password"] != "certa":
                return httpx.Response(401, json={"detail": "Usuário ou senha incorretos. Tente de novo."})
            return httpx.Response(200, json={"access_token": "tok123", "token_type": "bearer"})
        if path == "/robot/next-task":
            return httpx.Response(200, json=self.tasks.pop(0)) if self.tasks else httpx.Response(204)
        if path == "/robot/events":
            if self.event_status == 409:
                return httpx.Response(409, json={"detail": "Evento fora de hora."})
            return httpx.Response(200, json={"id": body["delivery_id"]})
        if path == "/robot/telemetry":
            return httpx.Response(204)
        if path.startswith("/deliveries/"):
            status = self.statuses.pop(0) if len(self.statuses) > 1 else self.statuses[0]
            return httpx.Response(200, json={"id": 7, "status": status})
        return httpx.Response(404)

    def events(self) -> list[str]:
        return [c[2]["event"] for c in self.calls if c[1] == "/robot/events"]

    def telemetry_states(self) -> list[str]:
        return [c[2]["robot_state"] for c in self.calls if c[1] == "/robot/telemetry"]

    def paths(self) -> list[str]:
        return [c[1] for c in self.calls]


def robot_for(backend, password="certa") -> MockRobot:
    robot = MockRobot(backend.client, "robo", password)
    robot.login()
    return robot


def test_login_sets_the_bearer_token():
    backend = FakeBackend([])
    robot_for(backend).next_task()
    assert backend.calls[-1][3] == "Bearer tok123"


def test_login_failure_raises_a_clear_error():
    with pytest.raises(RuntimeError, match="Login do robô falhou"):
        MockRobot(FakeBackend([]).client, "robo", "errada").login()


def test_next_task_returns_none_when_the_queue_is_empty():
    assert robot_for(FakeBackend([])).next_task() is None
    assert robot_for(FakeBackend([])).run_once(sleep=lambda s: None) is None


def test_without_report_it_only_takes_the_task_and_waits_the_travel_time():
    backend, slept = FakeBackend([TASK]), []
    assert robot_for(backend).run_once(travel_seconds=4.5, sleep=slept.append) == TASK
    assert slept == [4.5]
    assert backend.paths() == ["/auth/login", "/robot/next-task"]


def test_report_follows_the_protocol_sequence_and_unlocks_only_after_entregue():
    backend, slept = FakeBackend([TASK], statuses=("AGUARDANDO_RECEBIMENTO", "AGUARDANDO_RECEBIMENTO", "ENTREGUE")), []
    robot_for(backend).run_once(travel_seconds=1.0, report=True, sleep=slept.append, poll_seconds=2.0)
    assert backend.events() == ["LOADED", "ARRIVED", "UNLOCKED"]
    assert backend.telemetry_states() == ["A_CAMINHO", "CARREGANDO", "A_CAMINHO", "CHEGOU", "AGUARDANDO_RETIRADA", "VOLTANDO", "IDLE"]
    paths = backend.paths()
    last_status_check = max(i for i, p in enumerate(paths) if p == "/deliveries/7")
    unlocked = max(i for i, c in enumerate(backend.calls) if c[1] == "/robot/events")
    assert unlocked > last_status_check  # UNLOCKED depois da consulta que viu o ENTREGUE
    assert slept == [1.0, 1.0, 2.0, 2.0, 1.0]  # trecho 1, trecho 2, duas esperas de 2 s, volta


def test_all_events_carry_the_delivery_id_and_telemetry_matches_the_contract_fields():
    backend = FakeBackend([TASK])
    robot_for(backend).run_once(report=True, sleep=lambda s: None)
    assert all(c[2]["delivery_id"] == 7 for c in backend.calls if c[1] == "/robot/events")
    telemetry = [c[2] for c in backend.calls if c[1] == "/robot/telemetry"]
    assert all(set(t) == {"robot_state", "pose", "battery", "delivery_id", "route", "obstacles"} for t in telemetry)
    assert all(0 <= t["battery"] <= 100 for t in telemetry)
    assert [t["delivery_id"] for t in telemetry] == [7, 7, 7, 7, 7, None, None]


@pytest.mark.parametrize("status, reason", [("CANCELADA", "entrega cancelada"), ("FALHOU", "entrega falhou")])
def test_it_reports_failure_when_the_delivery_is_cancelled_or_failed_while_waiting(status, reason):
    backend = FakeBackend([TASK], statuses=(status,))
    robot_for(backend).run_once(report=True, sleep=lambda s: None)
    assert backend.events() == ["LOADED", "ARRIVED", "FAILED"]
    failed = [c[2] for c in backend.calls if c[1] == "/robot/events"][-1]
    assert failed["reason"] == reason
    assert backend.telemetry_states()[-2:] == ["VOLTANDO", "IDLE"]  # volta à base mesmo assim


def test_it_gives_up_after_the_receipt_timeout():
    backend, slept = FakeBackend([TASK], statuses=("AGUARDANDO_RECEBIMENTO",)), []
    robot_for(backend).run_once(report=True, sleep=slept.append, poll_seconds=2.0, receipt_timeout=6.0)
    assert slept.count(2.0) == 3
    assert backend.events()[-1] == "FAILED"
    assert [c[2]["reason"] for c in backend.calls if c[1] == "/robot/events"][-1] == "recebimento não confirmado a tempo"


def test_a_409_on_an_event_is_tolerated():
    backend = FakeBackend([TASK], event_status=409)
    assert robot_for(backend).run_once(report=True, sleep=lambda s: None) == TASK
```

Create `backend/tests/test_mock_robot_integration.py` (o `TestClient` é um `httpx.Client`; o "solicitante" confirma o recebimento de dentro do `sleep` injetado, no momento em que o robô espera):

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest  # noqa: E402
from tools.mock_robot import MockRobot  # noqa: E402

from app.main import app  # noqa: E402
from app.telemetry import TelemetryHub, get_hub  # noqa: E402
from tests.conftest import PASSWORD  # noqa: E402

BODY = {"origin_id": "farmacia", "items": [{"item_id": "dipirona-500mg", "quantity": 3}], "priority": "media"}
POLL = 0.5


@pytest.fixture(autouse=True)
def fresh_hub(client):
    hub = TelemetryHub()
    app.dependency_overrides[get_hub] = lambda: hub
    yield
    app.dependency_overrides.pop(get_hub, None)


def test_mock_robot_delivers_end_to_end_against_the_real_api(client, auth):
    delivery_id = client.post("/deliveries", json=BODY, headers=auth("medico1")).json()["id"]
    robot = MockRobot(client, "robo", PASSWORD)  # o TestClient é um httpx.Client
    robot.login()
    confirmed = []

    def sleep(seconds: float) -> None:
        if seconds == POLL and not confirmed:  # o robô está esperando: o solicitante confirma o recebimento
            r = client.post(f"/deliveries/{delivery_id}/confirm-receipt", headers=auth("medico1"))
            assert r.status_code == 200, r.text
            confirmed.append(True)

    task = robot.run_once(report=True, sleep=sleep, poll_seconds=POLL)

    assert task["id"] == delivery_id and task["origin_waypoint"] == "farmacia_balcao" and task["dest_waypoint"] == "cons1_entrega"
    assert confirmed == [True]
    assert client.get(f"/deliveries/{delivery_id}", headers=auth("medico1")).json()["status"] == "ENTREGUE"
    stock = {s["location_id"]: s for s in client.get("/stock", headers=auth("medico1")).json() if s["item_id"] == "dipirona-500mg"}
    assert (stock["farmacia"]["quantity"], stock["farmacia"]["reserved"], stock["consultorio1"]["quantity"]) == (417, 0, 3)
    assert client.get("/telemetry", headers=auth("medico1")).json()["robot_state"] == "IDLE"
    assert robot.run_once(sleep=lambda s: None) is None  # fila vazia
```

- [ ] **Step 2: Rodar e ver falhar.** Comando (na raiz da worktree): `backend/.venv/bin/python -m pytest tools/tests/test_mock_robot.py -q`. Resultado esperado: erro de coleta `ModuleNotFoundError: No module named 'tools.mock_robot'`.

- [ ] **Step 3: Implementar.** Create `tools/mock_robot.py`:

```python
#!/usr/bin/env python3
"""Robô de mentira: faz o papel do geraldo_dispatcher contra o backend, sem Gazebo nem ROS.

Segue a sequência de docs/contracts/robot-protocol.md (seção 2):
next-task -> LOADED -> ARRIVED -> espera o solicitante confirmar (ENTREGUE) -> UNLOCKED -> volta à base.

Uso (o backend precisa estar de pé, e a senha é a do usuário "robo"):
  GERALDO_ROBOT_PASSWORD=... python tools/mock_robot.py --api http://127.0.0.1:8000 --travel 5 --report
Sem --report ele só pega a próxima tarefa e espera o tempo do trajeto (não manda eventos nem telemetria).
"""
import argparse
import os
import time

import httpx

BASE_POSE = (6.5, 26.5)  # valores de mentira: o robô "anda" 10 m em linha reta e volta
TRAVEL_METERS = 10.0


class MockRobot:
    def __init__(self, client: httpx.Client, username: str = "robo", password: str = "") -> None:
        self.client = client
        self.username = username
        self.password = password
        self._battery = 100.0

    def login(self) -> None:
        r = self.client.post("/auth/login", json={"username": self.username, "password": self.password})
        if r.status_code != 200:
            raise RuntimeError(f"Login do robô falhou ({r.status_code}): {r.text}")
        self.client.headers["Authorization"] = f"Bearer {r.json()['access_token']}"

    def next_task(self) -> dict | None:
        r = self.client.post("/robot/next-task")
        if r.status_code == 204:
            return None
        r.raise_for_status()
        return r.json()

    def report(self, delivery_id: int, event: str, reason: str | None = None) -> dict | None:
        """Manda o evento. O 409 (ex.: FAILED de uma entrega já cancelada) só é registrado, como faz o dispatcher."""
        r = self.client.post("/robot/events", json={"delivery_id": delivery_id, "event": event, "reason": reason})
        if r.status_code == 409:
            print(f"evento {event} recusado (409): {r.json().get('detail')}")
            return None
        r.raise_for_status()
        return r.json()

    def send_telemetry(self, state: str, delivery_id: int | None = None, progress: float = 0.0) -> None:
        self._battery = max(0.0, self._battery - 0.2)
        body = {
            "robot_state": state,
            "pose": {"x": BASE_POSE[0] + TRAVEL_METERS * progress, "y": BASE_POSE[1], "yaw": 0.0},
            "battery": round(self._battery, 1),
            "delivery_id": delivery_id,
            "route": [],
            "obstacles": [],
        }
        self.client.post("/robot/telemetry", json=body).raise_for_status()

    def delivery_status(self, delivery_id: int) -> str:
        r = self.client.get(f"/deliveries/{delivery_id}")
        r.raise_for_status()
        return r.json()["status"]

    def wait_for_receipt(self, delivery_id: int, poll_seconds: float, timeout_seconds: float, sleep=time.sleep) -> str:
        """Espera o status virar ENTREGUE. Devolve ENTREGUE, CANCELADA, FALHOU ou TIMEOUT."""
        waited = 0.0
        while True:
            try:
                status = self.delivery_status(delivery_id)
            except httpx.HTTPError:
                status = "AGUARDANDO_RECEBIMENTO"  # consulta que falha conta como "ainda não"
            if status in ("ENTREGUE", "CANCELADA", "FALHOU"):
                return status
            if waited >= timeout_seconds:
                return "TIMEOUT"
            sleep(poll_seconds)
            waited += poll_seconds

    def run_once(
        self,
        travel_seconds: float = 0.0,
        report: bool = False,
        sleep=time.sleep,
        poll_seconds: float = 2.0,
        receipt_timeout: float = 300.0,
    ) -> dict | None:
        task = self.next_task()
        if task is None:
            return None
        print(f"entrega {task['id']}: {task['origin_waypoint']} -> {task['dest_waypoint']}")
        if not report:
            sleep(travel_seconds)
            return task
        delivery_id = task["id"]
        self.send_telemetry("A_CAMINHO", delivery_id, 0.0)
        sleep(travel_seconds)
        self.send_telemetry("CARREGANDO", delivery_id, 0.0)
        self.report(delivery_id, "LOADED")
        self.send_telemetry("A_CAMINHO", delivery_id, 0.5)
        sleep(travel_seconds)
        self.send_telemetry("CHEGOU", delivery_id, 1.0)
        self.report(delivery_id, "ARRIVED")
        self.send_telemetry("AGUARDANDO_RETIRADA", delivery_id, 1.0)
        outcome = self.wait_for_receipt(delivery_id, poll_seconds, receipt_timeout, sleep)
        if outcome == "ENTREGUE":
            self.report(delivery_id, "UNLOCKED")  # a tampa só abre depois do ENTREGUE
        else:
            reason = {"CANCELADA": "entrega cancelada", "FALHOU": "entrega falhou"}.get(outcome, "recebimento não confirmado a tempo")
            self.report(delivery_id, "FAILED", reason)
        self.send_telemetry("VOLTANDO", None, 0.5)
        sleep(travel_seconds)
        self.send_telemetry("IDLE", None, 0.0)
        return task


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--api", default="http://127.0.0.1:8000")
    ap.add_argument("--user", default="robo")
    ap.add_argument("--travel", type=float, default=5.0, help="segundos de cada trecho do trajeto")
    ap.add_argument("--poll", type=float, default=2.0, help="segundos entre as consultas do status, esperando o recebimento")
    ap.add_argument("--timeout", type=float, default=300.0, help="segundos esperando o recebimento antes de falhar a entrega")
    ap.add_argument("--report", action="store_true", help="manda telemetria e os eventos LOADED, ARRIVED e UNLOCKED")
    ap.add_argument("--once", action="store_true", help="processa no máximo uma entrega e sai")
    a = ap.parse_args()
    password = os.environ.get("GERALDO_ROBOT_PASSWORD") or os.environ.get("GERALDO_DEMO_PASSWORD")
    if not password:
        raise SystemExit("Defina GERALDO_ROBOT_PASSWORD (ou GERALDO_DEMO_PASSWORD) com a senha do usuário do robô.")
    with httpx.Client(base_url=a.api, timeout=10) as client:
        robot = MockRobot(client, a.user, password)
        robot.login()
        while True:
            task = robot.run_once(a.travel, a.report, poll_seconds=a.poll, receipt_timeout=a.timeout)
            if a.once:
                break
            if task is None:
                time.sleep(2)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Rodar e ver passar.** Comandos: `backend/.venv/bin/python -m pytest tools/tests/test_mock_robot.py -q` (na raiz; esperado `10 passed`) e `cd backend && python -m pytest -q` (esperado `168 passed`, contando o teste de integração). Em seguida, na raiz, com o Python do sistema: `python3 -m pytest tools robot -q`. Esperado: tudo verde, com `test_mock_robot.py` pulado (`s`).

- [ ] **Step 5: Commit.**

```bash
git add tools/mock_robot.py tools/tests/test_mock_robot.py backend/tests/test_mock_robot_integration.py
git commit -m "feat(tools): robo de mentira segue o protocolo do robo (eventos, espera do ENTREGUE, telemetria)" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 21: Ponta a ponta com `uvicorn` de verdade e o robô de mentira

**Files:**
- Create: `backend/e2e_smoke.sh`

**Interfaces:**
- Consumes: tudo das tarefas 1 a 20 (servidor `uvicorn`, `tools/mock_robot.py`, `backend/.venv`, o pacote `websockets` que vem com `uvicorn[standard]`).
- Produces: `bash backend/e2e_smoke.sh` sobe o backend em `127.0.0.1:8000` com um banco SQLite temporário e senhas falsas (`demo-local-falsa` e `robo-local-falso`, só para este teste local), roda o robô de mentira contra ele e confere cada passo; termina com `E2E OK` (código 0) ou `E2E COM FALHAS` (código 1). Encerra o `uvicorn` por PID (`kill -9`), sem `pkill`.

- [ ] **Step 1: Criar o script.** Create `backend/e2e_smoke.sh`:

```bash
#!/usr/bin/env bash
# Teste de ponta a ponta com o servidor de verdade: sobe o uvicorn, roda o robô de mentira e confere
# pedido -> next-task -> eventos -> confirmar recebimento -> estoque (e assinatura dupla, emergência e WebSocket).
# Uso: bash backend/e2e_smoke.sh   (precisa de backend/.venv com as dependências e da porta 8000 livre)
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API=http://127.0.0.1:8000
FAIL=0
expect() {  # expect "<esperado>" "<obtido>" "<descrição>"
  if [ "$1" = "$2" ]; then echo "ok: $3: $2"; else echo "FALHOU: $3: esperado '$1', veio '$2'"; FAIL=1; fi
}
if ss -ltn | grep -qE ':8000\b'; then echo "A porta 8000 está ocupada por outro processo: pare aqui e avise (não mate o que não é seu)."; exit 1; fi

WORK="$(mktemp -d)"
cd "$ROOT/backend" && . .venv/bin/activate
export GERALDO_JWT_SECRET="$(python -c 'import secrets; print(secrets.token_hex(32))')"
export GERALDO_DEMO_PASSWORD="demo-local-falsa" GERALDO_ROBOT_PASSWORD="robo-local-falso"
export GERALDO_DATABASE_URL="sqlite:///$WORK/e2e.db"

uvicorn app.main:app --host 127.0.0.1 --port 8000 > "$WORK/uvicorn.log" 2>&1 &
UVICORN=$!
trap 'kill -9 $UVICORN 2>/dev/null' EXIT
for _ in $(seq 1 30); do curl -sf $API/health > /dev/null && break; sleep 0.5; done

token() { curl -s $API/auth/login -H 'content-type: application/json' -d "{\"username\":\"$1\",\"password\":\"$2\"}" | python -c 'import sys,json; print(json.load(sys.stdin)["access_token"])'; }
field() { python -c "import sys,json; print(json.load(sys.stdin)$1)"; }
MED=$(token medico1 "$GERALDO_DEMO_PASSWORD"); PHARM=$(token farmaceutico1 "$GERALDO_DEMO_PASSWORD"); ROBO=$(token robo "$GERALDO_ROBOT_PASSWORD")
auth() { echo "authorization: Bearer $1"; }
JSON='content-type: application/json'

echo "--- 1. pedido (media): farmacia -> consultorio1"
expect NA_FILA "$(curl -s $API/deliveries -H "$(auth $MED)" -H "$JSON" -d '{"origin_id":"farmacia","items":[{"item_id":"dipirona-500mg","quantity":5}],"priority":"media"}' | field '["status"]')" "status do pedido"

echo "--- 2. robô de mentira: next-task, telemetria, LOADED, ARRIVED, espera, UNLOCKED"
python "$ROOT/tools/mock_robot.py" --api $API --travel 1 --poll 1 --report --once > "$WORK/robot.log" 2>&1 &
ROBOT=$!
STATUS=""
for _ in $(seq 1 30); do
  STATUS=$(curl -s $API/deliveries/1 -H "$(auth $MED)" | field '["status"]')
  [ "$STATUS" = AGUARDANDO_RECEBIMENTO ] && break; sleep 1
done
expect AGUARDANDO_RECEBIMENTO "$STATUS" "o robô chegou e espera a confirmação"

echo "--- 3. o solicitante confirma o recebimento"
expect ENTREGUE "$(curl -s -X POST $API/deliveries/1/confirm-receipt -H "$(auth $MED)" | field '["status"]')" "status depois de confirmar"
wait $ROBOT; expect 0 "$?" "código de saída do robô"
expect "entrega 1: farmacia_balcao -> cons1_entrega" "$(cat "$WORK/robot.log")" "log do robô"

echo "--- 4. estoque da dipirona e movimentações"
STOCK=$(curl -s $API/stock -H "$(auth $MED)" | python -c 'import sys,json; [print(s["location_id"], s["quantity"], s["reserved"]) for s in json.load(sys.stdin) if s["item_id"]=="dipirona-500mg"]')
expect "consultorio1 5 0
farmacia 415 0" "$STOCK" "saldo e reservado (local saldo reservado)"
MOVES=$(curl -s "$API/movements?delivery_id=1" -H "$(auth $MED)" | python -c 'import sys,json; [print(m["type"], m["location_id"], m["quantity"]) for m in json.load(sys.stdin)]')
expect "RESERVA farmacia 5
BAIXA farmacia 5
CREDITO consultorio1 5" "$MOVES" "movimentações da entrega 1"

echo "--- 5. última telemetria do robô"
expect IDLE "$(curl -s $API/telemetry -H "$(auth $MED)" | field '["robot_state"]')" "robot_state"

echo "--- 6. assinatura dupla: a crítica só sai da fila depois da aprovação do farmacêutico"
expect PENDENTE_APROVACAO "$(curl -s $API/deliveries -H "$(auth $MED)" -H "$JSON" -d '{"origin_id":"banco_sangue","items":[{"item_id":"bolsa-sangue-o-neg","quantity":1}],"priority":"critica"}' | field '["status"]')" "status da crítica"
expect 204 "$(curl -s -o /dev/null -w '%{http_code}' -X POST $API/robot/next-task -H "$(auth $ROBO)")" "next-task antes da aprovação"
expect NA_FILA "$(curl -s -X POST $API/deliveries/2/approve -H "$(auth $PHARM)" | field '["status"]')" "status depois da aprovação"
expect "2 EM_ROTA banco_sangue_retirada cons1_entrega" "$(curl -s -X POST $API/robot/next-task -H "$(auth $ROBO)" | python -c 'import sys,json; d=json.load(sys.stdin); print(d["id"], d["status"], d["origin_waypoint"], d["dest_waypoint"])')" "tarefa entregue ao robô"

echo "--- 7. emergência pelo painel"
expect 204 "$(curl -s -o /dev/null -w '%{http_code}' -X POST $API/robot/estop -H "$(auth $PHARM)" -H "$JSON" -d '{"active":true}')" "ligar a emergência"
expect True "$(curl -s $API/robot/estop -H "$(auth $ROBO)" | field '["active"]')" "o robô lê active"
expect 204 "$(curl -s -o /dev/null -w '%{http_code}' -X POST $API/robot/estop -H "$(auth $PHARM)" -H "$JSON" -d '{"active":false}')" "desligar a emergência"

echo "--- 8. WebSocket"
expect IDLE "$(python - "$MED" <<'PY'
import asyncio, json, sys, websockets

async def main():
    async with websockets.connect(f"ws://127.0.0.1:8000/ws/telemetry?token={sys.argv[1]}") as ws:
        print(json.loads(await asyncio.wait_for(ws.recv(), 3))["robot_state"])

asyncio.run(main())
PY
)" "primeiro quadro do WebSocket"

echo "--- 9. trilha de auditoria no log do servidor"
grep -E "geraldo\." "$WORK/uvicorn.log"
expect 1 "$(grep -c 'entrega 1: AGUARDANDO_RECEBIMENTO -> ENTREGUE (por medico1)' "$WORK/uvicorn.log")" "auditoria do recebimento"

[ $FAIL -eq 0 ] && echo "E2E OK" || echo "E2E COM FALHAS"
exit $FAIL
```

- [ ] **Step 2: Conferir que a porta 8000 está livre.** Comando: `ss -ltn | grep -E ':8000\b' || echo livre`. Resultado esperado: `livre`. Se houver algo escutando, é de outra sessão: pare e avise o líder; não mate o processo.

- [ ] **Step 3: Rodar.** Comando (na raiz da worktree): `bash backend/e2e_smoke.sh`. Resultado esperado (cada linha `ok:` é uma conferência; o tempo total fica em cerca de 10 segundos):

```
--- 1. pedido (media): farmacia -> consultorio1
ok: status do pedido: NA_FILA
--- 2. robô de mentira: next-task, telemetria, LOADED, ARRIVED, espera, UNLOCKED
ok: o robô chegou e espera a confirmação: AGUARDANDO_RECEBIMENTO
--- 3. o solicitante confirma o recebimento
ok: status depois de confirmar: ENTREGUE
ok: código de saída do robô: 0
ok: log do robô: entrega 1: farmacia_balcao -> cons1_entrega
--- 4. estoque da dipirona e movimentações
ok: saldo e reservado (local saldo reservado): consultorio1 5 0
farmacia 415 0
ok: movimentações da entrega 1: RESERVA farmacia 5
BAIXA farmacia 5
CREDITO consultorio1 5
--- 5. última telemetria do robô
ok: robot_state: IDLE
--- 6. assinatura dupla: a crítica só sai da fila depois da aprovação do farmacêutico
ok: status da crítica: PENDENTE_APROVACAO
ok: next-task antes da aprovação: 204
ok: status depois da aprovação: NA_FILA
ok: tarefa entregue ao robô: 2 EM_ROTA banco_sangue_retirada cons1_entrega
--- 7. emergência pelo painel
ok: ligar a emergência: 204
ok: o robô lê active: True
ok: desligar a emergência: 204
--- 8. WebSocket
ok: primeiro quadro do WebSocket: IDLE
--- 9. trilha de auditoria no log do servidor
INFO:     [geraldo.audit] entrega 1: nova -> NA_FILA (por medico1)
...
WARNING:     [geraldo.stock] Estoque baixo: bolsa-sangue-o-neg em banco_sangue tem 6 (mínimo 10). Reponha.
...
ok: auditoria do recebimento: 1
E2E OK
```

Se alguma linha começar com `FALHOU:`, o script mostra o esperado e o obtido; corrija a causa (não o script) e rode de novo.

- [ ] **Step 4: Conferir que nada ficou rodando.** Comando: `ss -ltn | grep -E ':8000\b' || echo livre`. Resultado esperado: `livre`.

- [ ] **Step 5: Regressão final.** Comandos: `cd backend && python -m pytest -q` (esperado `168 passed`), e na raiz `backend/.venv/bin/python -m pytest tools -q` (esperado `10 passed` mais os testes de layout e contrato existentes) e `python3 -m pytest tools robot -q` (esperado verde).

- [ ] **Step 6: Commit.**

```bash
git add backend/e2e_smoke.sh
git commit -m "test(backend): ponta a ponta com uvicorn e o robo de mentira" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```
