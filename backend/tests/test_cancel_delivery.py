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
