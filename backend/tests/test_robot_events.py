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
        DeliveryChanged(delivery_id, DeliveryStatus(stage), DeliveryStatus.FALHOU, "robo", "não chegou ao destino"),
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
