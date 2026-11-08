import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

URDF = Path(__file__).resolve().parents[1] / "urdf" / "geraldo.urdf.xacro"


@pytest.fixture(scope="module")
def robot():
    out = subprocess.run(["xacro", str(URDF)], check=True, capture_output=True, text=True).stdout
    return ET.fromstring(out)


def joints(robot):
    return {j.get("name"): j for j in robot.findall("joint")}


def xyz(el):
    return [float(v) for v in el.find("origin").get("xyz").split()]


def test_links_and_joints_exist(robot):
    assert {l.get("name") for l in robot.findall("link")} == {
        "base_link", "wheel_left_link", "wheel_right_link", "caster_link", "lidar_link",
    }
    assert set(joints(robot)) == {"wheel_left_joint", "wheel_right_joint", "caster_joint", "lidar_joint"}


def test_wheels_are_continuous_around_y(robot):
    for name in ("wheel_left_joint", "wheel_right_joint"):
        j = joints(robot)[name]
        assert j.get("type") == "continuous"
        assert j.find("axis").get("xyz").split() == ["0", "1", "0"]


def test_wheel_layout_matches_the_spec(robot):
    left, right = (xyz(joints(robot)[n]) for n in ("wheel_left_joint", "wheel_right_joint"))
    assert left == pytest.approx([0.10, 0.225, 0.10])
    assert right == pytest.approx([0.10, -0.225, 0.10])


def test_diff_drive_plugin_matches_the_joints(robot):
    plugin = next(
        p for g in robot.findall("gazebo") for p in g.findall("plugin") if p.get("filename") == "gz-sim-diff-drive-system"
    )
    separation = float(plugin.find("wheel_separation").text)
    radius = float(plugin.find("wheel_radius").text)
    left, right = (xyz(joints(robot)[n]) for n in ("wheel_left_joint", "wheel_right_joint"))
    assert separation == pytest.approx(left[1] - right[1])       # 0,45 m
    assert radius == pytest.approx(left[2])                      # roda apoiada no chão
    assert plugin.find("topic").text == "/cmd_vel"
    assert plugin.find("odom_topic").text == "/odom"
    assert plugin.find("frame_id").text == "odom"
    assert plugin.find("child_frame_id").text == "base_link"


def test_lidar_sensor_publishes_scan(robot):
    sensor = next(s for g in robot.findall("gazebo") if g.get("reference") == "lidar_link" for s in g.findall("sensor"))
    assert sensor.get("type") == "gpu_lidar"
    assert sensor.find("topic").text == "scan"
    assert sensor.find("gz_frame_id").text == "lidar_link"


def test_collision_footprint_is_70_by_50(robot):
    base = next(l for l in robot.findall("link") if l.get("name") == "base_link")
    sizes = [[float(v) for v in c.find("geometry/box").get("size").split()] for c in base.findall("collision")]
    assert [0.70, 0.50, 0.20] in sizes


def test_mesh_uri_points_to_the_package(robot):
    base = next(l for l in robot.findall("link") if l.get("name") == "base_link")
    assert base.find("visual/geometry/mesh").get("filename") == "package://geraldo_description/meshes/geraldo_body.obj"
