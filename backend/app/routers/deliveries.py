from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.commands.create_delivery import CreateDelivery, DeliveryError
from app.db import get_session
from app.deps import get_current_user, require_roles
from app.events import Subject, get_events
from app.models import Role, User
from app.queries import SEE_ALL, delivery_out, find_delivery_for, list_deliveries_for
from app.schemas import DeliveryCreate, DeliveryOut

router = APIRouter()
READ_ONE = (*SEE_ALL, Role.robo)  # o robô só consulta uma entrega, para esperar o ENTREGUE (robot-protocol.md, seção 7)


@router.post("/deliveries", response_model=DeliveryOut, status_code=201)
def create_delivery(
    body: DeliveryCreate,
    user: User = Depends(require_roles(Role.medico, Role.enfermeiro, Role.farmaceutico, Role.admin)),
    session: Session = Depends(get_session),
    events: Subject = Depends(get_events),
) -> DeliveryOut:
    try:
        delivery = CreateDelivery(session, user, body, events=events).execute()
    except DeliveryError as err:
        raise HTTPException(status_code=err.status_code, detail=str(err))
    return delivery_out(session, delivery)


@router.get("/deliveries", response_model=list[DeliveryOut])
def list_deliveries(user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    return [delivery_out(session, d) for d in list_deliveries_for(session, user)]


@router.get("/deliveries/{delivery_id}", response_model=DeliveryOut)
def get_delivery(delivery_id: int, user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    delivery = find_delivery_for(session, user, delivery_id, READ_ONE)
    if delivery is None:
        raise HTTPException(status_code=404, detail="Entrega não encontrada.")
    return delivery_out(session, delivery)
