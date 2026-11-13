"""Pedaços que os comandos de entrega compartilham (funções simples, sem estado)."""
from sqlmodel import Session

from app.commands.errors import NotFound
from app.events import StockChanged, Subject
from app.models import Delivery, Stock, User
from app.movements import MovementCreator
from app.queries import SEE_ALL, delivery_lines, find_delivery_for


def load_visible(session: Session, user: User, delivery_id: int) -> Delivery:
    """Entrega que o usuário pode ver; senão 404 (não revelamos que ela existe)."""
    delivery = find_delivery_for(session, user, delivery_id, SEE_ALL)
    if delivery is None:
        raise NotFound("Entrega não encontrada. Confira o número e tente de novo.")
    return delivery


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
