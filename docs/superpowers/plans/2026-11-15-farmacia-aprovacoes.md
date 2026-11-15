# Aba Farmácia: aprovação e recusa de pedidos críticos — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A aba Estoque vira Farmácia (só farmacêutico e admin), com Aprovações (aprovar e recusar pedidos críticos) acima do Estoque; a recusa é um endpoint novo; Minhas entregas mostra o motivo.

**Architecture:** Backend: Command `RejectDelivery` (molde do `ApproveDelivery`), router fino com `require_roles(Role.farmaceutico)`, coluna `Delivery.cancel_reason`. Web: interface `AprovacoesApi` (ISP) no `ApiClient`, painel `AprovacoesPanel` dentro da nova `FarmaciaPage`, abas do `AppShell` filtradas por papel, motivo em `DeliveryQueueRow`.

**Tech Stack:** FastAPI + SQLModel + pytest (backend); React 19 + Vite + vitest + MSW + Tailwind (web).

**Spec:** `docs/superpowers/specs/2026-11-15-farmacia-aprovacoes-design.md` (contrato já em `docs/contracts/openapi.yaml`: `POST /deliveries/{id}/reject` e `Delivery.cancel_reason`, commit `4a7b706`).

## Global Constraints

- Contrato primeiro: **não** mude `docs/contracts/` (o PR A já traz o reject). O `status` final da recusa é `CANCELADA`; o enum não muda.
- Recusa: só `farmaceutico` (`403` para os outros, inclusive `admin` e `robo`); corpo `{"reason": string}` de 3 a 200 caracteres, sem espaços nas pontas; `200` com a `Delivery`; `401`; `404`; `409` se a entrega não está em `PENDENTE_APROVACAO`; `422` com motivo inválido.
- Recusar estorna a reserva com `ESTORNO` (como o cancelamento) e avisa os observers (`DeliveryChanged` e `StockChanged`).
- Padrões (`docs/padroes-de-projeto.md`): Command com dependências injetadas no construtor, router fino, sem `if/elif` por papel; web: ISP nas interfaces da API, funções puras em `domain/`.
- Design system: texto em português (mensagem de erro = o que houve + o que fazer), sem hex solto, vermelho só para erro (recusar **não** é vermelho), alvo de toque de 44 px, um botão primário por linha.
- Comandos de teste: backend `cd backend && .venv/bin/python -m pytest -q` (**sem** carregar o ROS: com ele o pytest do backend quebra com `No module named lark`); web `cd web && npx vitest run <arquivo>` e, no fim, `npm test -- --run && npm run build`; raiz `python3 -m pytest tools robot -q`.
- Commits em português, `tipo: o que mudou`, terminando com `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.
- O banco do backend não tem migração (`create_all`): a coluna nova precisa de `ALTER TABLE` em bancos antigos (Task 1).

## Mapa de arquivos

| Arquivo | Responsabilidade | Task |
|---|---|---|
| `backend/app/models.py`, `schemas.py`, `queries.py`, `db.py` | coluna `cancel_reason`, saída da API, `ALTER TABLE` em banco antigo | 1 |
| `backend/app/commands/reject_delivery.py`, `routers/delivery_actions.py`, `schemas.py` (`RejectIn`), `errors.py` | Command e rota da recusa, validação do motivo em português | 2 |
| `backend/tests/test_reject_delivery.py`, `tests/test_contract.py` | testes da recusa e do roteiro do contrato | 1, 2, 3 |
| `web/src/api/types.ts`, `ApiClient.ts`, `HttpApiClient.ts`, `mocks/handlers.ts` | `approveDelivery`, `rejectDelivery`, mocks | 4 |
| `web/src/domain/operacoes.ts`, `domain/motivo.ts`, `domain/EntregaAdapter.ts` | funções puras: pendentes, motivo, adapter | 5 |
| `web/src/components/AppShell.tsx`, `App.tsx` | abas por papel, `farmacia` no lugar de `estoque` | 6 |
| `web/src/pages/AprovacoesPanel.tsx`, `FarmaciaPage.tsx`, `EstoquePage.tsx` | Aprovações e página Farmácia | 7, 8 |
| `web/src/components/DeliveryQueueRow.tsx` | "Recusada pela farmácia: <motivo>" | 9 |
| `web/AGENTS.md`, `backend/AGENTS.md`, `web/src/mobile.test.tsx` | documentação e 44 px | 10 |

---

### Task 1: Coluna `cancel_reason` e saída da API

**Files:**
- Modify: `backend/app/models.py` (classe `Delivery`), `backend/app/schemas.py` (`DeliveryOut`), `backend/app/queries.py` (`delivery_out`), `backend/app/db.py` (`create_db`)
- Test: `backend/tests/test_reject_delivery.py` (novo)

**Interfaces:**
- Produces: `Delivery.cancel_reason: str | None`; `DeliveryOut.cancel_reason: str | None = None` (herdado por `RobotTaskOut`); `create_db(eng)` adiciona a coluna em banco antigo.

- [ ] **Step 1: Escrever os testes que falham**

Crie `backend/tests/test_reject_delivery.py`:

```python
from sqlalchemy import inspect, text

from app.db import create_db, make_engine

MEDIA = {"origin_id": "farmacia", "items": [{"item_id": "dipirona-500mg", "quantity": 1}], "priority": "media"}


def test_a_new_delivery_has_no_cancel_reason(client, auth):
    r = client.post("/deliveries", json=MEDIA, headers=auth("medico1"))
    assert r.status_code == 201 and r.json()["cancel_reason"] is None


def test_create_db_adds_the_cancel_reason_column_to_an_old_database(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path}/velho.db")
    with engine.begin() as conn:  # banco de antes desta mudança: tabela delivery sem cancel_reason
        conn.execute(text("CREATE TABLE delivery (id INTEGER PRIMARY KEY, origin_id TEXT, dest_id TEXT, priority TEXT, status TEXT, requested_by INTEGER, created_at TEXT)"))
    create_db(engine)
    assert "cancel_reason" in {c["name"] for c in inspect(engine).get_columns("delivery")}
    create_db(engine)  # de novo: não pode falhar
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd backend && .venv/bin/python -m pytest tests/test_reject_delivery.py -q`
Expected: FAIL (`KeyError: 'cancel_reason'` e a coluna ausente).

- [ ] **Step 3: Implementar**

`backend/app/models.py`, na classe `Delivery`, depois de `created_at`:

```python
    cancel_reason: str | None = Field(default=None, max_length=200)  # só na recusa pela farmácia
```

`backend/app/schemas.py`, em `DeliveryOut`, depois de `created_at`:

```python
    cancel_reason: str | None = None
```

`backend/app/queries.py`, em `delivery_out`, depois de `created_at=delivery.created_at,`:

```python
        cancel_reason=delivery.cancel_reason,
```

`backend/app/db.py` (arquivo inteiro das funções que mudam):

```python
from sqlalchemy import inspect, text
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine
```

```python
def create_db(eng=None) -> None:
    eng = eng or engine
    SQLModel.metadata.create_all(eng)
    # Sem migrações: um banco criado antes da recusa não tem a coluna e ganharia erro em toda consulta de entrega.
    if "cancel_reason" not in {c["name"] for c in inspect(eng).get_columns("delivery")}:
        with eng.begin() as conn:
            conn.execute(text("ALTER TABLE delivery ADD COLUMN cancel_reason VARCHAR(200)"))
```

- [ ] **Step 4: Rodar e ver passar**

Run: `cd backend && .venv/bin/python -m pytest -q`
Expected: tudo passa (o teste de contrato do backend ainda aceita a saída: `cancel_reason` é opcional e anulável no contrato).

- [ ] **Step 5: Commit**

```bash
git add backend/app backend/tests/test_reject_delivery.py
git commit -m "feat(backend): coluna cancel_reason na entrega e ALTER TABLE em banco antigo

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 2: `RejectDelivery` (Command) e `POST /deliveries/{id}/reject`

**Files:**
- Create: `backend/app/commands/reject_delivery.py`
- Modify: `backend/app/schemas.py` (`RejectIn`), `backend/app/routers/delivery_actions.py`, `backend/app/errors.py`
- Test: `backend/tests/test_reject_delivery.py`

**Interfaces:**
- Consumes: `load_visible`, `release_reservation`, `notify_stocks` (`app/commands/common.py`), `InvalidState` (`errors.py`), `EstornoCreator`, `DeliveryChanged`, `Subject`, `serialized`.
- Produces: `RejectDelivery(session, user, delivery_id, reason, *, estorno=None, events=None, lock=stock_lock).execute() -> Delivery`; `RejectIn(reason: str)`; rota `POST /deliveries/{delivery_id}/reject` → `DeliveryOut`.

- [ ] **Step 1: Escrever os testes que falham**

Acrescente a `backend/tests/test_reject_delivery.py`:

```python
import pytest
from sqlmodel import select

from app.commands.create_delivery import CreateDelivery
from app.commands.errors import InvalidState
from app.commands.reject_delivery import RejectDelivery
from app.events import DeliveryChanged
from app.models import DeliveryStatus, Movement, MovementType, Priority, User
from app.schemas import DeliveryCreate, DeliveryItemIn

CRITICAL = {"origin_id": "banco_sangue", "items": [{"item_id": "bolsa-sangue-o-neg", "quantity": 2}], "priority": "critica"}


def create(client, auth, user, body) -> int:
    r = client.post("/deliveries", json=body, headers=auth(user))
    assert r.status_code == 201, r.text
    return r.json()["id"]


def reject(client, auth, delivery_id, user="farmaceutico1", reason="Sem justificativa clínica"):
    return client.post(f"/deliveries/{delivery_id}/reject", json={"reason": reason}, headers=auth(user))


def blood_stock(client, auth) -> dict:
    return client.get("/stock", params={"location_id": "banco_sangue"}, headers=auth("medico1")).json()[0]


def test_the_pharmacist_rejects_a_pending_critical_delivery_and_the_reservation_comes_back(client, auth, spy):
    before = blood_stock(client, auth)
    delivery_id = create(client, auth, "medico1", CRITICAL)
    assert blood_stock(client, auth)["reserved"] == before["reserved"] + 2
    r = reject(client, auth, delivery_id)
    assert r.status_code == 200
    assert r.json()["status"] == "CANCELADA" and r.json()["cancel_reason"] == "Sem justificativa clínica"
    assert blood_stock(client, auth)["reserved"] == before["reserved"]
    kinds = [m["type"] for m in client.get("/movements", params={"delivery_id": delivery_id}, headers=auth("admin")).json()]
    assert kinds == ["RESERVA", "ESTORNO"]
    assert DeliveryChanged(delivery_id, DeliveryStatus.PENDENTE_APROVACAO, DeliveryStatus.CANCELADA, "farmaceutico1") in spy.events
    assert client.post("/robot/next-task", headers=auth("robo")).status_code == 204  # nada entra na fila


def test_only_a_pharmacist_rejects(client, auth):
    delivery_id = create(client, auth, "medico1", CRITICAL)
    url = f"/deliveries/{delivery_id}/reject"
    assert client.post(url, json={"reason": "Sem justificativa"}).status_code == 401
    for user in ("medico1", "enfermeiro1", "admin", "robo"):
        r = reject(client, auth, delivery_id, user)
        assert r.status_code == 403, user
    assert blood_stock(client, auth)["reserved"] > 0  # nada foi estornado


def test_rejecting_an_unknown_delivery_is_404(client, auth):
    assert reject(client, auth, 9999).status_code == 404


def test_rejecting_twice_or_a_delivery_that_is_not_pending_is_409(client, auth):
    critical_id = create(client, auth, "medico1", CRITICAL)
    media_id = create(client, auth, "medico1", MEDIA)
    assert reject(client, auth, critical_id).status_code == 200
    again = reject(client, auth, critical_id)
    assert again.status_code == 409 and "CANCELADA" in again.json()["detail"]
    assert reject(client, auth, media_id).status_code == 409  # média já está NA_FILA


@pytest.mark.parametrize(
    "body",
    [{}, {"reason": ""}, {"reason": "ab"}, {"reason": "x" * 201}, {"reason": " começa com espaço"}, {"reason": "termina com espaço "}, {"reason": 123}],
)
def test_an_invalid_reason_is_422_in_portuguese_and_changes_nothing(client, auth, body):
    delivery_id = create(client, auth, "medico1", CRITICAL)
    r = client.post(f"/deliveries/{delivery_id}/reject", json=body, headers=auth("farmaceutico1"))
    assert r.status_code == 422 and r.json()["detail"].startswith("Dados inválidos (reason:")
    assert client.get(f"/deliveries/{delivery_id}", headers=auth("medico1")).json()["status"] == "PENDENTE_APROVACAO"


def test_the_edge_spaces_message_says_what_to_do(client, auth):
    delivery_id = create(client, auth, "medico1", CRITICAL)
    r = client.post(f"/deliveries/{delivery_id}/reject", json={"reason": " ok? "}, headers=auth("farmaceutico1"))
    assert "começar nem terminar com espaço" in r.json()["detail"]


def test_the_requester_sees_the_reason_in_their_own_list(client, auth):
    delivery_id = create(client, auth, "medico1", CRITICAL)
    reject(client, auth, delivery_id, reason="Use a prescrição digital")
    mine = client.get("/deliveries", headers=auth("medico1")).json()
    assert [(d["status"], d["cancel_reason"]) for d in mine if d["id"] == delivery_id] == [("CANCELADA", "Use a prescrição digital")]


def test_the_command_uses_the_injected_estorno_and_events(session):
    medico = session.exec(select(User).where(User.username == "medico1")).one()
    pharmacist = session.exec(select(User).where(User.username == "farmaceutico1")).one()
    payload = DeliveryCreate(origin_id="farmacia", items=[DeliveryItemIn(item_id="dipirona-500mg", quantity=1)], priority=Priority.critica)
    delivery = CreateDelivery(session, medico, payload).execute()

    class Spy:
        calls = 0

        def register(self, stock, *, delivery_id, quantity):
            Spy.calls += 1
            return Movement(delivery_id=delivery_id, type=MovementType.ESTORNO, item_id=stock.item_id, location_id=stock.location_id, quantity=quantity)

    rejected = RejectDelivery(session, pharmacist, delivery.id, "Sem justificativa", estorno=Spy()).execute()
    assert rejected.status == DeliveryStatus.CANCELADA and Spy.calls == 1
    with pytest.raises(InvalidState, match="não espera aprovação"):
        RejectDelivery(session, pharmacist, delivery.id, "Sem justificativa").execute()
```

No topo do arquivo defina também `MEDIA` (já existe da Task 1: `MEDIA = {...}`): confira que ele aparece uma vez só.

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd backend && .venv/bin/python -m pytest tests/test_reject_delivery.py -q`
Expected: FAIL (`ModuleNotFoundError: No module named 'app.commands.reject_delivery'` e 404/405 nas chamadas HTTP).

- [ ] **Step 3: Implementar**

`backend/app/commands/reject_delivery.py`:

```python
from sqlmodel import Session

from app.commands.common import load_visible, notify_stocks, release_reservation
from app.commands.errors import InvalidState
from app.events import DeliveryChanged, Subject
from app.models import Delivery, DeliveryStatus, User
from app.movements import EstornoCreator, MovementCreator
from app.stock_lock import serialized, stock_lock


# COMMAND
class RejectDelivery:
    """Comando RecusarEntrega: o farmacêutico recusa um pedido crítico pendente; a reserva volta (ESTORNO).

    O papel farmacêutico é conferido no router. A entrega vira CANCELADA com o motivo em `cancel_reason`
    (o enum de status não muda: o contrato guarda a recusa como cancelamento com motivo).
    """

    def __init__(
        self,
        session: Session,
        user: User,
        delivery_id: int,
        reason: str,
        *,
        estorno: MovementCreator | None = None,
        events: Subject | None = None,
        lock=stock_lock,
    ) -> None:
        self._session = session
        self._user = user
        self._delivery_id = delivery_id
        self._reason = reason
        self._estorno = estorno or EstornoCreator()
        self._events = events if events is not None else Subject()
        self._lock = lock

    @serialized
    def execute(self) -> Delivery:
        delivery = load_visible(self._session, self._user, self._delivery_id)
        if delivery.status != DeliveryStatus.PENDENTE_APROVACAO:
            raise InvalidState(
                f"A entrega está {delivery.status.value} e não espera aprovação. Só pedidos críticos pendentes são recusados."
            )
        old_status = delivery.status
        stocks = release_reservation(self._session, delivery, self._estorno)
        delivery.status = DeliveryStatus.CANCELADA
        delivery.cancel_reason = self._reason
        self._session.add(delivery)
        self._session.commit()
        self._session.refresh(delivery)
        self._events.notify(DeliveryChanged(delivery.id, old_status, delivery.status, self._user.username))
        notify_stocks(self._events, stocks)
        return delivery
```

`backend/app/schemas.py` (importe `field_validator` e `PydanticCustomError`; acrescente depois de `DeliveryCreate`):

```python
from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StrictBool, field_validator
from pydantic_core import PydanticCustomError
```

```python
class RejectIn(BaseModel):
    """Corpo do POST /deliveries/{id}/reject: o motivo que o solicitante vai ler (3 a 200 caracteres, sem espaços nas pontas)."""

    reason: str = Field(min_length=3, max_length=200)

    @field_validator("reason")
    @classmethod
    def no_edge_spaces(cls, value: str) -> str:
        if value != value.strip():
            raise PydanticCustomError("edge_spaces", "motivo com espaços nas pontas")
        return value
```

`backend/app/errors.py`, em `MESSAGES` (depois de `"list_type"`):

```python
    "edge_spaces": "não pode começar nem terminar com espaço (tire os espaços das pontas)",
```

`backend/app/routers/delivery_actions.py` (importe `RejectDelivery` e `RejectIn`; acrescente depois de `approve_delivery`):

```python
from app.commands.reject_delivery import RejectDelivery
from app.schemas import DeliveryOut, RejectIn
```

```python
@router.post("/deliveries/{delivery_id}/reject", response_model=DeliveryOut)
def reject_delivery(
    delivery_id: int,
    body: RejectIn,
    user: User = Depends(require_roles(Role.farmaceutico)),
    session: Session = Depends(get_session),
    events: Subject = Depends(get_events),
) -> DeliveryOut:
    try:
        delivery = RejectDelivery(session, user, delivery_id, body.reason, events=events).execute()
    except DeliveryError as err:
        raise HTTPException(status_code=err.status_code, detail=str(err))
    return delivery_out(session, delivery)
```

- [ ] **Step 4: Rodar e ver passar**

Run: `cd backend && .venv/bin/python -m pytest tests/test_reject_delivery.py -q`
Expected: PASS. Se `test_an_invalid_reason...` falhar no caso `{"reason": 123}`, confira que `describe` (em `errors.py`) devolve `reason: deve ser um texto`.

- [ ] **Step 5: Commit**

```bash
git add backend/app backend/tests/test_reject_delivery.py
git commit -m "feat(backend): RejectDelivery e POST /deliveries/{id}/reject (farmaceutico, estorno, motivo)

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Teste de contrato do backend exercita o reject

**Files:**
- Modify: `backend/tests/test_contract.py` (roteiro, depois do bloco "assinatura dupla da crítica")

- [ ] **Step 1: Escrever o teste que falha**

Rode antes: `cd backend && .venv/bin/python -m pytest tests/test_contract.py -q`. Ele já falha com `operações que o roteiro não chamou: {('post', '/deliveries/{}/reject')}` (o contrato do PR A declara a operação). Isso é o RED.

- [ ] **Step 2: Acrescentar ao roteiro**

Depois da linha `api("post", "/deliveries/{id}/approve", as_="farmaceutico1", id=critica["id"], expect=409)`, insira:

```python
    # recusar um pedido crítico pendente (farmacêutico): CANCELADA com cancel_reason
    recusar = api("post", "/deliveries", as_="medico1", json=CRITICA, expect=201).json()["id"]
    api("post", "/deliveries/{id}/reject", id=recusar, json={"reason": "Sem justificativa"}, expect=401)
    api("post", "/deliveries/{id}/reject", as_="medico1", id=recusar, json={"reason": "Sem justificativa"}, expect=403)
    api("post", "/deliveries/{id}/reject", as_="admin", id=recusar, json={"reason": "Sem justificativa"}, expect=403)
    api("post", "/deliveries/{id}/reject", as_="farmaceutico1", id=9999, json={"reason": "Sem justificativa"}, expect=404)
    api("post", "/deliveries/{id}/reject", as_="farmaceutico1", id=recusar, json={"reason": "ab"}, expect=422)
    recusada = api("post", "/deliveries/{id}/reject", as_="farmaceutico1", id=recusar, json={"reason": "Sem justificativa"}, expect=200).json()
    assert (recusada["status"], recusada["cancel_reason"]) == ("CANCELADA", "Sem justificativa")
    api("post", "/deliveries/{id}/reject", as_="farmaceutico1", id=recusar, json={"reason": "Sem justificativa"}, expect=409)
```

- [ ] **Step 3: Rodar e ver passar**

Run: `cd backend && .venv/bin/python -m pytest -q`
Expected: tudo passa (inclusive `test_contract`). O 422 do reject cai no schema `Error` (o contrato declara só a descrição).

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_contract.py
git commit -m "test(backend): roteiro do contrato chama o reject (200, 401, 403, 404, 409, 422)

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Web: tipos, `AprovacoesApi`, `HttpApiClient` e mocks

**Files:**
- Modify: `web/src/api/types.ts`, `web/src/api/ApiClient.ts`, `web/src/api/HttpApiClient.ts`, `web/src/api/mocks/handlers.ts`, `web/src/api/mocks/fixtures.ts`
- Test: `web/src/api/HttpApiClient.test.ts`

**Interfaces:**
- Produces: `Delivery.cancel_reason?: string | null`; `AprovacoesApi { approveDelivery(id: number): Promise<Delivery>; rejectDelivery(id: number, reason: string): Promise<Delivery> }` (entra em `ApiClient`); fixture `DELIVERY_PENDENTE: Delivery` (crítica `PENDENTE_APROVACAO`, id 4, `requested_by: 1`); os mocks implementam as duas rotas com as regras do backend (só `farmaceutico`, `404`, `409`, `422`).

- [ ] **Step 1: Escrever os testes que falham**

Acrescente a `web/src/api/HttpApiClient.test.ts` (troque o import de fixtures por `import { DELIVERY, DELIVERY_AGUARDANDO, DELIVERY_PENDENTE, ME } from "./mocks/fixtures";`):

```ts
test("approveDelivery aprova o pedido crítico pendente (só o farmacêutico)", async () => {
  semearEntregas([DELIVERY_PENDENTE]);
  await api.login("farmaceutico1", "demo");
  const entrega = await api.approveDelivery(4);
  expect(entrega.status).toBe("NA_FILA");
});

test("approveDelivery de quem não é farmacêutico levanta ApiError 403", async () => {
  semearEntregas([DELIVERY_PENDENTE]);
  await api.login("medico1", "demo");
  await expect(api.approveDelivery(4)).rejects.toMatchObject({ status: 403 });
});

test("rejectDelivery cancela com o motivo e devolve o estoque (ESTORNO)", async () => {
  semearEntregas([DELIVERY_PENDENTE]);
  await api.login("farmaceutico1", "demo");
  const entrega = await api.rejectDelivery(4, "Sem justificativa clínica");
  expect(entrega).toMatchObject({ status: "CANCELADA", cancel_reason: "Sem justificativa clínica" });
  expect(await api.movements({ deliveryId: 4 })).toMatchObject([{ type: "ESTORNO", location_id: "banco_sangue", quantity: 2 }]);
});

test("rejectDelivery com motivo curto levanta ApiError 422 e entrega que não está pendente, 409", async () => {
  semearEntregas([DELIVERY_PENDENTE, DELIVERY]);
  await api.login("farmaceutico1", "demo");
  await expect(api.rejectDelivery(4, "ab")).rejects.toMatchObject({ status: 422 });
  await expect(api.rejectDelivery(1, "Sem justificativa")).rejects.toMatchObject({ status: 409 });
});
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd web && npx vitest run src/api/HttpApiClient.test.ts`
Expected: FAIL (`DELIVERY_PENDENTE` não existe; `api.approveDelivery is not a function`).

- [ ] **Step 3: Implementar**

`web/src/api/types.ts`, na interface `Delivery`, depois de `created_at: string;`:

```ts
  cancel_reason?: string | null; // só na recusa pela farmácia
```

`web/src/api/ApiClient.ts`: depois de `EntregasApi` e antes de `HistoricoApi`, e na união `ApiClient`:

```ts
// Só o farmacêutico aprova e recusa pedidos críticos (contrato: /approve e /reject).
export interface AprovacoesApi {
  approveDelivery(id: number): Promise<Delivery>;
  rejectDelivery(id: number, reason: string): Promise<Delivery>;
}
```

```ts
export type ApiClient = SessaoApi & CatalogoApi & EntregasApi & AprovacoesApi & HistoricoApi & RoboApi;
```

`web/src/api/HttpApiClient.ts`, depois de `confirmReceipt`:

```ts
  approveDelivery(id: number) {
    return this.#request<Delivery>(`/deliveries/${id}/approve`, { method: "POST" });
  }

  rejectDelivery(id: number, reason: string) {
    return this.#request<Delivery>(`/deliveries/${id}/reject`, { method: "POST", body: JSON.stringify({ reason }) });
  }
```

`web/src/api/mocks/fixtures.ts`, depois de `DELIVERY_AGUARDANDO`:

```ts
export const DELIVERY_PENDENTE: Delivery = {
  id: 4,
  origin_id: "banco_sangue",
  dest_id: "consultorio1",
  items: [{ item_id: "bolsa-sangue-o-neg", quantity: 2 }],
  priority: "critica",
  status: "PENDENTE_APROVACAO",
  requested_by: 1,
  created_at: "2026-11-09T13:40:00Z",
};
```

`web/src/api/mocks/handlers.ts`: dentro de `handlers`, depois do handler de `confirm-receipt`:

```ts
  http.post(`${BASE}/deliveries/:id/approve`, ({ params }) => {
    if (usuario.role !== "farmaceutico") {
      return HttpResponse.json({ detail: "Só o farmacêutico aprova pedidos críticos." }, { status: 403 });
    }
    const entrega = entregas.find((e) => e.id === Number(params.id));
    if (!entrega) return HttpResponse.json({ detail: "Entrega não encontrada. Atualize a lista." }, { status: 404 });
    if (entrega.status !== "PENDENTE_APROVACAO") {
      return HttpResponse.json({ detail: `A entrega está ${entrega.status} e não espera aprovação.` }, { status: 409 });
    }
    entrega.status = "NA_FILA";
    return HttpResponse.json(entrega);
  }),
  http.post(`${BASE}/deliveries/:id/reject`, async ({ params, request }) => {
    if (usuario.role !== "farmaceutico") {
      return HttpResponse.json({ detail: "Só o farmacêutico recusa pedidos críticos." }, { status: 403 });
    }
    const entrega = entregas.find((e) => e.id === Number(params.id));
    if (!entrega) return HttpResponse.json({ detail: "Entrega não encontrada. Atualize a lista." }, { status: 404 });
    const { reason } = (await request.json()) as { reason?: unknown };
    if (typeof reason !== "string" || reason.length < 3 || reason.length > 200 || reason !== reason.trim()) {
      return HttpResponse.json({ detail: "Dados inválidos (reason: motivo de 3 a 200 caracteres, sem espaços nas pontas). Corrija e envie de novo." }, { status: 422 });
    }
    if (entrega.status !== "PENDENTE_APROVACAO") {
      return HttpResponse.json({ detail: `A entrega está ${entrega.status} e não espera aprovação.` }, { status: 409 });
    }
    entrega.status = "CANCELADA";
    entrega.cancel_reason = reason;
    for (const item of entrega.items) {
      movimentos.push({
        id: movimentos.length + 1,
        delivery_id: entrega.id,
        type: "ESTORNO",
        item_id: item.item_id,
        location_id: entrega.origin_id,
        quantity: item.quantity,
        created_at: new Date().toISOString(),
      });
    }
    return HttpResponse.json(entrega);
  }),
```

- [ ] **Step 4: Rodar e ver passar**

Run: `cd web && npx vitest run src/api && npx tsc --noEmit`
Expected: PASS e sem erro de tipo.

- [ ] **Step 5: Commit**

```bash
git add web/src/api
git commit -m "feat(web): AprovacoesApi (approve e reject) no cliente HTTP e nos mocks

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Funções puras: pendentes, papéis, motivo e adapter

**Files:**
- Modify: `web/src/domain/operacoes.ts`, `web/src/domain/EntregaAdapter.ts`
- Create: `web/src/domain/motivo.ts`
- Test: `web/src/domain/operacoes.test.ts`, `web/src/domain/motivo.test.ts`, `web/src/domain/EntregaAdapter.test.ts`

**Interfaces:**
- Produces: `pendentesDeAprovacao(entregas: Delivery[]): Delivery[]` (só `PENDENTE_APROVACAO`, por id); `podeVerFarmacia(role: Role): boolean` (`farmaceutico` e `admin`); `podeAprovar(role: Role): boolean` (só `farmaceutico`); `validarMotivo(texto: string): string | null` (mensagem de erro ou `null`); `Entrega.motivoDaRecusa: string | null`.

- [ ] **Step 1: Escrever os testes que falham**

`web/src/domain/motivo.test.ts`:

```ts
import { validarMotivo } from "./motivo";

test("motivo de 3 a 200 caracteres (sem contar os espaços das pontas) é aceito", () => {
  expect(validarMotivo("abc")).toBeNull();
  expect(validarMotivo("  Sem justificativa  ")).toBeNull();
  expect(validarMotivo("x".repeat(200))).toBeNull();
});

test("motivo curto ou longo demais diz o que fazer", () => {
  const msg = "Escreva o motivo da recusa com 3 a 200 caracteres.";
  expect(validarMotivo("")).toBe(msg);
  expect(validarMotivo("   ab  ")).toBe(msg);
  expect(validarMotivo("x".repeat(201))).toBe(msg);
});
```

Acrescente a `web/src/domain/operacoes.test.ts` (inclua `DELIVERY_PENDENTE` no import das fixtures e `pendentesDeAprovacao, podeAprovar, podeVerFarmacia` no import de `./operacoes`):

```ts
test("pendentesDeAprovacao deixa só os pedidos aguardando a assinatura, do mais antigo para o mais novo", () => {
  const lista = [{ ...DELIVERY_PENDENTE, id: 9 }, DELIVERY, DELIVERY_PENDENTE];
  expect(pendentesDeAprovacao(lista).map((e) => e.id)).toEqual([4, 9]);
});

test("só farmacêutico e admin veem a Farmácia; só o farmacêutico aprova", () => {
  expect((["medico", "enfermeiro", "farmaceutico", "admin", "robo"] as const).filter(podeVerFarmacia)).toEqual(["farmaceutico", "admin"]);
  expect((["medico", "farmaceutico", "admin"] as const).filter(podeAprovar)).toEqual(["farmaceutico"]);
});
```

Acrescente a `web/src/domain/EntregaAdapter.test.ts`:

```ts
test("a recusa vira motivoDaRecusa; sem recusa é null", () => {
  const adapter = new EntregaAdapter((id) => id);
  expect(adapter.adaptar({ ...DELIVERY, status: "CANCELADA", cancel_reason: "Sem justificativa" }).motivoDaRecusa).toBe("Sem justificativa");
  expect(adapter.adaptar(DELIVERY).motivoDaRecusa).toBeNull();
});
```

(Confira os imports já existentes no arquivo: `EntregaAdapter` e `DELIVERY`.)

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd web && npx vitest run src/domain`
Expected: FAIL (`./motivo` não existe, funções ausentes).

- [ ] **Step 3: Implementar**

`web/src/domain/motivo.ts`:

```ts
// Contrato: motivo da recusa de 3 a 200 caracteres, sem espaços nas pontas (a tela tira os espaços antes de enviar).
export const MOTIVO_MIN = 3;
export const MOTIVO_MAX = 200;

export function validarMotivo(texto: string): string | null {
  const tamanho = texto.trim().length;
  return tamanho >= MOTIVO_MIN && tamanho <= MOTIVO_MAX ? null : `Escreva o motivo da recusa com ${MOTIVO_MIN} a ${MOTIVO_MAX} caracteres.`;
}
```

`web/src/domain/operacoes.ts`, depois de `podeAcionarEstop`:

```ts
export const pendentesDeAprovacao = (entregas: Delivery[]): Delivery[] =>
  entregas.filter((e) => e.status === "PENDENTE_APROVACAO").sort((a, b) => a.id - b.id);

const PAPEIS_DA_FARMACIA: readonly Role[] = ["farmaceutico", "admin"];

// Estoque de todos os locais e a fila de aprovações não são assunto de médico nem de enfermeiro.
export const podeVerFarmacia = (role: Role): boolean => PAPEIS_DA_FARMACIA.includes(role);

// Contrato: só o farmacêutico chama /approve e /reject (o admin vê a fila, sem botões).
export const podeAprovar = (role: Role): boolean => role === "farmaceutico";
```

`web/src/domain/EntregaAdapter.ts`: na interface `Entrega`, depois de `solicitadaEm: Date;`:

```ts
  motivoDaRecusa: string | null;
```

e em `adaptar`, depois de `solicitadaEm: new Date(entrega.created_at),`:

```ts
      motivoDaRecusa: entrega.cancel_reason ?? null,
```

- [ ] **Step 4: Rodar e ver passar**

Run: `cd web && npx vitest run src/domain && npx tsc --noEmit`
Expected: PASS (se `tsc` reclamar de objetos `Entrega` literais nos testes, acrescente `motivoDaRecusa: null`).

- [ ] **Step 5: Commit**

```bash
git add web/src/domain
git commit -m "feat(web): funcoes puras da Farmacia (pendentes, papeis, motivo da recusa)

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 6: `AppShell` com abas por papel e `farmacia` no lugar de `estoque`

**Files:**
- Modify: `web/src/components/AppShell.tsx`, `web/src/App.tsx`
- Test: `web/src/components/AppShell.test.tsx`, `web/src/App.test.tsx`, `web/src/mobile.test.tsx`

**Interfaces:**
- Consumes: `podeVerFarmacia(role)` (Task 5).
- Produces: `PageId = "solicitar" | "entregas" | "farmacia" | "painel"`; `AppShell({ active, role, onNavigate, children })` (`role: Role`); `App` renderiza `<FarmaciaPage api role />` (criada na Task 8; nesta task use `EstoquePage` e troque na Task 8).

- [ ] **Step 1: Escrever/ajustar os testes (RED)**

`web/src/components/AppShell.test.tsx`: troque cada `<AppShell active="..." onNavigate={...}>` por `<AppShell active="..." role="farmaceutico" onNavigate={...}>` e as referências a `Estoque` por `Farmácia` (`name: "Farmácia"`, `toHaveBeenCalledWith("farmacia")`). Acrescente:

```tsx
test("médico e enfermeiro não veem a aba Farmácia; farmacêutico e admin veem", () => {
  const { rerender } = render(<AppShell active="solicitar" role="medico" onNavigate={vi.fn()}>x</AppShell>);
  expect(screen.queryByRole("button", { name: "Farmácia" })).not.toBeInTheDocument();
  expect(screen.getAllByRole("button", { name: "Painel" })).toHaveLength(2);
  rerender(<AppShell active="solicitar" role="enfermeiro" onNavigate={vi.fn()}>x</AppShell>);
  expect(screen.queryByRole("button", { name: "Farmácia" })).not.toBeInTheDocument();
  for (const role of ["farmaceutico", "admin"] as const) {
    rerender(<AppShell active="solicitar" role={role} onNavigate={vi.fn()}>x</AppShell>);
    expect(screen.getAllByRole("button", { name: "Farmácia" })).toHaveLength(2);
  }
});
```

`web/src/App.test.tsx`: troque o teste "a aba Estoque mostra os saldos" por:

```tsx
test("o médico não tem a aba Farmácia", async () => {
  montar();
  await entrar("medico1");
  expect(screen.queryByRole("button", { name: "Farmácia" })).not.toBeInTheDocument();
});

test("o farmacêutico abre a Farmácia e vê o estoque", async () => {
  montar();
  await entrar("farmaceutico1");
  await userEvent.click(screen.getAllByRole("button", { name: "Farmácia" })[0]);
  expect(await screen.findByRole("heading", { name: "Farmácia" })).toBeInTheDocument();
  expect(await screen.findByText("Bolsa de sangue O negativo")).toBeInTheDocument();
});
```

e no teste "sair do Painel fecha o WebSocket" troque o clique em `Estoque` por `Minhas entregas`. No `mobile.test.tsx`, nas chamadas `<AppShell active="painel" onNavigate=...>` acrescente `role="admin"`.

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd web && npx vitest run src/components/AppShell.test.tsx src/App.test.tsx src/mobile.test.tsx`
Expected: FAIL.

- [ ] **Step 3: Implementar**

`web/src/components/AppShell.tsx` (partes que mudam):

```tsx
import { Bot, PackageCheck, PackagePlus, Pill, type LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import type { Role } from "../api/types";
import { podeVerFarmacia } from "../domain/operacoes";

export type PageId = "solicitar" | "entregas" | "farmacia" | "painel";

interface Item {
  id: PageId;
  label: string;
  Icon: LucideIcon;
  visivelPara: (role: Role) => boolean;
}

const PARA_TODOS = () => true;

const ITEMS: Item[] = [
  { id: "solicitar", label: "Solicitar", Icon: PackagePlus, visivelPara: PARA_TODOS },
  { id: "entregas", label: "Minhas entregas", Icon: PackageCheck, visivelPara: PARA_TODOS },
  { id: "farmacia", label: "Farmácia", Icon: Pill, visivelPara: podeVerFarmacia },
  { id: "painel", label: "Painel", Icon: Bot, visivelPara: PARA_TODOS },
];

interface Props {
  active: PageId;
  role: Role;
  onNavigate: (page: PageId) => void;
  children: ReactNode;
}
```

`NavButton` passa a receber `Item & Pick<Props, "active" | "onNavigate"> & { vertical: boolean }` (troque o tipo `(typeof ITEMS)[number] & Omit<Props, "children">` por esse); em `AppShell({ active, role, onNavigate, children })` use `const itens = ITEMS.filter((item) => item.visivelPara(role));` e `itens.map(...)` nas duas barras (a barra inferior continua com no máximo 4 itens).

`web/src/App.tsx`: troque `{page === "estoque" && <EstoquePage api={cliente} />}` por `{page === "farmacia" && podeVerFarmacia(me.role) && <EstoquePage api={cliente} />}` (importe `podeVerFarmacia` de `./domain/operacoes`) e `<AppShell active={page} role={me.role} onNavigate={setPage}>`. A página `EstoquePage` ainda mostra o título "Estoque": o teste do farmacêutico espera "Farmácia", então nesta task troque só o `<h1>` de `EstoquePage.tsx` para `Farmácia` e ajuste `EstoquePage.test.tsx` (`name: "Farmácia"`); a Task 8 a reorganiza.

- [ ] **Step 4: Rodar e ver passar**

Run: `cd web && npx vitest run && npx tsc --noEmit`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src
git commit -m "feat(web): aba Farmacia (antes Estoque) so para farmaceutico e admin

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 7: `AprovacoesPanel` (aprovar e recusar)

**Files:**
- Create: `web/src/pages/AprovacoesPanel.tsx`
- Test: `web/src/pages/AprovacoesPanel.test.tsx` (novo)

**Interfaces:**
- Consumes: `EntregasApi & AprovacoesApi & CatalogoApi`, `pendentesDeAprovacao`, `podeAprovar`, `validarMotivo`, `EntregaAdapter`, `DeliveryQueueRow`, `AlertBanner`, `Button`, `Card`.
- Produces: `AprovacoesPanel({ api, role, intervaloMs = 5000 })`: seção `<section aria-labelledby>` com `<h2>Aprovações</h2>`.

- [ ] **Step 1: Escrever os testes que falham**

`web/src/pages/AprovacoesPanel.test.tsx`:

```tsx
import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { HttpApiClient } from "../api/HttpApiClient";
import { DELIVERY, DELIVERY_PENDENTE } from "../api/mocks/fixtures";
import { semearEntregas } from "../api/mocks/handlers";
import { server } from "../api/mocks/server";
import { AprovacoesPanel } from "./AprovacoesPanel";

async function montar(role: "farmaceutico" | "admin", intervaloMs?: number) {
  const api = new HttpApiClient();
  await api.login(role === "admin" ? "admin" : "farmaceutico1", "demo");
  render(<AprovacoesPanel api={api} role={role} intervaloMs={intervaloMs} />);
  return api;
}

test("lista só os pedidos pendentes, com itens, origem, destino e horário", async () => {
  semearEntregas([DELIVERY, DELIVERY_PENDENTE]);
  await montar("farmaceutico");
  expect(await screen.findByRole("heading", { name: "Aprovações" })).toBeInTheDocument();
  expect(await screen.findByText(/2 × Bolsa sangue o neg · Banco de sangue → Consultório 1/)).toBeInTheDocument();
  expect(screen.getAllByRole("listitem")).toHaveLength(1);
});

test("sem pedidos pendentes mostra o estado vazio", async () => {
  semearEntregas([DELIVERY]);
  await montar("farmaceutico");
  expect(await screen.findByText("Nenhum pedido crítico esperando a sua assinatura.")).toBeInTheDocument();
});

test("o farmacêutico aprova: o pedido sai da lista e aparece o aviso", async () => {
  semearEntregas([DELIVERY_PENDENTE]);
  await montar("farmaceutico");
  await userEvent.click(await screen.findByRole("button", { name: "Aprovar entrega 4" }));
  expect(await screen.findByRole("status")).toHaveTextContent("Entrega 4 aprovada. O robô vai buscar assim que estiver livre.");
  await waitFor(() => expect(screen.queryByRole("button", { name: "Aprovar entrega 4" })).not.toBeInTheDocument());
});

test("recusar pede o motivo, valida e só então envia; o pedido sai da lista", async () => {
  semearEntregas([DELIVERY_PENDENTE]);
  const api = await montar("farmaceutico");
  await userEvent.click(await screen.findByRole("button", { name: "Recusar entrega 4" }));
  const campo = screen.getByLabelText("Motivo da recusa");
  await userEvent.type(campo, "ab");
  await userEvent.click(screen.getByRole("button", { name: "Confirmar recusa" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Escreva o motivo da recusa com 3 a 200 caracteres.");
  expect(await api.deliveries()).toMatchObject([{ status: "PENDENTE_APROVACAO" }]);
  await userEvent.clear(campo);
  await userEvent.type(campo, "  Use a prescrição digital  ");
  await userEvent.click(screen.getByRole("button", { name: "Confirmar recusa" }));
  expect(await screen.findByRole("status")).toHaveTextContent("Entrega 4 recusada. O solicitante verá o motivo.");
  expect(await api.deliveries()).toMatchObject([{ status: "CANCELADA", cancel_reason: "Use a prescrição digital" }]);
  expect(screen.queryByLabelText("Motivo da recusa")).not.toBeInTheDocument();
});

test("cancelar a recusa fecha o campo sem enviar nada", async () => {
  semearEntregas([DELIVERY_PENDENTE]);
  const api = await montar("farmaceutico");
  await userEvent.click(await screen.findByRole("button", { name: "Recusar entrega 4" }));
  await userEvent.click(screen.getByRole("button", { name: "Cancelar" }));
  expect(screen.queryByLabelText("Motivo da recusa")).not.toBeInTheDocument();
  expect(await api.deliveries()).toMatchObject([{ status: "PENDENTE_APROVACAO" }]);
});

test("o admin vê a lista sem botões e com a nota", async () => {
  semearEntregas([DELIVERY_PENDENTE]);
  await montar("admin");
  expect(await screen.findByText(/2 × Bolsa sangue o neg/)).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /Aprovar|Recusar/ })).not.toBeInTheDocument();
  expect(screen.getByText("Só o farmacêutico aprova ou recusa pedidos críticos.")).toBeInTheDocument();
});

test("erro ao aprovar aparece como alerta e a lista continua", async () => {
  semearEntregas([DELIVERY_PENDENTE]);
  server.use(http.post("http://localhost:8000/deliveries/4/approve", () => HttpResponse.json({ detail: "A entrega está NA_FILA e não espera aprovação." }, { status: 409 })));
  await montar("farmaceutico");
  await userEvent.click(await screen.findByRole("button", { name: "Aprovar entrega 4" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("A entrega está NA_FILA e não espera aprovação.");
  expect(screen.getByRole("button", { name: "Aprovar entrega 4" })).toBeInTheDocument();
});

test("recarrega a lista sozinha: um pedido novo aparece sem trocar de aba", async () => {
  semearEntregas([]);
  vi.useFakeTimers({ toFake: ["setInterval", "clearInterval"] });
  try {
    await montar("farmaceutico", 5000);
    expect(await screen.findByText("Nenhum pedido crítico esperando a sua assinatura.")).toBeInTheDocument();
    semearEntregas([DELIVERY_PENDENTE]);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });
    expect(await screen.findByRole("button", { name: "Aprovar entrega 4" })).toBeInTheDocument();
  } finally {
    vi.useRealTimers();
  }
});

test("401 na recarga mostra a sessão expirada e mantém a lista", async () => {
  semearEntregas([DELIVERY_PENDENTE]);
  vi.useFakeTimers({ toFake: ["setInterval", "clearInterval"] });
  try {
    await montar("farmaceutico", 5000);
    await screen.findByRole("button", { name: "Aprovar entrega 4" });
    server.use(http.get("http://localhost:8000/deliveries", () => HttpResponse.json({ detail: "Faça login para continuar." }, { status: 401 })));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });
    await waitFor(() => expect(screen.getByText(/Sua sessão expirou/)).toBeInTheDocument());
    expect(within(screen.getByRole("list")).getAllByRole("listitem")).toHaveLength(1);
  } finally {
    vi.useRealTimers();
  }
});
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd web && npx vitest run src/pages/AprovacoesPanel.test.tsx`
Expected: FAIL (`./AprovacoesPanel` não existe).

- [ ] **Step 3: Implementar**

`web/src/pages/AprovacoesPanel.tsx`:

```tsx
import { Check, X } from "lucide-react";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { ApiError, type AprovacoesApi, type CatalogoApi, type EntregasApi } from "../api/ApiClient";
import type { Role } from "../api/types";
import { AlertBanner } from "../components/AlertBanner";
import { Button } from "../components/Button";
import { Card } from "../components/Card";
import { DeliveryQueueRow } from "../components/DeliveryQueueRow";
import { EntregaAdapter, type Entrega } from "../domain/EntregaAdapter";
import { MOTIVO_MAX, validarMotivo } from "../domain/motivo";
import { pendentesDeAprovacao, podeAprovar } from "../domain/operacoes";

interface Props {
  api: EntregasApi & AprovacoesApi & CatalogoApi;
  role: Role;
  intervaloMs?: number;
}

const CAMPO = "min-h-controle w-full rounded-controle border border-neutro-200 bg-branco px-3 py-2 text-base";

// Pedidos críticos esperando a assinatura do farmacêutico. Recarrega sozinho: o pedido chega sem ninguém tocar na tela.
export function AprovacoesPanel({ api, role, intervaloMs = 5000 }: Props) {
  const [pedidos, setPedidos] = useState<Entrega[] | null>(null);
  const [sessaoExpirada, setSessaoExpirada] = useState(false);
  const [erroRecarga, setErroRecarga] = useState<string | null>(null);
  const [erroAcao, setErroAcao] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const [recusando, setRecusando] = useState<number | null>(null);
  const [motivo, setMotivo] = useState("");
  const [erroMotivo, setErroMotivo] = useState<string | null>(null);
  const aprova = podeAprovar(role);

  const carregar = useCallback(async () => {
    const [entregas, locais] = await Promise.all([api.deliveries(), api.locations()]);
    const adapter = new EntregaAdapter((id) => locais.find((l) => l.id === id)?.name ?? id);
    setPedidos(pendentesDeAprovacao(entregas).map((d) => adapter.adaptar(d)));
    setErroRecarga(null);
  }, [api]);

  const falhou = useCallback((err: unknown) => {
    if (err instanceof ApiError && err.status === 401) {
      setSessaoExpirada(true);
      setErroRecarga(null);
    } else setErroRecarga(err instanceof Error ? err.message : "Erro desconhecido. Tente de novo.");
  }, []);

  useEffect(() => {
    carregar().catch(falhou);
  }, [carregar, falhou]);

  useEffect(() => {
    if (sessaoExpirada) return;
    const id = setInterval(() => carregar().catch(falhou), intervaloMs);
    return () => clearInterval(id);
  }, [carregar, falhou, intervaloMs, sessaoExpirada]);

  async function agir(acao: () => Promise<unknown>, sucesso: string) {
    setOcupado(true);
    setErroAcao(null);
    setAviso(null);
    try {
      await acao();
      setAviso(sucesso);
      setRecusando(null);
      setMotivo("");
      await carregar().catch(falhou);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) falhou(err);
      else setErroAcao(err instanceof Error ? err.message : "Não foi possível concluir. Tente de novo.");
    } finally {
      setOcupado(false);
    }
  }

  function abrirRecusa(id: number) {
    setRecusando(id);
    setMotivo("");
    setErroMotivo(null);
    setErroAcao(null);
    setAviso(null);
  }

  function confirmarRecusa(e: FormEvent) {
    e.preventDefault();
    const erro = validarMotivo(motivo);
    setErroMotivo(erro);
    if (erro || recusando === null) return;
    const id = recusando;
    void agir(() => api.rejectDelivery(id, motivo.trim()), `Entrega ${id} recusada. O solicitante verá o motivo.`);
  }

  return (
    <section aria-labelledby="titulo-aprovacoes" className="grid gap-4">
      <h2 id="titulo-aprovacoes" className="font-display text-xl font-semibold">Aprovações</h2>
      {sessaoExpirada && <AlertBanner>Sua sessão expirou. Entre de novo para ver os pedidos pendentes.</AlertBanner>}
      {erroRecarga && <AlertBanner>Não foi possível atualizar os pedidos. {erroRecarga}</AlertBanner>}
      {erroAcao && <AlertBanner>{erroAcao}</AlertBanner>}
      {aviso && (
        <p role="status" className="rounded-controle bg-sucesso-50 px-4 py-3 text-sucesso-700">
          {aviso}
        </p>
      )}
      {!aprova && <p className="text-sm text-neutro-500">Só o farmacêutico aprova ou recusa pedidos críticos.</p>}
      <Card>
        {pedidos === null ? (
          <p className="text-neutro-500">Carregando…</p>
        ) : pedidos.length === 0 ? (
          <p className="py-4 text-center text-neutro-500">Nenhum pedido crítico esperando a sua assinatura.</p>
        ) : (
          <ul className="grid gap-2">
            {pedidos.map((p) => (
              <DeliveryQueueRow
                key={p.id}
                entrega={p}
                acao={
                  aprova ? (
                    <>
                      <Button aria-label={`Aprovar entrega ${p.id}`} disabled={ocupado} onClick={() => void agir(() => api.approveDelivery(p.id), `Entrega ${p.id} aprovada. O robô vai buscar assim que estiver livre.`)}>
                        <Check size={20} aria-hidden="true" />
                        Aprovar
                      </Button>
                      <Button variant="secundario" aria-label={`Recusar entrega ${p.id}`} disabled={ocupado} onClick={() => abrirRecusa(p.id)}>
                        <X size={20} aria-hidden="true" />
                        Recusar
                      </Button>
                    </>
                  ) : undefined
                }
              />
            ))}
          </ul>
        )}
      </Card>
      {aprova && recusando !== null && (
        <Card>
          <form onSubmit={confirmarRecusa} className="grid gap-3" noValidate>
            <label htmlFor="motivo-recusa" className="text-sm font-medium">
              Motivo da recusa
            </label>
            <textarea id="motivo-recusa" className={CAMPO} rows={3} maxLength={MOTIVO_MAX + 20} value={motivo} onChange={(e) => setMotivo(e.target.value)} />
            <p className="text-xs text-neutro-500">Entrega {recusando}: o solicitante lê este texto em Minhas entregas.</p>
            {erroMotivo && (
              <p role="alert" className="text-sm text-vermelho-600">
                {erroMotivo}
              </p>
            )}
            <div className="flex flex-wrap gap-2">
              <Button type="submit" disabled={ocupado}>
                Confirmar recusa
              </Button>
              <Button variant="fantasma" disabled={ocupado} onClick={() => setRecusando(null)}>
                Cancelar
              </Button>
            </div>
          </form>
        </Card>
      )}
    </section>
  );
}
```

Nota de design: o botão "Confirmar recusa" é o primário do formulário e "Recusar" (na linha) é secundário; recusar não é vermelho. `text-vermelho-600` só no erro de validação.

- [ ] **Step 4: Rodar e ver passar**

Run: `cd web && npx vitest run src/pages/AprovacoesPanel.test.tsx` (repita 3 vezes: há timers) e `npx tsc --noEmit`
Expected: PASS nas três. Se o teste do 401 falhar por corrida, use `await waitFor` como já está.

- [ ] **Step 5: Commit**

```bash
git add web/src/pages/AprovacoesPanel.tsx web/src/pages/AprovacoesPanel.test.tsx
git commit -m "feat(web): painel de Aprovacoes (aprovar, recusar com motivo, admin so le)

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 8: `FarmaciaPage` (Aprovações + Estoque)

**Files:**
- Create: `web/src/pages/FarmaciaPage.tsx`
- Modify: `web/src/pages/EstoquePage.tsx`, `web/src/pages/EstoquePage.test.tsx`, `web/src/App.tsx`, `web/src/App.test.tsx`
- Test: `web/src/pages/FarmaciaPage.test.tsx` (novo)

**Interfaces:**
- Consumes: `AprovacoesPanel`, `EstoquePage`.
- Produces: `FarmaciaPage({ api, role })` com `<h1>Farmácia</h1>`, a seção Aprovações e a seção Estoque (`<h2>Estoque</h2>` com as abas Saldos/Histórico). `EstoquePage` passa a ser só a seção (h2).

- [ ] **Step 1: Escrever os testes que falham**

`web/src/pages/FarmaciaPage.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { HttpApiClient } from "../api/HttpApiClient";
import { DELIVERY_PENDENTE } from "../api/mocks/fixtures";
import { semearEntregas } from "../api/mocks/handlers";
import { FarmaciaPage } from "./FarmaciaPage";

async function montar(role: "farmaceutico" | "admin") {
  const api = new HttpApiClient();
  await api.login(role === "admin" ? "admin" : "farmaceutico1", "demo");
  render(<FarmaciaPage api={api} role={role} />);
}

test("a Farmácia tem as Aprovações no topo e o Estoque embaixo", async () => {
  semearEntregas([DELIVERY_PENDENTE]);
  await montar("farmaceutico");
  expect(screen.getByRole("heading", { level: 1, name: "Farmácia" })).toBeInTheDocument();
  const titulos = screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent);
  expect(titulos).toEqual(["Aprovações", "Estoque"]);
  expect(await screen.findByText("Bolsa de sangue O negativo")).toBeInTheDocument();
  expect(await screen.findByRole("button", { name: "Aprovar entrega 4" })).toBeInTheDocument();
});

test("o admin vê a fila e o estoque, sem botões de aprovar", async () => {
  semearEntregas([DELIVERY_PENDENTE]);
  await montar("admin");
  expect(await screen.findByText("Bolsa de sangue O negativo")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /Aprovar|Recusar/ })).not.toBeInTheDocument();
});
```

Ajuste `EstoquePage.test.tsx`: o título agora é `heading level 2 "Estoque"` (`screen.getByRole("heading", { name: "Estoque" })`).

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd web && npx vitest run src/pages/FarmaciaPage.test.tsx src/pages/EstoquePage.test.tsx`
Expected: FAIL.

- [ ] **Step 3: Implementar**

`web/src/pages/EstoquePage.tsx`: troque o `<section>`/`<h1>` por seção com `h2`:

```tsx
  return (
    <section aria-labelledby="titulo-estoque">
      <h2 id="titulo-estoque" className="font-display text-xl font-semibold">Estoque</h2>
      <Card className="mt-4 grid gap-4">
```

(o resto do arquivo não muda).

`web/src/pages/FarmaciaPage.tsx`:

```tsx
import type { AprovacoesApi, CatalogoApi, EntregasApi, HistoricoApi } from "../api/ApiClient";
import type { Role } from "../api/types";
import { AprovacoesPanel } from "./AprovacoesPanel";
import { EstoquePage } from "./EstoquePage";

// Só farmacêutico e admin chegam aqui (o AppShell esconde a aba dos outros papéis).
export function FarmaciaPage({ api, role }: { api: CatalogoApi & HistoricoApi & EntregasApi & AprovacoesApi; role: Role }) {
  return (
    <div className="grid gap-8">
      <h1 className="font-display text-2xl font-bold">Farmácia</h1>
      <AprovacoesPanel api={api} role={role} />
      <EstoquePage api={api} />
    </div>
  );
}
```

`web/src/App.tsx`: troque `<EstoquePage api={cliente} />` por `<FarmaciaPage api={cliente} role={me.role} />` (importe `FarmaciaPage`; remova o import de `EstoquePage`). `App.test.tsx`: o teste do farmacêutico continua esperando o heading "Farmácia" (agora o `h1`).

- [ ] **Step 4: Rodar e ver passar**

Run: `cd web && npx vitest run && npx tsc --noEmit`
Expected: PASS. Em `mobile.test.tsx` o teste "Estoque: filtro e abas têm 44 px" renderiza `EstoquePage` sozinho e continua valendo.

- [ ] **Step 5: Commit**

```bash
git add web/src
git commit -m "feat(web): FarmaciaPage com Aprovacoes no topo e o Estoque embaixo

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Minhas entregas mostra "Recusada pela farmácia: <motivo>"

**Files:**
- Modify: `web/src/components/DeliveryQueueRow.tsx`
- Test: `web/src/components/DeliveryQueueRow.test.tsx`, `web/src/pages/MinhasEntregasPage.test.tsx`

- [ ] **Step 1: Escrever os testes que falham**

Acrescente a `web/src/components/DeliveryQueueRow.test.tsx` (use o `ENTREGA` ou o helper já existente no arquivo; abaixo, com literal completo):

```tsx
test("entrega recusada mostra o motivo; sem recusa não mostra nada", () => {
  const base = { id: 4, origem: "Banco de sangue", destino: "Consultório 1", itens: [{ nome: "Bolsa", quantidade: 2 }], prioridade: "critica" as const, status: "CANCELADA" as const, solicitanteId: 1, solicitadaEm: new Date("2026-11-09T13:40:00Z"), motivoDaRecusa: "Use a prescrição digital" };
  const { rerender } = render(<ul><DeliveryQueueRow entrega={base} /></ul>);
  expect(screen.getByText("Recusada pela farmácia: Use a prescrição digital")).toBeInTheDocument();
  rerender(<ul><DeliveryQueueRow entrega={{ ...base, motivoDaRecusa: null }} /></ul>);
  expect(screen.queryByText(/Recusada pela farmácia/)).not.toBeInTheDocument();
});
```

Acrescente a `web/src/pages/MinhasEntregasPage.test.tsx`:

```tsx
test("o solicitante vê o motivo da recusa em Minhas entregas", async () => {
  semearEntregas([{ ...DELIVERY_PENDENTE, status: "CANCELADA", cancel_reason: "Use a prescrição digital" }]);
  render(<MinhasEntregasPage api={new HttpApiClient()} usuario={ME} onRequest={vi.fn()} />);
  expect(await screen.findByText("Recusada pela farmácia: Use a prescrição digital")).toBeInTheDocument();
});
```

(importe `DELIVERY_PENDENTE` das fixtures).

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd web && npx vitest run src/components/DeliveryQueueRow.test.tsx src/pages/MinhasEntregasPage.test.tsx`
Expected: FAIL.

- [ ] **Step 3: Implementar**

`web/src/components/DeliveryQueueRow.tsx`: dentro do `<span className="min-w-0 flex-1 text-sm">`, depois do texto dos itens:

```tsx
        {entrega.motivoDaRecusa && <span className="mt-1 block text-neutro-600">Recusada pela farmácia: {entrega.motivoDaRecusa}</span>}
```

- [ ] **Step 4: Rodar e ver passar**

Run: `cd web && npx vitest run && npx tsc --noEmit`
Expected: PASS (se algum teste monta `Entrega` literal, acrescente `motivoDaRecusa: null`).

- [ ] **Step 5: Commit**

```bash
git add web/src
git commit -m "feat(web): Minhas entregas mostra o motivo da recusa pela farmacia

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 10: 44 px, documentação e suítes

**Files:**
- Modify: `web/src/mobile.test.tsx`, `web/AGENTS.md`, `backend/AGENTS.md`
- Test: `web/src/mobile.test.tsx`

- [ ] **Step 1: Teste de 44 px da Farmácia**

Acrescente a `web/src/mobile.test.tsx` (com os imports que o arquivo já usa para `HttpApiClient`, `semearEntregas` e `conferirAlvos`; importe `DELIVERY_PENDENTE` e `FarmaciaPage`):

```tsx
test("Farmácia: Aprovar, Recusar, o campo do motivo e as abas têm 44 px", async () => {
  semearEntregas([DELIVERY_PENDENTE]);
  const api = new HttpApiClient();
  await api.login("farmaceutico1", "demo");
  const { container } = render(<FarmaciaPage api={api} role="farmaceutico" />);
  await userEvent.click(await screen.findByRole("button", { name: "Recusar entrega 4" }));
  await screen.findByLabelText("Motivo da recusa");
  await screen.findByText("Bolsa de sangue O negativo");
  conferirAlvos(container);
});
```

Run: `cd web && npx vitest run src/mobile.test.tsx` — se `conferirAlvos` reclamar do `textarea` (ele cobre `button`, `select`, `input`), ajuste a classe `CAMPO` para `min-h-controle` (já tem) e confira que o helper aceita `textarea`; senão acrescente `textarea` ao seletor do helper.

- [ ] **Step 2: Documentação**

`web/AGENTS.md`: acrescente no bloco de telas: "**Farmácia** (só `farmaceutico` e `admin`; o `AppShell` esconde a aba dos outros papéis via `podeVerFarmacia`): `AprovacoesPanel` (pedidos `PENDENTE_APROVACAO`, recarrega a cada 5 s; o farmacêutico aprova ou recusa com motivo de 3 a 200 caracteres; o admin só lê) e o Estoque (saldos e histórico). Minhas entregas mostra "Recusada pela farmácia: <motivo>". `GET /stock` continua aberto a todo usuário logado (o formulário de Solicitar usa)." Troque as menções à aba "Estoque" por "Farmácia".

`backend/AGENTS.md`: acrescente: "`POST /deliveries/{id}/reject` (só `farmaceutico`): `RejectDelivery` cancela o pedido crítico pendente com o motivo em `Delivery.cancel_reason` e estorna a reserva. Bancos antigos ganham a coluna sozinhos (`create_db` faz o `ALTER TABLE`)."

- [ ] **Step 3: Rodar tudo**

Run:
```bash
cd backend && .venv/bin/python -m pytest -q; cd ..
cd web && npm test -- --run && npm run build; cd ..
source /opt/ros/jazzy/setup.bash && python3 -m pytest tools robot -q
```
Expected: tudo verde.

- [ ] **Step 4: Commit**

```bash
git add web backend/AGENTS.md
git commit -m "docs(web): 44 px da Farmacia e notas de AGENTS sobre aprovacoes e recusa

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

## Verificação no navegador (depois das tasks)

Com o backend real e o robô no Gazebo (`bash robot/scripts/demo.sh`): `medico1` pede um crítico; `farmaceutico1` vê em Farmácia → Aprovações e aprova; o robô sai; um segundo crítico é recusado com motivo; `medico1` vê "Recusada pela farmácia: <motivo>" em Minhas entregas; Farmácia → Estoque → Histórico mostra o `ESTORNO`; `medico1` não vê a aba Farmácia; `admin` vê a fila sem botões.

## Self-review

- **Spec coverage:** aba renomeada e restrita (Task 6), Aprovações com Aprovar/Recusar/motivo/admin sem botões e recarga de 5 s (7), endpoint e Command (2), `cancel_reason` (1), Minhas entregas (9), design system e 44 px (7, 10), testes 403/404/409/422 e contrato do backend (2, 3), `GET /stock` aberto (nada muda).
- **Placeholders:** nenhum; cada passo traz código.
- **Tipos:** `AprovacoesApi.approveDelivery/rejectDelivery`, `pendentesDeAprovacao`, `podeVerFarmacia`, `podeAprovar`, `validarMotivo`, `Entrega.motivoDaRecusa`, `PageId "farmacia"` e `AppShell role` têm o mesmo nome em todas as tasks.
