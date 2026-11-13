from abc import ABC, abstractmethod

from .waypoints import Pose


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
