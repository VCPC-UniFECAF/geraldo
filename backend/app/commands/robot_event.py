from typing import NamedTuple

from sqlmodel import Session

from app.commands.common import notify_stocks, release_reservation
from app.commands.errors import InvalidState, NotFound
from app.events import DeliveryChanged, Subject
from app.models import Delivery, DeliveryStatus
from app.movements import EstornoCreator, MovementCreator
from app.schemas import RobotEventIn, RobotEventType

EM_ROTA = DeliveryStatus.EM_ROTA
AGUARDANDO = DeliveryStatus.AGUARDANDO_RECEBIMENTO


class Step(NamedTuple):
    new_status: DeliveryStatus
    releases_reservation: bool = False


# Tabela de transições: evento -> status em que ele vale -> o que acontece. Evento novo = linhas novas.
TRANSITIONS: dict[RobotEventType, dict[DeliveryStatus, Step]] = {
    RobotEventType.LOADED: {EM_ROTA: Step(EM_ROTA)},
    RobotEventType.ARRIVED: {EM_ROTA: Step(AGUARDANDO)},
    # a tampa só é liberada depois do ENTREGUE (docs/contracts/robot-protocol.md, passo 7): sem mudar o status
    RobotEventType.UNLOCKED: {DeliveryStatus.ENTREGUE: Step(DeliveryStatus.ENTREGUE)},
    RobotEventType.FAILED: {EM_ROTA: Step(DeliveryStatus.FALHOU, True), AGUARDANDO: Step(DeliveryStatus.FALHOU, True)},
}


# COMMAND
class RegisterRobotEvent:
    """Comando RegistrarEventoDoRobô: aplica LOADED, ARRIVED, UNLOCKED ou FAILED à entrega."""

    def __init__(
        self,
        session: Session,
        payload: RobotEventIn,
        *,
        estorno: MovementCreator | None = None,
        events: Subject | None = None,
        actor: str = "robo",
    ) -> None:
        self._session = session
        self._payload = payload
        self._estorno = estorno or EstornoCreator()
        self._events = events if events is not None else Subject()
        self._actor = actor

    def execute(self) -> Delivery:
        delivery = self._session.get(Delivery, self._payload.delivery_id)
        if delivery is None:
            raise NotFound("Entrega não encontrada. Confira o delivery_id do evento.")
        step = TRANSITIONS[self._payload.event].get(delivery.status)
        if step is None:
            raise InvalidState(
                f"O evento {self._payload.event.value} não se aplica a uma entrega {delivery.status.value}. "
                "Confira o status da entrega antes de enviar o evento."
            )
        old_status = delivery.status
        stocks = release_reservation(self._session, delivery, self._estorno) if step.releases_reservation else []
        delivery.status = step.new_status
        self._session.add(delivery)
        self._session.commit()
        self._session.refresh(delivery)
        if delivery.status != old_status:
            self._events.notify(DeliveryChanged(delivery.id, old_status, delivery.status, self._actor))
        notify_stocks(self._events, stocks)
        return delivery
