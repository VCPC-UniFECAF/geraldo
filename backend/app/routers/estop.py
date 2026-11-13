from fastapi import APIRouter, Depends, Response

from app.deps import require_roles
from app.estop import EstopStore, get_estop
from app.events import EstopChanged, Subject, get_events
from app.models import Role, User
from app.schemas import EstopState

router = APIRouter()


@router.post("/robot/estop", status_code=204)
def set_estop(
    body: EstopState,
    user: User = Depends(require_roles(Role.admin, Role.farmaceutico)),
    store: EstopStore = Depends(get_estop),
    events: Subject = Depends(get_events),
) -> Response:
    store.active = body.active
    events.notify(EstopChanged(body.active, user.username))
    return Response(status_code=204)


@router.get("/robot/estop", response_model=EstopState)
def read_estop(_: User = Depends(require_roles(Role.robo)), store: EstopStore = Depends(get_estop)) -> EstopState:
    return EstopState(active=store.active)
