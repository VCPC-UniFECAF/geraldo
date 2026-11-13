import time

from .emergency import EmergencyStop
from .ports import BackendPort, NavigationTuner, Navigator
from .profiles import DEFAULT_PROFILE, profile_for
from .states import State, StateMachine
from .waypoints import Pose


class Dispatcher:
    """Conduz uma entrega: origem, carga, destino, espera do recebimento e volta à base.

    Só conhece as portas `BackendPort` e `Navigator` (DIP) e a `StateMachine`: o Nav2, o HTTP e o relógio entram
    pelo construtor. Cada passo muda o estado e avisa o backend com o evento do contrato.
    """

    def __init__(self, backend: BackendPort, poses: dict[str, Pose], navigator: Navigator,
                 machine: StateMachine | None = None, home: str = "base_robo", sleep=time.sleep,
                 poll_interval: float = 2.0, receipt_timeout: float = 300.0,
                 estop: EmergencyStop | None = None, estop_poll: float = 0.5,
                 tuner: NavigationTuner | None = None, log=print) -> None:
        self.backend, self.poses, self.navigator, self.tuner = backend, poses, navigator, tuner
        self.machine = machine or StateMachine()
        self.home, self.sleep, self.log = home, sleep, log
        self.poll_interval, self.receipt_timeout = poll_interval, receipt_timeout
        self.estop, self.estop_poll = estop or EmergencyStop(), estop_poll
        self.delivery_id: int | None = None

    def run_once(self) -> dict | None:
        self.hold_if_stopped()
        task = self.backend.next_task()
        if task is None:
            return None
        for waypoint in (task["origin_waypoint"], task["dest_waypoint"], self.home):
            self._pose(waypoint)
        if self.tuner is not None:
            self.tuner.apply(profile_for(task["priority"]))
        self.delivery_id = task["id"]
        failure = self._deliver(task)
        if failure is not None:
            self.backend.send_event(task["id"], "FAILED", failure[1])
        self.machine.go(State.VOLTANDO)
        self._go(self.home)
        self.machine.go(State.IDLE)
        self.delivery_id = None
        if self.tuner is not None:
            self.tuner.apply(DEFAULT_PROFILE)
        if failure is None:
            return {**task, "result": "ENTREGUE"}
        return {**task, "result": "FALHOU", "failed_at": failure[0], "reason": failure[1]}

    def _deliver(self, task: dict) -> tuple[str, str] | None:
        """Faz a entrega. Devolve None se deu certo, ou (waypoint onde parou, motivo)."""
        origin, dest = task["origin_waypoint"], task["dest_waypoint"]
        self.machine.go(State.A_CAMINHO)
        if not self._go(origin):
            return origin, "não chegou à origem"
        self.machine.go(State.CARREGANDO)
        self.backend.send_event(task["id"], "LOADED")
        self.machine.go(State.A_CAMINHO)
        if not self._go(dest):
            return dest, "não chegou ao destino"
        self.machine.go(State.CHEGOU)
        self.backend.send_event(task["id"], "ARRIVED")
        self.machine.go(State.AGUARDANDO_RETIRADA)
        reason = self._wait_for_receipt(task["id"])
        if reason is not None:
            return dest, reason
        self.backend.send_event(task["id"], "UNLOCKED")
        return None

    def _wait_for_receipt(self, delivery_id: int) -> str | None:
        """Espera o solicitante confirmar o recebimento. Devolve None se confirmou, ou o motivo da falha."""
        waited = 0.0
        while True:
            self.hold_if_stopped()
            status = self.backend.delivery_status(delivery_id)
            if status == "ENTREGUE":
                return None
            if status in ("CANCELADA", "FALHOU"):
                return f"entrega {status.lower()}"
            if waited >= self.receipt_timeout:
                return "recebimento não confirmado a tempo"
            self.sleep(self.poll_interval)
            waited += self.poll_interval

    def _pose(self, waypoint: str) -> Pose:
        if waypoint not in self.poses:
            raise KeyError(f"Waypoint desconhecido: {waypoint}. Gere o hospital de novo (robot/hospital/gen_hospital.py).")
        return self.poses[waypoint]

    def hold_if_stopped(self) -> bool:
        """Com a emergência acionada, para em PARADA_EMERGENCIA até ela ser liberada e volta ao estado anterior."""
        if not self.estop.active:
            return False
        self.log("parada de emergência acionada: robô parado")
        self.machine.stop()
        while self.estop.active:
            self.sleep(self.estop_poll)
        self.machine.resume()
        self.log("parada de emergência liberada: retomando")
        return True

    def _go(self, waypoint: str) -> bool:
        self.log(f"entrega {self.delivery_id}: indo para {waypoint}")
        pose = self._pose(waypoint)
        while True:
            self.hold_if_stopped()
            reached = self.navigator.go_to(pose)
            if reached or not self.estop.active:  # chegou, ou falhou de verdade (não foi a emergência que cortou a meta)
                break
        if not reached:
            self.log(f"entrega {self.delivery_id}: não chegou a {waypoint}")
        return reached
