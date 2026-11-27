from geraldo_bridge.gazebo_gui import GuiError
from geraldo_bridge.ports import RosPort
from geraldo_bridge.state import BridgeState


class FakeRosPort(RosPort):  # substituto de teste do rclpy (LSP): guarda o que a ponte publicou
    def __init__(self) -> None:
        self.state: BridgeState | None = None
        self.estop_published: list[bool] = []
        self.stopped = False

    def start(self, state: BridgeState) -> None:
        self.state = state

    def publish_estop(self, active: bool) -> None:
        self.estop_published.append(active)

    def stop(self) -> None:
        self.stopped = True


class FakeGui:  # mesma interface do GazeboGui, sem processo
    def __init__(self, pid: int = 4321, error: str | None = None) -> None:
        self.pid, self.error, self.opened, self.closed = pid, error, 0, False

    def open(self) -> tuple[int, bool]:
        if self.error:
            raise GuiError(self.error)
        self.opened += 1
        return self.pid, self.opened > 1

    def close(self) -> None:
        self.closed = True
