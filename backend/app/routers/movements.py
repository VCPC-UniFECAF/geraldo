from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db import get_session
from app.deps import get_current_user
from app.models import User
from app.queries import movements_for
from app.schemas import MovementOut

router = APIRouter()


@router.get("/movements", response_model=list[MovementOut])
def movements(
    delivery_id: int | None = None,
    location_id: str | None = None,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return movements_for(session, user, delivery_id=delivery_id, location_id=location_id)
