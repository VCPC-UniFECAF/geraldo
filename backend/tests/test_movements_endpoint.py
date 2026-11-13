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
