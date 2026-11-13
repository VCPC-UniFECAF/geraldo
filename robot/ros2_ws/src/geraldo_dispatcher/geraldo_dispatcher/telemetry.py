import math
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from .ports import TelemetryPort
from .states import State, StateMachine
from .waypoints import Pose

TRAVELLING = {State.A_CAMINHO, State.VOLTANDO}


@dataclass
class BatteryModel:
    """Bateria virtual (a simulação não tem bateria): gasta andando, gasta pouco esperando, recarrega parada na base."""

    level: float = 100.0  # porcentagem, 0 a 100
    drain_per_s: float = 0.05
    idle_drain_per_s: float = 0.005
    recharge_per_s: float = 0.5

    def step(self, state: State, dt: float) -> float:
        if state is State.IDLE:
            self.level += self.recharge_per_s * dt
        elif state in TRAVELLING:
            self.level -= self.drain_per_s * dt
        else:
            self.level -= self.idle_drain_per_s * dt
        self.level = min(100.0, max(0.0, self.level))
        return self.level


def build_telemetry(state: State, pose: Pose, battery: float, delivery_id: int | None,
                    route: list[tuple[float, float]], obstacles: list[tuple[float, float, float]], now: datetime) -> dict:
    """Corpo de `Telemetry` do contrato (docs/contracts/openapi.yaml)."""
    return {
        "robot_state": state.value,
        "pose": {"x": pose.x, "y": pose.y, "yaw": pose.yaw},
        "battery": round(battery, 1),
        "delivery_id": delivery_id,
        "route": [{"x": x, "y": y} for x, y in route],
        "obstacles": [{"x": x, "y": y, "radius": r} for x, y, r in obstacles],
        "updated_at": now.isoformat(),
    }


def downsample(points: list, limit: int = 50) -> list:
    """No máximo `limit` pontos, espaçados por igual, sempre com o primeiro e o último."""
    if len(points) <= limit:
        return list(points)
    step = (len(points) - 1) / (limit - 1)
    return [points[round(i * step)] for i in range(limit)]


def yaw_from_quaternion(z: float, w: float) -> float:
    """Yaw (radianos) de uma rotação em torno de Z."""
    return math.atan2(2 * w * z, 1 - 2 * z * z)


class TelemetryReporter:
    """A cada `tick`: gasta a bateria, publica o nível e manda a telemetria ao backend, sem nunca derrubar o robô."""

    def __init__(self, sink: TelemetryPort, machine: StateMachine, battery: BatteryModel,
                 pose_source: Callable[[], Pose | None], route_source: Callable[[], list],
                 delivery_source: Callable[[], int | None], on_battery: Callable[[float], None],
                 clock: Callable[[], datetime], log=print) -> None:
        self.sink, self.machine, self.battery = sink, machine, battery
        self.pose_source, self.route_source, self.delivery_source = pose_source, route_source, delivery_source
        self.on_battery, self.clock, self.log = on_battery, clock, log

    def tick(self, dt: float) -> None:
        level = self.battery.step(self.machine.state, dt)
        self.on_battery(level)
        pose = self.pose_source()
        if pose is None:
            return
        body = build_telemetry(self.machine.state, pose, level, self.delivery_source(), self.route_source(), [], self.clock())
        try:
            self.sink.send_telemetry(body)
        except Exception as err:  # a telemetria é secundária: falha de rede não pode parar a entrega
            self.log(f"telemetria não enviada: {err}")
