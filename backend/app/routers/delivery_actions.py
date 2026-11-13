from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.commands.cancel_delivery import CancelDelivery
from app.commands.errors import DeliveryError
from app.db import get_session
from app.deps import require_roles
from app.events import Subject, get_events
from app.models import Role, User
from app.queries import delivery_out
from app.schemas import DeliveryOut

router = APIRouter()
REQUESTERS = (Role.medico, Role.enfermeiro, Role.farmaceutico, Role.admin)


@router.post("/deliveries/{delivery_id}/cancel", response_model=DeliveryOut)
def cancel_delivery(
    delivery_id: int,
    user: User = Depends(require_roles(*REQUESTERS)),
    session: Session = Depends(get_session),
    events: Subject = Depends(get_events),
) -> DeliveryOut:
    try:
        delivery = CancelDelivery(session, user, delivery_id, events=events).execute()
    except DeliveryError as err:
        raise HTTPException(status_code=err.status_code, detail=str(err))
    return delivery_out(session, delivery)
