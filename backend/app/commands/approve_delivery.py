from sqlmodel import Session

from app.commands.common import load_visible
from app.commands.errors import InvalidState, NotAllowed
from app.events import DeliveryChanged, Subject
from app.models import Delivery, DeliveryStatus, User
from app.priority import policy_for
from app.stock_lock import serialized, stock_lock


# COMMAND
class ApproveDelivery:
    """Comando AprovarEntrega: a assinatura dupla da prioridade crítica.

    Quem aprova precisa ser outra pessoa além de quem pediu (por isso "dupla"); o papel
    farmacêutico é conferido no router.
    """

    def __init__(
        self,
        session: Session,
        user: User,
        delivery_id: int,
        *,
        policy_for=policy_for,
        events: Subject | None = None,
        lock=stock_lock,
    ) -> None:
        self._session = session
        self._user = user
        self._delivery_id = delivery_id
        self._policy_for = policy_for
        self._events = events if events is not None else Subject()
        self._lock = lock

    @serialized
    def execute(self) -> Delivery:
        delivery = load_visible(self._session, self._user, self._delivery_id)
        waiting = delivery.status == DeliveryStatus.PENDENTE_APROVACAO
        if not (waiting and self._policy_for(delivery.priority).needs_approval):
            raise InvalidState(
                f"A entrega está {delivery.status.value} e não espera aprovação. Só entregas críticas pendentes são aprovadas."
            )
        if delivery.requested_by == self._user.id:
            raise NotAllowed(
                "A assinatura dupla exige outra pessoa: quem pediu a entrega não pode aprová-la. Peça a outro farmacêutico."
            )
        old_status = delivery.status
        delivery.status = DeliveryStatus.NA_FILA
        self._session.add(delivery)
        self._session.commit()
        self._session.refresh(delivery)
        self._events.notify(DeliveryChanged(delivery.id, old_status, delivery.status, self._user.username))
        return delivery
