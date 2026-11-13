from sqlmodel import select

from app.commands.create_delivery import CreateDelivery
from app.models import DeliveryStatus, Priority, User
from app.movements import ReservaCreator
from app.priority import PriorityPolicy
from app.schemas import DeliveryCreate, DeliveryItemIn


class HoldEverything(PriorityPolicy):
    priority = Priority.rotina
    rank = 9
    initial_status = DeliveryStatus.PENDENTE_APROVACAO


class SpyReserva(ReservaCreator):
    def __init__(self) -> None:
        self.calls = []

    def register(self, stock, *, delivery_id, quantity):
        self.calls.append((stock.item_id, quantity))
        return super().register(stock, delivery_id=delivery_id, quantity=quantity)


def test_command_uses_the_injected_policy_and_movement_creator(session):
    user = session.exec(select(User).where(User.username == "medico1")).one()
    spy = SpyReserva()
    payload = DeliveryCreate(origin_id="farmacia", items=[DeliveryItemIn(item_id="dipirona-500mg", quantity=2)], priority=Priority.media)

    delivery = CreateDelivery(session, user, payload, policy_for=lambda _: HoldEverything(), reserva=spy).execute()

    assert delivery.status == DeliveryStatus.PENDENTE_APROVACAO
    assert spy.calls == [("dipirona-500mg", 2)]
