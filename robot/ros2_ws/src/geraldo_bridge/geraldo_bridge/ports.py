from abc import ABC, abstractmethod

from .state import BridgeState


class RosPort(ABC):  # PORTA: o servidor só conhece isto; o rclpy fica atrás do adapter e os testes usam o FakeRosPort
    @abstractmethod
    def start(self, state: BridgeState) -> None:
        """Assina os tópicos e passa cada mensagem, já convertida, para os métodos `update_*` do `state`."""

    @abstractmethod
    def publish_estop(self, active: bool) -> None:
        """Publica `std_msgs/Bool` em /geraldo/estop (`true` para o robô, `false` libera)."""

    @abstractmethod
    def stop(self) -> None:
        """Encerra as assinaturas e solta o rclpy."""
