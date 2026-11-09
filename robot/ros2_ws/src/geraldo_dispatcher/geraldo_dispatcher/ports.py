from abc import ABC, abstractmethod

from .waypoints import Pose


class BackendPort(ABC):  # porta: tudo o que o dispatcher precisa do backend (ISP)
    @abstractmethod
    def next_task(self) -> dict | None:
        """Próxima entrega da fila, ou None se não há nenhuma."""


class Navigator(ABC):  # porta: tudo o que o dispatcher precisa da navegação
    @abstractmethod
    def go_to(self, pose: Pose) -> bool:
        """Leva o robô até a pose. True se chegou."""
