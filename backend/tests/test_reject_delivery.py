import pytest
from sqlalchemy import inspect, text
from sqlmodel import select

from app.commands.create_delivery import CreateDelivery
from app.commands.errors import InvalidState
from app.commands.reject_delivery import RejectDelivery
from app.db import create_db, make_engine
from app.events import DeliveryChanged
from app.models import DeliveryStatus, Movement, MovementType, Priority, User
from app.schemas import DeliveryCreate, DeliveryItemIn

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
    assert client.post(f"/deliveries/{delivery_id}/reject", json={"reason": "Sem justificativa"}).status_code == 401
    for user in ("medico1", "enfermeiro1", "admin", "robo"):
        assert reject(client, auth, delivery_id, user).status_code == 403, user
    assert client.get(f"/deliveries/{delivery_id}", headers=auth("medico1")).json()["status"] == "PENDENTE_APROVACAO"


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


def test_the_command_uses_the_injected_estorno(session):
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
