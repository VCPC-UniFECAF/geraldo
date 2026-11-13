from collections.abc import Callable
from dataclasses import dataclass

from sqlmodel import Session

from app.clock import Clock, OffPeakWindow
from app.events import DeliveryChanged, Subject
from app.models import Delivery, DeliveryStatus, Priority
from app.stock_lock import serialized, stock_lock
from app.priority import PriorityPolicy, policy_for
from app.queries import list_queued_deliveries, waypoint_of


@dataclass(frozen=True)
class Dispatch:
    delivery: Delivery
    origin_waypoint: str
    dest_waypoint: str


# COMMAND
class NextTask:
    """Comando PróximaTarefa: escolhe a entrega que o robô leva agora e a coloca EM_ROTA.

    Ordem: crítica, média, rotina; dentro da prioridade, a mais antiga (menor id). A rotina só
    sai em baixo pico: o robô não consegue devolver uma tarefa que já saiu da fila.
    """

    def __init__(
        self,
        session: Session,
        clock: Clock,
        off_peak: OffPeakWindow,
        *,
        policy_for: Callable[[Priority], PriorityPolicy] = policy_for,
        events: Subject | None = None,
        actor: str = "robo",
        lock=stock_lock,
    ) -> None:
        self._session = session
        self._clock = clock
        self._off_peak = off_peak
        self._policy_for = policy_for
        self._events = events if events is not None else Subject()
        self._actor = actor
        self._lock = lock

    @serialized
    def execute(self) -> Dispatch | None:
        off_peak_now = self._off_peak.contains(self._clock.now())
        candidates = []
        for delivery in list_queued_deliveries(self._session):
            policy = self._policy_for(delivery.priority)
            origin = waypoint_of(self._session, delivery.origin_id)
            dest = waypoint_of(self._session, delivery.dest_id)
            if origin and dest and (off_peak_now or not policy.off_peak_only):
                candidates.append((policy.rank, delivery.id, delivery, origin, dest))
        if not candidates:
            return None
        _, _, delivery, origin_waypoint, dest_waypoint = min(candidates, key=lambda c: c[:2])
        delivery.status = DeliveryStatus.EM_ROTA
        self._session.add(delivery)
        self._session.commit()
        self._session.refresh(delivery)
        self._events.notify(DeliveryChanged(delivery.id, DeliveryStatus.NA_FILA, delivery.status, self._actor))
        return Dispatch(delivery, origin_waypoint, dest_waypoint)
