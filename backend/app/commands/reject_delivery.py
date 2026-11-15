from sqlmodel import Session

from app.commands.common import load_visible, notify_stocks, release_reservation
from app.commands.errors import InvalidState
from app.events import DeliveryChanged, Subject
from app.models import Delivery, DeliveryStatus, User
from app.movements import EstornoCreator, MovementCreator
from app.stock_lock import serialized, stock_lock


# COMMAND
class RejectDelivery:
    """Comando RecusarEntrega: o farmacêutico recusa um pedido crítico pendente; a reserva volta (ESTORNO).

    O papel farmacêutico é conferido no router. A entrega vira CANCELADA com o motivo em `cancel_reason`
    (o enum de status não muda: o contrato guarda a recusa como cancelamento com motivo).
    """

    def __init__(
        self,
        session: Session,
        user: User,
        delivery_id: int,
        reason: str,
        *,
        estorno: MovementCreator | None = None,
        events: Subject | None = None,
        lock=stock_lock,
    ) -> None:
        self._session = session
        self._user = user
        self._delivery_id = delivery_id
        self._reason = reason
        self._estorno = estorno or EstornoCreator()
        self._events = events if events is not None else Subject()
        self._lock = lock

    @serialized
    def execute(self) -> Delivery:
        delivery = load_visible(self._session, self._user, self._delivery_id)
        if delivery.status != DeliveryStatus.PENDENTE_APROVACAO:
            raise InvalidState(
                f"A entrega está {delivery.status.value} e não espera aprovação. Só pedidos críticos pendentes são recusados."
            )
        old_status = delivery.status
        stocks = release_reservation(self._session, delivery, self._estorno)
        delivery.status = DeliveryStatus.CANCELADA
        delivery.cancel_reason = self._reason
        self._session.add(delivery)
        self._session.commit()
        self._session.refresh(delivery)
        self._events.notify(DeliveryChanged(delivery.id, old_status, delivery.status, self._user.username))
        notify_stocks(self._events, stocks)
        return delivery
