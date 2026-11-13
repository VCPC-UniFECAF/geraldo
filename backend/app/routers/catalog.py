from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db import get_session
from app.deps import get_current_user
from app.models import User
from app.queries import list_locations, list_stock
from app.schemas import LocationOut, StockOut

router = APIRouter()


@router.get("/locations", response_model=list[LocationOut])
def locations(_: User = Depends(get_current_user), session: Session = Depends(get_session)):
    return list_locations(session)


@router.get("/stock", response_model=list[StockOut])
def stock(location_id: str | None = None, _: User = Depends(get_current_user), session: Session = Depends(get_session)):
    return list_stock(session, location_id)
