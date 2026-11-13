import sys
from pathlib import Path

import pytest

rclpy = pytest.importorskip("rclpy")
from rclpy.qos import DurabilityPolicy  # noqa: E402

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))

from geraldo_dispatcher.emergency import EmergencyStop  # noqa: E402
from geraldo_dispatcher.node import GeraldoStateNode  # noqa: E402
from geraldo_dispatcher.obstacles import StaticMap  # noqa: E402


def test_the_pose_subscription_gets_the_last_amcl_pose_even_with_the_robot_standing_still():
    # o AMCL só publica de novo quando o robô anda; o último /amcl_pose fica guardado (TRANSIENT_LOCAL)
    rclpy.init()
    node = GeraldoStateNode(EmergencyStop(), StaticMap(1, 1, 0.05, (0.0, 0.0), b"\0"))
    try:
        sub = next(s for s in node.subscriptions if s.topic_name == "/amcl_pose")
        assert sub.qos_profile.durability == DurabilityPolicy.TRANSIENT_LOCAL
    finally:
        node.destroy_node()
        rclpy.shutdown()
