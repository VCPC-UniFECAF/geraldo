from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session

from app.clock import Clock, OffPeakWindow, get_clock, get_off_peak
from app.commands.errors import DeliveryError
from app.commands.next_task import NextTask
from app.commands.robot_event import RegisterRobotEvent
from app.db import get_session
from app.deps import require_roles
from app.events import Subject, get_events
from app.models import Role, User
from app.queries import delivery_out
from app.schemas import DeliveryOut, RobotEventIn, RobotTaskOut

router = APIRouter()


@router.post("/robot/next-task", response_model=RobotTaskOut, responses={204: {"description": "Fila vazia"}})
def next_task(
    user: User = Depends(require_roles(Role.robo)),
    session: Session = Depends(get_session),
    clock: Clock = Depends(get_clock),
    off_peak: OffPeakWindow = Depends(get_off_peak),
    events: Subject = Depends(get_events),
):
    dispatch = NextTask(session, clock, off_peak, events=events, actor=user.username).execute()
    if dispatch is None:
        return Response(status_code=204)
    return RobotTaskOut(
        **delivery_out(session, dispatch.delivery).model_dump(),
        origin_waypoint=dispatch.origin_waypoint,
        dest_waypoint=dispatch.dest_waypoint,
    )


@router.post("/robot/events", response_model=DeliveryOut)
def robot_event(
    body: RobotEventIn,
    user: User = Depends(require_roles(Role.robo)),
    session: Session = Depends(get_session),
    events: Subject = Depends(get_events),
) -> DeliveryOut:
    try:
        delivery = RegisterRobotEvent(session, body, events=events, actor=user.username).execute()
    except DeliveryError as err:
        raise HTTPException(status_code=err.status_code, detail=str(err))
    return delivery_out(session, delivery)
