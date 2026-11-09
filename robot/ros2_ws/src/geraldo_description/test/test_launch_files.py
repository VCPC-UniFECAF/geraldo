import ast
from pathlib import Path

import yaml

PKG = Path(__file__).resolve().parents[1]


def test_bridge_has_the_contract_topics():
    entries = yaml.safe_load((PKG / "config/bridge.yaml").read_text())
    by_topic = {e["ros_topic_name"]: e for e in entries}
    assert set(by_topic) == {"/clock", "/cmd_vel", "/odom", "/tf", "/scan"}
    assert by_topic["/cmd_vel"]["direction"] == "ROS_TO_GZ"
    assert by_topic["/cmd_vel"]["ros_type_name"] == "geometry_msgs/msg/Twist"
    assert by_topic["/scan"]["ros_type_name"] == "sensor_msgs/msg/LaserScan"
    assert by_topic["/tf"]["ros_type_name"] == "tf2_msgs/msg/TFMessage"


def test_launch_file_is_valid_python_and_declares_the_arguments():
    src = (PKG / "launch/sim.launch.py").read_text()
    ast.parse(src)
    for arg in ("headless", "x", "y", "yaw"):
        assert f'DeclareLaunchArgument("{arg}"' in src
    assert "generate_launch_description" in src


def test_gui_runs_on_x11_so_wayland_with_hybrid_gpu_does_not_crash_ogre():
    src = (PKG / "launch/sim.launch.py").read_text()
    assert 'SetEnvironmentVariable("QT_QPA_PLATFORM", "xcb"' in src
    assert 'SetEnvironmentVariable("EGL_PLATFORM", ""' in src
