"""Pedaços que os comandos de entrega compartilham (funções simples, sem estado)."""
from sqlmodel import Session, select

from app.commands.errors import NotFound
from app.events import StockChanged, Subject
from app.models import Delivery, DeliveryItem, Role, Stock, User
from app.movements import MovementCreator

SEE_ALL = (Role.admin, Role.farmaceutico)


def load_visible(session: Session, user: User, delivery_id: int) -> Delivery:
    """Entrega que o usuário pode ver; senão 404 (não revelamos que ela existe)."""
    delivery = session.get(Delivery, delivery_id)
    if delivery is None or (user.role not in SEE_ALL and delivery.requested_by != user.id):
        raise NotFound("Entrega não encontrada. Confira o número e tente de novo.")
    return delivery


def delivery_lines(session: Session, delivery: Delivery) -> list[DeliveryItem]:
    return list(session.exec(select(DeliveryItem).where(DeliveryItem.delivery_id == delivery.id).order_by(DeliveryItem.id)).all())


def release_reservation(session: Session, delivery: Delivery, estorno: MovementCreator) -> list[Stock]:
    """Devolve ao disponível tudo que a entrega tinha reservado na origem (um ESTORNO por item)."""
    stocks = []
    for line in delivery_lines(session, delivery):
        stock = session.get(Stock, (delivery.origin_id, line.item_id))
        session.add(estorno.register(stock, delivery_id=delivery.id, quantity=line.quantity))
        session.add(stock)
        stocks.append(stock)
    return stocks


def notify_stocks(events: Subject, stocks: list[Stock]) -> None:
    for stock in stocks:
        events.notify(StockChanged(stock.location_id, stock.item_id, stock.quantity, stock.reserved, stock.minimum))
