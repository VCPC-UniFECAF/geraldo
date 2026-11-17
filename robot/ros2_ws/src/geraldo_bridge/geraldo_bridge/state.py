import threading
import time
from collections.abc import Callable
from datetime import datetime, timezone

from .convert import RANGE_NAMES, closest_range, scan_to_map_points


class BridgeState:
    """Último valor de cada tópico que a ponte assina. As mensagens chegam na thread do rclpy e o servidor lê em outra."""

    STALE_AFTER_S = 3.0  # sem nenhuma mensagem há mais que isso: a simulação não está falando

    def __init__(
        self,
        clock: Callable[[], float] = time.monotonic,
        now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self._lock = threading.Lock()
        self._clock, self._now = clock, now
        self._robot_state: str | None = None
        self._battery: float | None = None
        self._pose: dict | None = None
        self._route: list[dict] = []
        self._scan: list[dict] = []
        self._ranges: dict[str, float | None] = {name: None for name in RANGE_NAMES}
        self._estop = False
        self._last_message: float | None = None

    def _heard(self) -> None:
        self._last_message = self._clock()

    def update_robot_state(self, value: str) -> None:
        with self._lock:
            self._robot_state = value
            self._heard()

    def update_battery(self, percent: float) -> None:
        with self._lock:
            self._battery = percent
            self._heard()

    def update_pose(self, pose: dict) -> None:
        with self._lock:
            self._pose = pose
            self._heard()

    def update_route(self, route: list[dict]) -> None:
        with self._lock:
            self._route = route
            self._heard()

    def update_scan(self, scan: dict) -> None:
        with self._lock:
            self._scan = scan_to_map_points(scan, self._pose) if self._pose else []
            self._heard()

    def update_range(self, name: str, scan: dict) -> None:
        if name not in self._ranges:
            raise ValueError(f"Sensor de alcance desconhecido: {name}. Use um de {', '.join(RANGE_NAMES)}.")
        with self._lock:
            self._ranges[name] = closest_range(scan)
            self._heard()

    def update_estop(self, active: bool) -> None:
        with self._lock:
            self._estop = active

    def snapshot(self) -> dict:
        """Corpo de `GET /snapshot` e de cada mensagem de `WS /ws/sim`."""
        with self._lock:
            stale = self._last_message is None or self._clock() - self._last_message > self.STALE_AFTER_S
            return {
                "robot_state": self._robot_state,
                "pose": dict(self._pose) if self._pose else None,
                "battery": self._battery,
                "route": list(self._route),
                "scan": list(self._scan),
                "ranges": dict(self._ranges),
                "estop": self._estop,
                "stale": stale,
                "updated_at": self._now().isoformat(),
            }
