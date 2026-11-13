from sqlmodel import Session, select

from app.models import Delivery, DeliveryItem
from app.schemas import DeliveryItemIn, DeliveryOut


def delivery_out(session: Session, delivery: Delivery) -> DeliveryOut:
    items = session.exec(select(DeliveryItem).where(DeliveryItem.delivery_id == delivery.id).order_by(DeliveryItem.id)).all()
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
