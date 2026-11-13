from sqlmodel import select

from app.models import Movement, MovementType


def payload(**over) -> dict:
    base = {"origin_id": "farmacia", "items": [{"item_id": "dipirona-500mg", "quantity": 10}], "priority": "media"}
    base.update(over)
    return base


def farmacia_stock(client, auth) -> dict:
    return client.get("/stock", params={"location_id": "farmacia"}, headers=auth("medico1")).json()[0]


def test_destination_defaults_to_the_users_location(client, auth):
    r = client.post("/deliveries", json=payload(), headers=auth("medico1"))
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["dest_id"] == "consultorio1"
    assert body["status"] == "NA_FILA"
    assert body["items"] == [{"item_id": "dipirona-500mg", "quantity": 10}]


def test_explicit_destination_is_respected(client, auth):
    r = client.post("/deliveries", json=payload(dest_id="enfermaria214"), headers=auth("medico1"))
    assert r.status_code == 201 and r.json()["dest_id"] == "enfermaria214"


def test_creating_reserves_stock_and_logs_a_movement(client, auth, session):
    client.post("/deliveries", json=payload(), headers=auth("medico1"))
    stock = farmacia_stock(client, auth)
    assert (stock["quantity"], stock["reserved"]) == (420, 10)
    moves = session.exec(select(Movement)).all()
    assert len(moves) == 1
    assert (moves[0].type, moves[0].item_id, moves[0].location_id, moves[0].quantity) == (
        MovementType.RESERVA, "dipirona-500mg", "farmacia", 10,
    )


def test_duplicate_items_are_summed(client, auth):
    items = [{"item_id": "dipirona-500mg", "quantity": 5}, {"item_id": "dipirona-500mg", "quantity": 7}]
    r = client.post("/deliveries", json=payload(items=items), headers=auth("medico1"))
    assert r.status_code == 201
    assert r.json()["items"] == [{"item_id": "dipirona-500mg", "quantity": 12}]
    assert farmacia_stock(client, auth)["reserved"] == 12


def test_critical_delivery_waits_for_the_pharmacists_approval(client, auth):
    body = payload(origin_id="banco_sangue", items=[{"item_id": "bolsa-sangue-o-neg", "quantity": 2}], priority="critica")
    r = client.post("/deliveries", json=body, headers=auth("medico1"))
    assert r.status_code == 201 and r.json()["status"] == "PENDENTE_APROVACAO"


def test_insufficient_stock_is_409_and_reserves_nothing(client, auth):
    items = [{"item_id": "dipirona-500mg", "quantity": 1000}]
    r = client.post("/deliveries", json=payload(items=items), headers=auth("medico1"))
    assert r.status_code == 409
    assert "Estoque insuficiente" in r.json()["detail"]
    assert farmacia_stock(client, auth)["reserved"] == 0


def test_reservations_count_against_the_available_balance(client, auth):
    items = [{"item_id": "dipirona-500mg", "quantity": 400}]
    assert client.post("/deliveries", json=payload(items=items), headers=auth("medico1")).status_code == 201
    r = client.post("/deliveries", json=payload(items=[{"item_id": "dipirona-500mg", "quantity": 30}]), headers=auth("medico2"))
    assert r.status_code == 409


def test_invalid_requests_are_422(client, auth):
    h = auth("medico1")
    assert client.post("/deliveries", json=payload(origin_id="narnia"), headers=h).status_code == 422
    assert client.post("/deliveries", json=payload(dest_id="recepcao"), headers=h).status_code == 422   # sem waypoint
    assert client.post("/deliveries", json=payload(dest_id="farmacia"), headers=h).status_code == 422   # origem = destino
    assert client.post("/deliveries", json=payload(items=[{"item_id": "cura-de-tudo", "quantity": 1}]), headers=h).status_code == 422
    assert client.post("/deliveries", json=payload(items=[]), headers=h).status_code == 422
    assert client.post("/deliveries", json=payload(items=[{"item_id": "dipirona-500mg", "quantity": 0}]), headers=h).status_code == 422
    assert client.post("/deliveries", json=payload(priority="urgentissima"), headers=h).status_code == 422


def test_user_without_default_location_must_inform_the_destination(client, auth):
    r = client.post("/deliveries", json=payload(), headers=auth("admin"))
    assert r.status_code == 422 and "destino" in r.json()["detail"].lower()


def test_roles_and_authentication(client, auth):
    assert client.post("/deliveries", json=payload()).status_code == 401
    assert client.post("/deliveries", json=payload(), headers=auth("robo")).status_code == 403


def test_list_shows_own_deliveries_to_doctors_and_all_to_the_pharmacist(client, auth):
    client.post("/deliveries", json=payload(), headers=auth("medico1"))
    client.post("/deliveries", json=payload(), headers=auth("medico2"))
    assert len(client.get("/deliveries", headers=auth("medico1")).json()) == 1
    assert len(client.get("/deliveries", headers=auth("farmaceutico1")).json()) == 2
    assert len(client.get("/deliveries", headers=auth("admin")).json()) == 2


def test_get_delivery_of_someone_else_is_404(client, auth):
    delivery_id = client.post("/deliveries", json=payload(), headers=auth("medico1")).json()["id"]
    assert client.get(f"/deliveries/{delivery_id}", headers=auth("medico1")).status_code == 200
    assert client.get(f"/deliveries/{delivery_id}", headers=auth("farmaceutico1")).status_code == 200
    assert client.get(f"/deliveries/{delivery_id}", headers=auth("medico2")).status_code == 404
    assert client.get("/deliveries/9999", headers=auth("medico1")).status_code == 404


def test_the_robot_can_read_any_delivery_but_does_not_list_them(client, auth):
    delivery_id = client.post("/deliveries", json=payload(), headers=auth("medico1")).json()["id"]
    assert client.get(f"/deliveries/{delivery_id}", headers=auth("robo")).status_code == 200
    assert client.get("/deliveries", headers=auth("robo")).json() == []
