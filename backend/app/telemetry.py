from datetime import datetime, timezone

from app.clock import Clock, SystemClock
from app.events import Subject
from app.schemas import PoseIn, RobotState, TelemetryIn, TelemetryOut

NEVER = datetime(1970, 1, 1, tzinfo=timezone.utc)


class TelemetryHub(Subject):  # OBSERVER: o POST do robô publica; cada WebSocket aberto é um assinante
    """Guarda o último estado do robô (só em memória) e avisa quem assina a cada novo."""

    def __init__(self, clock: Clock | None = None) -> None:
        super().__init__()
        self._clock = clock or SystemClock()
        # antes da primeira telemetria: robô parado, bateria 0 e updated_at em 1970 (o painel lê isso como "sem sinal")
        self._latest = TelemetryOut(robot_state=RobotState.IDLE, pose=PoseIn(x=0, y=0, yaw=0), battery=0, updated_at=NEVER)

    def latest(self) -> TelemetryOut:
        return self._latest

    def publish(self, telemetry: TelemetryIn) -> TelemetryOut:
        data = telemetry.model_dump(exclude={"updated_at"})
        self._latest = TelemetryOut(**data, updated_at=self._clock.now().astimezone(timezone.utc))
        self.notify(self._latest)
        return self._latest


hub = TelemetryHub()


def get_hub() -> TelemetryHub:
    return hub
