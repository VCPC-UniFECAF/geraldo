import math
import sys
from pathlib import Path

import pytest

rclpy = pytest.importorskip("rclpy")
from geometry_msgs.msg import TransformStamped  # noqa: E402
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


def transform(parent: str, child: str, stamp_s: int, x: float, y: float = 0.0, yaw: float = 0.0) -> TransformStamped:
    msg = TransformStamped()
    msg.header.frame_id, msg.child_frame_id = parent, child
    msg.header.stamp.sec = stamp_s
    msg.transform.translation.x, msg.transform.translation.y = x, y
    msg.transform.rotation.z, msg.transform.rotation.w = math.sin(yaw / 2), math.cos(yaw / 2)
    return msg


def test_the_sensor_pose_comes_from_the_tf_at_the_instant_of_the_scan_not_from_the_latest_one():
    rclpy.init()
    node = GeraldoStateNode(EmergencyStop(), StaticMap(1, 1, 0.05, (0.0, 0.0), b"\0"))
    try:
        node.tf_buffer.set_transform_static(transform("map", "odom", 0, 1.0, 2.0), "teste")
        node.tf_buffer.set_transform(transform("odom", "lidar_link", 4, 0.0, yaw=math.pi / 2), "teste")
        node.tf_buffer.set_transform(transform("odom", "lidar_link", 6, 2.0, yaw=math.pi / 2), "teste")  # o robô andou depois
        sensor = node.sensor_pose_at("lidar_link", 5_000_000_000)  # o scan é do meio do caminho
        assert (sensor.x, sensor.y, sensor.yaw) == pytest.approx((2.0, 2.0, math.pi / 2), abs=1e-6)
    finally:
        node.destroy_node()
        rclpy.shutdown()


def test_there_is_no_sensor_pose_when_the_tf_does_not_cover_the_scan_instant():
    rclpy.init()
    node = GeraldoStateNode(EmergencyStop(), StaticMap(1, 1, 0.05, (0.0, 0.0), b"\0"))
    try:
        node.tf_buffer.set_transform_static(transform("map", "odom", 0, 0.0), "teste")
        node.tf_buffer.set_transform(transform("odom", "lidar_link", 4, 0.0), "teste")
        assert node.sensor_pose_at("lidar_link", 9_000_000_000) is None  # depois do último TF
        assert node.sensor_pose_at("lidar_link", 1_000_000_000) is None  # antes do primeiro TF
    finally:
        node.destroy_node()
        rclpy.shutdown()
