from sqlmodel import Session, select

from app.models import Delivery, DeliveryItem, DeliveryStatus, Item, Location, Role, Stock, User
from app.schemas import DeliveryItemIn, DeliveryOut, StockOut

SEE_ALL = (Role.admin, Role.farmaceutico)


def delivery_lines(session: Session, delivery: Delivery) -> list[DeliveryItem]:
    return list(session.exec(select(DeliveryItem).where(DeliveryItem.delivery_id == delivery.id).order_by(DeliveryItem.id)).all())


def delivery_out(session: Session, delivery: Delivery) -> DeliveryOut:
    items = delivery_lines(session, delivery)
    return DeliveryOut(
        id=delivery.id,
        origin_id=delivery.origin_id,
        dest_id=delivery.dest_id,
        items=[DeliveryItemIn(item_id=i.item_id, quantity=i.quantity) for i in items],
        priority=delivery.priority,
        status=delivery.status,
        requested_by=delivery.requested_by,
        created_at=delivery.created_at,
    )


def list_deliveries_for(session: Session, user: User) -> list[Delivery]:
    query = select(Delivery).order_by(Delivery.id)
    if user.role not in SEE_ALL:
        query = query.where(Delivery.requested_by == user.id)
    return list(session.exec(query).all())


def find_delivery_for(session: Session, user: User, delivery_id: int, see_all: tuple[Role, ...]) -> Delivery | None:
    delivery = session.get(Delivery, delivery_id)
    if delivery is None or (user.role not in see_all and delivery.requested_by != user.id):
        return None
    return delivery


def list_locations(session: Session) -> list[Location]:
    return list(session.exec(select(Location).order_by(Location.id)).all())


def list_stock(session: Session, location_id: str | None = None) -> list[StockOut]:
    query = select(Stock, Item).join(Item, Item.id == Stock.item_id).order_by(Stock.location_id, Stock.item_id)
    if location_id:
        query = query.where(Stock.location_id == location_id)
    return [
        StockOut(location_id=s.location_id, item_id=s.item_id, item_name=i.name, quantity=s.quantity, reserved=s.reserved, minimum=s.minimum)
        for s, i in session.exec(query).all()
    ]


def find_user_by_username(session: Session, username: str) -> User | None:
    return session.exec(select(User).where(User.username == username)).first()


def list_queued_deliveries(session: Session) -> list[Delivery]:
    return list(session.exec(select(Delivery).where(Delivery.status == DeliveryStatus.NA_FILA).order_by(Delivery.id)).all())


def waypoint_of(session: Session, location_id: str) -> str | None:
    location = session.get(Location, location_id)
    return location.waypoint if location else None
