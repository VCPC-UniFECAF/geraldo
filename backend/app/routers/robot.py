from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session, select

from app.db import get_session
from app.deps import require_roles
from app.models import Delivery, DeliveryStatus, Location, Role, User
from app.priority import policy_for
from app.queries import delivery_out
from app.schemas import RobotTaskOut

router = APIRouter()


@router.post("/robot/next-task", response_model=RobotTaskOut, responses={204: {"description": "Fila vazia"}})
def next_task(_: User = Depends(require_roles(Role.robo)), session: Session = Depends(get_session)):
    queued = session.exec(select(Delivery).where(Delivery.status == DeliveryStatus.NA_FILA)).all()
    if not queued:
        return Response(status_code=204)
    delivery = min(queued, key=lambda d: (policy_for(d.priority).rank, d.id))
    origin, dest = session.get(Location, delivery.origin_id), session.get(Location, delivery.dest_id)
    if origin is None or dest is None or origin.waypoint is None or dest.waypoint is None:
        raise HTTPException(status_code=409, detail="A entrega aponta para um local sem ponto de parada. Corrija os locais.")
    delivery.status = DeliveryStatus.EM_ROTA
    session.add(delivery)
    session.commit()
    session.refresh(delivery)
    return RobotTaskOut(**delivery_out(session, delivery).model_dump(), origin_waypoint=origin.waypoint, dest_waypoint=dest.waypoint)
