from sqlmodel import Session

from app.events import DeliveryChanged, StockChanged, Subject
from app.models import Delivery, DeliveryItem, Item, Location, Stock, User
from app.movements import MovementCreator, ReservaCreator
from app.priority import policy_for
from app.schemas import DeliveryCreate


class DeliveryError(Exception):
    status_code = 400


class UnknownLocation(DeliveryError):
    status_code = 422


class UnknownItem(DeliveryError):
    status_code = 422


class SameLocation(DeliveryError):
    status_code = 422


class InsufficientStock(DeliveryError):
    status_code = 409


class CreateDelivery:
    """Comando CriarEntrega: valida, reserva o estoque na origem e registra a movimentação.

    As dependências entram pelo construtor (DIP): a política de prioridade e o criador de
    movimentação têm padrão real, e o teste passa um substituto.
    """

    def __init__(
        self,
        session: Session,
        user: User,
        payload: DeliveryCreate,
        *,
        policy_for=policy_for,
        reserva: MovementCreator | None = None,
        events: Subject | None = None,
    ) -> None:
        self.session = session
        self.user = user
        self.payload = payload
        self._policy_for = policy_for
        self._reserva = reserva or ReservaCreator()
        self._events = events if events is not None else Subject()

    def execute(self) -> Delivery:
        dest_id = self._destination()
        self._check_locations(dest_id)
        wanted = self._wanted_items()
        stocks = self._check_stock(wanted)
        return self._create(dest_id, wanted, stocks)

    def _destination(self) -> str:
        dest_id = self.payload.dest_id or self.user.local_id
        if dest_id is None:
            raise UnknownLocation("Informe o destino: seu usuário não tem um local padrão.")
        return dest_id

    def _check_locations(self, dest_id: str) -> None:
        for loc_id in (self.payload.origin_id, dest_id):
            location = self.session.get(Location, loc_id)
            if location is None:
                raise UnknownLocation(f"Local desconhecido: {loc_id}. Escolha um local da lista.")
            if location.waypoint is None:
                raise UnknownLocation(f"O local {location.name} não recebe entregas do robô. Escolha outro.")
        if self.payload.origin_id == dest_id:
            raise SameLocation("Origem e destino são o mesmo local. Escolha destinos diferentes.")

    def _wanted_items(self) -> dict[str, int]:
        wanted: dict[str, int] = {}
        for line in self.payload.items:
            wanted[line.item_id] = wanted.get(line.item_id, 0) + line.quantity
        return wanted

    def _check_stock(self, wanted: dict[str, int]) -> dict[str, Stock]:
        origin_id = self.payload.origin_id
        stocks: dict[str, Stock] = {}
        for item_id, qty in wanted.items():
            if self.session.get(Item, item_id) is None:
                raise UnknownItem(f"Item desconhecido: {item_id}. Escolha um item da lista.")
            stock = self.session.get(Stock, (origin_id, item_id))
            available = 0 if stock is None else stock.quantity - stock.reserved
            if available < qty:
                raise InsufficientStock(
                    f"Estoque insuficiente de {item_id} em {origin_id}: disponível {available}, pedido {qty}. Reduza a quantidade."
                )
            stocks[item_id] = stock
        return stocks

    def _create(self, dest_id: str, wanted: dict[str, int], stocks: dict[str, Stock]) -> Delivery:
        policy = self._policy_for(self.payload.priority)
        delivery = Delivery(
            origin_id=self.payload.origin_id,
            dest_id=dest_id,
            priority=self.payload.priority,
            status=policy.initial_status,
            requested_by=self.user.id,
        )
        self.session.add(delivery)
        self.session.flush()
        for item_id, qty in wanted.items():
            stock = stocks[item_id]
            self.session.add(DeliveryItem(delivery_id=delivery.id, item_id=item_id, quantity=qty))
            self.session.add(self._reserva.register(stock, delivery_id=delivery.id, quantity=qty))
            self.session.add(stock)
        self.session.commit()
        self.session.refresh(delivery)
        self._events.notify(DeliveryChanged(delivery.id, None, delivery.status, self.user.username))
        for stock in stocks.values():
            self._events.notify(StockChanged(stock.location_id, stock.item_id, stock.quantity, stock.reserved, stock.minimum))
        return delivery
