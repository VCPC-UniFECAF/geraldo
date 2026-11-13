from fastapi import APIRouter, Depends, Response
from sqlmodel import Session

from app.clock import Clock, OffPeakWindow, get_clock, get_off_peak
from app.commands.next_task import NextTask
from app.db import get_session
from app.deps import require_roles
from app.events import Subject, get_events
from app.models import Role, User
from app.queries import delivery_out
from app.schemas import RobotTaskOut

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
