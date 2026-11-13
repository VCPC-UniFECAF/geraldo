from abc import ABC, abstractmethod

from .profiles import NavProfile
from .waypoints import Pose


class BackendError(RuntimeError):
    """O backend recusou o pedido (status HTTP em `.status`) ou não respondeu (`.status` é None)."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class BackendPort(ABC):  # porta: tudo o que o dispatcher precisa do backend (ISP)
    @abstractmethod
    def next_task(self) -> dict | None:
        """Próxima entrega da fila, ou None se não há nenhuma."""

    @abstractmethod
    def send_event(self, delivery_id: int, event: str, reason: str | None = None) -> bool:
        """Avisa o backend (LOADED, ARRIVED, UNLOCKED, FAILED). False se ele recusou o evento (409)."""

    @abstractmethod
    def delivery_status(self, delivery_id: int) -> str:
        """Status atual da entrega (DeliveryStatus do contrato)."""


class TelemetryPort(ABC):  # porta: só o que a telemetria precisa
    @abstractmethod
    def send_telemetry(self, body: dict) -> None:
        """Envia o corpo de Telemetry ao backend."""


class Navigator(ABC):  # porta: tudo o que o dispatcher precisa da navegação
    @abstractmethod
    def go_to(self, pose: Pose) -> bool:
        """Leva o robô até a pose. True se chegou."""


class NavigationTuner(ABC):  # porta: ajusta a navegação para a prioridade da entrega
    @abstractmethod
    def apply(self, profile: NavProfile) -> None:
        """Aplica velocidade máxima e raio de inflação do perfil."""
