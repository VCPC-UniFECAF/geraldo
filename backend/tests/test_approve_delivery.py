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
    pharmacist = session.exec(select(User).where(User.username == "farmaceutico1")).one()
    payload = DeliveryCreate(origin_id="farmacia", items=[DeliveryItemIn(item_id="dipirona-500mg", quantity=1)], priority=Priority.critica)
    delivery = CreateDelivery(session, medico, payload).execute()

    class NoApprovalNeeded:
        needs_approval = False

    with pytest.raises(InvalidState, match="não espera aprovação"):
        ApproveDelivery(session, pharmacist, delivery.id, policy_for=lambda _: NoApprovalNeeded()).execute()
    assert ApproveDelivery(session, pharmacist, delivery.id).execute().status == DeliveryStatus.NA_FILA
