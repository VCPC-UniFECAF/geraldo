from sqlmodel import Session

from app.commands.common import load_visible, notify_stocks
from app.commands.errors import InvalidState, NotAllowed
from app.events import DeliveryChanged, Subject
from app.models import Delivery, DeliveryStatus, Role, Stock, User
from app.movements import BaixaCreator, CreditoCreator, MovementCreator
from app.queries import delivery_lines


# COMMAND
class ConfirmReceipt:
    """Comando ConfirmarRecebimento: o solicitante recebeu; a entrega termina e o estoque se move.

    Na origem, BAIXA (consome a reserva e o saldo); no destino, CREDITO (soma ao saldo; a linha de
    estoque do destino nasce zerada se ainda não existia). O robô libera a tampa ao ver o ENTREGUE.
    """

    def __init__(
        self,
        session: Session,
        user: User,
        delivery_id: int,
        *,
        baixa: MovementCreator | None = None,
        credito: MovementCreator | None = None,
        events: Subject | None = None,
    ) -> None:
        self._session = session
        self._user = user
        self._delivery_id = delivery_id
        self._baixa = baixa or BaixaCreator()
        self._credito = credito or CreditoCreator()
        self._events = events if events is not None else Subject()

    def execute(self) -> Delivery:
        delivery = load_visible(self._session, self._user, self._delivery_id)
        if self._user.role != Role.admin and delivery.requested_by != self._user.id:
            raise NotAllowed("Só quem pediu a entrega pode confirmar o recebimento. Peça a quem fez o pedido.")
        if delivery.status != DeliveryStatus.AGUARDANDO_RECEBIMENTO:
            raise InvalidState(
                f"A entrega está {delivery.status.value}: o recebimento só pode ser confirmado depois que o robô chegar. "
                "Espere o aviso de chegada."
            )
        stocks = []
        for line in delivery_lines(self._session, delivery):
            origin = self._session.get(Stock, (delivery.origin_id, line.item_id))
            dest = self._session.get(Stock, (delivery.dest_id, line.item_id)) or Stock(location_id=delivery.dest_id, item_id=line.item_id)
            self._session.add(self._baixa.register(origin, delivery_id=delivery.id, quantity=line.quantity))
            self._session.add(self._credito.register(dest, delivery_id=delivery.id, quantity=line.quantity))
            self._session.add_all([origin, dest])
            stocks += [origin, dest]
        delivery.status = DeliveryStatus.ENTREGUE
        self._session.add(delivery)
        self._session.commit()
        self._session.refresh(delivery)
        self._events.notify(DeliveryChanged(delivery.id, DeliveryStatus.AGUARDANDO_RECEBIMENTO, delivery.status, self._user.username))
        notify_stocks(self._events, stocks)
        return delivery
