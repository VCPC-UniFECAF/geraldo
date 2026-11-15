import time

import pytest

rclpy = pytest.importorskip("rclpy", reason="precisa do ROS carregado (source /opt/ros/jazzy/setup.bash)")

from geraldo_bridge.ros_adapter import RclpyRosPort  # noqa: E402
from geraldo_bridge.state import BridgeState  # noqa: E402


def test_the_adapter_publishes_estop_on_the_topic_and_stops_cleanly():
    from std_msgs.msg import Bool

    port = RclpyRosPort()
    port.start(BridgeState())
    got = []
    try:
        # o nó da própria ponte serve de ouvinte: o executor dela já está girando
        port._node.create_subscription(Bool, "/geraldo/estop", lambda m: got.append(m.data), 10)
        port.publish_estop(True)
        deadline = time.monotonic() + 5
        while not got and time.monotonic() < deadline:
            time.sleep(0.05)
        assert got and got[0] is True
    finally:
        port.stop()
    assert port._rclpy is None
