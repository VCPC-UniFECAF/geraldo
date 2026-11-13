from sqlmodel import Session

from app.commands.common import load_visible, notify_stocks, release_reservation
from app.commands.errors import InvalidState, NotAllowed
from app.events import DeliveryChanged, Subject
from app.models import Delivery, DeliveryStatus, Role, User
from app.movements import EstornoCreator, MovementCreator

CANCELLABLE = (
    DeliveryStatus.PENDENTE_APROVACAO,
    DeliveryStatus.NA_FILA,
    DeliveryStatus.EM_ROTA,
    DeliveryStatus.AGUARDANDO_RECEBIMENTO,
)


# COMMAND
class CancelDelivery:
    """Comando CancelarEntrega: só quem pediu (ou o admin) cancela; a reserva volta ao disponível (ESTORNO)."""

    def __init__(
        self,
        session: Session,
        user: User,
        delivery_id: int,
        *,
        estorno: MovementCreator | None = None,
        events: Subject | None = None,
    ) -> None:
        self.session = session
        self.user = user
        self.delivery_id = delivery_id
        self._estorno = estorno or EstornoCreator()
        self._events = events if events is not None else Subject()

    def execute(self) -> Delivery:
        delivery = load_visible(self.session, self.user, self.delivery_id)
        if self.user.role != Role.admin and delivery.requested_by != self.user.id:
            raise NotAllowed("Só quem pediu a entrega ou um administrador pode cancelá-la. Peça a quem fez o pedido.")
        if delivery.status not in CANCELLABLE:
            raise InvalidState(
                f"A entrega está {delivery.status.value} e não pode mais ser cancelada. Confira o status na lista de entregas."
            )
        old_status = delivery.status
        stocks = release_reservation(self.session, delivery, self._estorno)
        delivery.status = DeliveryStatus.CANCELADA
        self.session.add(delivery)
        self.session.commit()
        self.session.refresh(delivery)
        self._events.notify(DeliveryChanged(delivery.id, old_status, delivery.status, self.user.username))
        notify_stocks(self._events, stocks)
        return delivery
