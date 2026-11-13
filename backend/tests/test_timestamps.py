from datetime import datetime

from app.schemas import DeliveryOut, MovementOut


def test_naive_created_at_leaves_the_api_as_utc_with_offset():
    naive = datetime(2026, 11, 13, 15, 0, 0, 123000)  # o que um banco sem fuso devolveria
    delivery = DeliveryOut(id=1, origin_id="a", dest_id="b", items=[], priority="media", status="NA_FILA", requested_by=1, created_at=naive)
    movement = MovementOut(id=1, delivery_id=None, type="RESERVA", item_id="i", location_id="a", quantity=1, created_at=naive)
    for out in (delivery, movement):
        assert out.model_dump(mode="json")["created_at"].endswith("Z")


def test_created_at_in_the_responses_carries_the_utc_offset(client, auth):
    headers = auth("medico1")
    created = client.post("/deliveries", headers=headers, json={"origin_id": "farmacia", "items": [{"item_id": "dipirona-500mg", "quantity": 1}], "priority": "media"})
    assert created.json()["created_at"].endswith("Z")
    assert client.get("/movements", headers=auth("admin")).json()[0]["created_at"].endswith("Z")
