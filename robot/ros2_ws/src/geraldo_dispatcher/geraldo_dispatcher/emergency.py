import threading

from .ports import BackendPort

TOPIC, BACKEND = "topic", "backend"


class EmergencyStop:
    """Bandeira da parada de emergência, junção de fontes: o tópico /geraldo/estop e o backend (painel web).

    O robô está parado se QUALQUER fonte estiver ligada; só sai da parada com todas desligadas. O ROS e o relógio
    de consulta ligam e desligam as fontes (outras threads); o dispatcher só consulta `active`.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sources: dict[str, bool] = {}

    @property
    def active(self) -> bool:
        with self._lock:
            return any(self._sources.values())

    def set_source(self, source: str, active: bool) -> None:
        with self._lock:
            self._sources[source] = active

    def engage(self) -> None:  # o tópico /geraldo/estop
        self.set_source(TOPIC, True)

    def release(self) -> None:
        self.set_source(TOPIC, False)


class BackendEstopPoller:
    """A cada `poll()` (1 s) pergunta ao backend se o painel acionou a emergência e atualiza a fonte `backend`.

    Se a consulta falha, vale o último valor conhecido: um backend que cai não libera nem aciona o robô sozinho.
    """

    def __init__(self, backend: BackendPort, estop: EmergencyStop, log=print) -> None:
        self.backend, self.estop, self.log = backend, estop, log

    def poll(self) -> None:
        try:
            active = self.backend.estop_active()
        except Exception as err:  # qualquer falha (rede, 401, corpo estranho) mantém o valor; a thread não pode morrer
            self.log(f"emergência do backend não consultada ({err}); mantendo o último valor")
            return
        self.estop.set_source(BACKEND, active)
