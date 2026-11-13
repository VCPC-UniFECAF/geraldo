from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.commands.create_delivery import CreateDelivery, DeliveryError
from app.db import get_session
from app.deps import get_current_user, require_roles
from app.models import Delivery, Role, User
from app.queries import delivery_out
from app.schemas import DeliveryCreate, DeliveryOut

router = APIRouter()
SEE_ALL = (Role.admin, Role.farmaceutico)
READ_ONE = (*SEE_ALL, Role.robo)  # o robô só consulta uma entrega, para esperar o ENTREGUE (robot-protocol.md, seção 7)


@router.post("/deliveries", response_model=DeliveryOut, status_code=201)
def create_delivery(
    body: DeliveryCreate,
    user: User = Depends(require_roles(Role.medico, Role.enfermeiro, Role.farmaceutico, Role.admin)),
    session: Session = Depends(get_session),
) -> DeliveryOut:
    try:
        delivery = CreateDelivery(session, user, body).execute()
    except DeliveryError as err:
        raise HTTPException(status_code=err.status_code, detail=str(err))
    return delivery_out(session, delivery)


@router.get("/deliveries", response_model=list[DeliveryOut])
def list_deliveries(user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    query = select(Delivery).order_by(Delivery.id)
    if user.role not in SEE_ALL:
        query = query.where(Delivery.requested_by == user.id)
    return [delivery_out(session, d) for d in session.exec(query).all()]


@router.get("/deliveries/{delivery_id}", response_model=DeliveryOut)
def get_delivery(delivery_id: int, user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    delivery = session.get(Delivery, delivery_id)
    if delivery is None or (user.role not in READ_ONE and delivery.requested_by != user.id):
        raise HTTPException(status_code=404, detail="Entrega não encontrada.")
    return delivery_out(session, delivery)
