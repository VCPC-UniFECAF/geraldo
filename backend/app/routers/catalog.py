from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.db import get_session
from app.deps import get_current_user
from app.models import Item, Location, Stock, User
from app.schemas import LocationOut, StockOut

router = APIRouter()


@router.get("/locations", response_model=list[LocationOut])
def locations(_: User = Depends(get_current_user), session: Session = Depends(get_session)):
    return session.exec(select(Location).order_by(Location.id)).all()


@router.get("/stock", response_model=list[StockOut])
def stock(location_id: str | None = None, _: User = Depends(get_current_user), session: Session = Depends(get_session)):
    query = select(Stock, Item).join(Item, Item.id == Stock.item_id).order_by(Stock.location_id, Stock.item_id)
    if location_id:
        query = query.where(Stock.location_id == location_id)
    return [
        StockOut(location_id=s.location_id, item_id=s.item_id, item_name=i.name, quantity=s.quantity, reserved=s.reserved, minimum=s.minimum)
        for s, i in session.exec(query).all()
    ]
