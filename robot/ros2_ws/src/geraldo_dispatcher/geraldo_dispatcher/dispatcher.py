from .ports import BackendPort, Navigator
from .waypoints import Pose


class Dispatcher:
    """Pega a próxima entrega da fila e leva o robô à origem e depois ao destino.

    Só conhece as portas `BackendPort` e `Navigator` (DIP): o Nav2 e o HTTP entram pelo construtor.
    """

    def __init__(self, backend: BackendPort, poses: dict[str, Pose], navigator: Navigator, log=print) -> None:
        self.backend, self.poses, self.navigator, self.log = backend, poses, navigator, log

    def run_once(self) -> dict | None:
        task = self.backend.next_task()
        if task is None:
            return None
        for key in ("origin_waypoint", "dest_waypoint"):
            waypoint = task[key]
            if waypoint not in self.poses:
                raise KeyError(f"Waypoint desconhecido: {waypoint}. Gere o hospital de novo (robot/hospital/gen_hospital.py).")
            self.log(f"entrega {task['id']}: indo para {waypoint}")
            if not self.navigator.go_to(self.poses[waypoint]):
                self.log(f"entrega {task['id']}: não chegou a {waypoint}")
                return {**task, "result": "FALHOU", "failed_at": waypoint}
        self.log(f"entrega {task['id']}: chegou ao destino")
        return {**task, "result": "CHEGOU"}
