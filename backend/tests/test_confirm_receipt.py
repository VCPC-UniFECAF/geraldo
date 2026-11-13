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
